from __future__ import annotations

from sqlalchemy import func, or_, select

from app.models.ticket import Ticket, TicketComment, TicketHistory
from app.repositories.base import BaseRepository
from app.schemas.ticket import TicketQuery


class TicketRepository(BaseRepository[Ticket]):
    model = Ticket

    async def get_in_org(self, organization_id: int, ticket_id: int) -> Ticket | None:
        stmt = select(Ticket).where(
            Ticket.organization_id == organization_id, Ticket.id == ticket_id
        )
        return await self.session.scalar(stmt)

    async def search(
        self,
        organization_id: int,
        query: TicketQuery,
        *,
        user_id: int,
        see_all: bool,
        offset: int,
        limit: int,
    ) -> tuple[list[Ticket], int]:
        stmt = select(Ticket).where(Ticket.organization_id == organization_id)

        if query.keyword:
            like = f"%{query.keyword.strip()}%"
            stmt = stmt.where(or_(Ticket.title.like(like), Ticket.ticket_no.like(like)))
        if query.status:
            stmt = stmt.where(Ticket.status == query.status)
        if query.priority:
            stmt = stmt.where(Ticket.priority == query.priority)
        # 没有处理权限的人只能看到自己提的和指派给自己的
        if query.mine or not see_all:
            stmt = stmt.where(
                or_(Ticket.creator_id == user_id, Ticket.assignee_id == user_id)
            )

        total = await self.session.scalar(
            select(func.count()).select_from(stmt.subquery())
        )
        rows = await self.session.scalars(
            stmt.order_by(Ticket.id.desc()).offset(offset).limit(limit)
        )
        return list(rows), int(total or 0)


class TicketCommentRepository(BaseRepository[TicketComment]):
    model = TicketComment

    async def list_for(self, ticket_id: int) -> list[TicketComment]:
        stmt = (
            select(TicketComment)
            .where(TicketComment.ticket_id == ticket_id)
            .order_by(TicketComment.id.asc())
        )
        return list(await self.session.scalars(stmt))


class TicketHistoryRepository(BaseRepository[TicketHistory]):
    model = TicketHistory

    async def list_for(self, ticket_id: int) -> list[TicketHistory]:
        stmt = (
            select(TicketHistory)
            .where(TicketHistory.ticket_id == ticket_id)
            .order_by(TicketHistory.id.asc())
        )
        return list(await self.session.scalars(stmt))
