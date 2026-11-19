from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, DBDep, require_permissions
from app.schemas.common import MessageResponse
from app.schemas.department import DepartmentCreate, DepartmentRead, DepartmentUpdate
from app.services.department import DepartmentService

router = APIRouter(prefix="/departments", tags=["部门管理"])

ReadDept = Annotated[CurrentUser, Depends(require_permissions("department:read"))]
CreateDept = Annotated[CurrentUser, Depends(require_permissions("department:create"))]
UpdateDept = Annotated[CurrentUser, Depends(require_permissions("department:update"))]
DeleteDept = Annotated[CurrentUser, Depends(require_permissions("department:delete"))]


@router.get("", response_model=list[DepartmentRead], summary="部门树")
async def department_tree(current: ReadDept, db: DBDep) -> list[DepartmentRead]:
    return await DepartmentService(db).tree(current.organization_id)


@router.post(
    "",
    response_model=DepartmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="创建部门",
)
async def create_department(
    payload: DepartmentCreate, current: CreateDept, db: DBDep
) -> DepartmentRead:
    return await DepartmentService(db).create(current.organization_id, payload)


@router.put("/{department_id}", response_model=DepartmentRead, summary="修改部门")
async def update_department(
    department_id: int, payload: DepartmentUpdate, current: UpdateDept, db: DBDep
) -> DepartmentRead:
    return await DepartmentService(db).update(
        current.organization_id, department_id, payload
    )


@router.delete("/{department_id}", response_model=MessageResponse, summary="删除部门")
async def delete_department(
    department_id: int, current: DeleteDept, db: DBDep
) -> MessageResponse:
    await DepartmentService(db).delete(current.organization_id, department_id)
    return MessageResponse(message="部门已删除")
