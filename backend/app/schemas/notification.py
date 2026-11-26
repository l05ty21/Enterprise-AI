from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class NotificationRead(BaseModel):
    id: int
    title: str
    content: str | None = None
    type: str | None = None
    link_type: str | None = None
    link_id: int | None = None
    is_read: bool
    created_at: datetime | None = None


class UnreadCount(BaseModel):
    count: int = Field(ge=0)
