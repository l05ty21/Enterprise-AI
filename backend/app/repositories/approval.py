from __future__ import annotations

from sqlalchemy import exists, func, select

from app.models.approval import ApprovalInstance, ApprovalTask, ApprovalTemplate
from app.repositories.base import BaseRepository


class ApprovalTemplateRepository(BaseRepository[ApprovalTemplate]):
    model = ApprovalTemplate

    async def first_for_org(self, organization_id: int) -> ApprovalTemplate | None:
        stmt = (
            select(ApprovalTemplate)
            .where(
                ApprovalTemplate.organization_id == organization_id,
                ApprovalTemplate.status == 1,
            )
            .order_by(ApprovalTemplate.id.asc())
        )
        return await self.session.scalar(stmt)


class ApprovalInstanceRepository(BaseRepository[ApprovalInstance]):
    model = ApprovalInstance

    async def get_in_org(
        self, organization_id: int, instance_id: int
    ) -> ApprovalInstance | None:
        stmt = select(ApprovalInstance).where(
            ApprovalInstance.organization_id == organization_id,
            ApprovalInstance.id == instance_id,
        )
        return await self.session.scalar(stmt)

    async def search(
        self,
        organization_id: int,
        *,
        user_id: int,
        applicant_only: bool,
        todo_only: bool,
        see_all: bool,
        status: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[ApprovalInstance], int]:
        stmt = select(ApprovalInstance).where(
            ApprovalInstance.organization_id == organization_id
        )
        if status:
            stmt = stmt.where(ApprovalInstance.status == status)

        mine_as_applicant = ApprovalInstance.applicant_id == user_id
        mine_as_approver = exists().where(
            ApprovalTask.instance_id == ApprovalInstance.id,
            ApprovalTask.approver_id == user_id,
        )
        pending_for_me = exists().where(
            ApprovalTask.instance_id == ApprovalInstance.id,
            ApprovalTask.approver_id == user_id,
            ApprovalTask.status == "pending",
        )

        if todo_only:
            stmt = stmt.where(pending_for_me)
        elif applicant_only:
            stmt = stmt.where(mine_as_applicant)
        elif not see_all:
            stmt = stmt.where(mine_as_applicant | mine_as_approver)

        total = await self.session.scalar(
            select(func.count()).select_from(stmt.subquery())
        )
        rows = await self.session.scalars(
            stmt.order_by(ApprovalInstance.id.desc()).offset(offset).limit(limit)
        )
        return list(rows), int(total or 0)


class ApprovalTaskRepository(BaseRepository[ApprovalTask]):
    model = ApprovalTask

    async def list_for_instance(self, instance_id: int) -> list[ApprovalTask]:
        stmt = (
            select(ApprovalTask)
            .where(ApprovalTask.instance_id == instance_id)
            .order_by(ApprovalTask.node_index.asc(), ApprovalTask.id.asc())
        )
        return list(await self.session.scalars(stmt))

    async def pending_for(
        self, instance_id: int, approver_id: int
    ) -> ApprovalTask | None:
        stmt = select(ApprovalTask).where(
            ApprovalTask.instance_id == instance_id,
            ApprovalTask.approver_id == approver_id,
            ApprovalTask.status == "pending",
        )
        return await self.session.scalar(stmt)
