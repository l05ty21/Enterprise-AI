from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import SUPER_ADMIN_ROLE_CODE
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models.rbac import Role
from app.repositories.role import PermissionRepository, RoleRepository
from app.schemas.role import PermissionRead, RoleCreate, RoleRead, RoleUpdate


class RoleService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.roles = RoleRepository(session)
        self.permissions = PermissionRepository(session)

    async def _to_read(self, role, permission_ids: list[int], user_count: int) -> RoleRead:
        return RoleRead(
            id=role.id,
            organization_id=role.organization_id,
            name=role.name,
            code=role.code,
            description=role.description,
            permission_ids=permission_ids,
            user_count=user_count,
            created_at=role.created_at,
        )

    async def list_roles(self, organization_id: int) -> list[RoleRead]:
        roles = await self.roles.list_in_org(organization_id)
        permission_map = await self.roles.permission_ids_of_many([role.id for role in roles])
        counts = await self.roles.user_counts(organization_id)
        return [
            await self._to_read(
                role, permission_map.get(role.id, []), counts.get(role.id, 0)
            )
            for role in roles
        ]

    async def get_role(self, organization_id: int, role_id: int) -> RoleRead:
        role = await self.roles.get_in_org(organization_id, role_id)
        if role is None:
            raise NotFoundError("角色不存在")
        permission_ids = await self.roles.permission_ids_of(role.id)
        return await self._to_read(role, permission_ids, await self.roles.count_by_role(role.id))

    async def _validate_permissions(self, permission_ids: list[int]) -> None:
        if not permission_ids:
            return
        valid = await self.permissions.ids_exist(permission_ids)
        invalid = set(permission_ids) - valid
        if invalid:
            raise BadRequestError(f"权限点不存在: {sorted(invalid)}")

    async def create_role(self, organization_id: int, payload: RoleCreate) -> RoleRead:
        if await self.roles.code_exists(organization_id, payload.code):
            raise ConflictError("角色编码已存在")
        await self._validate_permissions(payload.permission_ids)

        role = Role(
            organization_id=organization_id,
            name=payload.name,
            code=payload.code,
            description=payload.description,
        )
        await self.roles.add(role)
        if payload.permission_ids:
            await self.roles.set_permissions(role.id, payload.permission_ids)
        await self.session.commit()
        return await self.get_role(organization_id, role.id)

    async def update_role(
        self, organization_id: int, role_id: int, payload: RoleUpdate
    ) -> RoleRead:
        role = await self.roles.get_in_org(organization_id, role_id)
        if role is None:
            raise NotFoundError("角色不存在")

        data = payload.model_dump(exclude_unset=True)
        permission_ids = data.pop("permission_ids", None)
        if permission_ids is not None:
            await self._validate_permissions(permission_ids)
            await self.roles.set_permissions(role.id, permission_ids)

        for field, value in data.items():
            setattr(role, field, value)

        await self.session.commit()
        return await self.get_role(organization_id, role.id)

    async def delete_role(self, organization_id: int, role_id: int) -> None:
        role = await self.roles.get_in_org(organization_id, role_id)
        if role is None:
            raise NotFoundError("角色不存在")
        if role.code == SUPER_ADMIN_ROLE_CODE:
            raise BadRequestError("内置超级管理员角色不允许删除")
        if await self.roles.count_by_role(role.id) > 0:
            raise ConflictError("该角色下仍有用户，请先调整用户角色")
        await self.roles.set_permissions(role.id, [])
        await self.roles.delete(role)
        await self.session.commit()

    async def list_permissions(self) -> list[PermissionRead]:
        rows = await self.permissions.list_all()
        return [PermissionRead.model_validate(row) for row in rows]
