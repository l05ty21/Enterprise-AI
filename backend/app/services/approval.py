"""审批业务逻辑：发起、待办、多级串签通过/驳回。"""

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
from app.services.attachment import AttachmentService
from app.services.notification import NotificationService
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
            raise BadRequestError(
                "没有可用的审批人：审批不能由申请人自己完成，"
                "请先在「用户管理」里添加一个具备「审批操作」权限的成员"
            )
        return candidates[0]

    async def _resolve_approver_ids(
        self, current: CurrentUser, payload: ApprovalCreate
    ) -> list[int]:
        if payload.approver_ids:
            ordered: list[int] = []
            seen: set[int] = set()
            for raw in payload.approver_ids:
                uid = int(raw)
                if uid in seen:
                    continue
                if uid == current.id:
                    raise BadRequestError("不能选择自己作为审批人")
                user = await self.users.get_in_org(current.organization_id, uid)
                if user is None or user.status != 1:
                    raise BadRequestError(f"审批人无效或不属于当前企业：{uid}")
                ordered.append(uid)
                seen.add(uid)
            if not ordered:
                raise BadRequestError("请至少选择一位审批人")
            return ordered
        return [await self._resolve_approver(current)]

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
            current_node=instance.current_node,
            current_approver_name=names.get(current_approver_id or 0),
            can_decide=can_decide,
            created_at=instance.created_at,
        )

    async def _current_pending_approver(
        self, instance_id: int
    ) -> ApprovalTask | None:
        tasks = await self.tasks.list_for_instance(instance_id)
        for task in tasks:
            if task.status == "pending":
                return task
        return None

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
            current_pending = await self._current_pending_approver(inst.id)
            approver_id = (
                pending_task.approver_id
                if pending_task is not None
                else (current_pending.approver_id if current_pending else None)
            )
            if approver_id and approver_id not in names:
                names.update(await self.users.names_by_ids([approver_id]))
            items.append(
                self._to_read(
                    inst,
                    names,
                    can_decide=pending_task is not None and inst.status == "pending",
                    current_approver_id=approver_id,
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
        current_pending = await self._current_pending_approver(instance.id)
        base = self._to_read(
            instance,
            names,
            can_decide=pending_task is not None and instance.status == "pending",
            current_approver_id=(
                pending_task.approver_id
                if pending_task
                else (current_pending.approver_id if current_pending else None)
            ),
        )
        attachments = await AttachmentService(self.session).list_briefs(
            current.organization_id, "approval", instance.id
        )
        return ApprovalDetail(
            **base.model_dump(),
            tasks=[
                ApprovalTaskRead(
                    id=t.id,
                    approver_id=t.approver_id,
                    approver_name=names.get(t.approver_id),
                    node_index=t.node_index,
                    status=t.status,
                    comment=t.comment,
                    handled_at=t.handled_at,
                )
                for t in tasks
            ],
            attachments=attachments,
        )

    # ------------------------------------------------------------------ 写入
    async def create(self, current: CurrentUser, payload: ApprovalCreate) -> ApprovalRead:
        template = await self._ensure_template(current.organization_id)
        approver_ids = await self._resolve_approver_ids(current, payload)
        names_preview = await self.users.names_by_ids(approver_ids)

        instance = ApprovalInstance(
            organization_id=current.organization_id,
            template_id=template.id,
            applicant_id=current.id,
            business_type=payload.business_type,
            business_data={
                "title": payload.title.strip(),
                "amount": float(payload.amount) if payload.amount is not None else None,
                "reason": payload.reason,
                "flow": [
                    {
                        "index": index,
                        "approver_id": uid,
                        "approver_name": names_preview.get(uid),
                    }
                    for index, uid in enumerate(approver_ids, start=1)
                ],
            },
            status="pending",
            current_node=1,
        )
        await self.instances.add(instance)

        for index, uid in enumerate(approver_ids, start=1):
            await self.tasks.add(
                ApprovalTask(
                    instance_id=instance.id,
                    approver_id=uid,
                    node_index=index,
                    status="pending" if index == 1 else "waiting",
                )
            )

        notify = NotificationService(self.session)
        await notify.notify(
            organization_id=current.organization_id,
            user_id=approver_ids[0],
            title=f"待你审批：{payload.title.strip()}",
            content="有新的审批单据到达你的待办",
            type="approval_todo",
            link_type="approval",
            link_id=instance.id,
        )

        await self.session.commit()
        await self.session.refresh(instance)

        names = await self.users.names_by_ids([instance.applicant_id, approver_ids[0]])
        return self._to_read(
            instance, names, can_decide=False, current_approver_id=approver_ids[0]
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

        notify = NotificationService(self.session)
        title = str((instance.business_data or {}).get("title") or "审批")

        if not approved:
            instance.status = "rejected"
            await notify.notify(
                organization_id=current.organization_id,
                user_id=instance.applicant_id,
                title=f"审批已驳回：{title}",
                content=payload.comment or "审批人驳回了你的申请",
                type="approval_rejected",
                link_type="approval",
                link_id=instance.id,
            )
        else:
            tasks = await self.tasks.list_for_instance(instance.id)
            next_task = next(
                (t for t in tasks if t.node_index == task.node_index + 1),
                None,
            )
            if next_task is not None:
                next_task.status = "pending"
                instance.current_node = next_task.node_index
                await notify.notify(
                    organization_id=current.organization_id,
                    user_id=next_task.approver_id,
                    title=f"待你审批：{title}",
                    content=f"第 {next_task.node_index} 级审批已到达你的待办",
                    type="approval_todo",
                    link_type="approval",
                    link_id=instance.id,
                )
            else:
                instance.status = "approved"
                await notify.notify(
                    organization_id=current.organization_id,
                    user_id=instance.applicant_id,
                    title=f"审批已通过：{title}",
                    content="全部审批节点已通过",
                    type="approval_approved",
                    link_type="approval",
                    link_id=instance.id,
                )

        await self.session.commit()
        return await self.get_detail(current, instance.id)
