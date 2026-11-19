from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select, update

from app.models.chat import AIModelConfig, AIUsageLog
from app.repositories.base import BaseRepository


class AIModelConfigRepository(BaseRepository[AIModelConfig]):
    model = AIModelConfig

    async def list_in_org(self, organization_id: int) -> list[AIModelConfig]:
        stmt = (
            select(AIModelConfig)
            .where(AIModelConfig.organization_id == organization_id)
            .order_by(AIModelConfig.id)
        )
        return list(await self.session.scalars(stmt))

    async def get_in_org(
        self, organization_id: int, config_id: int
    ) -> AIModelConfig | None:
        stmt = select(AIModelConfig).where(
            AIModelConfig.organization_id == organization_id,
            AIModelConfig.id == config_id,
        )
        return await self.session.scalar(stmt)

    async def get_default(
        self, organization_id: int, model_type: str
    ) -> AIModelConfig | None:
        stmt = (
            select(AIModelConfig)
            .where(
                AIModelConfig.organization_id == organization_id,
                AIModelConfig.model_type == model_type,
                AIModelConfig.is_default.is_(True),
                AIModelConfig.is_enabled.is_(True),
            )
            .order_by(AIModelConfig.id.desc())
        )
        return await self.session.scalar(stmt)

    async def first_enabled(
        self, organization_id: int, model_type: str
    ) -> AIModelConfig | None:
        stmt = (
            select(AIModelConfig)
            .where(
                AIModelConfig.organization_id == organization_id,
                AIModelConfig.model_type == model_type,
                AIModelConfig.is_enabled.is_(True),
            )
            .order_by(AIModelConfig.id)
        )
        return await self.session.scalar(stmt)

    async def clear_default(
        self, organization_id: int, model_type: str, exclude_id: int | None = None
    ) -> None:
        stmt = update(AIModelConfig).where(
            AIModelConfig.organization_id == organization_id,
            AIModelConfig.model_type == model_type,
            AIModelConfig.is_default.is_(True),
        )
        if exclude_id is not None:
            stmt = stmt.where(AIModelConfig.id != exclude_id)
        await self.session.execute(stmt.values(is_default=False))

    async def model_name_exists(
        self,
        organization_id: int,
        model_name: str,
        model_type: str,
        exclude_id: int | None = None,
    ) -> bool:
        stmt = select(func.count()).select_from(AIModelConfig).where(
            AIModelConfig.organization_id == organization_id,
            AIModelConfig.model_name == model_name,
            AIModelConfig.model_type == model_type,
        )
        if exclude_id is not None:
            stmt = stmt.where(AIModelConfig.id != exclude_id)
        return bool(await self.session.scalar(stmt))


class AIUsageLogRepository(BaseRepository[AIUsageLog]):
    model = AIUsageLog

    async def summary_by_model(
        self, organization_id: int, since: datetime
    ) -> list[dict]:
        stmt = (
            select(
                AIUsageLog.model_name,
                AIUsageLog.status,
                func.count(AIUsageLog.id),
                func.coalesce(func.sum(AIUsageLog.input_tokens), 0),
                func.coalesce(func.sum(AIUsageLog.output_tokens), 0),
                func.coalesce(func.avg(AIUsageLog.latency_ms), 0),
            )
            .where(
                AIUsageLog.organization_id == organization_id,
                AIUsageLog.created_at >= since,
            )
            .group_by(AIUsageLog.model_name, AIUsageLog.status)
            .order_by(func.count(AIUsageLog.id).desc())
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            {
                "model_name": model_name,
                "status": status,
                "calls": int(calls),
                "input_tokens": int(input_tokens),
                "output_tokens": int(output_tokens),
                "avg_latency_ms": int(avg_latency),
            }
            for model_name, status, calls, input_tokens, output_tokens, avg_latency in rows
        ]

    async def total(self, organization_id: int, since: datetime) -> dict:
        stmt = select(
            func.count(AIUsageLog.id),
            func.coalesce(func.sum(AIUsageLog.input_tokens), 0),
            func.coalesce(func.sum(AIUsageLog.output_tokens), 0),
        ).where(
            AIUsageLog.organization_id == organization_id,
            AIUsageLog.created_at >= since,
        )
        calls, input_tokens, output_tokens = (await self.session.execute(stmt)).one()
        return {
            "calls": int(calls or 0),
            "input_tokens": int(input_tokens or 0),
            "output_tokens": int(output_tokens or 0),
        }
