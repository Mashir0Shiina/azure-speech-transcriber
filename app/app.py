from flask import Flask, render_template, request, jsonify, Response, send_file
import os
import time
import uuid
import json
import mimetypes
import redis
from celery.result import AsyncResult
from flask_cors import CORS
import shutil
import threading
import tempfile
import re
import subprocess
from datetime import datetime
import glob

# 直接导入（用于Docker环境）
from celery_config import celery  # 直接使用celery_config中的celery实例
from tasks import transcribe_audio, get_audio_duration

app = Flask(__name__, static_folder='static')
CORS(app)  # 添加CORS支持，允许跨域请求

# 连接Redis
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

# 转换任务ID存储
task_storage = {}  # 简单起见，使用内存存储，生产环境应使用Redis或数据库

# 支持的媒体类型
ALLOWED_AUDIO_TYPES = {'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/x-wav', 'audio/ogg'}
ALLOWED_VIDEO_TYPES = {'video/mp4', 'video/avi', 'video/mpeg', 'video/quicktime', 'video/x-matroska', 'video/webm'}

# 存储ffmpeg转换进度信息
conversion_status = {}

@app.route('/')
def index():
    return render_template('index.html')

def get_file_type(file):
    """判断文件类型是音频还是视频"""
    mime_type = mimetypes.guess_type(file.filename)[0]
    
    if mime_type in ALLOWED_AUDIO_TYPES:
        return 'audio'
    elif mime_type in ALLOWED_VIDEO_TYPES:
        return 'video'
    else:
        # 如果无法识别，则通过扩展名判断
        extension = os.path.splitext(file.filename)[1].lower()
        if extension in ['.mp3', '.wav', '.ogg']:
            return 'audio'
        elif extension in ['.mp4', '.avi', '.mov', '.mkv', '.webm']:
            return 'video'
    
    return None

@app.route('/api/transcribe', methods=['POST'])
def transcribe():
    if 'audio' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400
    
    uploaded_file = request.files['audio']
    
    # 判断文件类型
    file_type = get_file_type(uploaded_file)
    if not file_type:
        return jsonify({'error': '不支持的文件类型'}), 400
    
    # 生成唯一文件名，并保存到工作目录
    audio_uuid = str(uuid.uuid4())
    original_extension = os.path.splitext(uploaded_file.filename)[1]
    # 保存到工作目录，Celery任务可以直接访问，任务完成后负责清理
    persistent_temp_filename = os.path.join(os.getcwd(), f"transcribe_orig_{audio_uuid}{original_extension}")
    uploaded_file.save(persistent_temp_filename)

    # 获取原始文件时长
    original_duration = get_audio_duration(persistent_temp_filename)
    
    # 获取语言设置
    language = request.form.get('language', 'ja-JP')
    
    # 获取用户提供的API设置
    user_api_key = request.form.get('api_key', '')
    user_api_region = request.form.get('api_region', '')
    
    # 获取并行处理设置
    try:
        parallel_threads = int(request.form.get('parallel_threads', '0'))
    except ValueError:
        parallel_threads = 0  # 使用默认值
    
    try:
        segment_length = int(request.form.get('segment_length', '0'))
    except ValueError:
        segment_length = 0  # 使用默认值

    # 获取格式化后的浏览器时间字符串 (用于文件名)
    formatted_browser_time = request.form.get('formatted_browser_time')
    
    # 只使用用户提供的API设置
    api_key = user_api_key
    api_region = user_api_region
    
    # 检查是否提供了API信息
    if not api_key or not api_region:
        return jsonify({
            'error': '未设置API密钥和区域', 
            'code': 'NO_API_SETTINGS'
        }), 400
    
    # 启动异步任务，传递API设置和并行处理参数
    task = transcribe_audio.delay(
        persistent_temp_filename, # 使用持久化的文件路径
        language, 
        file_type, 
        api_key, 
        api_region,
        parallel_threads,
        segment_length,
        original_duration # 传递原始时长
    )
    
    # 在Redis中存储任务的基本信息
    task_info = {
        'file': persistent_temp_filename, # 存储的是Celery任务将处理的文件路径
        'created_at': time.time(),
        'file_type': file_type,
        'original_name': uploaded_file.filename,
        'language': language,
        'api_region': api_region,
        'parallel_threads': parallel_threads,
        'segment_length': segment_length,
        'original_duration': original_duration
    }
    if formatted_browser_time:
        task_info['filename_timestamp_override'] = formatted_browser_time
    
    redis_client.hset(f'task:{task.id}', 'info', json.dumps(task_info))
    
    return jsonify({
        'task_id': task.id,
        'status': 'processing',
        'file_type': file_type,
        'parallel_threads': parallel_threads
    })

@app.route('/api/status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """获取转换任务的状态"""
    # 首先尝试从Redis获取进度信息
    progress_data = redis_client.hget(f'task:{task_id}', 'progress_data')
    task_info_data = redis_client.hget(f'task:{task_id}', 'info')
    
    # 如果Redis有进度信息
    if progress_data:
        progress_info = json.loads(progress_data)
        task_info = {}
        
        if task_info_data:
            task_info = json.loads(task_info_data)
        
        # 检查状态
        if progress_info.get('status') == 'completed':
            # 获取最终结果
            result_data = redis_client.hget(f'task:{task_id}', 'result')
            if result_data:
                result = json.loads(result_data)
                return jsonify({
                    'status': 'completed',
                    'result': result,
                    'progress': 100,
                    'file_info': {
                        'name': task_info.get('original_name', '未知文件'),
                        'type': task_info.get('file_type', 'unknown')
                    }
                })
            
        elif progress_info.get('status') == 'failed':
            return jsonify({
                'status': 'failed',
                'error': progress_info.get('error', '任务处理失败'),
                'file_info': {
                    'name': task_info.get('original_name', '未知文件'),
                    'type': task_info.get('file_type', 'unknown')
                }
            })
        
        # 处理中，返回进度和当前文本
        return jsonify({
            'status': 'processing',
            'progress': progress_info.get('progress', 0),
            'current_text': progress_info.get('current_text', ''),
            'file_info': {
                'name': task_info.get('original_name', '未知文件'),
                'type': task_info.get('file_type', 'unknown')
            }
        })
    
    # Redis中没有信息，使用Celery检查
    task_result = AsyncResult(task_id, app=celery)
    
    if task_result.ready():
        if task_result.successful():
            result = task_result.get()
            return jsonify({
                'status': 'completed',
                'result': result,
                'progress': 100
            })
        else:
            error = str(task_result.result)
            return jsonify({
                'status': 'failed',
                'error': error,
                'progress': 0
            })
    else:
        return jsonify({
            'status': 'processing',
            'progress': 0
        })

@app.route('/api/stream/<task_id>', methods=['GET'])
def stream_progress(task_id):
    """
    提供Server-Sent Events流，实时推送任务进度
    注意：前端已不再使用该接口，但保留以备将来需要
    """
    def generate():
        last_update = None
        retry_count = 0
        max_retries = 3600  # 最多推送1小时
        
        while retry_count < max_retries:
            # 获取最新进度
            progress_data = redis_client.hget(f'task:{task_id}', 'progress_data')
            
            if progress_data:
                progress_info = json.loads(progress_data)
                
                # 如果有新的更新或第一次推送
                if last_update != progress_data:
                    last_update = progress_data
                    
                    # 格式化为SSE事件
                    yield f"data: {json.dumps(progress_info)}\n\n"
                    
                    # 如果任务已完成或失败，结束流
                    if progress_info.get('status') in ['completed', 'failed']:
                        break
            
            # 休眠1秒
            time.sleep(1)
            retry_count += 1
        
        # 确保客户端知道流已结束
        yield "data: {\"status\": \"stream_ended\"}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/tasks', methods=['GET'])
def get_all_tasks():
    """获取所有任务列表"""
    tasks = []
    task_keys = redis_client.keys('task:*')
    
    for key in task_keys:
        task_id = key.decode('utf-8').split(':')[1]
        task_info_data = redis_client.hget(f'task:{task_id}', 'info')
        progress_data = redis_client.hget(f'task:{task_id}', 'progress_data')
        
        if task_info_data and progress_data:
            task_info = json.loads(task_info_data)
            progress_info = json.loads(progress_data)
            
            result_text = None
            if progress_info.get('status') == 'completed':
                result_data = redis_client.hget(f'task:{task_id}', 'result')
                if result_data:
                    result = json.loads(result_data)
                    result_text = result.get('text', '')
            
            tasks.append({
                'id': task_id,
                'file_name': task_info.get('original_name', '未知文件'),
                'file_type': task_info.get('file_type', 'unknown'),
                'status': progress_info.get('status', 'processing'),
                'progress': progress_info.get('progress', 0),
                'created_at': task_info.get('created_at'),
                'result': result_text,
                'language': task_info.get('language', 'zh-CN'),
                'original_duration': task_info.get('original_duration', 0),
                'processed_audio_file': task_info.get('processed_audio_file')
            })
    
    tasks.sort(key=lambda x: x.get('created_at', 0), reverse=True)
    return jsonify(tasks)

# 添加API测试端点
@app.route('/api/test-connection', methods=['POST'])
def test_connection():
    """测试Azure API连接"""
    import azure.cognitiveservices.speech as speechsdk
    
    # 获取API设置
    api_key = request.form.get('api_key', '')
    api_region = request.form.get('api_region', '')
    
    if not api_key or not api_region:
        return jsonify({
            'status': 'error',
            'error': '请提供API密钥和区域'
        }), 400
        
    try:
        # 使用Azure SDK检查连接
        # 创建语音配置
        speech_config = speechsdk.SpeechConfig(subscription=api_key, region=api_region)
        
        # 创建语音合成器 (比识别器更轻量级的测试)
        speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
        
        # 尝试获取语音列表
        result = speech_synthesizer.get_voices_async().get()
        
        return jsonify({
            'status': 'success',
            'message': f'连接成功! 获取到 {len(result.voices)} 个语音选项',
            'voices_count': len(result.voices)
        })
        
    except Exception as e:
        error_msg = str(e)
        
        # 判断是否为认证错误
        if "SPXERR_INVALID_HEADER" in error_msg:
            return jsonify({
                'status': 'error',
                'error': '认证错误: API密钥或区域设置不正确',
                'details': error_msg
            }), 400
            
        return jsonify({
            'status': 'error',
            'error': f'连接测试失败: {error_msg}',
            'details': error_msg
        }), 500

# 清理过期任务的辅助函数（实际使用应通过定时任务或Redis TTL实现）
def cleanup_old_tasks():
    current_time = time.time()
    
    # 1. 清理过期的Redis任务记录
    task_keys = redis_client.keys('task:*')
    for key in task_keys:
        task_id = key.decode('utf-8').split(':')[1]
        task_info_data = redis_client.hget(f'task:{task_id}', 'info')
        if task_info_data:
            task_info = json.loads(task_info_data)
            created_at = task_info.get('created_at', 0)
            if current_time - created_at > 86400 * 7:  # 7天后清理
                try:
                    # 使用delete_task_route函数来清理所有相关文件
                    delete_task_route(task_id)
                    app.logger.info(f"自动清理：已删除过期任务 {task_id}")
                except Exception as e:
                    app.logger.error(f"自动清理：删除过期任务 {task_id} 失败: {str(e)}")
    
    # 2. 清理临时目录
    try:
        app_dir = os.getcwd()
        temp_pattern = os.path.join(app_dir, "temp_*")
        for temp_file in glob.glob(temp_pattern):
            try:
                if os.path.isfile(temp_file):
                    # 获取文件修改时间
                    mod_time = os.path.getmtime(temp_file)
                    if current_time - mod_time > 3600:  # 1小时后清理
                        os.remove(temp_file)
                        app.logger.info(f"自动清理：删除临时文件 {temp_file}")
                elif os.path.isdir(temp_file):
                    # 获取目录修改时间
                    mod_time = os.path.getmtime(temp_file)
                    if current_time - mod_time > 3600:  # 1小时后清理
                        shutil.rmtree(temp_file)
                        app.logger.info(f"自动清理：删除临时目录 {temp_file}")
            except Exception as e:
                app.logger.error(f"自动清理：删除临时文件/目录 {temp_file} 失败: {str(e)}")
    except Exception as e:
        app.logger.error(f"自动清理：查找临时文件失败: {str(e)}")
    
    # 3. 检查uploads临时目录
    try:
        uploads_dir = os.path.join("uploads", "source_files")
        if os.path.isdir(uploads_dir):
            for subdir in os.listdir(uploads_dir):
                full_path = os.path.join(uploads_dir, subdir)
                if os.path.isdir(full_path):
                    # 获取目录修改时间
                    mod_time = os.path.getmtime(full_path)
                    if current_time - mod_time > 86400:  # 1天后清理
                        shutil.rmtree(full_path)
                        app.logger.info(f"自动清理：删除上传临时目录 {full_path}")
    except Exception as e:
        app.logger.error(f"自动清理：清理上传目录失败: {str(e)}")
    
    # 4. 清理转换任务的临时文件
    for conversion_id, status_data in list(conversion_status.items()):
        if current_time - status_data.get('created_at', current_time) > 3600:  # 1小时后清理
            try:
                # 删除原始文件
                original_file = status_data.get('original_file')
                if original_file and os.path.exists(original_file):
                    os.remove(original_file)
                    app.logger.info(f"自动清理：删除转换临时原始文件 {original_file}")
                
                # 删除输出文件
                output_file = status_data.get('output_file')
                if output_file and os.path.exists(output_file):
                    os.remove(output_file)
                    app.logger.info(f"自动清理：删除转换临时输出文件 {output_file}")
                
                # 删除临时目录
                if original_file:
                    temp_dir = os.path.dirname(original_file)
                    if os.path.isdir(temp_dir) and temp_dir.startswith(tempfile.gettempdir()):
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        app.logger.info(f"自动清理：删除转换临时目录 {temp_dir}")
                
                # 移除状态记录
                conversion_status.pop(conversion_id, None)
                app.logger.info(f"自动清理：移除过期转换任务状态记录 {conversion_id}")
            except Exception as e:
                app.logger.error(f"自动清理：清理转换任务 {conversion_id} 失败: {str(e)}")
                # 即使清理失败，也尝试移除状态记录，避免无限重试
                conversion_status.pop(conversion_id, None)

@app.route('/api/generate-txt/<task_id>', methods=['POST'])
def generate_txt(task_id):
    task_info_data = redis_client.hget(f'task:{task_id}', 'info')
    progress_data = redis_client.hget(f'task:{task_id}', 'progress_data') # Check if task is completed

    if not task_info_data or not progress_data:
        app.logger.warning(f"[/api/generate-txt {task_id}] Task info or progress data not found in Redis.")
        return jsonify({'status': 'error', 'error': '找不到任务信息或任务未完成'}), 404

    try:
        task_info = json.loads(task_info_data)
        progress_info = json.loads(progress_data)

        if progress_info.get('status') != 'completed':
            app.logger.warning(f"[/api/generate-txt {task_id}] Task status is '{progress_info.get('status')}', not completed.")
            return jsonify({'status': 'error', 'error': '任务尚未完成，无法获取TXT文件'}), 400

        txt_file_relative_path = task_info.get('txt_file')
        if not txt_file_relative_path:
            app.logger.error(f"[/api/generate-txt {task_id}] 'txt_file' field not found in Redis task info, though task is completed. TXT might not have been auto-generated.")
            return jsonify({'status': 'error', 'error': 'TXT文件路径未在任务信息中找到，可能自动生成失败'}), 404

        # Construct full path to check existence, though download URL uses relative
        full_txt_path_on_disk = os.path.join(os.getcwd(), 'downloads', txt_file_relative_path)
        
        if not os.path.exists(full_txt_path_on_disk):
            app.logger.error(f"[/api/generate-txt {task_id}] TXT file path '{txt_file_relative_path}' found in Redis, but file '{full_txt_path_on_disk}' does not exist on disk.")
            return jsonify({'status': 'error', 'error': 'TXT文件在服务器上未找到，可能已被意外删除或生成失败'}), 404
        
        # Extract just the filename for the 'filename' field in JSON response
        txt_filename_only = os.path.basename(txt_file_relative_path)

        app.logger.info(f"[/api/generate-txt {task_id}] Providing download URL for auto-generated TXT: {txt_file_relative_path}")
        return jsonify({
            'status': 'success',
            'filename': txt_filename_only, 
            'download_url': f'/api/download/{txt_file_relative_path}' 
        })
        
    except Exception as e:
        app.logger.error(f"[/api/generate-txt {task_id}] Error generating TXT download info: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'error': f'提供TXT下载链接时出错: {str(e)}'}), 500

@app.route('/api/download/<path:filename>', methods=['GET']) # Use <path:filename> to allow slashes
def download_file(filename):
    # filename is now expected to be like "text/some.txt" or "audio/some.wav"
    if '..' in filename or filename.startswith('/'): # Basic security check
        return jsonify({'error': '无效的文件名'}), 400
        
    # No longer check for .txt exclusively, more generic download
    # if not filename.endswith('.txt'):
    #     return jsonify({'error': '只能下载TXT文件'}), 400
    
    # Construct full path from the app's perspective
    file_path = os.path.join(os.getcwd(), 'downloads', filename) 
    # os.getcwd() in Flask app context is /app. So, /app/downloads/text/some.txt

    if not os.path.exists(file_path):
        # Try one level up for downloads if getcwd is already /app/downloads (less likely for Flask app)
        alt_file_path = os.path.join(os.path.dirname(os.getcwd()), 'downloads', filename)
        if os.path.exists(alt_file_path):
            file_path = alt_file_path
        else:
            app.logger.warning(f"Download attempt: File not found at {file_path} or {alt_file_path}")
            return jsonify({'error': '文件不存在'}), 404
    
    return send_file(file_path, as_attachment=True)

@app.route('/api/delete-task/<task_id>', methods=['DELETE'])
def delete_task_route(task_id):
    try:
        # 从Redis中获取任务信息
        task_info_json = redis_client.hget(f'task:{task_id}', 'info')
        task_result_json = redis_client.hget(f'task:{task_id}', 'result') # 检查是否有结果，例如Celery内部错误

        if not task_info_json and not task_result_json : # 如果两个都不存在，说明任务ID无效
            app.logger.warning(f"[Delete Task {task_id}] Task not found in Redis (no info and no result).")
            return jsonify({'status': 'error', 'message': '任务未找到'}), 404

        task_info = {}
        if task_info_json:
            task_info = json.loads(task_info_json)
            app.logger.info(f"[Delete Task {task_id}] Raw task_info from Redis: {task_info}")

        # 1. 删除处理后的音频文件 (downloads/audio/)
        processed_audio_relative_path = task_info.get('processed_audio_file')
        if processed_audio_relative_path:
            full_audio_path = os.path.join('downloads', processed_audio_relative_path)
            if os.path.exists(full_audio_path):
                try:
                    os.remove(full_audio_path)
                    app.logger.info(f"[Delete Task {task_id}] Successfully deleted processed audio file: {full_audio_path}")
                except Exception as e:
                    app.logger.error(f"[Delete Task {task_id}] Failed to delete processed audio file {full_audio_path}: {e}")
            else:
                app.logger.warning(f"[Delete Task {task_id}] Processed audio file not found, cannot delete: {full_audio_path}")
        else:
            app.logger.info(f"[Delete Task {task_id}] 'processed_audio_file' not found in task_info.")

        # 2. 删除生成的TXT文件 (downloads/text/)
        txt_file_relative_path = task_info.get('txt_file') 
        app.logger.info(f"[Delete Task {task_id}] Attempting to delete TXT. Relative path from Redis ('txt_file'): {txt_file_relative_path}")

        if txt_file_relative_path:
            full_txt_path = os.path.join('downloads', txt_file_relative_path) 
            app.logger.info(f"[Delete Task {task_id}] Calculated full_txt_path for TXT: {full_txt_path}")
            
            path_exists = os.path.exists(full_txt_path)
            app.logger.info(f"[Delete Task {task_id}] Does TXT file at full_txt_path exist? {path_exists}")

            if path_exists:
                try:
                    os.remove(full_txt_path)
                    app.logger.info(f"[Delete Task {task_id}] Successfully deleted TXT file: {full_txt_path}")
                except Exception as e:
                    app.logger.error(f"[Delete Task {task_id}] Failed to delete TXT file {full_txt_path}: {e}")
            else:
                app.logger.warning(f"[Delete Task {task_id}] TXT file not found at {full_txt_path}, cannot delete.")
        else:
            app.logger.info(f"[Delete Task {task_id}] 'txt_file' field not found in task_info. Cannot determine TXT file to delete.")
        
        # 3. 删除Celery任务处理长音频时产生的临时分段目录
        segment_temp_dir_name = task_info.get('segment_temp_dir')
        if segment_temp_dir_name:
            full_segment_dir_path = os.path.join(os.getcwd(), segment_temp_dir_name)
            if os.path.isdir(full_segment_dir_path):
                try:
                    shutil.rmtree(full_segment_dir_path)
                    app.logger.info(f"[Delete Task {task_id}] Successfully deleted Celery temp segment directory: {full_segment_dir_path}")
                except Exception as e:
                    app.logger.error(f"[Delete Task {task_id}] Failed to delete Celery temp segment directory {full_segment_dir_path}: {e}")
            else:
                app.logger.warning(f"[Delete Task {task_id}] Celery temp segment directory not found or not a dir: {full_segment_dir_path}")
        else:
            app.logger.info(f"[Delete Task {task_id}] 'segment_temp_dir' not found in task_info.")
        
        # 4. 删除uploads目录中的原始临时文件
        original_file_path = task_info.get('file')
        if original_file_path and os.path.exists(original_file_path):
            try:
                os.remove(original_file_path)
                app.logger.info(f"[Delete Task {task_id}] Successfully deleted original file: {original_file_path}")
            except Exception as e:
                app.logger.error(f"[Delete Task {task_id}] Failed to delete original file {original_file_path}: {e}")
        
        # 5. 检查uploads/source_files目录下是否有任何相关文件夹
        if 'original_name' in task_info:
            # 查找可能包含上传文件的目录
            uploads_dir = os.path.join('uploads', 'source_files')
            if os.path.isdir(uploads_dir):
                for subdir in os.listdir(uploads_dir):
                    full_subdir_path = os.path.join(uploads_dir, subdir)
                    if os.path.isdir(full_subdir_path):
                        # 检查目录内容是否与当前任务相关
                        for filename in os.listdir(full_subdir_path):
                            if task_info.get('original_name') == filename or (
                                filename == 'microphone-recording.wav' and 
                                task_info.get('original_name') == 'microphone-recording.wav'
                            ):
                                try:
                                    shutil.rmtree(full_subdir_path)
                                    app.logger.info(f"[Delete Task {task_id}] Deleted uploads directory {full_subdir_path} containing {filename}")
                                    break
                                except Exception as e:
                                    app.logger.error(f"[Delete Task {task_id}] Failed to delete uploads directory {full_subdir_path}: {e}")
        
        # 6. 从Redis删除任务记录
        deleted_keys = redis_client.delete(f'task:{task_id}')
        if deleted_keys > 0:
            app.logger.info(f"[Delete Task {task_id}] Successfully deleted task record from Redis: task:{task_id}")
        else:
            app.logger.warning(f"[Delete Task {task_id}] Task record task:{task_id} not found in Redis for deletion (possibly already deleted or never existed).")

        return jsonify({'status': 'success', 'message': '任务及相关文件已删除'}), 200
    except Exception as e:
        app.logger.error(f"[Delete Task {task_id}] An unhandled exception occurred: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': f'删除任务失败: {str(e)}'}), 500

@app.route('/api/upload-check', methods=['POST'])
def check_file_format():
    """检查上传文件格式是否需要转换"""
    if 'file' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400
    
    uploaded_file = request.files['file']
    
    # 生成临时文件保存上传的文件
    temp_dir = tempfile.mkdtemp(prefix="upload_")
    original_filename = uploaded_file.filename
    file_path = os.path.join(temp_dir, original_filename)
    uploaded_file.save(file_path)
    
    # 获取MIME类型
    mime_type = mimetypes.guess_type(original_filename)[0]
    extension = os.path.splitext(original_filename)[1].lower()
    
    # 获取原始文件时长
    original_file_duration = get_audio_duration(file_path)
    
    # 检查是否为视频
    is_video = False
    if mime_type and mime_type.startswith('video/'):
        is_video = True
    elif extension in ['.mp4', '.avi', '.mov', '.mkv', '.webm']:
        is_video = True
    
    # 检查是否为Azure支持的音频格式
    supported_audio = False
    if mime_type in ALLOWED_AUDIO_TYPES:
        supported_audio = True
    elif extension in ['.wav']:  # Azure最佳支持wav格式
        supported_audio = True
    
    # 生成唯一ID用于跟踪转换进度
    conversion_id = str(uuid.uuid4())
    conversion_status[conversion_id] = {
        'status': 'pending',
        'progress': 0,
        'message': '等待处理',
        'original_file': file_path,
        'output_file': None,
        'original_filename': original_filename,
        'original_duration': original_file_duration
    }
    
    # 返回检查结果
    return jsonify({
        'status': 'success',
        'needs_conversion': is_video or not supported_audio,
        'is_video': is_video,
        'file_path': file_path,
        'conversion_id': conversion_id,
        'original_filename': original_filename,
        'original_duration': original_file_duration,
        'message': '文件上传成功' + (', 需要格式转换' if is_video or not supported_audio else '')
    })

@app.route('/api/convert-file/<conversion_id>', methods=['POST'])
def convert_file(conversion_id):
    """转换文件格式"""
    if conversion_id not in conversion_status:
        return jsonify({'error': '无效的转换ID'}), 400
    
    # 获取原始文件路径
    status_data = conversion_status[conversion_id]
    original_file = status_data['original_file']
    original_filename = status_data['original_filename']
    
    if not os.path.exists(original_file):
        return jsonify({'error': '原始文件不存在'}), 400
    
    # 生成输出文件路径
    output_filename = f"temp_{str(uuid.uuid4())[:8]}.wav"
    output_file = os.path.join(os.path.dirname(original_file), output_filename)
    
    # 更新状态
    status_data['status'] = 'converting'
    status_data['progress'] = 0
    status_data['message'] = '开始转换'
    status_data['output_file'] = output_file
    
    # 在后台线程中执行转换
    thread = threading.Thread(
        target=run_conversion,
        args=(conversion_id, original_file, output_file)
    )
    thread.daemon = True  # 设置为守护线程
    thread.start()
    
    return jsonify({
        'status': 'success',
        'message': '开始转换文件',
        'conversion_id': conversion_id
    })

def run_conversion(conversion_id, input_file, output_file):
    """运行ffmpeg转换并更新进度"""
    try:
        # 确定是否为视频
        is_video = mimetypes.guess_type(input_file)[0] and mimetypes.guess_type(input_file)[0].startswith('video/')
        
        # 构建ffmpeg命令
        cmd = [
            'ffmpeg',
            '-i', input_file,
            '-acodec', 'pcm_s16le',    # PCM 16bit编码
            '-ar', '16000',            # 16kHz采样率
            '-ac', '1',                # 单声道
            '-y',                      # 覆盖已存在的文件
            '-progress', 'pipe:1',     # 输出进度信息到stdout
            output_file
        ]
        
        # 执行命令
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )
        
        # 读取进度信息
        conversion_status[conversion_id]['message'] = '转换中...' + ('从视频提取音频' if is_video else '转换音频格式')
        
        # 跟踪进度
        duration_seconds = None
        for line in process.stdout:
            line = line.strip()
            
            # 如果是总时长信息
            if line.startswith('Duration:'):
                match = re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)', line)
                if match:
                    hours, minutes, seconds = map(float, match.groups())
                    duration_seconds = hours * 3600 + minutes * 60 + seconds
                    conversion_status[conversion_id]['total_duration'] = duration_seconds
            
            # 如果是out_time信息
            if line.startswith('out_time='):
                time_str = line.split('=')[1].strip()
                if time_str and time_str != 'N/A':
                    match = re.search(r'(\d+):(\d+):(\d+\.\d+)', time_str)
                    if match and duration_seconds:
                        hours, minutes, seconds = map(float, match.groups())
                        current_seconds = hours * 3600 + minutes * 60 + seconds
                        progress = min(99, int((current_seconds / duration_seconds) * 100))
                        conversion_status[conversion_id]['progress'] = progress
                        conversion_status[conversion_id]['message'] = f'转换中...{progress}%'
            
            # 检查进度的另一种方法
            if line.startswith('frame=') and duration_seconds:
                # 例如: frame=2154 fps=55 q=-1.0 size=   30276kB time=00:01:11.76 bitrate=3450.3kbits/s
                time_match = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', line)
                if time_match:
                    hours, minutes, seconds = map(float, time_match.groups())
                    current_seconds = hours * 3600 + minutes * 60 + seconds
                    progress = min(99, int((current_seconds / duration_seconds) * 100))
                    conversion_status[conversion_id]['progress'] = progress
                    conversion_status[conversion_id]['message'] = f'转换中...{progress}%'
        
        # 等待进程完成
        process.wait()
        
        # 检查转换结果
        if process.returncode == 0 and os.path.exists(output_file):
            conversion_status[conversion_id]['status'] = 'completed'
            conversion_status[conversion_id]['progress'] = 100
            conversion_status[conversion_id]['message'] = '转换完成'
        else:
            stderr_output = process.stderr.read()
            conversion_status[conversion_id]['status'] = 'failed'
            conversion_status[conversion_id]['message'] = f'转换失败: {stderr_output}'
            
    except Exception as e:
        conversion_status[conversion_id]['status'] = 'failed'
        conversion_status[conversion_id]['message'] = f'转换过程中出错: {str(e)}'

@app.route('/api/conversion-status/<conversion_id>', methods=['GET'])
def get_conversion_status(conversion_id):
    """获取文件转换状态"""
    if conversion_id not in conversion_status:
        return jsonify({'error': '无效的转换ID'}), 400
    
    status_data = conversion_status[conversion_id].copy()
    
    # 清理可能不需要的字段
    if 'original_file' in status_data:
        del status_data['original_file']
    
    return jsonify(status_data)

@app.route('/api/complete-conversion/<conversion_id>', methods=['POST'])
def complete_conversion(conversion_id):
    """完成转换，开始转写任务"""
    if conversion_id not in conversion_status:
        return jsonify({'error': '无效的转换ID'}), 400
    
    status_data = conversion_status[conversion_id]
    
    if status_data['status'] != 'completed':
        return jsonify({'error': '转换尚未完成'}), 400
    
    output_file = status_data['output_file']
    original_filename = status_data['original_filename']
    original_duration = status_data.get('original_duration', 0)
    
    if not os.path.exists(output_file):
        return jsonify({'error': '转换后的文件不存在'}), 400
    
    # 将转换后的文件移动到主工作目录
    final_filename = f"temp_{str(uuid.uuid4())}.wav"
    final_path = os.path.join(os.getcwd(), final_filename)
    shutil.copy(output_file, final_path)
    
    # 从请求中获取其他参数
    data = request.get_json()
    language = data.get('language', 'ja-JP')
    api_key = data.get('api_key', '')
    api_region = data.get('api_region', '')
    parallel_threads = data.get('parallel_threads', 10)
    segment_length = data.get('segment_length', 60)
    formatted_browser_time = data.get('formatted_browser_time') # Get formatted time string
    
    # 检查是否提供了API信息
    if not api_key or not api_region:
        return jsonify({
            'error': '未设置API密钥和区域', 
            'code': 'NO_API_SETTINGS'
        }), 400
    
    # 启动异步任务，传递API设置和并行处理参数
    task = transcribe_audio.delay(
        final_path, 
        language, 
        'audio',  # 转换后都是音频文件
        api_key, 
        api_region,
        parallel_threads,
        segment_length,
        original_duration
    )
    
    # 在Redis中存储任务的基本信息
    task_info = {
        'file': final_path,
        'created_at': time.time(),
        'file_type': 'audio',
        'original_name': original_filename,  # 保留原始文件名
        'language': language,
        'api_region': api_region,
        'parallel_threads': parallel_threads,
        'segment_length': segment_length,
        'original_duration': original_duration
    }
    if formatted_browser_time:
        task_info['filename_timestamp_override'] = formatted_browser_time
    
    redis_client.hset(f'task:{task.id}', 'info', json.dumps(task_info))
    
    # 清理转换临时文件
    try:
        temp_dir = os.path.dirname(status_data['original_file'])
        if os.path.exists(temp_dir) and temp_dir.startswith(tempfile.gettempdir()):
            shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception as e:
        app.logger.error(f"清理临时目录失败: {str(e)}")
    
    # 从状态字典中移除这个转换任务
    conversion_status.pop(conversion_id, None)
    
    return jsonify({
        'task_id': task.id,
        'status': 'processing',
        'file_type': 'audio',
        'original_filename': original_filename,
        'original_duration': original_duration
    })

@app.route('/api/tasks/search', methods=['GET'])
def search_tasks():
    """根据文件名搜索任务"""
    query = request.args.get('q', '').lower()
    if not query:
        return jsonify([])

    tasks = []
    task_keys = redis_client.keys('task:*')

    for key in task_keys:
        task_id = key.decode('utf-8').split(':')[1]
        task_info_data = redis_client.hget(f'task:{task_id}', 'info')
        progress_data = redis_client.hget(f'task:{task_id}', 'progress_data')

        if task_info_data and progress_data:
            task_info = json.loads(task_info_data)
            progress_info = json.loads(progress_data)
            
            original_name = task_info.get('original_name', '').lower()
            if query in original_name:
                result_text = None
                if progress_info.get('status') == 'completed':
                    result_data = redis_client.hget(f'task:{task_id}', 'result')
                    if result_data:
                        result = json.loads(result_data)
                        result_text = result.get('text', '')
                
                tasks.append({
                    'id': task_id,
                    'file_name': task_info.get('original_name', '未知文件'),
                    'file_type': task_info.get('file_type', 'unknown'),
                    'status': progress_info.get('status', 'processing'),
                    'progress': progress_info.get('progress', 0),
                    'created_at': task_info.get('created_at'),
                    'result': result_text,
                    'language': task_info.get('language', 'zh-CN'),
                    'original_duration': task_info.get('original_duration', 0),
                    'processed_audio_file': task_info.get('processed_audio_file')
                })
    
    tasks.sort(key=lambda x: x.get('created_at', 0), reverse=True)
    return jsonify(tasks)

def clean_all_files():
    """
    清理所有临时文件和上传文件，但保留任务记录
    """
    app.logger.info("开始清理所有临时文件和上传文件...")
    cleaned_files = 0
    
    # 1. 清理 temp_* 临时目录和文件
    try:
        app_dir = os.getcwd()
        temp_pattern = os.path.join(app_dir, "temp_*")
        for temp_file in glob.glob(temp_pattern):
            try:
                if os.path.isfile(temp_file):
                    os.remove(temp_file)
                    app.logger.info(f"已删除临时文件: {temp_file}")
                    cleaned_files += 1
                elif os.path.isdir(temp_file):
                    shutil.rmtree(temp_file)
                    app.logger.info(f"已删除临时目录: {temp_file}")
                    cleaned_files += 1
            except Exception as e:
                app.logger.error(f"删除临时文件/目录 {temp_file} 失败: {str(e)}")
    except Exception as e:
        app.logger.error(f"查找临时文件失败: {str(e)}")
    
    # 2. 清理 app 目录下的临时目录
    try:
        app_dir = os.path.join(os.getcwd(), "app")
        temp_pattern = os.path.join(app_dir, "temp_*")
        for temp_file in glob.glob(temp_pattern):
            try:
                if os.path.isdir(temp_file):
                    shutil.rmtree(temp_file)
                    app.logger.info(f"已删除app目录下临时目录: {temp_file}")
                    cleaned_files += 1
            except Exception as e:
                app.logger.error(f"删除app目录下临时目录 {temp_file} 失败: {str(e)}")
    except Exception as e:
        app.logger.error(f"查找app目录下临时目录失败: {str(e)}")
    
    # 3. 清理 uploads/source_files 目录
    try:
        uploads_dir = os.path.join("uploads", "source_files")
        if os.path.isdir(uploads_dir):
            for subdir in os.listdir(uploads_dir):
                full_path = os.path.join(uploads_dir, subdir)
                if os.path.isdir(full_path):
                    shutil.rmtree(full_path)
                    app.logger.info(f"已删除上传临时目录: {full_path}")
                    cleaned_files += 1
    except Exception as e:
        app.logger.error(f"清理上传目录失败: {str(e)}")
    
    # 4. 清理 uploads 目录中的临时文件
    try:
        uploads_dir = "uploads"
        if os.path.isdir(uploads_dir):
            for item in os.listdir(uploads_dir):
                full_path = os.path.join(uploads_dir, item)
                if os.path.isfile(full_path):
                    os.remove(full_path)
                    app.logger.info(f"已删除上传文件: {full_path}")
                    cleaned_files += 1
    except Exception as e:
        app.logger.error(f"清理上传文件失败: {str(e)}")
    
    # 5. 清理 uploads 目录下的转换临时文件
    try:
        conversion_temp_pattern = os.path.join("uploads", "temp_*")
        for temp_file in glob.glob(conversion_temp_pattern):
            try:
                if os.path.isfile(temp_file):
                    os.remove(temp_file)
                    app.logger.info(f"已删除转换临时文件: {temp_file}")
                    cleaned_files += 1
                elif os.path.isdir(temp_file):
                    shutil.rmtree(temp_file)
                    app.logger.info(f"已删除转换临时目录: {temp_file}")
                    cleaned_files += 1
            except Exception as e:
                app.logger.error(f"删除转换临时文件/目录 {temp_file} 失败: {str(e)}")
    except Exception as e:
        app.logger.error(f"查找转换临时文件失败: {str(e)}")
    
    # 6. 清理转换任务状态字典
    for conversion_id in list(conversion_status.keys()):
        try:
            # 删除原始文件
            original_file = conversion_status[conversion_id].get('original_file')
            if original_file and os.path.exists(original_file):
                os.remove(original_file)
                app.logger.info(f"已删除转换临时原始文件: {original_file}")
                cleaned_files += 1
            
            # 删除输出文件
            output_file = conversion_status[conversion_id].get('output_file')
            if output_file and os.path.exists(output_file):
                os.remove(output_file)
                app.logger.info(f"已删除转换临时输出文件: {output_file}")
                cleaned_files += 1
            
            # 删除临时目录
            if original_file:
                temp_dir = os.path.dirname(original_file)
                if os.path.isdir(temp_dir) and temp_dir.startswith(tempfile.gettempdir()):
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    app.logger.info(f"已删除转换临时目录: {temp_dir}")
                    cleaned_files += 1
            
            # 移除状态记录
            conversion_status.pop(conversion_id, None)
            app.logger.info(f"已移除转换任务状态记录: {conversion_id}")
        except Exception as e:
            app.logger.error(f"清理转换任务 {conversion_id} 失败: {str(e)}")
            # 即使清理失败，也尝试移除状态记录
            conversion_status.pop(conversion_id, None)
    
    app.logger.info(f"清理完成，共删除 {cleaned_files} 个文件/目录")
    return cleaned_files

@app.route('/api/clean-files', methods=['POST'])
def clean_files_route():
    """
    清理所有临时文件和上传文件的API端点
    """
    try:
        cleaned_count = clean_all_files()
        return jsonify({
            'status': 'success',
            'message': f'已清理 {cleaned_count} 个临时文件和上传文件',
            'cleaned_count': cleaned_count
        })
    except Exception as e:
        app.logger.error(f"清理文件时出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'清理文件时出错: {str(e)}'
        }), 500

if __name__ == '__main__':
    # 启动清理定时任务
    import threading
    
    def cleanup_thread_function():
        while True:
            try:
                time.sleep(3600)  # 每小时执行一次清理
                cleanup_old_tasks()
            except Exception as e:
                app.logger.error(f"清理线程出错: {str(e)}")
    
    # 启动清理线程
    cleanup_thread = threading.Thread(target=cleanup_thread_function, daemon=True)
    cleanup_thread.start()
    app.logger.info("已启动自动清理线程")
    
    app.run(host='0.0.0.0', port=5000, debug=True) 