from __future__ import annotations

from sqlalchemy import delete, func, insert, select

from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.repositories.base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    model = Role

    async def list_in_org(self, organization_id: int) -> list[Role]:
        stmt = (
            select(Role)
            .where(Role.organization_id == organization_id)
            .order_by(Role.id)
        )
        return list(await self.session.scalars(stmt))

    async def get_in_org(self, organization_id: int, role_id: int) -> Role | None:
        stmt = select(Role).where(
            Role.organization_id == organization_id, Role.id == role_id
        )
        return await self.session.scalar(stmt)

    async def code_exists(
        self, organization_id: int, code: str, exclude_id: int | None = None
    ) -> bool:
        stmt = select(func.count()).select_from(Role).where(
            Role.organization_id == organization_id, Role.code == code
        )
        if exclude_id:
            stmt = stmt.where(Role.id != exclude_id)
        return bool(await self.session.scalar(stmt))

    async def ids_in_org(self, organization_id: int, role_ids: list[int]) -> set[int]:
        if not role_ids:
            return set()
        stmt = select(Role.id).where(
            Role.organization_id == organization_id, Role.id.in_(role_ids)
        )
        return set(await self.session.scalars(stmt))

    async def permission_ids_of(self, role_id: int) -> list[int]:
        stmt = select(RolePermission.permission_id).where(
            RolePermission.role_id == role_id
        )
        return list(await self.session.scalars(stmt))

    async def permission_ids_of_many(self, role_ids: list[int]) -> dict[int, list[int]]:
        if not role_ids:
            return {}
        stmt = select(RolePermission.role_id, RolePermission.permission_id).where(
            RolePermission.role_id.in_(role_ids)
        )
        result: dict[int, list[int]] = {}
        for role_id, permission_id in (await self.session.execute(stmt)).all():
            result.setdefault(role_id, []).append(permission_id)
        return result

    async def set_permissions(self, role_id: int, permission_ids: list[int]) -> None:
        await self.session.execute(
            delete(RolePermission).where(RolePermission.role_id == role_id)
        )
        unique_ids = sorted(set(permission_ids))
        if unique_ids:
            await self.session.execute(
                insert(RolePermission).values(
                    [
                        {"role_id": role_id, "permission_id": permission_id}
                        for permission_id in unique_ids
                    ]
                )
            )
        await self.session.flush()

    async def user_counts(self, organization_id: int) -> dict[int, int]:
        stmt = (
            select(UserRole.role_id, func.count(UserRole.user_id))
            .join(Role, Role.id == UserRole.role_id)
            .where(Role.organization_id == organization_id)
            .group_by(UserRole.role_id)
        )
        return {role_id: count for role_id, count in (await self.session.execute(stmt)).all()}

    async def has_users(self, role_id: int) -> bool:
        return bool(await self.count_by_role(role_id))

    async def count_by_role(self, role_id: int) -> int:
        stmt = select(func.count()).select_from(UserRole).where(
            UserRole.role_id == role_id
        )
        return int(await self.session.scalar(stmt) or 0)


class PermissionRepository(BaseRepository[Permission]):
    model = Permission

    async def list_all(self) -> list[Permission]:
        stmt = select(Permission).order_by(Permission.id)
        return list(await self.session.scalars(stmt))

    async def ids_exist(self, permission_ids: list[int]) -> set[int]:
        if not permission_ids:
            return set()
        stmt = select(Permission.id).where(Permission.id.in_(permission_ids))
        return set(await self.session.scalars(stmt))
