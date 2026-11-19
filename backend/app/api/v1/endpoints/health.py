from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import DBDep
from app.core.config import settings

router = APIRouter(tags=["系统"])


@router.get("/health", summary="健康检查")
async def health(db: DBDep) -> dict:
    database = "up"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        database = "down"
    return {
        "status": "ok" if database == "up" else "degraded",
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
        "version": "0.1.0",
        "database": database,
    }
