from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ALL_PERMISSION_CODES, SUPER_ADMIN_ROLE_CODE
from app.core.exceptions import AuthError, PermissionDenied
from app.core.security import TokenPayload, decode_token
from app.core.token_store import get_token_store
from app.db.session import get_db
from app.models.user import User
from app.repositories.user import UserRepository

bearer_scheme = HTTPBearer(auto_error=False, description="Bearer <access_token>")


@dataclass(slots=True)
class CurrentUser:
    """当前请求的登录上下文。权限集合在进入接口前就计算好，避免重复查库。"""

    user: User
    payload: TokenPayload
    permissions: set[str]
    is_superuser: bool

    @property
    def organization_id(self) -> int:
        return self.user.organization_id

    @property
    def id(self) -> int:
        return self.user.id

    def has(self, *codes: str) -> bool:
        return self.is_superuser or all(code in self.permissions for code in codes)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CurrentUser:
    if credentials is None:
        raise AuthError("缺少访问令牌")
    try:
        payload = decode_token(credentials.credentials, expected_type="access")
    except jwt.PyJWTError as exc:
        raise AuthError("访问令牌无效或已过期") from exc

    if await get_token_store().is_revoked(payload.jti):
        raise AuthError("令牌已失效，请重新登录")

    repo = UserRepository(db)
    user = await repo.get(int(payload.sub))
    if user is None or user.status != 1:
        raise AuthError("账号不存在或已被禁用")
    if user.organization_id != payload.organization_id:
        raise AuthError("令牌与账号所属企业不匹配")

    roles = await repo.roles_of(user.id)
    is_superuser = any(role.code == SUPER_ADMIN_ROLE_CODE for role in roles)
    permissions = (
        set(ALL_PERMISSION_CODES)
        if is_superuser
        else set(await repo.permission_codes_of(user.id))
    )
    return CurrentUser(
        user=user, payload=payload, permissions=permissions, is_superuser=is_superuser
    )


def require_permissions(*codes: str):
    """接口级权限校验。超级管理员默认放行。"""

    async def _checker(
        current: Annotated[CurrentUser, Depends(get_current_user)]
    ) -> CurrentUser:
        if current.is_superuser:
            return current
        missing = [code for code in codes if code not in current.permissions]
        if missing:
            raise PermissionDenied(f"缺少权限: {', '.join(missing)}")
        return current

    return _checker


DBDep = Annotated[AsyncSession, Depends(get_db)]
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
