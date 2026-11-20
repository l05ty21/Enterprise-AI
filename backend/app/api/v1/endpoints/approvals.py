from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, DBDep, require_permissions
from app.schemas.approval import (
    ApprovalCreate,
    ApprovalDecision,
    ApprovalDetail,
    ApprovalRead,
)
from app.schemas.common import Page, PageParams, page_params
from app.services.approval import ApprovalService

router = APIRouter(prefix="/approvals", tags=["审批"])

ReadApproval = Annotated[CurrentUser, Depends(require_permissions("approval:read"))]
CreateApproval = Annotated[CurrentUser, Depends(require_permissions("approval:create"))]
DecideApproval = Annotated[CurrentUser, Depends(require_permissions("approval:approve"))]


@router.get("", response_model=Page[ApprovalRead], summary="审批列表")
async def list_approvals(
    current: ReadApproval,
    db: DBDep,
    page: Annotated[PageParams, Depends(page_params)],
    scope: str = Query(
        default="all",
        pattern="^(all|mine|todo)$",
        description="all=我能看到的 / mine=我发起的 / todo=待我审批",
    ),
    status_value: str | None = Query(default=None, alias="status"),
) -> Page[ApprovalRead]:
    return await ApprovalService(db).list_approvals(
        current, scope=scope, status=status_value, page=page
    )


@router.post(
    "",
    response_model=ApprovalRead,
    status_code=status.HTTP_201_CREATED,
    summary="发起审批",
)
async def create_approval(
    payload: ApprovalCreate, current: CreateApproval, db: DBDep
) -> ApprovalRead:
    return await ApprovalService(db).create(current, payload)


@router.get("/{instance_id}", response_model=ApprovalDetail, summary="审批详情")
async def get_approval(
    instance_id: int, current: ReadApproval, db: DBDep
) -> ApprovalDetail:
    return await ApprovalService(db).get_detail(current, instance_id)


@router.post(
    "/{instance_id}/decision",
    response_model=ApprovalDetail,
    summary="通过 / 驳回",
)
async def decide(
    instance_id: int, payload: ApprovalDecision, current: DecideApproval, db: DBDep
) -> ApprovalDetail:
    return await ApprovalService(db).decide(current, instance_id, payload)
