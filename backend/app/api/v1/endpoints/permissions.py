from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, DBDep, require_permissions
from app.schemas.role import PermissionRead
from app.services.role import RoleService

router = APIRouter(prefix="/permissions", tags=["角色权限"])

ReadPermission = Annotated[CurrentUser, Depends(require_permissions("role:read"))]


@router.get("", response_model=list[PermissionRead], summary="全部权限点")
async def list_permissions(current: ReadPermission, db: DBDep) -> list[PermissionRead]:
    return await RoleService(db).list_permissions()
