FROM python:3.13-slim

LABEL maintainer="BabyBus Downloader"

# 换国内镜像源
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    nodejs \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
RUN pip install --no-cache-dir yt-dlp fastapi uvicorn jinja2 python-multipart -i https://pypi.tuna.tsinghua.edu.cn/simple

WORKDIR /app

COPY config.py fetcher.py downloader.py mover.py utils.py logger.py main.py web.py web_templates.py ./

# yt-dlp 指定 node 运行时 + iOS 客户端绕过容器限制
RUN mkdir -p /root/.config/yt-dlp && \
    echo '--js-runtimes node:/usr/bin/node' > /root/.config/yt-dlp/config && \
    echo '--extractor-args youtube:player_client=android' >> /root/.config/yt-dlp/config

# Docker 模式
ENV DOCKER=1

# 持久化目录
VOLUME ["/app/logs", "/output"]

ENV PYTHONUNBUFFERED=1

# Web 服务端口
EXPOSE 8080

# 主进程：Web + 下载任务（web.py 内含后台调度）
CMD ["python", "web.py"]
