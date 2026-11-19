from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin
from app.db.types import bigint_unsigned


class Role(Base, CreatedAtMixin):
    """角色。角色属于某个企业，code 在企业内唯一。"""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(bigint_unsigned(), primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("organizations.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))

    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uk_role_org_code"),
    )


class Permission(Base, CreatedAtMixin):
    """权限点。code 形如 user:create、ticket:read，全局唯一。"""

    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(bigint_unsigned(), primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    code: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="menu / button / api"
    )
    parent_id: Mapped[int | None] = mapped_column(
        bigint_unsigned(), ForeignKey("permissions.id"), nullable=True
    )
    path: Mapped[str | None] = mapped_column(String(255))
    method: Mapped[str | None] = mapped_column(String(16))


class UserRole(Base):
    """用户-角色关联。"""

    __tablename__ = "user_roles"

    user_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("users.id"), primary_key=True
    )
    role_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("roles.id"), primary_key=True
    )


class RolePermission(Base):
    """角色-权限关联。"""

    __tablename__ = "role_permissions"

    role_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("roles.id"), primary_key=True
    )
    permission_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("permissions.id"), primary_key=True
    )
