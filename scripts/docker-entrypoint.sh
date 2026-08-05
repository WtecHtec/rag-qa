#!/bin/sh
set -e

echo "=== 正在启动 BiYou 综合一体化容器服务 ==="

# 启动后端 Python FastAPI 服务 (本地监听 8000 端口)
echo "[1/2] 启动后端 FastAPI 服务..."
cd /app/backend
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 &

# 等待后端端口就绪
echo "等待后端 API 就绪..."
until nc -z 127.0.0.1 8000; do
  sleep 0.5
done
echo "后端 API 已成功就绪。"

# 启动前端 Nginx 服务 (主进程前台运行，监听 80 端口)
echo "[2/2] 启动 Nginx 前端与反向代理..."
exec nginx -g 'daemon off;'
