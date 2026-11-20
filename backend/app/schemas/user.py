from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.auth import RoleBrief

USERNAME_PATTERN = r"^[A-Za-z][A-Za-z0-9_.-]{2,63}$"


def _validate_password(value: str) -> str:
    if len(value) < 8:
        raise ValueError("密码长度不能少于 8 位")
    if not any(ch.isalpha() for ch in value):
        raise ValueError("密码必须包含字母")
    if not any(ch.isdigit() for ch in value):
        raise ValueError("密码必须包含数字")
    return value


class UserCreate(BaseModel):
    username: str = Field(pattern=USERNAME_PATTERN, description="3-64 位，字母开头")
    password: str = Field(min_length=8, max_length=128)
    real_name: str | None = Field(default=None, max_length=64)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=32)
    avatar: str | None = Field(default=None, max_length=512)
    department_id: int | None = None
    status: int = Field(default=1, ge=0, le=1)
    role_ids: list[int] = Field(default_factory=list)

    @field_validator("password")
    @classmethod
    def _check_password(cls, value: str) -> str:
        return _validate_password(value)

    @field_validator("role_ids")
    @classmethod
    def _single_role(cls, value: list[int]) -> list[int]:
        # 产品约定：一个账号只挂一个角色，避免权限叠加后说不清是谁
        if len(value) > 1:
            raise ValueError("一个账号只能分配一个角色")
        return value


class UserUpdate(BaseModel):
    real_name: str | None = Field(default=None, max_length=64)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=32)
    avatar: str | None = Field(default=None, max_length=512)
    department_id: int | None = None
    status: int | None = Field(default=None, ge=0, le=1)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role_ids: list[int] | None = None

    @field_validator("password")
    @classmethod
    def _check_password(cls, value: str | None) -> str | None:
        return None if value is None else _validate_password(value)

    @field_validator("role_ids")
    @classmethod
    def _single_role(cls, value: list[int] | None) -> list[int] | None:
        if value is not None and len(value) > 1:
            raise ValueError("一个账号只能分配一个角色")
        return value


class UserRead(BaseModel):
    id: int
    organization_id: int
    department_id: int | None = None
    department_name: str | None = None
    username: str
    real_name: str | None = None
    email: str | None = None
    phone: str | None = None
    avatar: str | None = None
    status: int
    roles: list[RoleBrief] = Field(default_factory=list)
    last_login_at: datetime | None = None
    created_at: datetime | None = None


class UserQuery(BaseModel):
    keyword: str | None = Field(default=None, description="匹配用户名 / 姓名 / 邮箱")
    department_id: int | None = None
    status: int | None = Field(default=None, ge=0, le=1)
    role_id: int | None = None
