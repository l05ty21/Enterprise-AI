from __future__ import annotations

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin
from app.db.types import bigint_unsigned


class Attachment(Base, CreatedAtMixin):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(bigint_unsigned(), primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("organizations.id"), nullable=False
    )
    biz_type: Mapped[str] = mapped_column(String(32), nullable=False)
    biz_id: Mapped[int] = mapped_column(bigint_unsigned(), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(bigint_unsigned(), nullable=False, server_default="0")
    content_type: Mapped[str | None] = mapped_column(String(128))
    uploader_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("users.id"), nullable=False
    )

    __table_args__ = (
        Index("idx_attachment_biz", "organization_id", "biz_type", "biz_id"),
    )
