import os
import time
import subprocess
import json
import uuid
from pathlib import Path
import azure.cognitiveservices.speech as speechsdk
import redis
import multiprocessing
from celery import shared_task, chord, group
from celery_config import celery
import shutil
from datetime import datetime

# 连接Redis
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

# 默认并行处理设置
DEFAULT_PARALLEL_THREADS = 10  # 默认使用10个并行线程
DEFAULT_SEGMENT_LENGTH = 60  # 默认60秒一段

def extract_audio_from_video(video_path, output_audio_path):
    """
    使用ffmpeg从视频文件中提取音频并转换为WAV格式
    
    Args:
        video_path: 视频文件路径
        output_audio_path: 输出音频文件路径
        
    Returns:
        bool: 是否成功提取
    """
    try:
        # 使用ffmpeg提取音频，转换为wav格式（16kHz采样率，单声道，PCM编码）
        cmd = [
            'ffmpeg', '-i', video_path, 
            '-acodec', 'pcm_s16le',    # PCM 16bit编码
            '-ar', '16000',            # 16kHz采样率
            '-ac', '1',                # 单声道
            output_audio_path,
            '-y'  # 覆盖已存在的文件
        ]
        
        # 执行命令
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            print(f"提取音频失败: {stderr.decode()}")
            return False
            
        return True
    except Exception as e:
        print(f"提取音频时发生错误: {str(e)}")
        return False

def convert_audio_to_wav(audio_path, output_path):
    """
    将任何音频格式转换为Azure Speech兼容的WAV格式
    
    Args:
        audio_path: 输入音频文件路径
        output_path: 输出WAV文件路径
        
    Returns:
        bool: 是否成功转换
    """
    try:
        # 转换为wav格式（16kHz采样率，单声道，PCM编码）
        cmd = [
            'ffmpeg', '-i', audio_path,
            '-acodec', 'pcm_s16le',    # PCM 16bit编码
            '-ar', '16000',            # 16kHz采样率
            '-ac', '1',                # 单声道
            output_path,
            '-y'  # 覆盖已存在的文件
        ]
        
        # 执行命令
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            print(f"音频转换失败: {stderr.decode()}")
            return False
            
        return True
    except Exception as e:
        print(f"音频转换时发生错误: {str(e)}")
        return False

def get_audio_duration(audio_path):
    """
    获取音频或视频文件的时长（秒）
    
    Args:
        audio_path: 音频或视频文件路径
        
    Returns:
        float: 时长（秒），如果失败则返回 0.0
    """
    try:
        cmd = [
            'ffprobe', 
            '-v', 'error', 
            '-show_entries', 'format=duration', 
            '-of', 'default=noprint_wrappers=1:nokey=1', 
            audio_path
        ]
        
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            print(f"获取时长失败 for {audio_path}: {stderr.decode()}")
            return 0.0
            
        duration_str = stdout.decode().strip()
        if not duration_str or duration_str == 'N/A':
            print(f"获取的时长无效 for {audio_path}: {duration_str}")
            return 0.0
        
        return float(duration_str)
    except Exception as e:
        print(f"获取时长时发生错误 for {audio_path}: {str(e)}")
        return 0.0

def split_audio_file(audio_path, output_dir, segment_length=DEFAULT_SEGMENT_LENGTH, max_segments=None):
    """
    将长音频文件分割成多个较小的片段
    
    Args:
        audio_path: 输入音频文件路径
        output_dir: 输出目录
        segment_length: 每个片段的长度（秒）
        max_segments: 最大分段数量（用于控制并行度）
        
    Returns:
        list: 分割后的音频片段路径列表
    """
    try:
        # 检查输入文件是否存在
        if not os.path.exists(audio_path):
            print(f"输入音频文件不存在: {audio_path}")
            return []
        
        # 使用绝对路径，避免路径问题
        audio_path = os.path.abspath(audio_path)
        output_dir = os.path.abspath(output_dir)
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        print(f"音频分段存储目录: {output_dir}")
        
        # 获取音频时长
        duration = get_audio_duration(audio_path)
        if duration <= 0:
            print(f"获取音频时长失败或音频为空: {audio_path}")
            return []
        
        print(f"原始音频时长: {duration}秒，计划分段长度: {segment_length}秒")
        
        # 动态调整分段大小，确保分段数不超过max_segments
        if max_segments and duration > segment_length * max_segments:
            # 计算需要的段长度，使得分段数量不超过max_segments
            segment_length = int(duration / max_segments) + 1
            print(f"调整段长度为 {segment_length} 秒以限制分段数不超过 {max_segments}")
        
        # 计算需要分割的片段数
        num_segments = int(duration / segment_length) + 1
        print(f"计划分割为 {num_segments} 个片段")
        
        # 分割音频
        segment_files = []
        for i in range(num_segments):
            start_time = i * segment_length
            segment_file = os.path.join(output_dir, f"segment_{i:03d}.wav")
            
            # 使用ffmpeg分割
            cmd = [
                'ffmpeg',
                '-i', audio_path,
                '-ss', str(start_time),
                '-t', str(segment_length),
                '-acodec', 'pcm_s16le',
                '-ar', '16000',
                '-ac', '1',
                segment_file,
                '-y'
            ]
            
            print(f"执行分割命令: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                print(f"分割音频片段{i}失败: {stderr.decode()}")
                continue
                
            # 验证分段文件是否存在
            if not os.path.exists(segment_file):
                print(f"分段文件创建失败: {segment_file}")
                continue
                
            print(f"成功创建分段 {i+1}/{num_segments}: {segment_file}")
            segment_files.append(segment_file)
        
        print(f"成功创建 {len(segment_files)}/{num_segments} 个分段")
        return segment_files
    except Exception as e:
        print(f"分割音频文件时发生错误: {str(e)}")
        return []

def update_task_progress(task_id, progress, text=None, status='processing'):
    """
    更新任务进度到Redis
    
    Args:
        task_id: 任务ID
        progress: 进度百分比 (0-100)
        text: 当前识别的文本
        status: 任务状态
    """
    try:
        task_data = {
            'status': status,
            'progress': progress,
            'updated_at': time.time()
        }
        
        if text is not None:
            task_data['current_text'] = text
            
        redis_client.hset(f'task:{task_id}', 'progress_data', json.dumps(task_data))
        
        # 如果是最终结果，也保存到结果字段
        if status == 'completed' and text is not None:
            redis_client.hset(f'task:{task_id}', 'result', json.dumps({
                'status': 'success',
                'text': text
            }))
            
        # 设置过期时间（7天）
        redis_client.expire(f'task:{task_id}', 60 * 60 * 24 * 7)
    except Exception as e:
        print(f"更新任务进度失败: {str(e)}")

def update_progress_counter(task_id, total_segments, completed_segments, text=None):
    """
    基于完成的片段数量更新进度条
    
    Args:
        task_id: 任务ID
        total_segments: 总片段数
        completed_segments: 已完成的片段数
        text: 当前识别的文本
    """
    try:
        # 前20%用于准备工作，后80%用于实际处理
        progress_share_per_segment = 80.0 / total_segments if total_segments > 0 else 0
        progress = 20 + int(completed_segments * progress_share_per_segment)
        progress = min(95, progress)  # 确保不超过95%，留5%给最终的合并工作
        
        # 获取已有的进度数据
        progress_data_json = redis_client.hget(f'task:{task_id}', 'progress_data')
        if progress_data_json:
            progress_data = json.loads(progress_data_json)
            # 只有新进度更大时才更新进度
            if progress <= progress_data.get('progress', 0) and progress_data.get('status') != 'failed':
                # 即使进度相同，也要确保文本能更新
                if text is not None:
                    progress_data['current_text'] = text
                    redis_client.hset(f'task:{task_id}', 'progress_data', json.dumps(progress_data))
                return
        
        # 更新进度
        task_data = {
            'status': 'processing',
            'progress': progress,
            'updated_at': time.time(),
            'completed_segments': completed_segments,
            'total_segments': total_segments
        }
        
        if text is not None:
            task_data['current_text'] = text
            
        redis_client.hset(f'task:{task_id}', 'progress_data', json.dumps(task_data))
        redis_client.expire(f'task:{task_id}', 60 * 60 * 24 * 7)  # 7天过期
    except Exception as e:
        print(f"更新任务进度计数器失败: {str(e)}")

def _save_transcription_to_txt(task_id, text_content):
    """
    辅助函数：将识别文本保存到TXT文件，并更新Redis中的路径。
    命名逻辑与 app.py 中的 generate_txt 保持一致。
    """
    try:
        task_info_json = redis_client.hget(f'task:{task_id}', 'info')
        if not task_info_json:
            print(f"[Save TXT Error {task_id}] 未能从Redis获取任务信息，无法保存TXT文件。")
            return

        task_info = json.loads(task_info_json)
        # Log the task_info and specifically the override value when saving TXT
        print(f"[Celery Task {task_id} - Save TXT] Task info from Redis: {task_info}")
        original_name = task_info.get('original_name', 'unknown_file')
        created_at_timestamp = task_info.get('created_at', time.time()) # Fallback to current time if not found
        filename_ts_override = task_info.get('filename_timestamp_override')
        print(f"[Celery Task {task_id} - Save TXT] filename_timestamp_override from Redis: {filename_ts_override}")
        txt_filename_only = ""

        if original_name == "microphone-recording.wav":
            if filename_ts_override:
                txt_filename_only = f"{filename_ts_override}-recording.txt"
            else:
                try:
                    dt_object = datetime.fromtimestamp(float(created_at_timestamp))
                    formatted_timestamp = dt_object.strftime("%Y-%m-%d-%H-%M-%S")
                    txt_filename_only = f"{formatted_timestamp}-recording.txt"
                except ValueError: 
                    formatted_timestamp = datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d-%H-%M-%S")
                    txt_filename_only = f"{formatted_timestamp}-recording-fallback.txt"
        else:
            base_name = os.path.splitext(original_name)[0]
            txt_filename_only = f"{base_name}.txt"
        
        text_dir = os.path.join('downloads', 'text')
        os.makedirs(text_dir, exist_ok=True)
        txt_path_on_disk = os.path.join(text_dir, txt_filename_only)
        
        with open(txt_path_on_disk, 'w', encoding='utf-8') as f:
            f.write(text_content)
        
        stored_txt_path_in_redis = os.path.join('text', txt_filename_only)
        task_info['txt_file'] = stored_txt_path_in_redis 
        redis_client.hset(f'task:{task_id}', 'info', json.dumps(task_info))
        print(f"[Save TXT Success {task_id}] 文本已自动保存到: {txt_path_on_disk}")
        
    except Exception as e:
        print(f"[Save TXT Error {task_id}] 自动保存TXT文件时出错: {str(e)}")

@celery.task(name='tasks.process_audio_segment', bind=True, max_retries=3)
def process_audio_segment(self, segment_file, task_id, segment_index, total_segments, language, api_key, api_region):
    """
    处理单个音频片段并返回识别结果
    
    Args:
        segment_file: 音频片段文件路径
        task_id: 主任务ID
        segment_index: 片段索引
        total_segments: 总片段数
        language: 语言代码
        api_key: Azure API密钥
        api_region: Azure API区域
        
    Returns:
        dict: 识别结果
    """
    try:
        print(f"开始处理音频片段 {segment_index+1}/{total_segments}: {segment_file}")
        
        # 使用绝对路径
        segment_file = os.path.abspath(segment_file)
        
        # 检查文件是否存在
        if not os.path.exists(segment_file):
            error_msg = f"音频片段文件不存在: {segment_file}"
            print(error_msg)
            
            # 查看目录内容，帮助调试
            dir_path = os.path.dirname(segment_file)
            if os.path.exists(dir_path):
                print(f"目录 {dir_path} 内容:")
                for file in os.listdir(dir_path):
                    print(f"  - {file}")
            else:
                print(f"目录不存在: {dir_path}")
                
            return {'index': segment_index, 'text': '', 'error': '文件不存在'}
        
        # 检查文件大小
        file_size = os.path.getsize(segment_file)
        if file_size == 0:
            print(f"音频片段文件为空: {segment_file}")
            return {'index': segment_index, 'text': '', 'error': '文件为空'}
        
        print(f"音频片段文件存在，大小: {file_size} 字节")
        
        # 计算整体进度基准 - 每个片段占总进度的(80/总片段数)，前20%留给准备阶段
        base_progress = 20 + (segment_index * 80.0 / total_segments)
        segment_progress_share = 80.0 / total_segments
        
        # 更新进度（开始处理片段）
        update_task_progress(task_id, int(base_progress), f"正在处理第 {segment_index+1}/{total_segments} 段音频...")
        
        try:
            # 配置Azure语音识别
            speech_config = speechsdk.SpeechConfig(subscription=api_key, region=api_region)
            speech_config.speech_recognition_language = language
            
            # 配置识别选项
            speech_config.set_property_by_name("DiarizationEnabled", "true")
            speech_config.set_property_by_name("ProfanityFilterMode", "None")
            speech_config.request_word_level_timestamps()
            
            # 创建音频配置和识别器
            audio_config = speechsdk.audio.AudioConfig(filename=segment_file)
            speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
            
            print(f"已配置语音识别器，语言: {language}, 区域: {api_region}")
        except Exception as config_error:
            error_msg = f"配置语音识别器失败: {str(config_error)}"
            print(error_msg)
            return {'index': segment_index, 'text': '', 'error': error_msg}
        
        # 处理片段
        all_results = []
        done = False
        
        def recognized_cb(evt):
            text = evt.result.text
            if text.strip():
                all_results.append(text)
                # 实时更新识别进度 - 根据识别结果数量更新进度
                # 假设每个结果占10%的片段进度，最多更新到70%的片段进度
                recognition_progress = min(0.7, len(all_results) * 0.1)
                current_progress = base_progress + (recognition_progress * segment_progress_share)
                
                # 两种进度更新方式同时使用
                update_task_progress(task_id, int(current_progress), None)
                
                # 同时更新进度计数器
                try:
                    progress_data_json = redis_client.hget(f'task:{task_id}', 'progress_data')
                    completed_segments = 0
                    if progress_data_json:
                        progress_data = json.loads(progress_data_json)
                        completed_segments = progress_data.get('completed_segments', 0)
                        # 分段内进度，计算部分完成
                        partial_complete = segment_index + recognition_progress
                        update_progress_counter(task_id, total_segments, partial_complete)
                except Exception as e:
                    print(f"更新部分进度失败: {str(e)}")
                    
                print(f"片段{segment_index}识别到: {text}")
        
        def canceled_cb(evt):
            nonlocal done
            print(f"片段{segment_index}识别取消: {evt.reason}")
            print(f"取消详情: {evt.cancellation_details.reason} - {evt.cancellation_details.error_details}")
            done = True
        
        def session_stopped_cb(evt):
            nonlocal done
            print(f"片段{segment_index}会话结束")
            done = True
        
        # 添加回调
        speech_recognizer.recognized.connect(recognized_cb)
        speech_recognizer.canceled.connect(canceled_cb)
        speech_recognizer.session_stopped.connect(session_stopped_cb)
        
        # 开始连续识别
        print(f"开始连续识别片段 {segment_index+1}/{total_segments}")
        speech_recognizer.start_continuous_recognition_async()
        
        # 等待识别完成，且定期更新进度
        timeout = 600  # 10分钟超时
        start_time = time.time()
        last_update_time = start_time
        progress_value = base_progress
        
        while not done and (time.time() - start_time) < timeout:
            time.sleep(0.5)  # 减少等待时间，更频繁检查状态
            
            # 每2秒更新一次进度，即使没有新的识别结果
            current_time = time.time()
            if current_time - last_update_time >= 2:
                last_update_time = current_time
                
                # 计算经过时间的百分比，最多到70%
                elapsed_percent = min(0.7, (current_time - start_time) / timeout)
                # 计算基于时间的进度值
                time_based_progress = base_progress + (elapsed_percent * segment_progress_share)
                
                # 如果基于时间的进度比当前进度大，则更新
                if time_based_progress > progress_value:
                    progress_value = time_based_progress
                    # 更新进度
                    update_task_progress(task_id, int(progress_value), f"正在处理第 {segment_index+1}/{total_segments} 段音频...")
                    # 更新进度计数器
                    partial_complete = segment_index + elapsed_percent
                    update_progress_counter(task_id, total_segments, partial_complete)
                    
                    print(f"片段{segment_index}处理中: {int(elapsed_percent*100)}% (基于时间)")
        
        # 检查是否超时
        if (time.time() - start_time) >= timeout:
            print(f"片段{segment_index}处理超时")
        
        # 停止识别
        print(f"停止识别片段 {segment_index+1}/{total_segments}")
        speech_recognizer.stop_continuous_recognition_async()
        time.sleep(2)  # 等待停止完成
        
        # 合并片段结果
        result_text = " ".join(all_results)
        print(f"片段{segment_index}识别完成，文本长度: {len(result_text)}")
        
        # 如果结果为空但没有报错，可能是语音太短或没有内容
        if not result_text.strip():
            print(f"片段{segment_index}识别结果为空，可能是无声片段")
        
        # 更新最终进度 - 片段完成
        current_progress = base_progress + segment_progress_share
        update_task_progress(task_id, int(current_progress), None)
        
        # 更新进度 - 该段已完成
        # 从Redis获取当前已完成的段数，并递增
        try:
            progress_data_json = redis_client.hget(f'task:{task_id}', 'progress_data')
            completed_segments = 0
            if progress_data_json:
                progress_data = json.loads(progress_data_json)
                completed_segments = progress_data.get('completed_segments', 0)
            completed_segments += 1
            
            # 使用新的进度更新函数
            update_progress_counter(task_id, total_segments, completed_segments)
        except Exception as e:
            print(f"更新片段进度失败: {str(e)}")
        
        # 删除临时片段文件
        try:
            if os.path.exists(segment_file):
                os.remove(segment_file)
                print(f"已删除临时片段文件: {segment_file}")
            else:
                print(f"临时片段文件已不存在: {segment_file}")
        except Exception as e:
            print(f"删除临时片段文件失败: {str(e)}")
        
        return {'index': segment_index, 'text': result_text}
        
    except Exception as e:
        error_msg = str(e)
        print(f"处理音频片段时发生错误: {error_msg}")
        
        # 识别出API相关错误
        if "SPXERR_INVALID_HEADER" in error_msg:
            error_msg = '认证错误: API密钥或区域设置不正确'
            
        # 如果是非致命错误，可以尝试重试
        if self.request.retries < self.max_retries:
            print(f"将在5秒后重试任务，当前重试次数: {self.request.retries+1}/{self.max_retries}")
            time.sleep(5)  # 等待5秒后重试
            self.retry(exc=e, countdown=5)
        
        return {'index': segment_index, 'text': '', 'error': error_msg}

@celery.task(name='tasks.combine_segment_results')
def combine_segment_results(results, task_id):
    """
    合并所有片段的识别结果
    
    Args:
        results: 所有片段的识别结果列表
        task_id: 任务ID
        
    Returns:
        dict: 最终合并的结果
    """
    try:
        # 打印收到的结果数量
        print(f"收到分段结果，总共 {len(results)} 个片段")
        
        # 更新进度 - 开始合并阶段 - 95%
        update_task_progress(task_id, 95, "开始合并识别结果...")
        
        # 检查结果列表是否为空
        if not results:
            error_msg = "没有收到任何分段结果"
            print(error_msg)
            update_task_progress(task_id, 100, status='failed')
            return {'status': 'error', 'error': error_msg}
            
        # 按片段索引排序
        sorted_results = sorted(results, key=lambda x: x['index'])
        
        # 更新进度 - 排序完成 - 96%
        update_task_progress(task_id, 96, "正在整理识别结果...")
        
        # 检查是否所有结果都有错误
        successful_results = [r for r in sorted_results if not r.get('error')]
        if not successful_results:
            error_msg = sorted_results[0].get('error', '所有片段处理失败')
            print(f"所有分段处理出现错误: {error_msg}")
            update_task_progress(task_id, 100, status='failed')
            return {'status': 'error', 'error': error_msg}
        
        # 有部分错误但不致命
        error_count = len([r for r in sorted_results if r.get('error')])
        if error_count > 0:
            print(f"检测到{error_count}个片段处理错误，但将继续合并可用结果")
        
        # 更新进度 - 错误检查完成 - 97%
        update_task_progress(task_id, 97, "正在检查分段结果...")
        
        # 合并文本（只使用成功处理的片段）
        combined_text = " ".join(r['text'] for r in successful_results if r.get('text'))
        
        # 更新进度 - 文本合并完成 - 98%
        update_task_progress(task_id, 98, "已合并文本，准备输出结果...")
        
        # 如果合并文本为空，返回错误
        if not combined_text.strip():
            error_msg = "识别结果为空"
            print(error_msg)
            update_task_progress(task_id, 100, status='failed')
            return {'status': 'error', 'error': error_msg}
        
        # 更新进度 - 即将完成 - 99%
        update_task_progress(task_id, 99, "识别完成，正在保存结果...")
        time.sleep(0.5)  # 短暂延迟，使进度更新能够显示
        
        # 更新最终结果
        update_task_progress(task_id, 100, combined_text, 'completed')
        print(f"成功合并 {len(successful_results)}/{len(sorted_results)} 个片段的文本，总长度: {len(combined_text)}")
        
        # 自动保存TXT文件
        _save_transcription_to_txt(task_id, combined_text)
        
        return {'status': 'success', 'text': combined_text}
    except Exception as e:
        error_msg = str(e)
        print(f"合并结果时发生错误: {error_msg}")
        update_task_progress(task_id, 100, status='failed')
        return {'status': 'error', 'error': error_msg}

@celery.task
def transcribe_audio(file_path, language='ja-JP', file_type=None, api_key=None, api_region=None, parallel_threads=None, segment_length=None, original_duration=0.0):
    """
    异步处理音频/视频文件并转文字
    
    Args:
        file_path: 文件路径
        language: 语言代码
        file_type: 文件类型，可以是'audio'或'video'
        api_key: Azure Speech API密钥，如果为None则使用环境变量
        api_region: Azure Speech区域，如果为None则使用环境变量
        parallel_threads: 并行处理线程数（默认为CPU核心数-1）
        segment_length: 音频分段长度（秒）（默认300秒）
        original_duration: 原始文件的时长（秒）
    """
    task_id = transcribe_audio.request.id
    
    # 设置并行线程数
    if parallel_threads is None or parallel_threads <= 0:
        parallel_threads = DEFAULT_PARALLEL_THREADS
        
    # 设置分段长度
    if segment_length is None or segment_length <= 0:
        segment_length = DEFAULT_SEGMENT_LENGTH
    
    # 记录初始参数（不记录完整的API密钥，只记录前后4个字符）
    masked_key = "********"
    if api_key and len(api_key) > 8:
        masked_key = api_key[:4] + "****" + api_key[-4:]
    print(f"开始处理任务：ID={task_id}, 文件={file_path}, 语言={language}, 文件类型={file_type}, API密钥={masked_key}, 区域={api_region}, 并行线程数={parallel_threads}, 分段长度={segment_length}秒, 原始时长={original_duration}秒")
    
    # 初始化任务进度
    update_task_progress(task_id, 0, "任务初始化...")
    
    # 检查参数
    if not api_key:
        update_task_progress(task_id, 0, status='failed')
        return {'status': 'error', 'error': '未提供Azure Speech API密钥'}
    
    if not api_region:
        update_task_progress(task_id, 0, status='failed')
        return {'status': 'error', 'error': '未提供Azure Speech API区域'}
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        update_task_progress(task_id, 0, status='failed')
        return {'status': 'error', 'error': f'文件不存在: {file_path}'}
    
    audio_path = file_path
    extracted_audio = None
    converted_wav = None
    temp_dir = None
    
    try:
        update_task_progress(task_id, 5, "准备音频文件...")
        
        # 如果是视频文件，先提取音频为WAV格式
        if file_type == 'video':
            file_name = os.path.basename(file_path)
            file_base = os.path.splitext(file_name)[0]
            extracted_audio_filename = f"temp_extracted_audio_{file_base}_{task_id}.wav"
            extracted_audio = os.path.join(os.getcwd(), extracted_audio_filename)
            
            print(f"从视频提取音频: {file_path} -> {extracted_audio}")
            update_task_progress(task_id, 8, "从视频提取音频...")
            
            if not extract_audio_from_video(file_path, extracted_audio):
                update_task_progress(task_id, 10, status='failed')
                return {'status': 'error', 'error': '从视频提取音频失败'}
                
            audio_path = extracted_audio
            
            if not os.path.exists(audio_path):
                update_task_progress(task_id, 10, status='failed')
                return {'status': 'error', 'error': f'提取的音频文件不存在: {audio_path}'}
            
            print(f"音频提取成功: {audio_path}")
        # 如果是音频文件但不是WAV格式或需要转换采样率，转换为16kHz WAV格式
        else:
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_name)[1].lower()
            
            # 检查是否需要转换格式
            if file_ext != '.wav' or True:  # 始终进行转换以确保正确格式
                file_base = os.path.splitext(file_name)[0]
                converted_wav_filename = f"temp_converted_audio_{file_base}_{task_id}.wav"
                converted_wav = os.path.join(os.getcwd(), converted_wav_filename)
                print(f"转换音频格式: {file_path} -> {converted_wav}")
                
                update_task_progress(task_id, 10, "转换音频格式...")
                
                if not convert_audio_to_wav(file_path, converted_wav):
                    update_task_progress(task_id, 15, status='failed')
                    return {'status': 'error', 'error': '音频格式转换失败'}
                    
                audio_path = converted_wav
                
                if not os.path.exists(audio_path):
                    update_task_progress(task_id, 15, status='failed')
                    return {'status': 'error', 'error': f'转换后的音频文件不存在: {audio_path}'}
                
                print(f"音频格式转换成功: {audio_path}")
        
        # --- Persist the processed audio_path before transcription ---
        try:
            task_info_json = redis_client.hget(f'task:{task_id}', 'info')
            if task_info_json:
                task_info = json.loads(task_info_json)
                # Log the task_info and specifically the override value when persisting audio
                print(f"[Celery Task {task_id} - Persist WAV] Task info from Redis: {task_info}")
                original_name_for_naming = task_info.get('original_name', 'unknown_file')
                created_at_timestamp = task_info.get('created_at', time.time())
                filename_ts_override = task_info.get('filename_timestamp_override') 
                print(f"[Celery Task {task_id} - Persist WAV] filename_timestamp_override from Redis: {filename_ts_override}")

                # This will always be .wav because audio_path is the converted/extracted WAV
                processed_audio_extension = os.path.splitext(audio_path)[1] 

                persistent_audio_filename = ""
                if original_name_for_naming == "microphone-recording.wav":
                    if filename_ts_override:
                        persistent_audio_filename = f"{filename_ts_override}-recording{processed_audio_extension}"
                    else:
                        # Fallback to created_at
                        dt_object = datetime.fromtimestamp(float(created_at_timestamp))
                        formatted_timestamp = dt_object.strftime("%Y-%m-%d-%H-%M-%S")
                        persistent_audio_filename = f"{formatted_timestamp}-recording{processed_audio_extension}"
                else:
                    base_name = os.path.splitext(original_name_for_naming)[0]
                    # For other uploaded files, use base name + extension. Override not typically used here for WAV.
                    persistent_audio_filename = f"{base_name}{processed_audio_extension}"
                
                persistent_audio_dir = os.path.join('downloads', 'audio')
                if not os.path.exists(persistent_audio_dir):
                    os.makedirs(persistent_audio_dir, exist_ok=True)
                
                final_persistent_audio_path = os.path.join(persistent_audio_dir, persistent_audio_filename)
                
                # Add a small delay and check file existence before copying
                time.sleep(0.5) # छोटा विराम
                if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                    shutil.copy(audio_path, final_persistent_audio_path)
                    print(f"已保存处理后的音频到: {final_persistent_audio_path}, 源文件: {audio_path}, 大小: {os.path.getsize(audio_path)} bytes")
                else:
                    print(f"[Error] 源文件 {audio_path} 不存在或为空，无法复制到 {final_persistent_audio_path}")
                    # Still try to proceed with transcription if possible, but log this issue.
                    # task_info['processed_audio_file'] will not be set if copy fails.

                # Store the relative path for deletion logic later ONLY IF copy was successful
                if os.path.exists(final_persistent_audio_path):
                    task_info['processed_audio_file'] = os.path.join('audio', persistent_audio_filename)
                    redis_client.hset(f'task:{task_id}', 'info', json.dumps(task_info))
                else:
                    print(f"[Warning] 处理后的音频文件未能保存到 {final_persistent_audio_path}，将不会在Redis中记录 processed_audio_file")
            else:
                print(f"[Warning] 未能从Redis获取任务 {task_id} 的信息，无法保存处理后的音频文件。")
        except Exception as e_persist:
            print(f"[Error] 保存处理后的音频文件时出错: {str(e_persist)}")
        # --- End of persisting audio ---

        update_task_progress(task_id, 12, "检查音频时长...")
        
        # 获取音频时长
        audio_duration = get_audio_duration(audio_path)
        print(f"音频时长: {audio_duration}秒")
        
        update_task_progress(task_id, 15, f"音频文件准备完成，时长: {int(audio_duration)}秒，并行处理线程: {parallel_threads}")
        
        # 获取Speech API密钥和区域
        speech_key = api_key
        speech_region = api_region
        
        # 判断是否需要分段处理（超过限制时长或指定了并行处理）
        LONG_AUDIO_THRESHOLD = 60  # 超过60秒使用分段并行处理
        should_segment = (
            audio_duration > LONG_AUDIO_THRESHOLD or 
            parallel_threads > 1
        )
        
        # 短音频直接处理
        if not should_segment:
            update_task_progress(task_id, 20, "开始识别音频...")
            
            # 初始化进度计数器，单段处理（总共10段，初始为0段完成）
            update_progress_counter(task_id, 10, 0, "开始识别短音频...")
            
            # 配置Azure语音识别
            try:
                speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
                speech_config.speech_recognition_language = language
                
                # 根据微软文档配置识别选项
                speech_config.set_property_by_name("DiarizationEnabled", "true")
                speech_config.set_property_by_name("ProfanityFilterMode", "None")
                speech_config.request_word_level_timestamps()
                
                # 创建音频配置和识别器
                audio_config = speechsdk.audio.AudioConfig(filename=audio_path)
                speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
            except Exception as config_error:
                update_task_progress(task_id, 30, status='failed')
                return {'status': 'error', 'error': f'配置Speech服务失败: {str(config_error)}'}
            
            # 使用连续识别方法处理音频
            all_results = []
            done = False
            result_counter = 0
            
            # 创建事件处理程序
            def recognized_cb(evt):
                nonlocal result_counter
                text = evt.result.text
                if text.strip():
                    all_results.append(text)
                    # 实时更新当前识别结果
                    current_text = " ".join(all_results)
                    # 计算粗略进度
                    result_counter += 1
                    progress = min(20 + int(result_counter * 75 / 10), 95)
                    update_task_progress(task_id, progress, current_text)
                    # 短音频也使用计数器方式更新进度
                    update_progress_counter(task_id, 10, min(result_counter, 9))
                    print(f"识别到文本: {text}")
            
            def canceled_cb(evt):
                nonlocal done
                print(f"识别取消: {evt.reason}")
                print(f"取消详情: {evt.cancellation_details}")
                done = True
            
            def session_stopped_cb(evt):
                nonlocal done
                print("会话结束")
                done = True
            
            # 添加回调
            speech_recognizer.recognized.connect(recognized_cb)
            speech_recognizer.canceled.connect(canceled_cb)
            speech_recognizer.session_stopped.connect(session_stopped_cb)
            
            # 开始连续识别
            speech_recognizer.start_continuous_recognition_async()
            
            # 等待识别完成
            timeout = 1200  # 20分钟超时（足够大多数短音频）
            start_time = time.time()
            last_update_time = start_time
            progress_value = 20  # 短音频处理从20%开始
            
            while not done and (time.time() - start_time) < timeout:
                time.sleep(0.5)  # 减少等待时间，更频繁检查状态
                
                # 每2秒更新一次进度，即使没有新的识别结果
                current_time = time.time()
                if current_time - last_update_time >= 2:
                    last_update_time = current_time
                    
                    # 计算经过时间的百分比，最多到80%（留20%给最后处理）
                    elapsed_percent = min(0.8, (current_time - start_time) / (timeout * 0.5))  # 乘以0.5加快进度增长
                    # 计算基于时间的进度值
                    time_based_progress = 20 + int(elapsed_percent * 75)
                    
                    # 如果基于时间的进度比当前进度大，则更新
                    if time_based_progress > progress_value:
                        progress_value = time_based_progress
                        time_based_segment = elapsed_percent * 10  # 假设短音频有10个虚拟片段
                        
                        # 更新进度
                        update_task_progress(task_id, progress_value, f"音频处理中: {progress_value}%...")
                        # 更新进度计数器
                        update_progress_counter(task_id, 10, time_based_segment)
                        
                        print(f"短音频处理中: {progress_value}% (基于时间)")
            
            # 停止识别
            speech_recognizer.stop_continuous_recognition_async()
            time.sleep(2)  # 等待停止完成
            
            # 检查结果
            if all_results:
                # 合并所有识别结果
                result_text = " ".join(all_results)
                update_task_progress(task_id, 100, result_text, 'completed')
                
                # 自动保存TXT文件 (短音频)
                _save_transcription_to_txt(task_id, result_text)
                
                return {'status': 'success', 'text': result_text}
            else:
                update_task_progress(task_id, 100, status='failed')
                return {'status': 'error', 'error': '未识别到任何内容'}
                
        # 长音频使用分段处理
        else:
            update_task_progress(task_id, 18, f"音频时长较长，准备分段处理，分段长度: {segment_length}秒...")
            
            # 创建临时目录存放分段音频
            session_id = str(uuid.uuid4())
            temp_dir_name = f"temp_segments_{session_id}_{task_id}"
            temp_dir = os.path.join(os.getcwd(), temp_dir_name)
            
            print(f"创建临时分段目录: {temp_dir}")

            # 将临时分段目录名保存到Redis，以便后续清理
            try:
                task_info_json = redis_client.hget(f'task:{task_id}', 'info')
                if task_info_json:
                    task_info_data = json.loads(task_info_json)
                    task_info_data['segment_temp_dir'] = temp_dir_name # 存储基础目录名
                    redis_client.hset(f'task:{task_id}', 'info', json.dumps(task_info_data))
                    print(f"已将临时分段目录名 {temp_dir_name} 保存到Redis任务 {task_id}")
                else:
                    print(f"[警告] 无法获取任务 {task_id} 的信息，未能保存临时分段目录名。")
            except Exception as e_redis_update:
                print(f"[错误] 保存临时分段目录名到Redis时出错: {str(e_redis_update)}")
            
            # 检查目录权限
            try:
                test_file = os.path.join(temp_dir, 'test_permission.txt')
                # with open(test_file, 'w') as f:
                #     f.write('test')
                # os.remove(test_file)
                # print(f"临时目录权限检查通过: {temp_dir}")
            except Exception as perm_error:
                error_msg = f"临时目录权限错误: {str(perm_error)}"
                print(error_msg)
                update_task_progress(task_id, 18, status='failed')
                return {'status': 'error', 'error': error_msg}
            
            # 分割音频文件
            update_task_progress(task_id, 18, "正在分割音频文件...")
            segment_files = split_audio_file(audio_path, temp_dir, segment_length=segment_length, max_segments=parallel_threads*3)
            
            if not segment_files:
                error_msg = f"分割音频文件失败，未能生成任何有效的分段文件 from {audio_path} into {temp_dir}"
                print(error_msg)
                update_task_progress(task_id, 19, status='failed')
                return {'status': 'error', 'error': error_msg}
            
            print(f"音频分割成功，共 {len(segment_files)} 个片段，并行处理线程: {parallel_threads}")
            
            # 初始化进度计数器系统，设置总段数和初始完成数为0
            update_progress_counter(task_id, len(segment_files), 0, f"音频已分割为 {len(segment_files)} 个片段，开始识别（{parallel_threads}个并行线程）...")
            
            # 创建处理任务组
            tasks_group = []
            for i, segment_file_path in enumerate(segment_files):
                tasks_group.append(process_audio_segment.s(
                    segment_file_path, 
                    task_id, 
                    i, 
                    len(segment_files), 
                    language, 
                    speech_key, 
                    speech_region
                ))
            
            # 创建任务链，先并行处理所有片段，然后合并结果
            # 使用用户指定的并行度
            workflow = chord(group(tasks_group), combine_segment_results.s(task_id))
            
            # 启动任务链
            result = workflow.apply_async()
            
            # 返回一个标识，表明任务已分发
            # 注意：这里不等待结果，因为我们是通过Redis和进度更新来处理结果
            return {
                'status': 'processing', 
                'message': f'长音频处理中，共 {len(segment_files)} 个片段，并行线程: {parallel_threads}，任务ID: {task_id}',
                'task_id': task_id
            }
            
    except Exception as e:
        error_msg = str(e)
        print(f"发生未预期错误: {error_msg}")
        
        # 判断是否为认证错误
        if "SPXERR_INVALID_HEADER" in error_msg:
            error_msg = '认证错误: API密钥或区域设置不正确。请确保您输入了正确的Speech API密钥和区域。'
        
        update_task_progress(task_id, 100, status='failed')
        return {'status': 'error', 'error': error_msg}
    finally:
        # The `finally` block now cleans up the original uploaded file (`file_path`)
        # and any intermediate ffmpeg outputs (`extracted_audio`, `converted_wav`).
        # The `audio_path` variable itself (which points to one of these) will be among those deleted.
        # The copy made to `downloads/audio/` is the one that persists.
        # Segment files in `temp_dir` are deleted by `process_audio_segment` tasks.
        # The `temp_dir` itself for segments needs to be cleaned up after chord finishes.
        # This is complex if chord is async. Best to leave temp_dir cleanup to `delete_task` in app.py.

        print(f"开始清理任务 {task_id} 的临时文件。")
        time.sleep(2) # Allow for file operations to complete, though not strictly necessary for os.remove
        
        files_to_delete_in_finally = {
            "原始上传文件": file_path,
            "临时提取的音频": extracted_audio,
            "临时转换的音频": converted_wav 
        }

        for desc, f_path in files_to_delete_in_finally.items():
            if f_path and os.path.exists(f_path):
                try:
                    # Ensure that we are not deleting the persisted file if, by some logic error,
                    # f_path happens to be the same as the one copied to downloads/audio.
                    # This check is a safeguard, current logic should prevent this.
                    is_persisted_copy = False
                    if 'final_persistent_audio_path' in locals() and os.path.samefile(f_path, final_persistent_audio_path):
                         is_persisted_copy = True
                    
                    if not is_persisted_copy:
                        os.remove(f_path)
                        print(f"已删除临时文件 ({desc}): {f_path}")
                    else:
                        print(f"跳过删除 {f_path} 因为它是持久化副本。")

                except Exception as cleanup_error:
                    print(f"清理临时文件 {f_path} ({desc}) 时发生错误: {str(cleanup_error)}")
        
        # Note: `temp_dir` (for segments) is NOT cleaned here. 
        # `process_audio_segment` deletes individual segments.
        # The `temp_dir` (e.g. temp_segments_...) should ideally be cleaned by `delete_task` in app.py
        # or a separate cleanup Celery task, as the main task `transcribe_audio` returns before chord completion. 