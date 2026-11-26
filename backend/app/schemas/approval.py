from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.attachment import AttachmentBrief

ApprovalStatus = Literal["pending", "approved", "rejected"]
BusinessType = Literal["expense", "leave", "purchase", "other"]


class ApprovalCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200, description="审批标题")
    business_type: BusinessType = Field(default="other", description="业务类型")
    amount: Decimal | None = Field(
        default=None, ge=0, le=99999999, description="金额（报销/采购时填写）"
    )
    reason: str | None = Field(default=None, max_length=2000, description="申请说明")
    approver_ids: list[int] | None = Field(
        default=None,
        min_length=1,
        max_length=10,
        description="有序审批人列表；不传则自动解析单级审批人",
    )


class ApprovalDecision(BaseModel):
    action: Literal["approve", "reject"]
    comment: str | None = Field(default=None, max_length=500)


class ApprovalTaskRead(BaseModel):
    id: int
    approver_id: int
    approver_name: str | None = None
    node_index: int = 1
    status: str
    comment: str | None = None
    handled_at: datetime | None = None


class ApprovalRead(BaseModel):
    id: int
    title: str
    business_type: str
    # business_data 里存的是 JSON number，用 float 回吐，避免 Decimal 被序列化成字符串
    amount: float | None = None
    reason: str | None = None
    status: str
    applicant_id: int
    applicant_name: str | None = None
    current_node: int = 1
    current_approver_name: str | None = None
    can_decide: bool = False
    created_at: datetime | None = None


class ApprovalDetail(ApprovalRead):
    tasks: list[ApprovalTaskRead] = Field(default_factory=list)
    attachments: list[AttachmentBrief] = Field(default_factory=list)
