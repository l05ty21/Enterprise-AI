"""第三阶段会在这里实现文档解析、切片、向量化任务。

现在只放一个占位任务，保证 Celery worker 启动时模块可导入。
"""

from __future__ import annotations

from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.document.parse_document")
def parse_document(document_id: int) -> dict:
    return {"document_id": document_id, "status": "not_implemented"}
