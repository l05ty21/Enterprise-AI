from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, CurrentUserDep, DBDep, require_permissions
from app.schemas.common import Page, PageParams, page_params
from app.schemas.ticket import (
    TicketCommentCreate,
    TicketCommentRead,
    TicketCreate,
    TicketDetail,
    TicketQuery,
    TicketRead,
    TicketUpdate,
)
from app.services.ticket import TicketService

router = APIRouter(prefix="/tickets", tags=["工单"])

ReadTicket = Annotated[CurrentUser, Depends(require_permissions("ticket:read"))]
CreateTicket = Annotated[CurrentUser, Depends(require_permissions("ticket:create"))]


@router.get("", response_model=Page[TicketRead], summary="工单列表")
async def list_tickets(
    current: ReadTicket,
    db: DBDep,
    page: Annotated[PageParams, Depends(page_params)],
    keyword: str | None = Query(default=None, description="编号或标题模糊匹配"),
    status_value: str | None = Query(default=None, alias="status"),
    priority: str | None = Query(default=None),
    mine: bool = Query(default=False, description="只看我提交或被指派的"),
) -> Page[TicketRead]:
    query = TicketQuery(
        keyword=keyword, status=status_value, priority=priority, mine=mine
    )
    return await TicketService(db).list_tickets(current, query, page)


@router.post(
    "",
    response_model=TicketRead,
    status_code=status.HTTP_201_CREATED,
    summary="创建工单",
)
async def create_ticket(
    payload: TicketCreate, current: CreateTicket, db: DBDep
) -> TicketRead:
    return await TicketService(db).create(current, payload)


@router.get("/{ticket_id}", response_model=TicketDetail, summary="工单详情")
async def get_ticket(ticket_id: int, current: ReadTicket, db: DBDep) -> TicketDetail:
    return await TicketService(db).get_detail(current, ticket_id)


@router.patch("/{ticket_id}", response_model=TicketDetail, summary="流转工单")
async def update_ticket(
    ticket_id: int, payload: TicketUpdate, current: CurrentUserDep, db: DBDep
) -> TicketDetail:
    """指派 / 改状态 / 调优先级。没有 ticket:update 时只允许创建人关闭自己的工单。"""
    return await TicketService(db).update(current, ticket_id, payload)


@router.post(
    "/{ticket_id}/comments",
    response_model=TicketCommentRead,
    status_code=status.HTTP_201_CREATED,
    summary="追加工单评论",
)
async def add_comment(
    ticket_id: int, payload: TicketCommentCreate, current: ReadTicket, db: DBDep
) -> TicketCommentRead:
    return await TicketService(db).add_comment(current, ticket_id, payload)
