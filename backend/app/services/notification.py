"""站内通知：写入与查询。"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.exceptions import NotFoundError
from app.models.system import Notification
from app.repositories.notification import NotificationRepository
from app.schemas.common import Page, PageParams
from app.schemas.notification import NotificationRead, UnreadCount


class NotificationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.notifications = NotificationRepository(session)

    @staticmethod
    def _to_read(row: Notification) -> NotificationRead:
        return NotificationRead(
            id=row.id,
            title=row.title,
            content=row.content,
            type=row.type,
            link_type=row.link_type,
            link_id=row.link_id,
            is_read=bool(row.is_read),
            created_at=row.created_at,
        )

    async def notify(
        self,
        *,
        organization_id: int,
        user_id: int,
        title: str,
        content: str | None = None,
        type: str | None = None,
        link_type: str | None = None,
        link_id: int | None = None,
        commit: bool = False,
    ) -> None:
        if not user_id:
            return
        self.session.add(
            Notification(
                organization_id=organization_id,
                user_id=user_id,
                title=title,
                content=content,
                type=type,
                link_type=link_type,
                link_id=link_id,
                is_read=False,
            )
        )
        if commit:
            await self.session.commit()

    async def list(
        self,
        current: CurrentUser,
        page: PageParams,
        *,
        unread_only: bool = False,
    ) -> Page[NotificationRead]:
        rows, total = await self.notifications.list_for_user(
            current.organization_id,
            current.id,
            unread_only=unread_only,
            offset=page.offset,
            limit=page.limit,
        )
        return Page[NotificationRead](
            items=[self._to_read(r) for r in rows],
            total=total,
            page=page.page,
            page_size=page.page_size,
        )

    async def unread_count(self, current: CurrentUser) -> UnreadCount:
        count = await self.notifications.unread_count(
            current.organization_id, current.id
        )
        return UnreadCount(count=count)

    async def mark_read(self, current: CurrentUser, notification_id: int) -> NotificationRead:
        row = await self.notifications.get_for_user(
            current.organization_id, current.id, notification_id
        )
        if row is None:
            raise NotFoundError("通知不存在")
        row.is_read = True
        await self.session.commit()
        await self.session.refresh(row)
        return self._to_read(row)

    async def mark_all_read(self, current: CurrentUser) -> UnreadCount:
        await self.notifications.mark_all_read(current.organization_id, current.id)
        await self.session.commit()
        return UnreadCount(count=0)
