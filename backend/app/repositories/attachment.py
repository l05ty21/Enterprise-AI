from __future__ import annotations

from sqlalchemy import select

from app.models.attachment import Attachment
from app.repositories.base import BaseRepository


class AttachmentRepository(BaseRepository[Attachment]):
    model = Attachment

    async def list_for(
        self, organization_id: int, biz_type: str, biz_id: int
    ) -> list[Attachment]:
        stmt = (
            select(Attachment)
            .where(
                Attachment.organization_id == organization_id,
                Attachment.biz_type == biz_type,
                Attachment.biz_id == biz_id,
            )
            .order_by(Attachment.id.asc())
        )
        return list(await self.session.scalars(stmt))

    async def get_in_org(self, organization_id: int, attachment_id: int) -> Attachment | None:
        stmt = select(Attachment).where(
            Attachment.organization_id == organization_id,
            Attachment.id == attachment_id,
        )
        return await self.session.scalar(stmt)
