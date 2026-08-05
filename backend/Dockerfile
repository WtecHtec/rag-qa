# BiYou 后端独立 Dockerfile (Python 3.12 + uv + FastAPI)
FROM ghcr.io/astral-sh/uv:latest AS uv_bin
FROM python:3.12-slim

# 设置工作目录与环境变量
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_HTTP_TIMEOUT=60

# 从 uv 镜像复制二进制可执行文件
COPY --from=uv_bin /uv /uvx /bin/

# 复制依赖声明文件
COPY pyproject.toml uv.lock .python-version ./

# 同步安装 Python 运行时环境与依赖
RUN uv sync --frozen --no-dev

# 复制后端业务源码
COPY app ./app

# 创建持久化数据与日志目录
RUN mkdir -p /app/data /app/logs

EXPOSE 8000

# 启动 FastAPI 异步服务
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
