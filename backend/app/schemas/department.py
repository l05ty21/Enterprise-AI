from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    parent_id: int | None = None
    leader_id: int | None = None


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    parent_id: int | None = None
    leader_id: int | None = None


class DepartmentRead(BaseModel):
    id: int
    organization_id: int
    parent_id: int | None = None
    name: str
    leader_id: int | None = None
    leader_name: str | None = None
    member_count: int = 0
    created_at: datetime | None = None
    children: list["DepartmentRead"] = Field(default_factory=list)


DepartmentRead.model_rebuild()
