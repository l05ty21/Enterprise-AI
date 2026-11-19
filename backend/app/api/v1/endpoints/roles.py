from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, DBDep, require_permissions
from app.schemas.common import MessageResponse
from app.schemas.role import RoleCreate, RoleRead, RoleUpdate
from app.services.role import RoleService

router = APIRouter(prefix="/roles", tags=["角色权限"])

ReadRole = Annotated[CurrentUser, Depends(require_permissions("role:read"))]
CreateRole = Annotated[CurrentUser, Depends(require_permissions("role:create"))]
UpdateRole = Annotated[CurrentUser, Depends(require_permissions("role:update"))]
DeleteRole = Annotated[CurrentUser, Depends(require_permissions("role:delete"))]


@router.get("", response_model=list[RoleRead], summary="角色列表")
async def list_roles(current: ReadRole, db: DBDep) -> list[RoleRead]:
    return await RoleService(db).list_roles(current.organization_id)


@router.post(
    "", response_model=RoleRead, status_code=status.HTTP_201_CREATED, summary="创建角色"
)
async def create_role(payload: RoleCreate, current: CreateRole, db: DBDep) -> RoleRead:
    return await RoleService(db).create_role(current.organization_id, payload)


@router.get("/{role_id}", response_model=RoleRead, summary="角色详情")
async def get_role(role_id: int, current: ReadRole, db: DBDep) -> RoleRead:
    return await RoleService(db).get_role(current.organization_id, role_id)


@router.put("/{role_id}", response_model=RoleRead, summary="修改角色（含权限分配）")
async def update_role(
    role_id: int, payload: RoleUpdate, current: UpdateRole, db: DBDep
) -> RoleRead:
    return await RoleService(db).update_role(current.organization_id, role_id, payload)


@router.delete("/{role_id}", response_model=MessageResponse, summary="删除角色")
async def delete_role(role_id: int, current: DeleteRole, db: DBDep) -> MessageResponse:
    await RoleService(db).delete_role(current.organization_id, role_id)
    return MessageResponse(message="角色已删除")
