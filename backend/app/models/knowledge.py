from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, JSON, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin
from app.db.types import bigint_unsigned, long_text


class KnowledgeBase(Base, CreatedAtMixin):
    __tablename__ = "knowledge_bases"

    id: Mapped[int] = mapped_column(bigint_unsigned(), primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("organizations.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(long_text())
    owner_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("users.id"), nullable=False
    )
    department_id: Mapped[int | None] = mapped_column(
        bigint_unsigned(), ForeignKey("departments.id"), nullable=True
    )
    visibility: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="private", comment="private / department / org"
    )
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="1")

    __table_args__ = (Index("idx_kb_org", "organization_id"),)


class Document(Base, CreatedAtMixin):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(bigint_unsigned(), primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("organizations.id"), nullable=False
    )
    kb_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("knowledge_bases.id"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_hash: Mapped[str | None] = mapped_column(String(128))
    file_type: Mapped[str | None] = mapped_column(String(32))
    file_size: Mapped[int | None] = mapped_column(bigint_unsigned(), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="pending")
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    error_message: Mapped[str | None] = mapped_column(long_text())
    created_by: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("users.id"), nullable=False
    )

    __table_args__ = (
        Index("idx_document_kb", "kb_id"),
        Index("idx_document_status", "status"),
    )


class DocumentChunk(Base, CreatedAtMixin):
    """文档切片元数据；向量本体存放在 Milvus，这里只保存定位信息。"""

    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(bigint_unsigned(), primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("organizations.id"), nullable=False
    )
    document_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("documents.id"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(long_text(), nullable=False)
    vector_id: Mapped[str] = mapped_column(String(128), nullable=False)
    collection_name: Mapped[str] = mapped_column(String(128), nullable=False)
    embedding_model: Mapped[str | None] = mapped_column(String(128))
    # 列名必须是 metadata，用 chunk_metadata 作为 Python 属性名避开 SQLAlchemy 保留字
    chunk_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uk_document_chunk"),
        UniqueConstraint("collection_name", "vector_id", name="uk_vector_id"),
    )
