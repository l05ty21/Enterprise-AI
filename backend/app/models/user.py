from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Index, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.db.types import bigint_unsigned


class User(Base, TimestampMixin):
    """用户。除超级管理员外，所有查询都必须带上 organization_id。"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(bigint_unsigned(), primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("organizations.id"), nullable=False
    )
    department_id: Mapped[int | None] = mapped_column(
        bigint_unsigned(), ForeignKey("departments.id"), nullable=True
    )
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    real_name: Mapped[str | None] = mapped_column(String(64))
    email: Mapped[str | None] = mapped_column(String(128))
    phone: Mapped[str | None] = mapped_column(String(32))
    avatar: Mapped[str | None] = mapped_column(String(512))
    status: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="1", comment="1 正常 / 0 禁用"
    )
    must_change_password: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default="0",
        comment="1 首次登录须改密 / 0 正常",
    )
    last_login_at: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (
        UniqueConstraint("organization_id", "username", name="uk_user_org_username"),
        UniqueConstraint("organization_id", "email", name="uk_user_org_email"),
        Index("idx_user_department", "department_id"),
    )
