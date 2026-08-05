"""日志核心配置模块。

采用 Loguru 框架替代默认日志系统，统一拦截标准库日志，
并将日志文件自动输出与切割归档存放在 logs/ 目录中。
同时保留内存 RingBuffer 以支持诊断控制台真实日志展示。
"""

from collections import deque
from datetime import UTC, datetime
import logging
from pathlib import Path
import sys
from threading import Lock
from typing import Any

from loguru import logger

from app.middleware.trace import current_trace_id

# 默认日志存储目录 logs/ (项目根目录下)
LOGS_DIR = Path(__file__).resolve().parents[3] / "logs"

_RESERVED_LOG_RECORD_KEYS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
}


class LogBufferItem:
    """真实日志节点项。"""

    def __init__(
        self,
        timestamp: datetime,
        level: str,
        event: str,
        message: str,
        trace_id: str | None,
    ):
        self.timestamp = timestamp
        self.level = level
        self.event = event
        self.message = message
        self.trace_id = trace_id


class RingBufferHandler:
    """内存环形缓冲区日志管理器，捕获系统运行真实日志供诊断控制台展示。"""

    def __init__(self, capacity: int = 500):
        self._capacity = capacity
        self._buffer: deque[LogBufferItem] = deque(maxlen=capacity)
        self._lock = Lock()

    def add(self, item: LogBufferItem) -> None:
        with self._lock:
            self._buffer.append(item)

    def get_logs(self, level: str | None = None, limit: int = 50) -> list[LogBufferItem]:
        with self._lock:
            items = list(self._buffer)

        if level:
            target_level = level.upper()
            items = [item for item in items if item.level == target_level]

        # 倒序展示最新的日志
        items.reverse()
        return items[:limit]


_GLOBAL_RING_BUFFER = RingBufferHandler(capacity=500)


class InterceptHandler(logging.Handler):
    """拦截标准 Python logging 日志并转发给 Loguru 处理。"""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        extras: dict[str, Any] = {}
        for key, value in record.__dict__.items():
            if key not in _RESERVED_LOG_RECORD_KEYS and not key.startswith("_"):
                extras[key] = value

        logger.opt(depth=depth, exception=record.exc_info).bind(**extras).log(
            level,
            record.getMessage(),
        )


def _ring_buffer_sink(message: Any) -> None:
    """Loguru 内存环形缓冲区 Sink 回调。"""
    record = message.record
    dt = record["time"].astimezone(UTC)
    level = record["level"].name
    event = record["name"] or "biyou"
    msg = record["message"]
    trace_id = record["extra"].get("trace_id") or current_trace_id.get()

    item = LogBufferItem(
        timestamp=dt,
        level=level,
        event=event,
        message=msg,
        trace_id=trace_id,
    )
    _GLOBAL_RING_BUFFER.add(item)


def _patch_trace_id(record: dict[str, Any]) -> None:
    """Loguru 记录补丁：动态注入当前请求 Trace ID。"""
    if "trace_id" not in record["extra"] or not record["extra"]["trace_id"]:
        record["extra"]["trace_id"] = current_trace_id.get() or "—"


def configure_logging(
    level: str = "INFO",
    log_format: str = "console",
    logs_dir: Path | None = None,
) -> None:
    """配置初始化 Loguru 日志系统。

    - 统一拦截 Python 标准 logging 模块
    - 日志持久化输出到 logs/ 目录（10MB 自动轮转切片，保留 14 天）
    - 包含控制台终端输出与诊断环形缓冲区 Sink
    """
    target_dir = logs_dir or LOGS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    # 移除 Loguru 默认 Handler
    logger.remove()

    # 1. 控制台终端输出
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{line}</cyan> | "
        "Trace: <yellow>{extra[trace_id]}</yellow> - "
        "<level>{message}</level>"
    )
    logger.add(
        sys.stderr,
        level=level.upper(),
        format=console_format,
        enqueue=True,
    )

    # 2. 文件持久化 Sink (保存在 logs 文件夹)
    log_file = target_dir / "biyou.log"
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "{level: <8} | "
        "{name}:{line} | "
        "Trace: {extra[trace_id]} - "
        "{message}"
    )
    logger.add(
        str(log_file),
        level=level.upper(),
        format=file_format,
        rotation="10 MB",
        retention="14 days",
        encoding="utf-8",
        enqueue=True,
    )

    # 3. 内存环形缓冲区 Sink (供 /diagnostics 诊断控制台展示)
    logger.add(
        _ring_buffer_sink,
        level=level.upper(),
        enqueue=True,
    )

    # 配置全局 Trace ID 补丁
    logger.configure(patcher=_patch_trace_id)

    # 拦截标准库 logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for logger_name in ("uvicorn", "uvicorn.access", "fastapi", "aiosqlite", "lancedb"):
        mod_logger = logging.getLogger(logger_name)
        mod_logger.handlers = [InterceptHandler()]
        mod_logger.propagate = False


def get_recent_log_events(level: str | None = None, limit: int = 50) -> list[LogBufferItem]:
    """获取内存缓冲区中保存的最近真实系统日志。"""
    return _GLOBAL_RING_BUFFER.get_logs(level=level, limit=limit)


def get_logger(name: str) -> logging.Logger:
    """返回标准 logging.Logger，由 InterceptHandler 拦截并由 Loguru 统一处理。"""
    return logging.getLogger(name)
