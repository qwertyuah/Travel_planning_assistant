FROM python:3.11.15-slim

WORKDIR /app

# 安装系统依赖（gcc、curl 以及 Node.js 安装所需）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 使用淘宝 npm 镜像加速
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && npm config set registry https://registry.npmmirror.com \
    && npm install -g tuniu-cli
    
    
# 复制并安装 Python 依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY backend/ ./backend/

ENV PYTHONPATH=/app/backend

EXPOSE 8000

CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]    