import os
from celery import Celery

# 创建Celery实例
redis_host = os.environ.get('REDIS_HOST', 'redis')
redis_port = os.environ.get('REDIS_PORT', '6379')
redis_url = f'redis://{redis_host}:{redis_port}/0'

print(f"使用Redis URL: {redis_url}")  # 调试信息

# 直接创建celery实例，而不是函数
celery = Celery(
    'speech_app',
    broker=redis_url,
    backend=redis_url,
    include=['tasks']
)

# 配置
celery.conf.update(
    result_expires=3600,  # 结果过期时间1小时
    task_track_started=True,  # 跟踪任务开始状态
    task_time_limit=600,  # 任务超时10分钟
    broker_connection_retry=True,  # 确保重试连接
    broker_connection_retry_on_startup=True,  # 启动时重试连接
    broker_connection_max_retries=10,  # 最大重试次数
)

def create_celery(app=None):
    """兼容旧代码的创建函数"""
    if app:
        # 集成Flask上下文
        class ContextTask(celery.Task):
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)
        
        celery.Task = ContextTask
    
    return celery

# 为了支持作为主模块运行
if __name__ == '__main__':
    celery.start() 