from __future__ import annotations

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, TimestampMixin
from app.db.types import bigint_unsigned, long_text


class Ticket(Base, TimestampMixin):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(bigint_unsigned(), primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("organizations.id"), nullable=False
    )
    ticket_no: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(long_text())
    creator_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("users.id"), nullable=False
    )
    assignee_id: Mapped[int | None] = mapped_column(
        bigint_unsigned(), ForeignKey("users.id"), nullable=True
    )
    priority: Mapped[str] = mapped_column(String(32), nullable=False, server_default="medium")
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="pending")

    __table_args__ = (
        UniqueConstraint("organization_id", "ticket_no", name="uk_ticket_no"),
        Index("idx_ticket_assignee", "assignee_id", "status"),
    )


class TicketComment(Base, CreatedAtMixin):
    __tablename__ = "ticket_comments"

    id: Mapped[int] = mapped_column(bigint_unsigned(), primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("tickets.id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("users.id"), nullable=False
    )
    content: Mapped[str] = mapped_column(long_text(), nullable=False)


class TicketHistory(Base, CreatedAtMixin):
    __tablename__ = "ticket_histories"

    id: Mapped[int] = mapped_column(bigint_unsigned(), primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("tickets.id"), nullable=False
    )
    operator_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("users.id"), nullable=False
    )
    old_status: Mapped[str | None] = mapped_column(String(32))
    new_status: Mapped[str | None] = mapped_column(String(32))
    remark: Mapped[str | None] = mapped_column(long_text())
