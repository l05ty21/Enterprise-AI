from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin
from app.db.types import bigint_unsigned, long_text


class Project(Base, CreatedAtMixin):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(bigint_unsigned(), primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("organizations.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(long_text())
    owner_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("users.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="active")
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)


class Task(Base, CreatedAtMixin):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(bigint_unsigned(), primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("organizations.id"), nullable=False
    )
    project_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("projects.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(long_text())
    assignee_id: Mapped[int | None] = mapped_column(
        bigint_unsigned(), ForeignKey("users.id"), nullable=True
    )
    creator_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("users.id"), nullable=False
    )
    priority: Mapped[str] = mapped_column(String(32), nullable=False, server_default="medium")
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="todo")
    due_date: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (Index("idx_task_assignee", "assignee_id", "status"),)


class TaskComment(Base, CreatedAtMixin):
    __tablename__ = "task_comments"

    id: Mapped[int] = mapped_column(bigint_unsigned(), primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("tasks.id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        bigint_unsigned(), ForeignKey("users.id"), nullable=False
    )
    content: Mapped[str] = mapped_column(long_text(), nullable=False)
