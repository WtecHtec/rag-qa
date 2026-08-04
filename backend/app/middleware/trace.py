import logging
from contextvars import ContextVar
from time import perf_counter
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

current_trace_id: ContextVar[str] = ContextVar("trace_id", default="-")


class TraceIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        trace_id = request.headers.get("X-Trace-ID") or f"tr_{uuid4().hex[:12]}"
        token = current_trace_id.set(trace_id)
        request.state.trace_id = trace_id
        started_at = perf_counter()

        try:
            response = await call_next(request)
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            logging.getLogger("biyou.http").info(
                "http.request_completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )
            response.headers["X-Trace-ID"] = trace_id
            return response
        except Exception:
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            logging.getLogger("biyou.http").exception(
                "http.request_failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                },
            )
            raise
        finally:
            current_trace_id.reset(token)
