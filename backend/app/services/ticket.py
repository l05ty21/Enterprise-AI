"""工单业务逻辑：创建、查询、流转、评论。"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.exceptions import BadRequestError, NotFoundError, PermissionDenied
from app.models.ticket import Ticket, TicketComment, TicketHistory
from app.repositories.ticket import (
    TicketCommentRepository,
    TicketHistoryRepository,
    TicketRepository,
)
from app.repositories.user import UserRepository
from app.schemas.common import Page, PageParams
from app.schemas.ticket import (
    TicketCommentCreate,
    TicketCommentRead,
    TicketCreate,
    TicketDetail,
    TicketHistoryRead,
    TicketQuery,
    TicketRead,
    TicketUpdate,
)

# 允许的状态流转：处理人把工单往下推，创建人可以关闭自己的单子
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"processing", "closed"},
    "processing": {"resolved", "closed", "pending"},
    "resolved": {"closed", "processing"},
    "closed": set(),
}

STATUS_LABEL = {
    "pending": "待处理",
    "processing": "处理中",
    "resolved": "已解决",
    "closed": "已关闭",
}


class TicketService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.tickets = TicketRepository(session)
        self.comments = TicketCommentRepository(session)
        self.histories = TicketHistoryRepository(session)
        self.users = UserRepository(session)

    # ------------------------------------------------------------------ 查询
    async def _names(self, ids: set[int]) -> dict[int, str]:
        return await self.users.names_by_ids([i for i in ids if i])

    def _to_read(self, ticket: Ticket, names: dict[int, str]) -> TicketRead:
        return TicketRead(
            id=ticket.id,
            ticket_no=ticket.ticket_no,
            title=ticket.title,
            description=ticket.description,
            priority=ticket.priority,
            status=ticket.status,
            creator_id=ticket.creator_id,
            creator_name=names.get(ticket.creator_id),
            assignee_id=ticket.assignee_id,
            assignee_name=names.get(ticket.assignee_id or 0),
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
        )

    async def list_tickets(
        self, current: CurrentUser, query: TicketQuery, page: PageParams
    ) -> Page[TicketRead]:
        see_all = current.has("ticket:update")
        tickets, total = await self.tickets.search(
            current.organization_id,
            query,
            user_id=current.id,
            see_all=see_all,
            offset=page.offset,
            limit=page.limit,
        )
        ids = {t.creator_id for t in tickets} | {t.assignee_id or 0 for t in tickets}
        names = await self._names(ids)
        return Page[TicketRead](
            items=[self._to_read(t, names) for t in tickets],
            total=total,
            page=page.page,
            page_size=page.page_size,
        )

    async def _get_visible(self, current: CurrentUser, ticket_id: int) -> Ticket:
        ticket = await self.tickets.get_in_org(current.organization_id, ticket_id)
        if ticket is None:
            raise NotFoundError("工单不存在")
        if not current.has("ticket:update") and current.id not in (
            ticket.creator_id,
            ticket.assignee_id,
        ):
            # 不暴露别人工单的存在性
            raise NotFoundError("工单不存在")
        return ticket

    async def get_detail(self, current: CurrentUser, ticket_id: int) -> TicketDetail:
        ticket = await self._get_visible(current, ticket_id)
        comments = await self.comments.list_for(ticket.id)
        histories = await self.histories.list_for(ticket.id)
        names = await self._names(
            {ticket.creator_id, ticket.assignee_id or 0}
            | {c.user_id for c in comments}
            | {h.operator_id for h in histories}
        )
        base = self._to_read(ticket, names)
        return TicketDetail(
            **base.model_dump(),
            comments=[
                TicketCommentRead(
                    id=c.id,
                    user_id=c.user_id,
                    user_name=names.get(c.user_id),
                    content=c.content,
                    created_at=c.created_at,
                )
                for c in comments
            ],
            histories=[
                TicketHistoryRead(
                    id=h.id,
                    operator_id=h.operator_id,
                    operator_name=names.get(h.operator_id),
                    old_status=h.old_status,
                    new_status=h.new_status,
                    remark=h.remark,
                    created_at=h.created_at,
                )
                for h in histories
            ],
        )

    # ------------------------------------------------------------------ 写入
    async def create(self, current: CurrentUser, payload: TicketCreate) -> TicketRead:
        ticket = Ticket(
            organization_id=current.organization_id,
            ticket_no=f"T{datetime.now():%Y%m%d}-{uuid4().hex[:5].upper()}",
            title=payload.title.strip(),
            description=payload.description,
            creator_id=current.id,
            priority=payload.priority,
            status="pending",
        )
        await self.tickets.add(ticket)
        self.session.add(
            TicketHistory(
                ticket_id=ticket.id,
                operator_id=current.id,
                old_status=None,
                new_status="pending",
                remark="创建工单",
            )
        )
        await self.session.commit()
        await self.session.refresh(ticket)
        names = await self._names({ticket.creator_id})
        return self._to_read(ticket, names)

    async def update(
        self, current: CurrentUser, ticket_id: int, payload: TicketUpdate
    ) -> TicketDetail:
        """只有具备 ticket:update 的人能改状态/指派；创建人可以关闭自己的单子。"""
        ticket = await self._get_visible(current, ticket_id)
        is_manager = current.has("ticket:update")
        is_creator = ticket.creator_id == current.id

        if not is_manager:
            closing_own = (
                payload.status == "closed"
                and is_creator
                and ticket.status in {"pending", "processing", "resolved"}
                and payload.assignee_id is None
                and payload.priority is None
            )
            if not closing_own:
                raise PermissionDenied("没有处理工单的权限")

        old_status = ticket.status
        remark = payload.remark

        if payload.assignee_id is not None:
            assignee = await self.users.get_in_org(
                current.organization_id, payload.assignee_id
            )
            if assignee is None:
                raise BadRequestError("指派对象不存在或不属于当前企业")
            ticket.assignee_id = assignee.id
            # 指派即进入处理中
            if ticket.status == "pending" and payload.status is None:
                ticket.status = "processing"

        if payload.priority is not None:
            ticket.priority = payload.priority

        if payload.status is not None and payload.status != ticket.status:
            allowed = ALLOWED_TRANSITIONS.get(ticket.status, set())
            if payload.status not in allowed:
                raise BadRequestError(
                    f"不能从「{STATUS_LABEL.get(ticket.status, ticket.status)}」"
                    f"直接变成「{STATUS_LABEL.get(payload.status, payload.status)}」"
                )
            if payload.status in {"processing", "resolved"} and ticket.assignee_id is None:
                # 谁处理就默认指派给谁，避免出现"处理中但没人负责"
                ticket.assignee_id = current.id
            ticket.status = payload.status

        if ticket.status != old_status:
            self.session.add(
                TicketHistory(
                    ticket_id=ticket.id,
                    operator_id=current.id,
                    old_status=old_status,
                    new_status=ticket.status,
                    remark=remark or "状态变更",
                )
            )
        await self.session.commit()
        return await self.get_detail(current, ticket.id)

    async def add_comment(
        self, current: CurrentUser, ticket_id: int, payload: TicketCommentCreate
    ) -> TicketCommentRead:
        ticket = await self._get_visible(current, ticket_id)
        comment = TicketComment(
            ticket_id=ticket.id, user_id=current.id, content=payload.content.strip()
        )
        await self.comments.add(comment)
        await self.session.commit()
        await self.session.refresh(comment)
        names = await self._names({current.id})
        return TicketCommentRead(
            id=comment.id,
            user_id=comment.user_id,
            user_name=names.get(comment.user_id),
            content=comment.content,
            created_at=comment.created_at,
        )
