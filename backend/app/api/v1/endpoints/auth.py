from __future__ import annotations

from fastapi import APIRouter, Request, status

from app.api.deps import DBDep, CurrentUserDep
from app.schemas.auth import (
    CurrentUserOut,
    LoginRequest,
    LogoutRequest,
    PasswordChangeRequest,
    ProfileUpdateRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.common import MessageResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["认证"])


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("/login", response_model=TokenResponse, summary="用户登录")
async def login(payload: LoginRequest, request: Request, db: DBDep) -> TokenResponse:
    service = AuthService(db)
    return await service.login(
        payload,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="企业自助注册",
)
async def register(payload: RegisterRequest, request: Request, db: DBDep) -> TokenResponse:
    """公开接口：创建企业 + 内置角色 + 管理员账号，成功后直接返回登录令牌。"""
    return await AuthService(db).register(
        payload,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/refresh", response_model=TokenResponse, summary="刷新访问令牌")
async def refresh(payload: RefreshRequest, db: DBDep) -> TokenResponse:
    return await AuthService(db).refresh(payload.refresh_token)


@router.post("/logout", response_model=MessageResponse, summary="退出登录")
async def logout(
    payload: LogoutRequest, current: CurrentUserDep, db: DBDep
) -> MessageResponse:
    await AuthService(db).logout(current.payload, payload.refresh_token)
    return MessageResponse(message="已退出登录")


@router.get("/me", response_model=CurrentUserOut, summary="当前登录用户")
async def me(current: CurrentUserDep, db: DBDep) -> CurrentUserOut:
    return await AuthService(db).build_current_user(current.user)


@router.put("/me", response_model=CurrentUserOut, summary="修改个人资料")
async def update_me(
    payload: ProfileUpdateRequest, current: CurrentUserDep, db: DBDep
) -> CurrentUserOut:
    return await AuthService(db).update_profile(current.user, payload)


@router.put("/me/password", response_model=MessageResponse, summary="修改密码")
async def change_password(
    payload: PasswordChangeRequest, current: CurrentUserDep, db: DBDep
) -> MessageResponse:
    await AuthService(db).change_password(current.user, payload)
    return MessageResponse(message="密码修改成功，请重新登录")
