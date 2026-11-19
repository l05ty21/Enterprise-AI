from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.api.deps import CurrentUser, DBDep, require_permissions
from app.core.exceptions import BadRequestError
from app.schemas.common import MessageResponse
from app.schemas.knowledge import (
    DocumentRead,
    KnowledgeBaseCreate,
    KnowledgeBaseRead,
    KnowledgeBaseUpdate,
    SearchHit,
    SearchRequest,
)
from app.services.knowledge import KnowledgeService

router = APIRouter(prefix="/knowledge-bases", tags=["知识库"])

ReadKB = Annotated[CurrentUser, Depends(require_permissions("knowledge:read"))]
CreateKB = Annotated[CurrentUser, Depends(require_permissions("knowledge:create"))]
UpdateKB = Annotated[CurrentUser, Depends(require_permissions("knowledge:update"))]
DeleteKB = Annotated[CurrentUser, Depends(require_permissions("knowledge:delete"))]


# ------------------------------------------------------------------ 知识库
@router.get("", response_model=list[KnowledgeBaseRead], summary="知识库列表")
async def list_bases(current: ReadKB, db: DBDep) -> list[KnowledgeBaseRead]:
    return await KnowledgeService(db).list_bases(current.organization_id)


@router.post(
    "",
    response_model=KnowledgeBaseRead,
    status_code=status.HTTP_201_CREATED,
    summary="新建知识库",
)
async def create_base(
    payload: KnowledgeBaseCreate, current: CreateKB, db: DBDep
) -> KnowledgeBaseRead:
    return await KnowledgeService(db).create_base(
        current.organization_id, current.id, payload
    )


@router.get(
    "/{kb_id}", response_model=KnowledgeBaseRead, summary="知识库详情"
)
async def get_base(
    kb_id: int, current: ReadKB, db: DBDep
) -> KnowledgeBaseRead:
    return await KnowledgeService(db).get_base(current.organization_id, kb_id)


@router.put("/{kb_id}", response_model=KnowledgeBaseRead, summary="修改知识库")
async def update_base(
    kb_id: int, payload: KnowledgeBaseUpdate, current: UpdateKB, db: DBDep
) -> KnowledgeBaseRead:
    return await KnowledgeService(db).update_base(
        current.organization_id, kb_id, payload
    )


@router.delete("/{kb_id}", response_model=MessageResponse, summary="删除知识库")
async def delete_base(
    kb_id: int, current: DeleteKB, db: DBDep
) -> MessageResponse:
    await KnowledgeService(db).delete_base(current.organization_id, kb_id)
    return MessageResponse(message="知识库及其文档已删除")


# ------------------------------------------------------------------ 文档
@router.get(
    "/{kb_id}/documents",
    response_model=list[DocumentRead],
    summary="文档列表",
)
async def list_documents(
    kb_id: int, current: ReadKB, db: DBDep
) -> list[DocumentRead]:
    return await KnowledgeService(db).list_documents(current.organization_id, kb_id)


@router.post(
    "/{kb_id}/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    summary="上传文档（自动解析、切片、向量化）",
)
async def upload_document(
    kb_id: int,
    current: CreateKB,
    db: DBDep,
    file: Annotated[UploadFile, File(description="txt / md / csv / pdf / docx")],
) -> DocumentRead:
    data = await file.read()
    if not data:
        raise BadRequestError("上传的文件为空")
    return await KnowledgeService(db).upload_document(
        current.organization_id,
        current.id,
        kb_id,
        file.filename or "未命名文档",
        data,
    )


@router.delete(
    "/{kb_id}/documents/{document_id}",
    response_model=MessageResponse,
    summary="删除文档（连同切片与向量）",
)
async def delete_document(
    kb_id: int, document_id: int, current: DeleteKB, db: DBDep
) -> MessageResponse:
    await KnowledgeService(db).delete_document(current.organization_id, document_id)
    return MessageResponse(message="文档已删除")


# ------------------------------------------------------------------ 检索
@router.post("/search/query", response_model=list[SearchHit], summary="语义检索")
async def search(
    payload: SearchRequest, current: ReadKB, db: DBDep
) -> list[SearchHit]:
    """不经过大模型，直接返回相似度最高的切片，用于调试和前端预览。"""
    return await KnowledgeService(db).search(
        current.organization_id,
        payload.query,
        kb_ids=payload.kb_ids,
        top_k=payload.top_k,
    )
