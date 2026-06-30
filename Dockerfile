# ========== 构建阶段：精简但完整 ==========
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libsqlite3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖并安装
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir fastapi uvicorn

# 可选：安装 playwright（如果需要浏览器回退）
# RUN pip install --no-cache-dir playwright
# RUN python -m playwright install chromium || true

# 复制项目代码
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
