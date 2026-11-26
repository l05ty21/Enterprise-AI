from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUserDep, DBDep
from app.schemas.common import MessageResponse, Page, PageParams, page_params
from app.schemas.notification import NotificationRead, UnreadCount
from app.services.notification import NotificationService

router = APIRouter(prefix="/notifications", tags=["通知"])


@router.get("", response_model=Page[NotificationRead], summary="通知列表")
async def list_notifications(
    current: CurrentUserDep,
    db: DBDep,
    page: Annotated[PageParams, Depends(page_params)],
    unread_only: bool = Query(default=False),
) -> Page[NotificationRead]:
    return await NotificationService(db).list(current, page, unread_only=unread_only)


@router.get("/unread-count", response_model=UnreadCount, summary="未读数量")
async def unread_count(current: CurrentUserDep, db: DBDep) -> UnreadCount:
    return await NotificationService(db).unread_count(current)


@router.post(
    "/{notification_id}/read",
    response_model=NotificationRead,
    summary="标记已读",
)
async def mark_read(
    notification_id: int, current: CurrentUserDep, db: DBDep
) -> NotificationRead:
    return await NotificationService(db).mark_read(current, notification_id)


@router.post("/read-all", response_model=MessageResponse, summary="全部已读")
async def mark_all_read(current: CurrentUserDep, db: DBDep) -> MessageResponse:
    await NotificationService(db).mark_all_read(current)
    return MessageResponse(message="已全部标记为已读")
