# 语音/视频转文字工具

这是一个基于Docker的网页版语音/视频转文字工具，使用Azure的语音识别API进行转换。

由Cursor+Claude-3.7-sonnet+gemini-2.5-pro完成开发

## 功能

- 支持麦克风实时录音识别
- 支持上传音频文件识别
- **支持上传视频文件，自动提取音轨后识别**
- **支持后台处理转换任务，即使关闭页面转换也会继续进行**
- 简洁美观的用户界面
- 结果可一键复制
- 任务进度跟踪和历史记录
- **多语言界面支持（中文、英语、日语）**

## 部署步骤

### 使用DockerHub镜像部署

我们已经提供了现成的多平台Docker镜像，支持AMD64和ARM64架构。

1. 使用docker-compose启动服务：
```bash
docker-compose up -d
```

2. 访问 http://localhost:9527 使用服务

3. 在网页界面的设置中填入Azure语音服务密钥和区域

### 本地Docker部署

#### 准备工作

1. 注册Azure账号并创建语音服务资源，获取API密钥和区域信息
2. 确保已安装Docker和Docker Compose

### 启动服务

使用Docker Compose构建并启动服务：

```bash
docker-compose up -d
```

服务将在后台运行，访问 http://localhost:9527 即可使用。

包含的服务：
- Flask Web应用 (前端界面和API)
- Celery Worker (处理后台任务)
- Redis (消息队列和结果存储)

### 停止服务

```bash
docker-compose down
```

## 使用方法

1. 访问网页，在设置中填入Azure语音服务密钥和区域
2. 选择语言和音频/视频来源（麦克风或文件）
3. 上传音频/视频文件或进行录音
   - 对于视频文件，系统会自动提取音轨后进行识别
   - 支持的视频格式：MP4, AVI, MOV, MKV, WEBM等
   - 支持的音频格式：MP3, WAV, OGG等
4. 系统会在后台处理转换任务，即使关闭网页也会继续处理
5. 任务完成后，可以在任务列表中查看结果
6. 任务信息会保存在浏览器本地存储中，即使关闭页面后仍可查看历史任务

## 本地开发

如果你想在本地开发而不使用Docker：

1. 确保已安装ffmpeg（视频处理需要）
   ```bash
   # Ubuntu/Debian
   sudo apt-get install ffmpeg
   
   # macOS
   brew install ffmpeg
   
   # Windows
   # 下载 https://www.ffmpeg.org/download.html 并添加到PATH
   ```

2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

3. 启动Redis服务（使用Docker或本地安装）

4. 在一个终端启动Flask应用：
   ```bash
   cd app
   flask run
   ```

5. 在另一个终端启动Celery Worker：
   ```bash
   celery -A app.celery_config:create_celery worker --loglevel=info
   ```

## 技术栈

- 后端：Flask (Python)
- 语音识别：Azure 认知服务语音API
- 视频处理：FFmpeg
- 前端：HTML/CSS/JavaScript, Bootstrap 5
- 任务队列：Celery + Redis
- 容器化：Docker, Docker Compose
