from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, MetaData, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# MySQL 的 DEFAULT 只接受 CURRENT_TIMESTAMP 这种关键字写法，
# 用 text() 而不是 func.now()，否则会生成 MySQL 不认的 DEFAULT now()。
CURRENT_TIMESTAMP = text("CURRENT_TIMESTAMP")


class Base(DeclarativeBase):
    """所有 ORM 模型的基类，统一约束命名，方便 Alembic 生成稳定的迁移。"""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=CURRENT_TIMESTAMP,
        comment="创建时间",
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=CURRENT_TIMESTAMP,
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=CURRENT_TIMESTAMP,
        onupdate=func.now(),
        comment="更新时间",
    )
