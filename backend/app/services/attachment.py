"""工单 / 审批附件：本地磁盘存储。"""

from __future__ import annotations

import re
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.config import settings
from app.core.exceptions import BadRequestError, NotFoundError, PermissionDenied
from app.models.attachment import Attachment
from app.repositories.approval import ApprovalInstanceRepository, ApprovalTaskRepository
from app.repositories.attachment import AttachmentRepository
from app.repositories.ticket import TicketRepository
from app.repositories.user import UserRepository
from app.schemas.attachment import AttachmentBrief, AttachmentRead

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".txt",
    ".zip",
}
MAX_BYTES = 20 * 1024 * 1024
SAFE_NAME = re.compile(r"[^\w.\u4e00-\u9fff\-]+")


class AttachmentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.attachments = AttachmentRepository(session)
        self.tickets = TicketRepository(session)
        self.approvals = ApprovalInstanceRepository(session)
        self.tasks = ApprovalTaskRepository(session)
        self.users = UserRepository(session)

    async def _names(self, ids: set[int]) -> dict[int, str]:
        return await self.users.names_by_ids([i for i in ids if i])

    def _to_read(self, row: Attachment, names: dict[int, str]) -> AttachmentRead:
        return AttachmentRead(
            id=row.id,
            biz_type=row.biz_type,
            biz_id=row.biz_id,
            filename=row.filename,
            file_size=row.file_size,
            content_type=row.content_type,
            uploader_id=row.uploader_id,
            uploader_name=names.get(row.uploader_id),
            created_at=row.created_at,
        )

    def _to_brief(self, row: Attachment, names: dict[int, str]) -> AttachmentBrief:
        return AttachmentBrief(
            id=row.id,
            filename=row.filename,
            file_size=row.file_size,
            content_type=row.content_type,
            uploader_name=names.get(row.uploader_id),
            created_at=row.created_at,
        )

    async def list_briefs(
        self, organization_id: int, biz_type: str, biz_id: int
    ) -> list[AttachmentBrief]:
        rows = await self.attachments.list_for(organization_id, biz_type, biz_id)
        names = await self._names({r.uploader_id for r in rows})
        return [self._to_brief(r, names) for r in rows]

    async def _assert_biz_access(
        self, current: CurrentUser, biz_type: str, biz_id: int, *, write: bool
    ) -> None:
        if biz_type == "ticket":
            ticket = await self.tickets.get_in_org(current.organization_id, biz_id)
            if ticket is None:
                raise NotFoundError("工单不存在")
            if write:
                if not (
                    current.has("ticket:update")
                    or current.id in {ticket.creator_id, ticket.assignee_id}
                ):
                    raise PermissionDenied("没有上传附件的权限")
            elif not (
                current.has("ticket:update")
                or current.id in {ticket.creator_id, ticket.assignee_id}
            ):
                raise NotFoundError("工单不存在")
            return

        if biz_type == "approval":
            instance = await self.approvals.get_in_org(current.organization_id, biz_id)
            if instance is None:
                raise NotFoundError("审批不存在")
            tasks = await self.tasks.list_for_instance(instance.id)
            involved = {instance.applicant_id, *[t.approver_id for t in tasks]}
            if write:
                if current.id != instance.applicant_id and not current.has(
                    "approval:approve"
                ):
                    raise PermissionDenied("没有上传附件的权限")
            elif current.id not in involved and not current.has("approval:approve"):
                raise NotFoundError("审批不存在")
            return

        raise BadRequestError("不支持的业务类型")

    @staticmethod
    def _save_file(organization_id: int, filename: str, data: bytes) -> str:
        safe = SAFE_NAME.sub("_", filename).strip("._") or "file"
        stored = f"{uuid4().hex}_{safe}"
        directory = Path(settings.UPLOAD_DIR) / str(organization_id) / "attachments"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / stored
        path.write_bytes(data)
        return str(path)

    async def upload(
        self,
        current: CurrentUser,
        biz_type: str,
        biz_id: int,
        file: UploadFile,
    ) -> AttachmentRead:
        await self._assert_biz_access(current, biz_type, biz_id, write=True)
        filename = file.filename or "unnamed"
        suffix = Path(filename).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise BadRequestError(
                f"不支持的文件类型，允许：{', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )
        data = await file.read()
        if not data:
            raise BadRequestError("文件为空")
        if len(data) > MAX_BYTES:
            raise BadRequestError("文件不能超过 20MB")

        stored_path = self._save_file(current.organization_id, filename, data)
        row = Attachment(
            organization_id=current.organization_id,
            biz_type=biz_type,
            biz_id=biz_id,
            filename=filename,
            file_path=stored_path,
            file_size=len(data),
            content_type=file.content_type,
            uploader_id=current.id,
        )
        await self.attachments.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        names = await self._names({current.id})
        return self._to_read(row, names)

    async def list(
        self, current: CurrentUser, biz_type: str, biz_id: int
    ) -> list[AttachmentRead]:
        await self._assert_biz_access(current, biz_type, biz_id, write=False)
        rows = await self.attachments.list_for(
            current.organization_id, biz_type, biz_id
        )
        names = await self._names({r.uploader_id for r in rows})
        return [self._to_read(r, names) for r in rows]

    async def get_for_download(
        self, current: CurrentUser, attachment_id: int
    ) -> Attachment:
        row = await self.attachments.get_in_org(current.organization_id, attachment_id)
        if row is None:
            raise NotFoundError("附件不存在")
        await self._assert_biz_access(
            current, row.biz_type, row.biz_id, write=False
        )
        return row

    async def delete(self, current: CurrentUser, attachment_id: int) -> None:
        row = await self.attachments.get_in_org(current.organization_id, attachment_id)
        if row is None:
            raise NotFoundError("附件不存在")
        can_manage = (
            (row.biz_type == "ticket" and current.has("ticket:update"))
            or (row.biz_type == "approval" and current.has("approval:approve"))
            or row.uploader_id == current.id
        )
        if not can_manage:
            raise PermissionDenied("只能删除自己上传的附件")
        path = Path(row.file_path)
        await self.attachments.delete(row)
        await self.session.commit()
        if path.exists():
            path.unlink(missing_ok=True)
