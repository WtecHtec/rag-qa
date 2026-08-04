#!/usr/bin/env bash
set -Eeuo pipefail

# 从脚本所在位置计算仓库根目录，避免依赖调用时的工作目录。
BIYOU_ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIYOU_BACKEND_PORT="${BIYOU_BACKEND_PORT:-8001}"
BIYOU_FRONTEND_PORT="${BIYOU_FRONTEND_PORT:-4173}"
BIYOU_BACKEND_PID=""
BIYOU_FRONTEND_PID=""

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "缺少命令：$1，请先安装后再启动。" >&2
    exit 1
  fi
}

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  echo
  echo "正在停止 BiYou 前后端服务…"
  if [[ -n "${BIYOU_BACKEND_PID}" ]]; then
    kill "${BIYOU_BACKEND_PID}" 2>/dev/null || true
  fi
  if [[ -n "${BIYOU_FRONTEND_PID}" ]]; then
    kill "${BIYOU_FRONTEND_PID}" 2>/dev/null || true
  fi
  wait "${BIYOU_BACKEND_PID}" 2>/dev/null || true
  wait "${BIYOU_FRONTEND_PID}" 2>/dev/null || true
  exit "${exit_code}"
}

trap cleanup EXIT INT TERM

require_command uv
require_command npm

ensure_port_available() {
  local port="$1"
  local service_name="$2"
  if command -v lsof >/dev/null 2>&1 \
    && lsof -nP -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "${service_name}端口 ${port} 已被占用，请先停止旧进程或设置对应的 BIYOU_*_PORT。" >&2
    exit 1
  fi
}

# 开发服务器禁止静默切换端口，否则浏览器可能仍停留在旧项目页面。
ensure_port_available "${BIYOU_BACKEND_PORT}" "后端"
ensure_port_available "${BIYOU_FRONTEND_PORT}" "前端"

echo "正在同步后端依赖…"
(
  cd "${BIYOU_ROOT_DIR}/backend"
  uv sync --extra dev
)

if [[ ! -d "${BIYOU_ROOT_DIR}/frontend/node_modules" ]]; then
  echo "正在安装前端依赖…"
  (
    cd "${BIYOU_ROOT_DIR}/frontend"
    npm install
  )
fi

echo "启动后端：http://127.0.0.1:${BIYOU_BACKEND_PORT}"
(
  cd "${BIYOU_ROOT_DIR}/backend"
  exec uv run uvicorn app.main:app --reload --host 127.0.0.1 --port "${BIYOU_BACKEND_PORT}"
) &
BIYOU_BACKEND_PID=$!

echo "启动前端：http://127.0.0.1:${BIYOU_FRONTEND_PORT}"
(
  cd "${BIYOU_ROOT_DIR}/frontend"
  exec env BIYOU_BACKEND_PORT="${BIYOU_BACKEND_PORT}" \
    BIYOU_FRONTEND_PORT="${BIYOU_FRONTEND_PORT}" \
    npm run dev -- --host 127.0.0.1 --port "${BIYOU_FRONTEND_PORT}"
) &
BIYOU_FRONTEND_PID=$!

echo "按 Ctrl+C 同时停止两个服务。"

# macOS 自带 Bash 不保证支持 wait -n，轮询进程状态可兼容旧版本。
while kill -0 "${BIYOU_BACKEND_PID}" 2>/dev/null \
  && kill -0 "${BIYOU_FRONTEND_PID}" 2>/dev/null; do
  sleep 1
done

# 任一服务异常退出时把状态码返回给终端，避免研发脚本误报启动成功。
BIYOU_CHILD_STATUS=0
if ! kill -0 "${BIYOU_BACKEND_PID}" 2>/dev/null; then
  wait "${BIYOU_BACKEND_PID}" || BIYOU_CHILD_STATUS=$?
else
  wait "${BIYOU_FRONTEND_PID}" || BIYOU_CHILD_STATUS=$?
fi
exit "${BIYOU_CHILD_STATUS}"
