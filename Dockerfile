# BiYou 全功能综合一体化 Dockerfile (Single-Container: Frontend + Backend + Nginx)

# Stage 1: 前端静态资源打包
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json ./
RUN npm install
COPY frontend/tsconfig*.json frontend/vite.config.ts frontend/index.html ./
COPY frontend/src ./src
COPY frontend/public ./public
RUN npm run build

# Stage 2: 综合一体化运行镜像 (Python 3.12 + Nginx + uv)
FROM ghcr.io/astral-sh/uv:latest AS uv_bin
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# 安装 Nginx 与 netcat (网络校验)
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# 从 uv 镜像复制二进制可执行文件
COPY --from=uv_bin /uv /uvx /bin/

# 复制前端打包产物到 Nginx 托管路径
COPY --from=frontend-builder /app/frontend/dist /usr/share/nginx/html

# 复制后端业务代码与依赖配置
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./
RUN uv sync --frozen --no-dev
COPY backend/app ./app

# 创建持久化存储目录
RUN mkdir -p /app/data /app/logs

# 配置 Nginx 反向代理与前端静态托管
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

# 复制一键并发启动脚本
COPY scripts/docker-entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

WORKDIR /app
EXPOSE 80 8000

ENTRYPOINT ["/app/entrypoint.sh"]
