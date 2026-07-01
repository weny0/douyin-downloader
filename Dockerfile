# ========== 构建阶段：精简但完整 ==========
FROM python:3.11-slim

WORKDIR /app

# 设置环境变量，确保 Playwright 浏览器安装在项目内，防止容器重启丢失
ENV PLAYWRIGHT_BROWSERS_PATH=/app/ms-playwright

# 安装系统依赖（增加了 Playwright 运行 Chromium 必须的 Linux 系统库）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libsqlite3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖并安装
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir fastapi uvicorn pyyaml playwright

# 关键步骤：安装 Playwright 浏览器内核 (Chromium) 及其 Linux 依赖环境
RUN python -m playwright install chromium
RUN python -m playwright install-deps chromium

# 复制项目代码（包括你的 web_server.py 和 web 静态网页文件夹）
COPY . .

# 创建下载目录
RUN mkdir -p /app/Downloaded

# 暴露端口
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/v1/health || exit 1

# 启动 Web 服务（同时提供 API + Web UI）
CMD ["python", "web_server.py", "--port", "8080", "--host", "0.0.0.0"]
