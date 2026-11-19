from __future__ import annotations

from sqlalchemy import ForeignKey, Index, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, TimestampMixin
from app.db.types import bigint_unsigned


class Organization(Base, TimestampMixin):
    """企业租户。所有业务表都通过 organization_id 做数据隔离。"""

    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(bigint_unsigned(), primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="企业名称")
    code: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, comment="企业编码"
    )
    status: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="1", comment="1 启用 / 0 停用"
    )


class Department(Base, CreatedAtMixin):
    """部门，通过 parent_id 组成树形结构。"""

    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(bigint_unsigned(), primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("organizations.id"), nullable=False
    )
    parent_id: Mapped[int | None] = mapped_column(
        bigint_unsigned(), ForeignKey("departments.id"), nullable=True, comment="上级部门"
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    # 负责人不建外键：users 与 departments 互相引用会形成建表环，业务层校验即可
    leader_id: Mapped[int | None] = mapped_column(bigint_unsigned(), nullable=True)

    __table_args__ = (Index("idx_department_org", "organization_id"),)
