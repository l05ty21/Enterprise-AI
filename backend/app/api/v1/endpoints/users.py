from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, DBDep, require_permissions
from app.schemas.common import MessageResponse, Page, PageParams, page_params
from app.schemas.user import UserCreate, UserQuery, UserRead, UserUpdate
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["用户管理"])

ReadUser = Annotated[CurrentUser, Depends(require_permissions("user:read"))]
CreateUser = Annotated[CurrentUser, Depends(require_permissions("user:create"))]
UpdateUser = Annotated[CurrentUser, Depends(require_permissions("user:update"))]
DeleteUser = Annotated[CurrentUser, Depends(require_permissions("user:delete"))]


@router.get("", response_model=Page[UserRead], summary="用户列表")
async def list_users(
    current: ReadUser,
    db: DBDep,
    page: Annotated[PageParams, Depends(page_params)],
    keyword: str | None = Query(default=None, description="用户名/姓名/邮箱模糊匹配"),
    department_id: int | None = Query(default=None),
    status_value: int | None = Query(default=None, alias="status", ge=0, le=1),
    role_id: int | None = Query(default=None),
) -> Page[UserRead]:
    query = UserQuery(
        keyword=keyword,
        department_id=department_id,
        status=status_value,
        role_id=role_id,
    )
    return await UserService(db).list_users(current.organization_id, query, page)


@router.post(
    "", response_model=UserRead, status_code=status.HTTP_201_CREATED, summary="创建用户"
)
async def create_user(payload: UserCreate, current: CreateUser, db: DBDep) -> UserRead:
    return await UserService(db).create_user(current.organization_id, payload)


@router.get("/{user_id}", response_model=UserRead, summary="用户详情")
async def get_user(user_id: int, current: ReadUser, db: DBDep) -> UserRead:
    return await UserService(db).get_user(current.organization_id, user_id)


@router.put("/{user_id}", response_model=UserRead, summary="修改用户")
async def update_user(
    user_id: int, payload: UserUpdate, current: UpdateUser, db: DBDep
) -> UserRead:
    return await UserService(db).update_user(
        current.organization_id, user_id, payload, operator_id=current.id
    )


@router.delete("/{user_id}", response_model=MessageResponse, summary="禁用用户（软删除）")
async def disable_user(user_id: int, current: DeleteUser, db: DBDep) -> MessageResponse:
    await UserService(db).disable_user(
        current.organization_id, user_id, operator_id=current.id
    )
    return MessageResponse(message="用户已禁用")
