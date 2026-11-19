from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.config import settings


class LoginRequest(BaseModel):
    username: str = Field(min_length=2, max_length=64, description="用户名")
    password: str = Field(min_length=1, max_length=128, description="密码")
    organization_code: str | None = Field(
        default=None, max_length=64, description="企业编码，多租户登录时使用"
    )


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=10)


class LogoutRequest(BaseModel):
    refresh_token: str | None = Field(default=None, description="可选，用于同时吊销刷新令牌")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="访问令牌有效期（秒）")


class RoleBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str


class CurrentUserOut(BaseModel):
    id: int
    username: str
    real_name: str | None = None
    email: str | None = None
    phone: str | None = None
    avatar: str | None = None
    organization_id: int
    organization_name: str | None = None
    department_id: int | None = None
    department_name: str | None = None
    is_superuser: bool = False
    roles: list[RoleBrief] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)


class PasswordChangeRequest(BaseModel):
    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def _check_strength(cls, value: str) -> str:
        has_letter = any(ch.isalpha() for ch in value)
        has_digit = any(ch.isdigit() for ch in value)
        if not (has_letter and has_digit):
            raise ValueError("新密码必须同时包含字母和数字")
        if len(value) < settings.PASSWORD_MIN_LENGTH:
            raise ValueError(f"新密码长度不能少于 {settings.PASSWORD_MIN_LENGTH} 位")
        return value


class ProfileUpdateRequest(BaseModel):
    real_name: str | None = Field(default=None, max_length=64)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=32)
    avatar: str | None = Field(default=None, max_length=512)
