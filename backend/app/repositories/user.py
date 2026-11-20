from __future__ import annotations

from sqlalchemy import delete, func, insert, or_, select

from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.user import UserQuery


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_username(self, organization_id: int, username: str) -> User | None:
        stmt = select(User).where(
            User.organization_id == organization_id, User.username == username
        )
        return await self.session.scalar(stmt)

    async def get_in_org(self, organization_id: int, user_id: int) -> User | None:
        stmt = select(User).where(
            User.organization_id == organization_id, User.id == user_id
        )
        return await self.session.scalar(stmt)

    async def username_exists(
        self, organization_id: int, username: str, exclude_id: int | None = None
    ) -> bool:
        stmt = select(func.count()).select_from(User).where(
            User.organization_id == organization_id, User.username == username
        )
        if exclude_id:
            stmt = stmt.where(User.id != exclude_id)
        return bool(await self.session.scalar(stmt))

    async def email_exists(
        self, organization_id: int, email: str, exclude_id: int | None = None
    ) -> bool:
        stmt = select(func.count()).select_from(User).where(
            User.organization_id == organization_id, User.email == email
        )
        if exclude_id:
            stmt = stmt.where(User.id != exclude_id)
        return bool(await self.session.scalar(stmt))

    async def search(
        self, organization_id: int, query: UserQuery, offset: int, limit: int
    ) -> tuple[list[User], int]:
        stmt = select(User).where(User.organization_id == organization_id)
        if query.keyword:
            like = f"%{query.keyword.strip()}%"
            stmt = stmt.where(
                or_(
                    User.username.like(like),
                    User.real_name.like(like),
                    User.email.like(like),
                )
            )
        if query.department_id is not None:
            stmt = stmt.where(User.department_id == query.department_id)
        if query.status is not None:
            stmt = stmt.where(User.status == query.status)
        if query.role_id is not None:
            stmt = stmt.where(
                User.id.in_(
                    select(UserRole.user_id).where(UserRole.role_id == query.role_id)
                )
            )

        total = int(
            await self.session.scalar(select(func.count()).select_from(stmt.subquery()))
            or 0
        )
        rows = await self.session.scalars(
            stmt.order_by(User.id.desc()).offset(offset).limit(limit)
        )
        return list(rows), total

    async def roles_of(self, user_id: int) -> list[Role]:
        stmt = (
            select(Role)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
            .order_by(Role.id)
        )
        return list(await self.session.scalars(stmt))

    async def roles_of_many(self, user_ids: list[int]) -> dict[int, list[Role]]:
        if not user_ids:
            return {}
        stmt = (
            select(UserRole.user_id, Role)
            .join(Role, Role.id == UserRole.role_id)
            .where(UserRole.user_id.in_(user_ids))
            .order_by(Role.id)
        )
        result: dict[int, list[Role]] = {}
        for user_id, role in (await self.session.execute(stmt)).all():
            result.setdefault(user_id, []).append(role)
        return result

    async def permission_codes_of(self, user_id: int) -> list[str]:
        stmt = (
            select(Permission.code)
            .distinct()
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(UserRole, UserRole.role_id == RolePermission.role_id)
            .where(UserRole.user_id == user_id)
        )
        return sorted(await self.session.scalars(stmt))

    async def role_ids_of(self, user_id: int) -> list[int]:
        stmt = select(UserRole.role_id).where(UserRole.user_id == user_id)
        return list(await self.session.scalars(stmt))

    async def set_roles(self, user_id: int, role_ids: list[int]) -> None:
        await self.session.execute(delete(UserRole).where(UserRole.user_id == user_id))
        unique_ids = sorted(set(role_ids))
        if unique_ids:
            await self.session.execute(
                insert(UserRole).values(
                    [{"user_id": user_id, "role_id": role_id} for role_id in unique_ids]
                )
            )
        await self.session.flush()

    async def count_in_department(self, organization_id: int, department_id: int) -> int:
        return await self.count(
            User.organization_id == organization_id,
            User.department_id == department_id,
        )

    async def count_by_department(self, organization_id: int) -> dict[int, int]:
        stmt = (
            select(User.department_id, func.count(User.id))
            .where(
                User.organization_id == organization_id,
                User.department_id.is_not(None),
            )
            .group_by(User.department_id)
        )
        return {dept_id: count for dept_id, count in (await self.session.execute(stmt)).all()}

    async def names_by_ids(self, user_ids: list[int]) -> dict[int, str]:
        if not user_ids:
            return {}
        stmt = select(User.id, User.real_name, User.username).where(
            User.id.in_(set(user_ids))
        )
        return {
            user_id: (real_name or username)
            for user_id, real_name, username in (await self.session.execute(stmt)).all()
        }

    async def ids_with_permission(self, organization_id: int, code: str) -> list[int]:
        """该企业下拥有某个权限点的启用账号，按 id 升序（用于自动指派审批人）。"""
        stmt = (
            select(User.id)
            .distinct()
            .join(UserRole, UserRole.user_id == User.id)
            .join(RolePermission, RolePermission.role_id == UserRole.role_id)
            .join(Permission, Permission.id == RolePermission.permission_id)
            .where(
                User.organization_id == organization_id,
                User.status == 1,
                Permission.code == code,
            )
            .order_by(User.id)
        )
        return list(await self.session.scalars(stmt))
