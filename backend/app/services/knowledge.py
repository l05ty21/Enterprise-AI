"""知识库业务逻辑：知识库 CRUD、文档入库（解析→切片→向量化）、检索。"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import gateway
from app.ai.vector_store import MySQLVectorStore, encode_vector
from app.core.config import settings
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models.knowledge import Document, DocumentChunk, KnowledgeBase
from app.repositories.knowledge import (
    DocumentChunkRepository,
    DocumentRepository,
    KnowledgeBaseRepository,
)
from app.schemas.knowledge import (
    Citation,
    DocumentRead,
    KnowledgeBaseCreate,
    KnowledgeBaseRead,
    KnowledgeBaseUpdate,
    SearchHit,
)
from app.utils.documents import chunk_text, extension_of, extract_text

logger = logging.getLogger(__name__)

# 单个文档最多入库的切片数。切片太多会让上传请求长时间阻塞（要反复调用 embedding），
# 1 GiB 的机器上也要控制单次内存占用。
MAX_CHUNKS_PER_DOC = 300
SNIPPET_LENGTH = 160


def _to_base_read(
    base: KnowledgeBase, document_count: int, chunk_count: int
) -> KnowledgeBaseRead:
    return KnowledgeBaseRead(
        id=base.id,
        name=base.name,
        description=base.description,
        owner_id=base.owner_id,
        visibility=base.visibility,
        status=base.status,
        document_count=document_count,
        chunk_count=chunk_count,
        created_at=base.created_at,
    )


def _to_document_read(document: Document) -> DocumentRead:
    return DocumentRead(
        id=document.id,
        kb_id=document.kb_id,
        filename=document.filename,
        file_type=document.file_type,
        file_size=document.file_size,
        status=document.status,
        chunk_count=document.chunk_count,
        error_message=document.error_message,
        created_at=document.created_at,
    )


class KnowledgeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.bases = KnowledgeBaseRepository(session)
        self.docs = DocumentRepository(session)
        self.chunks = DocumentChunkRepository(session)
        self.vectors = MySQLVectorStore(session)

    # ---------------------------------------------------------------- 知识库
    async def list_bases(self, organization_id: int) -> list[KnowledgeBaseRead]:
        bases = await self.bases.list_in_org(organization_id)
        result: list[KnowledgeBaseRead] = []
        for base in bases:
            result.append(
                _to_base_read(
                    base,
                    await self.docs.count_by_kb(organization_id, base.id),
                    await self.docs.chunks_of_kb(organization_id, base.id),
                )
            )
        return result

    async def create_base(
        self, organization_id: int, owner_id: int, payload: KnowledgeBaseCreate
    ) -> KnowledgeBaseRead:
        name = payload.name.strip()
        if await self.bases.name_exists(organization_id, name):
            raise ConflictError("同名知识库已存在")
        base = KnowledgeBase(
            organization_id=organization_id,
            name=name,
            description=payload.description,
            owner_id=owner_id,
            visibility=payload.visibility,
            status=1,
        )
        await self.bases.add(base)
        await self.session.commit()
        await self.session.refresh(base)
        return _to_base_read(base, 0, 0)

    async def get_base(self, organization_id: int, kb_id: int) -> KnowledgeBaseRead:
        base = await self.bases.get_in_org(organization_id, kb_id)
        if base is None:
            raise NotFoundError("知识库不存在")
        return _to_base_read(
            base,
            await self.docs.count_by_kb(organization_id, kb_id),
            await self.docs.chunks_of_kb(organization_id, kb_id),
        )

    async def update_base(
        self, organization_id: int, kb_id: int, payload: KnowledgeBaseUpdate
    ) -> KnowledgeBaseRead:
        base = await self.bases.get_in_org(organization_id, kb_id)
        if base is None:
            raise NotFoundError("知识库不存在")

        data = payload.model_dump(exclude_unset=True)
        if "name" in data and data["name"] and data["name"].strip() != base.name:
            if await self.bases.name_exists(organization_id, data["name"].strip(), base.id):
                raise ConflictError("同名知识库已存在")
            data["name"] = data["name"].strip()

        for field, value in data.items():
            setattr(base, field, value)
        await self.session.commit()
        return _to_base_read(
            base,
            await self.docs.count_by_kb(organization_id, kb_id),
            await self.docs.chunks_of_kb(organization_id, kb_id),
        )

    async def delete_base(self, organization_id: int, kb_id: int) -> None:
        base = await self.bases.get_in_org(organization_id, kb_id)
        if base is None:
            raise NotFoundError("知识库不存在")

        documents = await self.docs.list_by_kb(organization_id, kb_id)
        await self.chunks.delete_by_kb(organization_id, kb_id)
        for document in documents:
            self._remove_file(document.file_path)
            await self.docs.delete(document)
        await self.bases.delete(base)
        await self.session.commit()

    # ---------------------------------------------------------------- 文档
    async def list_documents(
        self, organization_id: int, kb_id: int
    ) -> list[DocumentRead]:
        base = await self.bases.get_in_org(organization_id, kb_id)
        if base is None:
            raise NotFoundError("知识库不存在")
        return [
            _to_document_read(item)
            for item in await self.docs.list_by_kb(organization_id, kb_id)
        ]

    async def upload_document(
        self,
        organization_id: int,
        user_id: int,
        kb_id: int,
        filename: str,
        data: bytes,
    ) -> DocumentRead:
        base = await self.bases.get_in_org(organization_id, kb_id)
        if base is None:
            raise NotFoundError("知识库不存在")

        text = extract_text(filename, data)
        pieces = chunk_text(text)
        if not pieces:
            raise BadRequestError("文档内容为空，未提取到可用文本")

        truncated = False
        if len(pieces) > MAX_CHUNKS_PER_DOC:
            pieces = pieces[:MAX_CHUNKS_PER_DOC]
            truncated = True

        stored_path = self._save_file(organization_id, filename, data)
        document = Document(
            organization_id=organization_id,
            kb_id=kb_id,
            filename=filename,
            file_path=stored_path,
            file_type=extension_of(filename).lstrip(".") or None,
            file_size=len(data),
            status="processing",
            chunk_count=0,
            created_by=user_id,
        )
        await self.docs.add(document)
        await self.session.commit()
        await self.session.refresh(document)

        try:
            vectors = await gateway.embed(
                self.session, organization_id=organization_id, texts=pieces
            )
        except Exception as exc:  # noqa: BLE001 —— 失败也要落库，便于排查
            document.status = "failed"
            document.error_message = str(exc)[:2000]
            await self.session.commit()
            raise

        collection = f"kb_{kb_id}"
        for index, (piece, vector) in enumerate(zip(pieces, vectors, strict=False)):
            self.session.add(
                DocumentChunk(
                    organization_id=organization_id,
                    document_id=document.id,
                    chunk_index=index,
                    content=piece,
                    vector_id=f"{document.id}:{index}",
                    collection_name=collection,
                    embedding_model=settings.AI_EMBEDDING_MODEL,
                    embedding=encode_vector(vector),
                    embedding_dim=len(vector),
                    chunk_metadata={"truncated": truncated} if truncated else None,
                )
            )

        document.status = "ready"
        document.chunk_count = len(pieces)
        await self.session.commit()
        return _to_document_read(document)

    async def delete_document(self, organization_id: int, document_id: int) -> None:
        document = await self.docs.get_in_org(organization_id, document_id)
        if document is None:
            raise NotFoundError("文档不存在")
        await self.chunks.delete_by_document(document_id)
        self._remove_file(document.file_path)
        await self.docs.delete(document)
        await self.session.commit()

    # ---------------------------------------------------------------- 检索
    async def search(
        self,
        organization_id: int,
        query: str,
        *,
        kb_ids: list[int] | None = None,
        top_k: int | None = None,
    ) -> list[SearchHit]:
        vector = (await gateway.embed(
            self.session, organization_id=organization_id, texts=[query]
        ))[0]
        hits = await self.vectors.search(
            organization_id,
            vector,
            query_text=query,
            kb_ids=kb_ids,
            top_k=top_k or settings.RAG_TOP_K,
            min_score=settings.RAG_MIN_SCORE,
            vector_weight=settings.RAG_VECTOR_WEIGHT,
        )
        return [
            SearchHit(
                chunk_id=hit.chunk.id,
                document_id=hit.chunk.document_id,
                filename=hit.filename,
                content=hit.chunk.content,
                score=round(hit.score, 4),
            )
            for hit in hits
        ]

    async def build_context(
        self,
        organization_id: int,
        query: str,
        *,
        kb_ids: list[int] | None = None,
        top_k: int | None = None,
    ) -> tuple[str, list[Citation]]:
        """把检索到的片段拼成提示词上下文，同时返回引用列表。"""
        hits = await self.search(
            organization_id, query, kb_ids=kb_ids, top_k=top_k
        )
        if not hits:
            return "", []

        blocks = []
        for index, hit in enumerate(hits, start=1):
            blocks.append(f"[{index}] 来源：{hit.filename}\n{hit.content}")
        context = "\n\n".join(blocks)

        citations = [
            Citation(
                document_id=hit.document_id,
                filename=hit.filename,
                chunk_id=hit.chunk_id,
                score=hit.score,
                snippet=hit.content[:SNIPPET_LENGTH],
            )
            for hit in hits
        ]
        return context, citations

    # ---------------------------------------------------------------- 文件
    @staticmethod
    def _save_file(organization_id: int, filename: str, data: bytes) -> str:
        suffix = extension_of(filename) or ".bin"
        directory = Path(settings.UPLOAD_DIR) / str(organization_id)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{uuid.uuid4().hex}{suffix}"
        path.write_bytes(data)
        return str(path)

    @staticmethod
    def _remove_file(file_path: str | None) -> None:
        if not file_path:
            return
        try:
            Path(file_path).unlink(missing_ok=True)
        except OSError as exc:  # pragma: no cover
            logger.warning("删除文件失败 %s: %s", file_path, exc)
