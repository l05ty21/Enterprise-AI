from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.security import hash_password
from app.models.user import User
from app.repositories.department import DepartmentRepository
from app.repositories.role import RoleRepository
from app.repositories.user import UserRepository
from app.schemas.auth import RoleBrief
from app.schemas.common import Page, PageParams
from app.schemas.user import UserCreate, UserQuery, UserRead, UserUpdate


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.roles = RoleRepository(session)
        self.depts = DepartmentRepository(session)

    # ------------------------------------------------------------------ 查询
    async def _to_reads(self, users: list[User]) -> list[UserRead]:
        if not users:
            return []
        roles_map = await self.users.roles_of_many([user.id for user in users])
        dept_ids = [user.department_id for user in users if user.department_id]
        dept_names = await self.depts.names_by_ids([int(dept_id) for dept_id in dept_ids])
        return [
            UserRead(
                id=user.id,
                organization_id=user.organization_id,
                department_id=user.department_id,
                department_name=dept_names.get(user.department_id or 0),
                username=user.username,
                real_name=user.real_name,
                email=user.email,
                phone=user.phone,
                avatar=user.avatar,
                status=user.status,
                roles=[RoleBrief.model_validate(role) for role in roles_map.get(user.id, [])],
                last_login_at=user.last_login_at,
                created_at=user.created_at,
            )
            for user in users
        ]

    async def list_users(
        self, organization_id: int, query: UserQuery, page: PageParams
    ) -> Page[UserRead]:
        users, total = await self.users.search(
            organization_id, query, offset=page.offset, limit=page.limit
        )
        items = await self._to_reads(users)
        return Page[UserRead](
            items=items, total=total, page=page.page, page_size=page.page_size
        )

    async def get_user(self, organization_id: int, user_id: int) -> UserRead:
        user = await self.users.get_in_org(organization_id, user_id)
        if user is None:
            raise NotFoundError("用户不存在")
        return (await self._to_reads([user]))[0]

    # ------------------------------------------------------------------ 校验
    async def _validate_relations(
        self, organization_id: int, department_id: int | None, role_ids: list[int]
    ) -> None:
        if department_id is not None:
            dept = await self.depts.get_in_org(organization_id, department_id)
            if dept is None:
                raise BadRequestError("部门不存在或不属于当前企业")
        if role_ids:
            valid_ids = await self.roles.ids_in_org(organization_id, role_ids)
            invalid = set(role_ids) - valid_ids
            if invalid:
                raise BadRequestError(f"角色不存在或越权: {sorted(invalid)}")

    # ------------------------------------------------------------------ 写入
    async def create_user(self, organization_id: int, payload: UserCreate) -> UserRead:
        if await self.users.username_exists(organization_id, payload.username):
            raise ConflictError("用户名已存在")
        if payload.email and await self.users.email_exists(
            organization_id, str(payload.email)
        ):
            raise ConflictError("邮箱已被使用")
        await self._validate_relations(
            organization_id, payload.department_id, payload.role_ids
        )

        user = User(
            organization_id=organization_id,
            department_id=payload.department_id,
            username=payload.username,
            password_hash=hash_password(payload.password),
            real_name=payload.real_name,
            email=str(payload.email) if payload.email else None,
            phone=payload.phone,
            avatar=payload.avatar,
            status=payload.status,
            must_change_password=1,
        )
        await self.users.add(user)
        if payload.role_ids:
            await self.users.set_roles(user.id, payload.role_ids)
        await self.session.commit()
        # MySQL 没有 RETURNING，created_at / updated_at 是库端默认值，
        # 提交后仍是「未加载」状态；不显式回读，序列化时会触发异步惰性查询（MissingGreenlet → 500）
        await self.session.refresh(user)
        return (await self._to_reads([user]))[0]

    async def update_user(
        self,
        organization_id: int,
        user_id: int,
        payload: UserUpdate,
        *,
        operator_id: int,
    ) -> UserRead:
        user = await self.users.get_in_org(organization_id, user_id)
        if user is None:
            raise NotFoundError("用户不存在")

        data = payload.model_dump(exclude_unset=True)
        role_ids = data.pop("role_ids", None)

        if data.get("status") == 0 and user.id == operator_id:
            raise BadRequestError("不能禁用当前登录账号")

        if "email" in data:
            if data["email"]:
                email = str(data["email"])
                if await self.users.email_exists(
                    organization_id, email, exclude_id=user.id
                ):
                    raise ConflictError("邮箱已被使用")
                data["email"] = email
            else:
                data["email"] = None

        if role_ids is not None:
            await self._validate_relations(
                organization_id, data.get("department_id"), role_ids
            )
        elif "department_id" in data:
            await self._validate_relations(organization_id, data["department_id"], [])

        password = data.pop("password", None)
        if password:
            user.password_hash = hash_password(password)

        for field, value in data.items():
            setattr(user, field, value)

        if role_ids is not None:
            await self.users.set_roles(user.id, role_ids)

        await self.session.commit()
        return (await self._to_reads([user]))[0]

    async def disable_user(
        self, organization_id: int, user_id: int, *, operator_id: int
    ) -> None:
        """软删除：置为禁用，保留工单 / 审批 / 日志中的历史关联。"""
        if user_id == operator_id:
            raise BadRequestError("不能禁用当前登录账号")
        user = await self.users.get_in_org(organization_id, user_id)
        if user is None:
            raise NotFoundError("用户不存在")
        user.status = 0
        await self.session.commit()
