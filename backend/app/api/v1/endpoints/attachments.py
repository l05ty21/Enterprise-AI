from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import CurrentUserDep, DBDep
from app.core.exceptions import NotFoundError
from app.schemas.attachment import AttachmentRead
from app.schemas.common import MessageResponse
from app.services.attachment import AttachmentService

router = APIRouter(prefix="/attachments", tags=["附件"])


@router.get("/{attachment_id}/download", summary="下载附件")
async def download_attachment(
    attachment_id: int, current: CurrentUserDep, db: DBDep
) -> FileResponse:
    row = await AttachmentService(db).get_for_download(current, attachment_id)
    path = Path(row.file_path)
    if not path.exists():
        raise NotFoundError("附件文件已丢失")
    return FileResponse(
        path,
        filename=row.filename,
        media_type=row.content_type or "application/octet-stream",
    )


@router.delete("/{attachment_id}", response_model=MessageResponse, summary="删除附件")
async def delete_attachment(
    attachment_id: int, current: CurrentUserDep, db: DBDep
) -> MessageResponse:
    await AttachmentService(db).delete(current, attachment_id)
    return MessageResponse(message="附件已删除")


@router.post(
    "/tickets/{ticket_id}",
    response_model=AttachmentRead,
    summary="上传工单附件",
)
async def upload_ticket_attachment(
    ticket_id: int,
    current: CurrentUserDep,
    db: DBDep,
    file: UploadFile = File(...),
) -> AttachmentRead:
    return await AttachmentService(db).upload(current, "ticket", ticket_id, file)


@router.get(
    "/tickets/{ticket_id}",
    response_model=list[AttachmentRead],
    summary="工单附件列表",
)
async def list_ticket_attachments(
    ticket_id: int, current: CurrentUserDep, db: DBDep
) -> list[AttachmentRead]:
    return await AttachmentService(db).list(current, "ticket", ticket_id)


@router.post(
    "/approvals/{approval_id}",
    response_model=AttachmentRead,
    summary="上传审批附件",
)
async def upload_approval_attachment(
    approval_id: int,
    current: CurrentUserDep,
    db: DBDep,
    file: UploadFile = File(...),
) -> AttachmentRead:
    return await AttachmentService(db).upload(current, "approval", approval_id, file)


@router.get(
    "/approvals/{approval_id}",
    response_model=list[AttachmentRead],
    summary="审批附件列表",
)
async def list_approval_attachments(
    approval_id: int, current: CurrentUserDep, db: DBDep
) -> list[AttachmentRead]:
    return await AttachmentService(db).list(current, "approval", approval_id)
