#!/usr/bin/env python
import os
import redis
import json
import shutil
import sys

# 连接Redis
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

def is_test_task(task_info):
    """判断任务是否为测试任务"""
    if not task_info:
        return False
        
    file_name = task_info.get('original_name', '').lower()
    test_keywords = [
        'test', 'test.', 'test_', 'test-', 
        'testing', 'tester', 'tested',
        '测试', '样本', '示例', '例子',
        'sample', 'sample.', 'sample_', 'sample-',
        'example', 'example.', 'example_', 'example-',
        'demo', 'demo.', 'demo_', 'demo-',
        'temp', 'temp.', 'temp_', 'temp-',
        'tmp', 'tmp.', 'tmp_', 'tmp-'
    ]
    
    # 检查是否包含测试关键词
    for keyword in test_keywords:
        if keyword in file_name:
            return True
    
    # 检查是否为特定测试文件
    specific_files = ['test.wav', 'test.mp3', 'test.ogg', 'test.m4a', 'test.mp4', 'test.mov', 'test.flac']
    if file_name in specific_files:
        return True
    
    return False

def clean_tasks(test_only=True):
    """删除任务记录及相关文件
    
    Args:
        test_only: 如果为True，只删除测试任务；如果为False，删除所有任务
    """
    print("开始清理任务记录...")
    
    # 查找所有任务
    task_keys = redis_client.keys('task:*')
    print(f"找到 {len(task_keys)} 个任务记录")
    
    cleaned_tasks = 0
    for key in task_keys:
        task_id = key.decode('utf-8').split(':')[1]
        
        try:
            # 从Redis中获取任务信息
            task_info_json = redis_client.hget(f'task:{task_id}', 'info')
            
            if task_info_json:
                task_info = json.loads(task_info_json)
                
                # 如果test_only为True且不是测试任务，则跳过
                if test_only and not is_test_task(task_info):
                    continue
                
                file_name = task_info.get('original_name', '未知文件')
                print(f"正在处理任务: {task_id} ({file_name})")
                
                # 1. 删除处理后的音频文件
                processed_audio_relative_path = task_info.get('processed_audio_file')
                if processed_audio_relative_path:
                    full_audio_path = os.path.join('downloads', processed_audio_relative_path)
                    if os.path.exists(full_audio_path):
                        os.remove(full_audio_path)
                        print(f"  已删除音频文件: {full_audio_path}")
                
                # 2. 删除TXT文件
                txt_file_relative_path = task_info.get('txt_file')
                if txt_file_relative_path:
                    full_txt_path = os.path.join('downloads', txt_file_relative_path)
                    if os.path.exists(full_txt_path):
                        os.remove(full_txt_path)
                        print(f"  已删除TXT文件: {full_txt_path}")
                
                # 3. 删除临时分段目录
                segment_temp_dir_name = task_info.get('segment_temp_dir')
                if segment_temp_dir_name:
                    full_segment_dir_path = os.path.join(os.getcwd(), segment_temp_dir_name)
                    if os.path.isdir(full_segment_dir_path):
                        shutil.rmtree(full_segment_dir_path)
                        print(f"  已删除临时分段目录: {full_segment_dir_path}")
                
                # 4. 删除原始文件
                original_file_path = task_info.get('file')
                if original_file_path and os.path.exists(original_file_path):
                    os.remove(original_file_path)
                    print(f"  已删除原始文件: {original_file_path}")
                
                # 5. 检查uploads/source_files目录
                if 'original_name' in task_info:
                    uploads_dir = os.path.join('uploads', 'source_files')
                    if os.path.isdir(uploads_dir):
                        for subdir in os.listdir(uploads_dir):
                            full_subdir_path = os.path.join(uploads_dir, subdir)
                            if os.path.isdir(full_subdir_path):
                                for filename in os.listdir(full_subdir_path):
                                    if task_info.get('original_name') == filename or (
                                        filename == 'microphone-recording.wav' and 
                                        task_info.get('original_name') == 'microphone-recording.wav'
                                    ):
                                        shutil.rmtree(full_subdir_path)
                                        print(f"  已删除上传目录: {full_subdir_path}")
                                        break
            
            # 6. 从Redis删除任务记录
            redis_client.delete(f'task:{task_id}')
            print(f"  已从Redis删除任务记录: task:{task_id}")
            cleaned_tasks += 1
            
        except Exception as e:
            print(f"  处理任务 {task_id} 时出错: {str(e)}")
    
    print(f"\n清理完成！共删除 {cleaned_tasks} 个任务记录。")

def print_usage():
    print("使用方法:")
    print("  python clean_tasks.py [选项]")
    print("\n选项:")
    print("  --all    删除所有任务记录")
    print("  --test   只删除测试任务记录（默认）")
    print("  --help   显示帮助信息")

if __name__ == "__main__":
    # 默认只删除测试任务
    test_only = True
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--all":
            test_only = False
            print("已选择: 删除所有任务记录")
        elif sys.argv[1] == "--test":
            test_only = True
            print("已选择: 只删除测试任务记录")
        elif sys.argv[1] == "--help":
            print_usage()
            sys.exit(0)
        else:
            print(f"未知选项: {sys.argv[1]}")
            print_usage()
            sys.exit(1)
    else:
        print("没有提供选项，默认只删除测试任务记录")
    
    if test_only:
        confirm = input("确认要删除所有测试任务记录吗？(y/n): ")
    else:
        confirm = input("警告: 即将删除所有任务记录，此操作不可恢复。确认继续吗？(y/n): ")
    
    if confirm.lower() == 'y':
        clean_tasks(test_only)
    else:
        print("已取消操作。") 