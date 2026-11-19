from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, TimestampMixin
from app.db.types import bigint_unsigned, long_text


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(bigint_unsigned(), primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("organizations.id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("users.id"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(255))
    conversation_type: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="chat"
    )

    __table_args__ = (Index("idx_conversation_user", "user_id"),)


class ChatMessage(Base, CreatedAtMixin):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(bigint_unsigned(), primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("conversations.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="system / user / assistant / tool"
    )
    content: Mapped[str | None] = mapped_column(long_text())
    model_name: Mapped[str | None] = mapped_column(String(128))
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    references_json: Mapped[list | dict | None] = mapped_column(JSON)
    tool_calls: Mapped[list | dict | None] = mapped_column(JSON)

    __table_args__ = (Index("idx_chat_conversation", "conversation_id"),)


class AIModelConfig(Base, CreatedAtMixin):
    """模型配置。api_key_encrypted 只保存密文，禁止明文落库。"""

    __tablename__ = "ai_model_configs"

    id: Mapped[int] = mapped_column(bigint_unsigned(), primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("organizations.id"), nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="openai / azure / ollama / qwen ..."
    )
    model_type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="llm / embedding / rerank"
    )
    base_url: Mapped[str | None] = mapped_column(String(512))
    api_key_encrypted: Mapped[str | None] = mapped_column(long_text())
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    parameters: Mapped[dict | None] = mapped_column(JSON)

    __table_args__ = (Index("idx_ai_config_org", "organization_id"),)


class AIUsageLog(Base, CreatedAtMixin):
    __tablename__ = "ai_usage_logs"

    id: Mapped[int] = mapped_column(bigint_unsigned(), primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("organizations.id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("users.id"), nullable=False
    )
    model_name: Mapped[str | None] = mapped_column(String(128))
    provider: Mapped[str | None] = mapped_column(String(64))
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    status: Mapped[str | None] = mapped_column(String(32))

    __table_args__ = (Index("idx_ai_usage_time", "organization_id", "created_at"),)
