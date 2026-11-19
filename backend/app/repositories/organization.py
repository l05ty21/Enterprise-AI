from __future__ import annotations

from sqlalchemy import select

from app.models.organization import Organization
from app.repositories.base import BaseRepository


class OrganizationRepository(BaseRepository[Organization]):
    model = Organization

    async def get_by_code(self, code: str) -> Organization | None:
        return await self.session.scalar(
            select(Organization).where(Organization.code == code)
        )

    async def list_all(self) -> list[Organization]:
        return list(await self.session.scalars(select(Organization).order_by(Organization.id)))
