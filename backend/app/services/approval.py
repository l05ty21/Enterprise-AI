"""审批业务逻辑：发起、待办、通过/驳回。

一期只做单节点审批（一个审批人），但数据模型保留 tasks / node_index，
后续加多级审批时不用改表。
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.exceptions import BadRequestError, NotFoundError, PermissionDenied
from app.models.approval import ApprovalInstance, ApprovalTask, ApprovalTemplate
from app.repositories.approval import (
    ApprovalInstanceRepository,
    ApprovalTaskRepository,
    ApprovalTemplateRepository,
)
from app.repositories.department import DepartmentRepository
from app.repositories.user import UserRepository
from app.schemas.approval import (
    ApprovalCreate,
    ApprovalDecision,
    ApprovalDetail,
    ApprovalRead,
    ApprovalTaskRead,
)
from app.schemas.common import Page, PageParams
from app.utils.datetime import now_naive

DEFAULT_TEMPLATE_NAME = "通用审批"


class ApprovalService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.instances = ApprovalInstanceRepository(session)
        self.tasks = ApprovalTaskRepository(session)
        self.templates = ApprovalTemplateRepository(session)
        self.users = UserRepository(session)
        self.depts = DepartmentRepository(session)

    # ------------------------------------------------------------------ 辅助
    async def _ensure_template(self, organization_id: int) -> ApprovalTemplate:
        template = await self.templates.first_for_org(organization_id)
        if template is not None:
            return template
        template = ApprovalTemplate(
            organization_id=organization_id,
            name=DEFAULT_TEMPLATE_NAME,
            business_type="general",
            flow_config={"nodes": [{"index": 1, "name": "负责人审批"}]},
            status=1,
        )
        await self.templates.add(template)
        await self.session.commit()
        await self.session.refresh(template)
        return template

    async def _resolve_approver(self, current: CurrentUser) -> int:
        """优先找部门负责人，其次找企业里第一个有「审批操作」权限的人。"""
        user = current.user
        if user.department_id:
            dept = await self.depts.get_in_org(current.organization_id, user.department_id)
            if dept is not None and dept.leader_id and dept.leader_id != user.id:
                leader = await self.users.get_in_org(
                    current.organization_id, dept.leader_id
                )
                if leader is not None and leader.status == 1:
                    return leader.id

        candidates = await self.users.ids_with_permission(
            current.organization_id, "approval:approve"
        )
        candidates = [i for i in candidates if i != user.id]
        if not candidates:
            raise BadRequestError("当前企业还没有可用的审批人（需要「审批操作」权限）")
        return candidates[0]

    def _to_read(
        self,
        instance: ApprovalInstance,
        names: dict[int, str],
        *,
        can_decide: bool = False,
        current_approver_id: int | None = None,
    ) -> ApprovalRead:
        data = instance.business_data or {}
        return ApprovalRead(
            id=instance.id,
            title=str(data.get("title") or "(无标题)"),
            business_type=instance.business_type,
            amount=data.get("amount"),
            reason=data.get("reason"),
            status=instance.status,
            applicant_id=instance.applicant_id,
            applicant_name=names.get(instance.applicant_id),
            current_approver_name=names.get(current_approver_id or 0),
            can_decide=can_decide,
            created_at=instance.created_at,
        )

    # ------------------------------------------------------------------ 查询
    async def list_approvals(
        self,
        current: CurrentUser,
        *,
        scope: str,
        status: str | None,
        page: PageParams,
    ) -> Page[ApprovalRead]:
        see_all = current.has("approval:approve")
        instances, total = await self.instances.search(
            current.organization_id,
            user_id=current.id,
            applicant_only=scope == "mine",
            todo_only=scope == "todo",
            see_all=see_all,
            status=status,
            offset=page.offset,
            limit=page.limit,
        )

        ids = {i.applicant_id for i in instances}
        names = await self.users.names_by_ids(list(ids))

        items: list[ApprovalRead] = []
        for inst in instances:
            pending_task = await self.tasks.pending_for(inst.id, current.id)
            if pending_task is not None and pending_task.approver_id not in names:
                names.update(await self.users.names_by_ids([pending_task.approver_id]))
            items.append(
                self._to_read(
                    inst,
                    names,
                    can_decide=pending_task is not None and inst.status == "pending",
                    current_approver_id=(
                        pending_task.approver_id if pending_task is not None else None
                    ),
                )
            )

        return Page[ApprovalRead](
            items=items, total=total, page=page.page, page_size=page.page_size
        )

    async def _get_visible(
        self, current: CurrentUser, instance_id: int
    ) -> ApprovalInstance:
        instance = await self.instances.get_in_org(current.organization_id, instance_id)
        if instance is None:
            raise NotFoundError("审批不存在")
        if instance.applicant_id == current.id or current.has("approval:approve"):
            return instance
        task = await self.tasks.pending_for(instance.id, current.id)
        if task is None and not any(
            t.approver_id == current.id
            for t in await self.tasks.list_for_instance(instance.id)
        ):
            raise NotFoundError("审批不存在")
        return instance

    async def get_detail(self, current: CurrentUser, instance_id: int) -> ApprovalDetail:
        instance = await self._get_visible(current, instance_id)
        tasks = await self.tasks.list_for_instance(instance.id)
        names = await self.users.names_by_ids(
            [instance.applicant_id, *[t.approver_id for t in tasks]]
        )
        pending_task = await self.tasks.pending_for(instance.id, current.id)
        base = self._to_read(
            instance,
            names,
            can_decide=pending_task is not None and instance.status == "pending",
            current_approver_id=pending_task.approver_id if pending_task else None,
        )
        return ApprovalDetail(
            **base.model_dump(),
            tasks=[
                ApprovalTaskRead(
                    id=t.id,
                    approver_id=t.approver_id,
                    approver_name=names.get(t.approver_id),
                    status=t.status,
                    comment=t.comment,
                    handled_at=t.handled_at,
                )
                for t in tasks
            ],
        )

    # ------------------------------------------------------------------ 写入
    async def create(self, current: CurrentUser, payload: ApprovalCreate) -> ApprovalRead:
        template = await self._ensure_template(current.organization_id)
        approver_id = await self._resolve_approver(current)

        instance = ApprovalInstance(
            organization_id=current.organization_id,
            template_id=template.id,
            applicant_id=current.id,
            business_type=payload.business_type,
            business_data={
                "title": payload.title.strip(),
                "amount": float(payload.amount) if payload.amount is not None else None,
                "reason": payload.reason,
            },
            status="pending",
            current_node=1,
        )
        await self.instances.add(instance)
        await self.tasks.add(
            ApprovalTask(
                instance_id=instance.id,
                approver_id=approver_id,
                node_index=1,
                status="pending",
            )
        )
        await self.session.commit()
        await self.session.refresh(instance)

        names = await self.users.names_by_ids([instance.applicant_id, approver_id])
        return self._to_read(
            instance, names, can_decide=False, current_approver_id=approver_id
        )

    async def decide(
        self, current: CurrentUser, instance_id: int, payload: ApprovalDecision
    ) -> ApprovalDetail:
        instance = await self.instances.get_in_org(current.organization_id, instance_id)
        if instance is None:
            raise NotFoundError("审批不存在")
        if instance.status != "pending":
            raise BadRequestError("这条审批已经处理过了")

        task = await self.tasks.pending_for(instance.id, current.id)
        if task is None:
            raise PermissionDenied("这条审批不在你的待办里")

        approved = payload.action == "approve"
        task.status = "approved" if approved else "rejected"
        task.comment = payload.comment
        task.handled_at = now_naive()
        instance.status = "approved" if approved else "rejected"

        await self.session.commit()
        return await self.get_detail(current, instance.id)
