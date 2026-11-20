from __future__ import annotations

from jwt import PyJWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import ALL_PERMISSION_CODES, SUPER_ADMIN_ROLE_CODE
from app.core.exceptions import AuthError, BadRequestError
from app.core.security import (
    TokenPayload,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.token_store import get_token_store
from app.models.organization import Organization
from app.models.rbac import Role
from app.models.system import LoginLog
from app.models.user import User
from app.repositories.department import DepartmentRepository
from app.repositories.organization import OrganizationRepository
from app.repositories.user import UserRepository
from app.schemas.auth import (
    CurrentUserOut,
    LoginRequest,
    PasswordChangeRequest,
    ProfileUpdateRequest,
    RoleBrief,
    TokenResponse,
)
from app.utils.datetime import now_naive


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.orgs = OrganizationRepository(session)
        self.depts = DepartmentRepository(session)
        self.tokens = get_token_store()

    # ------------------------------------------------------------------ 登录
    async def _resolve_org(self, organization_code: str | None) -> Organization:
        if organization_code:
            org = await self.orgs.get_by_code(organization_code.strip())
            if org is None:
                raise AuthError("企业编码不存在")
            if org.status != 1:
                raise AuthError("该企业已停用")
            return org

        active = [org for org in await self.orgs.list_all() if org.status == 1]
        if not active:
            raise BadRequestError("系统尚未初始化，请先执行种子脚本")
        if len(active) > 1:
            raise BadRequestError("存在多个企业，请提供 organization_code")
        return active[0]

    async def login(
        self,
        payload: LoginRequest,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TokenResponse:
        org = await self._resolve_org(payload.organization_code)
        user = await self.users.get_by_username(org.id, payload.username)

        if user is None or not verify_password(payload.password, user.password_hash):
            await self._record_login(org.id, user.id if user else None, "failed", ip_address, user_agent)
            raise AuthError("用户名或密码错误")

        if user.status != 1:
            await self._record_login(org.id, user.id, "disabled", ip_address, user_agent)
            raise AuthError("账号已被禁用，请联系管理员")

        user.last_login_at = now_naive()
        await self._record_login(org.id, user.id, "success", ip_address, user_agent)
        await self.session.commit()
        return self._issue_tokens(user)

    # ------------------------------------------------------------------ 注册
    async def _record_login(
        self,
        organization_id: int,
        user_id: int | None,
        status: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> None:
        self.session.add(
            LoginLog(
                organization_id=organization_id,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=(user_agent or "")[:2000] or None,
                status=status,
            )
        )
        await self.session.flush()

    # ------------------------------------------------------------------ 令牌
    def _issue_tokens(self, user: User) -> TokenResponse:
        access_token, _ = create_access_token(user.id, user.organization_id)
        refresh_token, _ = create_refresh_token(user.id, user.organization_id)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            payload = decode_token(refresh_token, expected_type="refresh")
        except PyJWTError as exc:
            raise AuthError("刷新令牌无效或已过期") from exc

        if await self.tokens.is_revoked(payload.jti):
            raise AuthError("刷新令牌已失效，请重新登录")

        user = await self.users.get(int(payload.sub))
        if user is None or user.status != 1:
            raise AuthError("账号不存在或已被禁用")

        # 刷新令牌轮换：旧的立即作废，降低泄露风险
        await self.tokens.revoke(payload.jti, payload.exp)
        return self._issue_tokens(user)

    async def logout(self, access_payload: TokenPayload, refresh_token: str | None = None) -> None:
        await self.tokens.revoke(access_payload.jti, access_payload.exp)
        if refresh_token:
            try:
                refresh_payload = decode_token(refresh_token, expected_type="refresh")
            except PyJWTError:
                return
            await self.tokens.revoke(refresh_payload.jti, refresh_payload.exp)

    # ------------------------------------------------------------------ 资料
    async def build_current_user(self, user: User) -> CurrentUserOut:
        org = await self.orgs.get(user.organization_id)
        dept = await self.depts.get(user.department_id) if user.department_id else None
        roles: list[Role] = await self.users.roles_of(user.id)
        is_superuser = any(role.code == SUPER_ADMIN_ROLE_CODE for role in roles)
        permissions = (
            list(ALL_PERMISSION_CODES)
            if is_superuser
            else await self.users.permission_codes_of(user.id)
        )
        return CurrentUserOut(
            id=user.id,
            username=user.username,
            real_name=user.real_name,
            email=user.email,
            phone=user.phone,
            avatar=user.avatar,
            organization_id=user.organization_id,
            organization_name=org.name if org else None,
            department_id=user.department_id,
            department_name=dept.name if dept else None,
            is_superuser=is_superuser,
            roles=[RoleBrief.model_validate(role) for role in roles],
            permissions=permissions,
        )

    async def change_password(self, user: User, payload: PasswordChangeRequest) -> None:
        if not verify_password(payload.old_password, user.password_hash):
            raise AuthError("原密码不正确")
        if payload.old_password == payload.new_password:
            raise BadRequestError("新密码不能与原密码相同")
        user.password_hash = hash_password(payload.new_password)
        await self.session.commit()

    async def update_profile(
        self, user: User, payload: ProfileUpdateRequest
    ) -> CurrentUserOut:
        data = payload.model_dump(exclude_unset=True)
        if "email" in data and data["email"]:
            if await self.users.email_exists(user.organization_id, str(data["email"]), user.id):
                raise BadRequestError("该邮箱已被其他用户使用")
            data["email"] = str(data["email"])
        for field, value in data.items():
            setattr(user, field, value)
        await self.session.commit()
        return await self.build_current_user(user)
