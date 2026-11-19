from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

ROLE_CODE_PATTERN = r"^[a-z][a-z0-9_]{1,63}$"


class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    code: str = Field(pattern=ROLE_CODE_PATTERN, description="小写字母开头，可含数字和下划线")
    description: str | None = Field(default=None, max_length=255)
    permission_ids: list[int] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=255)
    permission_ids: list[int] | None = None


class PermissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    type: str
    parent_id: int | None = None
    path: str | None = None
    method: str | None = None


class RoleRead(BaseModel):
    id: int
    organization_id: int
    name: str
    code: str
    description: str | None = None
    permission_ids: list[int] = Field(default_factory=list)
    user_count: int = 0
    created_at: datetime | None = None


class RoleBriefOut(BaseModel):
    id: int
    name: str
    code: str
