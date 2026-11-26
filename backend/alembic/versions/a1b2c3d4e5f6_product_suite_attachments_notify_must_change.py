"""product suite: attachments, notification links, must_change_password

Revision ID: a1b2c3d4e5f6
Revises: f30e28d12d78
Create Date: 2026-11-26
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f30e28d12d78"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "attachments",
        sa.Column("id", mysql.BIGINT(unsigned=True).with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("organization_id", mysql.BIGINT(unsigned=True).with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("biz_type", sa.String(length=32), nullable=False),
        sa.Column("biz_id", mysql.BIGINT(unsigned=True).with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=512), nullable=False),
        sa.Column("file_size", mysql.BIGINT(unsigned=True).with_variant(sa.Integer(), "sqlite"), server_default="0", nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("uploader_id", mysql.BIGINT(unsigned=True).with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name=op.f("fk_attachments_organization_id_organizations")),
        sa.ForeignKeyConstraint(["uploader_id"], ["users.id"], name=op.f("fk_attachments_uploader_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_attachments")),
    )
    with op.batch_alter_table("attachments", schema=None) as batch_op:
        batch_op.create_index(
            "idx_attachment_biz",
            ["organization_id", "biz_type", "biz_id"],
            unique=False,
        )

    with op.batch_alter_table("notifications", schema=None) as batch_op:
        batch_op.add_column(sa.Column("link_type", sa.String(length=32), nullable=True))
        batch_op.add_column(
            sa.Column(
                "link_id",
                mysql.BIGINT(unsigned=True).with_variant(sa.Integer(), "sqlite"),
                nullable=True,
            )
        )

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "must_change_password",
                sa.SmallInteger(),
                server_default="0",
                nullable=False,
                comment="1 首次登录须改密 / 0 正常",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("must_change_password")

    with op.batch_alter_table("notifications", schema=None) as batch_op:
        batch_op.drop_column("link_id")
        batch_op.drop_column("link_type")

    with op.batch_alter_table("attachments", schema=None) as batch_op:
        batch_op.drop_index("idx_attachment_biz")
    op.drop_table("attachments")
