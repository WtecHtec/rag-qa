from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.error_handlers import register_error_handlers
from app.api.router import api_router
from app.container import AppContainer, build_default_container
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.middleware.trace import TraceIdMiddleware


def create_app(container: AppContainer | None = None) -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        configure_logging(settings.log_level, settings.log_format)
        await application.state.container.startup()
        get_logger(__name__).info(
            "application.started",
            extra={"environment": settings.environment},
        )
        yield
        get_logger(__name__).info("application.stopped")

    openapi_description = """
### BiYou 本地知识库问答系统 —— 交互式 API 接口文档

欢迎使用 **BiYou** 交互式 Swagger API 文档网站。系统基于 RAG (检索增强生成) 架构构建，支持知识库隔离、Parent/Child 文本切片、SSE 流式问答与本地向量检索。

#### 核心 API 模块：
- 📚 **知识库管理 (`/api/v1/knowledge-bases`)**: 知识库 CRUD、文档上传与解析状态追踪。
- 💬 **智能问答 (`/api/v1/conversations`)**: 会话管理、SSE 流式对话 (`/stream`)、重新生成与点赞点踩反馈。
- 🩺 **系统诊断 (`/api/v1/diagnostics`)**: 探针检测、满意度统计、RAG 检索 Trace 与日志控制台。
- ⚙️ **系统设置 (`/api/v1/settings`)**: 大模型 Provider 热重载与在线连通性测试。

#### 全局 Header 规范：
- `X-Trace-ID`: 每个请求响应自动附带链路 Trace ID，便于在线调试。
"""

    tags_metadata = [
        {
            "name": "knowledge_bases",
            "description": "知识库创建、检索、编辑以及文档上传与切片管理",
        },
        {
            "name": "conversations",
            "description": "智能问答会话管理、SSE 流式打字生成、重新生成与点赞点踩评价",
        },
        {
            "name": "diagnostics",
            "description": "系统健康检查探针、数据指标、RAG 检索链路 Trace 与审计控制台日志",
        },
        {
            "name": "settings",
            "description": "AI 大模型 Provider 参数管理、运行期热重载与连通性测试",
        },
    ]

    application = FastAPI(
        title="BiYou 本地知识库问答系统 API",
        description=openapi_description,
        version="1.0.0",
        openapi_tags=tags_metadata,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    application.state.container = container or build_default_container(settings)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Trace-ID"],
    )
    application.add_middleware(TraceIdMiddleware)
    register_error_handlers(application)
    application.include_router(api_router, prefix="/api/v1")
    return application


app = create_app()
