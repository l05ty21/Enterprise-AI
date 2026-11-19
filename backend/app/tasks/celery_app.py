"""Celery 应用入口。

第一阶段只提供 ping 任务用于验证队列连通性；文档解析任务会在第三阶段加入。
启动：
    celery -A app.tasks.celery_app worker -l info
"""

from __future__ import annotations

from celery import Celery

from app.core.config import settings

broker_url = settings.REDIS_URL or "redis://127.0.0.1:6379/0"

celery_app = Celery(
    "enterprise_ai",
    broker=broker_url,
    backend=broker_url,
    include=["app.tasks.document_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
)


@celery_app.task(name="app.tasks.ping")
def ping() -> str:
    return "pong"
