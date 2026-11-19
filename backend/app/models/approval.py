from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Index, Integer, JSON, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, TimestampMixin
from app.db.types import bigint_unsigned, long_text


class ApprovalTemplate(Base, CreatedAtMixin):
    __tablename__ = "approval_templates"

    id: Mapped[int] = mapped_column(bigint_unsigned(), primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("organizations.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    business_type: Mapped[str] = mapped_column(String(64), nullable=False)
    flow_config: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="1")


class ApprovalInstance(Base, TimestampMixin):
    __tablename__ = "approval_instances"

    id: Mapped[int] = mapped_column(bigint_unsigned(), primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("organizations.id"), nullable=False
    )
    template_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("approval_templates.id"), nullable=False
    )
    applicant_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("users.id"), nullable=False
    )
    business_type: Mapped[str] = mapped_column(String(64), nullable=False)
    business_data: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="pending")
    current_node: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")


class ApprovalTask(Base, CreatedAtMixin):
    __tablename__ = "approval_tasks"

    id: Mapped[int] = mapped_column(bigint_unsigned(), primary_key=True, autoincrement=True)
    instance_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("approval_instances.id"), nullable=False
    )
    approver_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("users.id"), nullable=False
    )
    node_index: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="pending")
    comment: Mapped[str | None] = mapped_column(long_text())
    handled_at: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (Index("idx_approval_task", "approver_id", "status"),)
