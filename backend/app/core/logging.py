import json
import logging
from collections import deque
from datetime import UTC, datetime
from threading import Lock
from typing import Any

from app.middleware.trace import current_trace_id

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


class RingBufferHandler(logging.Handler):
    """内存环形缓冲区日志 Handler，捕获系统运行真实日志供诊断控制台展示。"""

    def __init__(self, capacity: int = 500):
        super().__init__()
        self._capacity = capacity
        self._buffer: deque[LogBufferItem] = deque(maxlen=capacity)
        self._lock = Lock()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = record.getMessage()
            dt = datetime.fromtimestamp(record.created, tz=UTC)
            t_id = getattr(record, "trace_id", None) or current_trace_id.get()
            item = LogBufferItem(
                timestamp=dt,
                level=record.levelname,
                event=record.name,
                message=msg,
                trace_id=t_id,
            )
            with self._lock:
                self._buffer.append(item)
        except Exception:
            self.handleError(record)

    def get_logs(self, level: str | None = None, limit: int = 50) -> list[LogBufferItem]:
        with self._lock:
            items = list(self._buffer)

        if level:
            target_level = level.upper()
            items = [item for item in items if item.level == target_level]

        # 按倒序排列，优先展示最新的系统日志
        items.reverse()
        return items[:limit]


_GLOBAL_RING_BUFFER = RingBufferHandler(capacity=500)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
            "logger": record.name,
            "trace_id": current_trace_id.get(),
        }

        for key, value in record.__dict__.items():
            if key not in _RESERVED_LOG_RECORD_KEYS and not key.startswith("_"):
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str, log_format: str) -> None:
    handler = logging.StreamHandler()
    if log_format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # 挂载环形缓冲区 Handler，捕获真实日志供诊断监控读取
    _GLOBAL_RING_BUFFER.setLevel(level.upper())
    root_logger.addHandler(_GLOBAL_RING_BUFFER)
    root_logger.setLevel(level.upper())


def get_recent_log_events(level: str | None = None, limit: int = 50) -> list[LogBufferItem]:
    """获取内存缓冲区中保存的最近真实系统日志。"""
    return _GLOBAL_RING_BUFFER.get_logs(level=level, limit=limit)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
