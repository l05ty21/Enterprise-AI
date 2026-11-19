"""AI 网关：配置解析 → 解密 Key → 调用 → 记账。

业务代码只需要 ``await chat(...)``，不关心用哪家模型、Key 存在哪里。
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import AINotConfiguredError, ChatResult, ModelType, ProviderSettings
from app.ai.crypto import decrypt_api_key
from app.ai.factory import build_provider
from app.ai.openai_compat import default_base_url
from app.core.config import settings
from app.models.chat import AIModelConfig, AIUsageLog
from app.repositories.ai import AIModelConfigRepository, AIUsageLogRepository

logger = logging.getLogger(__name__)


def _from_platform(model_type: ModelType) -> ProviderSettings | None:
    """企业没配模型时，回落到平台级环境变量（.env 里的 AI_*）。"""
    provider = (settings.AI_DEFAULT_PROVIDER or "").strip().lower()
    if not provider:
        return None

    if provider == "ollama":
        return ProviderSettings(
            provider="ollama",
            model=(
                settings.AI_EMBEDDING_MODEL
                if model_type == "embedding"
                else settings.AI_DEFAULT_MODEL
            ),
            base_url=settings.AI_OLLAMA_BASE_URL,
            api_key="",
        )

    if not settings.AI_CLOUD_API_KEY:
        return None
    return ProviderSettings(
        provider=provider,
        model=(
            settings.AI_EMBEDDING_MODEL
            if model_type == "embedding"
            else settings.AI_DEFAULT_MODEL
        ),
        base_url=settings.AI_CLOUD_BASE_URL or default_base_url(provider),
        api_key=settings.AI_CLOUD_API_KEY,
    )


def _from_config(config: AIModelConfig) -> ProviderSettings:
    provider = config.provider.strip().lower()
    return ProviderSettings(
        provider=provider,
        model=config.model_name,
        base_url=config.base_url or default_base_url(provider),
        api_key=decrypt_api_key(config.api_key_encrypted)
        if config.api_key_encrypted
        else "",
        parameters=dict(config.parameters or {}),
    )


async def resolve_settings(
    session: AsyncSession,
    organization_id: int,
    *,
    model_type: ModelType = "llm",
    config_id: int | None = None,
) -> tuple[ProviderSettings, AIModelConfig | None]:
    """按 指定配置 → 企业默认配置 → 企业任一启用配置 → 平台环境变量 的顺序解析。"""
    repo = AIModelConfigRepository(session)

    config: AIModelConfig | None = None
    if config_id is not None:
        config = await repo.get_in_org(organization_id, config_id)
        if config is None or not config.is_enabled:
            raise AINotConfiguredError("指定的模型配置不存在或已禁用")
    else:
        config = await repo.get_default(organization_id, model_type)
        if config is None:
            config = await repo.first_enabled(organization_id, model_type)

    if config is not None:
        return _from_config(config), config

    fallback = _from_platform(model_type)
    if fallback is None:
        raise AINotConfiguredError(
            "还没有可用的模型配置：请在「系统设置 → AI 模型」里添加，或在部署环境配置 AI_CLOUD_API_KEY"
        )
    return fallback, None


async def _log_usage(
    session: AsyncSession,
    *,
    organization_id: int,
    user_id: int,
    config_settings: ProviderSettings,
    result: ChatResult | None,
    status_value: str,
    started_at: float,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
) -> None:
    latency_ms = int((time.perf_counter() - started_at) * 1000)
    await AIUsageLogRepository(session).add(
        AIUsageLog(
            organization_id=organization_id,
            user_id=user_id,
            model_name=config_settings.model,
            provider=config_settings.provider,
            input_tokens=(
                input_tokens if input_tokens is not None else (result.input_tokens if result else 0)
            ),
            output_tokens=(
                output_tokens
                if output_tokens is not None
                else (result.output_tokens if result else 0)
            ),
            latency_ms=latency_ms,
            status=status_value,
        )
    )


async def chat(
    session: AsyncSession,
    *,
    organization_id: int,
    user_id: int,
    messages: list[dict[str, Any]],
    config_id: int | None = None,
    **overrides: Any,
) -> ChatResult:
    config_settings, _ = await resolve_settings(
        session, organization_id, model_type="llm", config_id=config_id
    )
    provider = build_provider(config_settings)
    started_at = time.perf_counter()
    try:
        result = await provider.chat(messages, **overrides)
    except Exception:
        await _log_usage(
            session,
            organization_id=organization_id,
            user_id=user_id,
            config_settings=config_settings,
            result=None,
            status_value="error",
            started_at=started_at,
        )
        # 失败也要留下审计记录：先提交，否则随后的异常会让 get_db 回滚掉这条日志
        await session.commit()
        raise
    await _log_usage(
        session,
        organization_id=organization_id,
        user_id=user_id,
        config_settings=config_settings,
        result=result,
        status_value="success",
        started_at=started_at,
    )
    return result


async def stream_chat(
    session: AsyncSession,
    *,
    organization_id: int,
    user_id: int,
    messages: list[dict[str, Any]],
    config_id: int | None = None,
    **overrides: Any,
) -> AsyncIterator[str]:
    config_settings, _ = await resolve_settings(
        session, organization_id, model_type="llm", config_id=config_id
    )
    provider = build_provider(config_settings)
    started_at = time.perf_counter()
    status_value = "success"
    try:
        async for text in provider.stream(messages, **overrides):
            yield text
    except Exception:
        status_value = "error"
        raise
    finally:
        input_tokens, output_tokens = provider.last_usage
        await _log_usage(
            session,
            organization_id=organization_id,
            user_id=user_id,
            config_settings=config_settings,
            result=None,
            status_value=status_value,
            started_at=started_at,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        if status_value != "success":
            # 异常路径下 get_db 会回滚，先把失败记录落盘
            await session.commit()


async def embed(
    session: AsyncSession, *, organization_id: int, texts: list[str]
) -> list[list[float]]:
    config_settings, _ = await resolve_settings(
        session, organization_id, model_type="embedding"
    )
    return await build_provider(config_settings).embed(texts)
