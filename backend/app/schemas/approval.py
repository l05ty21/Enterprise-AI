from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

ApprovalStatus = Literal["pending", "approved", "rejected"]
BusinessType = Literal["expense", "leave", "purchase", "other"]


class ApprovalCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200, description="审批标题")
    business_type: BusinessType = Field(default="other", description="业务类型")
    amount: Decimal | None = Field(
        default=None, ge=0, le=99999999, description="金额（报销/采购时填写）"
    )
    reason: str | None = Field(default=None, max_length=2000, description="申请说明")


class ApprovalDecision(BaseModel):
    action: Literal["approve", "reject"]
    comment: str | None = Field(default=None, max_length=500)


class ApprovalTaskRead(BaseModel):
    id: int
    approver_id: int
    approver_name: str | None = None
    status: str
    comment: str | None = None
    handled_at: datetime | None = None


class ApprovalRead(BaseModel):
    id: int
    title: str
    business_type: str
    amount: Decimal | None = None
    reason: str | None = None
    status: str
    applicant_id: int
    applicant_name: str | None = None
    current_approver_name: str | None = None
    can_decide: bool = False
    created_at: datetime | None = None


class ApprovalDetail(ApprovalRead):
    tasks: list[ApprovalTaskRead] = Field(default_factory=list)
