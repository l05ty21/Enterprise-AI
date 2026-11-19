from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """通用仓储。只做数据访问，业务规则放在 service 层。"""

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, obj_id: int) -> ModelT | None:
        return await self.session.get(self.model, obj_id)

    async def add(self, obj: ModelT) -> ModelT:
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def delete(self, obj: ModelT) -> None:
        await self.session.delete(obj)
        await self.session.flush()

    async def count(self, *conditions) -> int:
        stmt = select(func.count()).select_from(self.model)
        if conditions:
            stmt = stmt.where(*conditions)
        return int(await self.session.scalar(stmt) or 0)
