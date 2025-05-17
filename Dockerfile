FROM python:3.11-slim

# 安装ffmpeg
RUN apt-get update && apt-get install -y ffmpeg && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./

# 环境变量设置
ENV REDIS_HOST="redis"
ENV FLASK_APP=app.py
ENV PYTHONPATH=/app

EXPOSE 5000

# 默认启动Flask应用，但可以通过command覆盖
CMD ["flask", "run", "--host=0.0.0.0"] 