from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AttachmentRead(BaseModel):
    id: int
    biz_type: str
    biz_id: int
    filename: str
    file_size: int
    content_type: str | None = None
    uploader_id: int
    uploader_name: str | None = None
    created_at: datetime | None = None


class AttachmentBrief(BaseModel):
    id: int
    filename: str
    file_size: int
    content_type: str | None = None
    uploader_name: str | None = None
    created_at: datetime | None = None
