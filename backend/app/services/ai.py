from __future__ import annotations

import time
from collections.abc import AsyncIterator
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import gateway
from app.ai.crypto import encrypt_api_key, mask_api_key
from app.ai.openai_compat import DEFAULT_BASE_URLS
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models.chat import AIModelConfig
from app.repositories.ai import AIModelConfigRepository, AIUsageLogRepository
from app.schemas.ai import (
    AIModelConfigCreate,
    AIModelConfigRead,
    AIModelConfigUpdate,
    AIUsageSummary,
    ChatRequest,
    ChatResponse,
    ProviderOption,
)
from app.schemas.knowledge import Citation
from app.services.knowledge import KnowledgeService

PROVIDER_LABELS: list[tuple[str, str, str, bool]] = [
    ("bailian", "阿里云百炼", "qwen-plus", True),
    ("deepseek", "DeepSeek", "deepseek-chat", True),
    ("siliconflow", "硅基流动", "deepseek-ai/DeepSeek-V3", True),
    ("zhipu", "智谱 GLM", "glm-4-plus", True),
    ("openai", "OpenAI", "gpt-4o-mini", True),
    ("ollama", "本地 Ollama", "qwen2.5:7b", False),
]


class AIService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.configs = AIModelConfigRepository(session)
        self.usage_logs = AIUsageLogRepository(session)

    # ---------------------------------------------------------------- 工具
    @staticmethod
    def _to_read(config: AIModelConfig) -> AIModelConfigRead:
        masked = None
        if config.api_key_encrypted:
            # 解密只为回显首尾 4 位，绝不返回完整 Key
            from app.ai.crypto import decrypt_api_key

            masked = mask_api_key(decrypt_api_key(config.api_key_encrypted))
        return AIModelConfigRead(
            id=config.id,
            organization_id=config.organization_id,
            model_name=config.model_name,
            provider=config.provider,
            model_type=config.model_type,
            base_url=config.base_url,
            api_key_masked=masked,
            has_api_key=bool(config.api_key_encrypted),
            is_default=config.is_default,
            is_enabled=config.is_enabled,
            parameters=config.parameters,
            created_at=config.created_at,
        )

    @staticmethod
    def providers() -> list[ProviderOption]:
        return [
            ProviderOption(
                provider=code,
                label=label,
                base_url=DEFAULT_BASE_URLS.get(code, ""),
                default_model=model,
                requires_api_key=needs_key,
            )
            for code, label, model, needs_key in PROVIDER_LABELS
        ]

    # ---------------------------------------------------------------- 配置
    async def list_configs(self, organization_id: int) -> list[AIModelConfigRead]:
        return [self._to_read(c) for c in await self.configs.list_in_org(organization_id)]

    async def get_config(self, organization_id: int, config_id: int) -> AIModelConfigRead:
        config = await self.configs.get_in_org(organization_id, config_id)
        if config is None:
            raise NotFoundError("模型配置不存在")
        return self._to_read(config)

    async def create_config(
        self, organization_id: int, payload: AIModelConfigCreate
    ) -> AIModelConfigRead:
        if await self.configs.model_name_exists(
            organization_id, payload.model_name, payload.model_type
        ):
            raise ConflictError("同类型下已存在同名模型配置")

        config = AIModelConfig(
            organization_id=organization_id,
            model_name=payload.model_name,
            provider=payload.provider,
            model_type=payload.model_type,
            base_url=payload.base_url,
            api_key_encrypted=encrypt_api_key(payload.api_key) if payload.api_key else None,
            is_default=payload.is_default,
            is_enabled=payload.is_enabled,
            parameters=payload.parameters,
        )
        if payload.is_default:
            await self.configs.clear_default(organization_id, payload.model_type)
        await self.configs.add(config)
        await self.session.commit()
        # created_at 是 server_default，commit 后属性已过期，
        # 不 refresh 就读取会触发同步 IO（async 下报 MissingGreenlet）
        await self.session.refresh(config)
        return self._to_read(config)

    async def update_config(
        self, organization_id: int, config_id: int, payload: AIModelConfigUpdate
    ) -> AIModelConfigRead:
        config = await self.configs.get_in_org(organization_id, config_id)
        if config is None:
            raise NotFoundError("模型配置不存在")

        data = payload.model_dump(exclude_unset=True)

        new_name = data.get("model_name")
        if new_name and new_name != config.model_name:
            if await self.configs.model_name_exists(
                organization_id, new_name, config.model_type, exclude_id=config.id
            ):
                raise ConflictError("同类型下已存在同名模型配置")

        if "api_key" in data:
            api_key = data.pop("api_key")
            config.api_key_encrypted = encrypt_api_key(api_key) if api_key else None

        if data.get("is_default"):
            await self.configs.clear_default(
                organization_id, config.model_type, exclude_id=config.id
            )

        for field, value in data.items():
            setattr(config, field, value)

        await self.session.commit()
        await self.session.refresh(config)
        return self._to_read(config)

    async def delete_config(self, organization_id: int, config_id: int) -> None:
        config = await self.configs.get_in_org(organization_id, config_id)
        if config is None:
            raise NotFoundError("模型配置不存在")
        await self.configs.delete(config)
        await self.session.commit()

    # ---------------------------------------------------------------- 对话
    @staticmethod
    def _build_messages(payload: ChatRequest) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        if payload.system_prompt:
            messages.append({"role": "system", "content": payload.system_prompt})
        messages.extend(
            {"role": item.role, "content": item.content} for item in payload.messages
        )
        if not messages:
            raise BadRequestError("消息不能为空")
        return messages

    RAG_PROMPT = (
        "以下是企业知识库中检索到的参考资料，请优先依据这些内容回答；"
        "如果资料不足以回答，请明确说明「知识库中没有找到相关内容」，不要编造。\n"
        "回答中可以用 [1] [2] 这样的编号标注引用来源。\n\n"
    )

    async def _with_rag(
        self, organization_id: int, payload: ChatRequest
    ) -> tuple[list[dict[str, Any]], list[Citation]]:
        """按需做一次向量检索，把命中的片段拼到 system 提示词里。"""
        messages = self._build_messages(payload)
        if payload.knowledge_base_ids is None:
            return messages, []

        question = next(
            (
                item.content
                for item in reversed(payload.messages)
                if item.role == "user"
            ),
            "",
        )
        if not question:
            return messages, []

        context, citations = await KnowledgeService(self.session).build_context(
            organization_id,
            question,
            kb_ids=payload.knowledge_base_ids or None,
        )
        if context:
            messages.insert(
                0, {"role": "system", "content": self.RAG_PROMPT + context}
            )
        return messages, citations

    async def chat(
        self, organization_id: int, user_id: int, payload: ChatRequest
    ) -> ChatResponse:
        messages, citations = await self._with_rag(organization_id, payload)
        started_at = time.perf_counter()
        result = await gateway.chat(
            self.session,
            organization_id=organization_id,
            user_id=user_id,
            messages=messages,
            config_id=payload.model_config_id,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
        )
        await self.session.commit()
        return ChatResponse(
            content=result.content,
            model=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            latency_ms=int((time.perf_counter() - started_at) * 1000),
            citations=citations,
        )

    async def stream_chat(
        self, organization_id: int, user_id: int, payload: ChatRequest
    ) -> tuple[AsyncIterator[str], list[Citation]]:
        """返回 (增量文本流, 引用列表)。检索在流开始前完成，引用可先推给前端。"""
        messages, citations = await self._with_rag(organization_id, payload)

        async def token_stream() -> AsyncIterator[str]:
            async for text in gateway.stream_chat(
                self.session,
                organization_id=organization_id,
                user_id=user_id,
                messages=messages,
                config_id=payload.model_config_id,
                temperature=payload.temperature,
                max_tokens=payload.max_tokens,
            ):
                yield text
            # 流正常结束后落库用量
            await self.session.commit()

        return token_stream(), citations

    # ---------------------------------------------------------------- 用量
    async def usage_summary(self, organization_id: int, days: int = 7) -> AIUsageSummary:
        since = datetime.now() - timedelta(days=days)
        rows = await self.usage_logs.summary_by_model(organization_id, since)
        total = await self.usage_logs.total(organization_id, since)
        return AIUsageSummary(
            days=days,
            calls=total["calls"],
            input_tokens=total["input_tokens"],
            output_tokens=total["output_tokens"],
            items=rows,  # type: ignore[arg-type]
        )
