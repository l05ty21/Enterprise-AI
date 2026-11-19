from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging
from app.db.session import dispose_engine, get_engine

logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("starting %s (env=%s)", settings.APP_NAME, settings.APP_ENV)

    if settings.AUTO_CREATE_TABLES:
        # 仅用于本地快速体验；正式环境请使用 alembic upgrade head
        from app import models  # noqa: F401  确保模型已注册
        from app.db.base import Base

        async with get_engine().begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.warning("AUTO_CREATE_TABLES 已开启：已按模型创建缺失的表")

    yield

    await dispose_engine()
    logger.info("application stopped")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.message,
                "detail": exc.detail,
                "path": request.url.path,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = []
        for error in exc.errors():
            errors.append(
                {
                    "field": ".".join(str(part) for part in error.get("loc", []) if part != "body"),
                    "message": error.get("msg"),
                    "type": error.get("type"),
                }
            )
        return JSONResponse(
            status_code=422,
            content={
                "code": "validation_error",
                "message": "请求参数校验失败",
                "detail": errors,
                "path": request.url.path,
            },
        )


def create_app() -> FastAPI:
    configure_logging()
    application = FastAPI(
        title=settings.APP_NAME,
        description="智企协同 Enterprise AI —— 企业级 AI SaaS 平台后端（第一阶段：基础框架与权限系统）",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(application)
    application.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @application.get("/", tags=["系统"], summary="服务信息")
    async def root() -> dict:
        return {
            "app": settings.APP_NAME,
            "version": "0.1.0",
            "docs": "/docs",
            "api_prefix": settings.API_V1_PREFIX,
        }

    return application


app = create_app()
