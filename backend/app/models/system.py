from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin
from app.db.types import bigint_unsigned, long_text


class Notification(Base, CreatedAtMixin):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(bigint_unsigned(), primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("organizations.id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("users.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str | None] = mapped_column(long_text())
    type: Mapped[str | None] = mapped_column(String(32))
    link_type: Mapped[str | None] = mapped_column(String(32))
    link_id: Mapped[int | None] = mapped_column(bigint_unsigned(), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")

    __table_args__ = (Index("idx_notification_user", "user_id", "is_read"),)


class OperationLog(Base, CreatedAtMixin):
    __tablename__ = "operation_logs"

    id: Mapped[int] = mapped_column(bigint_unsigned(), primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("organizations.id"), nullable=False
    )
    user_id: Mapped[int | None] = mapped_column(
        bigint_unsigned(), ForeignKey("users.id"), nullable=True
    )
    module: Mapped[str | None] = mapped_column(String(64))
    action: Mapped[str | None] = mapped_column(String(64))
    request_method: Mapped[str | None] = mapped_column(String(16))
    request_path: Mapped[str | None] = mapped_column(String(255))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    detail: Mapped[dict | None] = mapped_column(JSON)

    __table_args__ = (Index("idx_operation_time", "organization_id", "created_at"),)


class LoginLog(Base, CreatedAtMixin):
    __tablename__ = "login_logs"

    id: Mapped[int] = mapped_column(bigint_unsigned(), primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("organizations.id"), nullable=False
    )
    user_id: Mapped[int | None] = mapped_column(
        bigint_unsigned(), ForeignKey("users.id"), nullable=True
    )
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(long_text())
    status: Mapped[str | None] = mapped_column(String(32))
