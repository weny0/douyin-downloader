FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 安装可选依赖
RUN pip install --no-cache-dir fastapi uvicorn playwright
RUN python -m playwright install chromium || true

# 复制项目代码
COPY . .

# 创建下载目录
RUN mkdir -p /app/Downloaded

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# 启动命令
CMD ["python", "run.py", "--serve", "--serve-port", "8000", "--serve-host", "0.0.0.0"]
