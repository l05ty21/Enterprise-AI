from __future__ import annotations

from sqlalchemy import func, select, update

from app.models.system import Notification
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    model = Notification

    async def list_for_user(
        self,
        organization_id: int,
        user_id: int,
        *,
        unread_only: bool,
        offset: int,
        limit: int,
    ) -> tuple[list[Notification], int]:
        stmt = select(Notification).where(
            Notification.organization_id == organization_id,
            Notification.user_id == user_id,
        )
        if unread_only:
            stmt = stmt.where(Notification.is_read.is_(False))
        total = await self.session.scalar(
            select(func.count()).select_from(stmt.subquery())
        )
        rows = await self.session.scalars(
            stmt.order_by(Notification.id.desc()).offset(offset).limit(limit)
        )
        return list(rows), int(total or 0)

    async def unread_count(self, organization_id: int, user_id: int) -> int:
        stmt = select(func.count()).where(
            Notification.organization_id == organization_id,
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        return int(await self.session.scalar(stmt) or 0)

    async def get_for_user(
        self, organization_id: int, user_id: int, notification_id: int
    ) -> Notification | None:
        stmt = select(Notification).where(
            Notification.organization_id == organization_id,
            Notification.user_id == user_id,
            Notification.id == notification_id,
        )
        return await self.session.scalar(stmt)

    async def mark_all_read(self, organization_id: int, user_id: int) -> int:
        result = await self.session.execute(
            update(Notification)
            .where(
                Notification.organization_id == organization_id,
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
            .values(is_read=True)
        )
        return int(result.rowcount or 0)
