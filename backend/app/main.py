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

    application = FastAPI(
        title="BiYou API",
        version="0.1.0",
        docs_url="/docs" if settings.environment == "development" else None,
        redoc_url=None,
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
