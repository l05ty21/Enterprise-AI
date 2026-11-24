from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

TicketPriority = Literal["low", "medium", "high", "urgent"]
TicketStatus = Literal["pending", "processing", "resolved", "closed"]


class TicketCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255, description="工单标题")
    description: str | None = Field(default=None, max_length=5000, description="问题描述")
    priority: TicketPriority = Field(default="medium", description="优先级")


class TicketUpdate(BaseModel):
    status: TicketStatus | None = None
    assignee_id: int | None = None
    priority: TicketPriority | None = None
    remark: str | None = Field(default=None, max_length=500, description="流转备注")


class TicketCommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class TicketQuery(BaseModel):
    keyword: str | None = None
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    mine: bool = Field(default=False, description="只看我提交或被指派的")


class TicketCommentRead(BaseModel):
    id: int
    user_id: int
    user_name: str | None = None
    content: str
    created_at: datetime | None = None


class TicketHistoryRead(BaseModel):
    id: int
    operator_id: int
    operator_name: str | None = None
    old_status: str | None = None
    new_status: str | None = None
    remark: str | None = None
    created_at: datetime | None = None


class TicketRead(BaseModel):
    id: int
    ticket_no: str
    title: str
    description: str | None = None
    priority: str
    status: str
    creator_id: int
    creator_name: str | None = None
    assignee_id: int | None = None
    assignee_name: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TicketDetail(TicketRead):
    comments: list[TicketCommentRead] = Field(default_factory=list)
    histories: list[TicketHistoryRead] = Field(default_factory=list)
