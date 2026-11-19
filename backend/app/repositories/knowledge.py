from __future__ import annotations

from sqlalchemy import delete, func, select

from app.models.knowledge import Document, DocumentChunk, KnowledgeBase
from app.repositories.base import BaseRepository


class KnowledgeBaseRepository(BaseRepository[KnowledgeBase]):
    model = KnowledgeBase

    async def list_in_org(self, organization_id: int) -> list[KnowledgeBase]:
        stmt = (
            select(KnowledgeBase)
            .where(
                KnowledgeBase.organization_id == organization_id,
                KnowledgeBase.status == 1,
            )
            .order_by(KnowledgeBase.id.desc())
        )
        return list(await self.session.scalars(stmt))

    async def get_in_org(
        self, organization_id: int, kb_id: int
    ) -> KnowledgeBase | None:
        stmt = select(KnowledgeBase).where(
            KnowledgeBase.organization_id == organization_id,
            KnowledgeBase.id == kb_id,
        )
        return await self.session.scalar(stmt)

    async def name_exists(
        self, organization_id: int, name: str, exclude_id: int | None = None
    ) -> bool:
        stmt = select(func.count()).select_from(KnowledgeBase).where(
            KnowledgeBase.organization_id == organization_id,
            KnowledgeBase.name == name,
            KnowledgeBase.status == 1,
        )
        if exclude_id is not None:
            stmt = stmt.where(KnowledgeBase.id != exclude_id)
        return bool(await self.session.scalar(stmt))


class DocumentRepository(BaseRepository[Document]):
    model = Document

    async def list_by_kb(self, organization_id: int, kb_id: int) -> list[Document]:
        stmt = (
            select(Document)
            .where(
                Document.organization_id == organization_id,
                Document.kb_id == kb_id,
            )
            .order_by(Document.id.desc())
        )
        return list(await self.session.scalars(stmt))

    async def get_in_org(
        self, organization_id: int, document_id: int
    ) -> Document | None:
        stmt = select(Document).where(
            Document.organization_id == organization_id,
            Document.id == document_id,
        )
        return await self.session.scalar(stmt)

    async def count_by_kb(self, organization_id: int, kb_id: int) -> int:
        return await self.count(
            Document.organization_id == organization_id, Document.kb_id == kb_id
        )

    async def chunks_of_kb(self, organization_id: int, kb_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(DocumentChunk)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(
                DocumentChunk.organization_id == organization_id,
                Document.kb_id == kb_id,
            )
        )
        return int(await self.session.scalar(stmt) or 0)


class DocumentChunkRepository(BaseRepository[DocumentChunk]):
    model = DocumentChunk

    async def delete_by_document(self, document_id: int) -> None:
        await self.session.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        await self.session.flush()

    async def delete_by_kb(self, organization_id: int, kb_id: int) -> None:
        subquery = select(Document.id).where(
            Document.organization_id == organization_id, Document.kb_id == kb_id
        )
        await self.session.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id.in_(subquery))
        )
        await self.session.flush()

    async def list_by_document(self, document_id: int) -> list[DocumentChunk]:
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        return list(await self.session.scalars(stmt))
