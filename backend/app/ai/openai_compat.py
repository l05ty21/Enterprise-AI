"""OpenAI 兼容协议适配器。

阿里云百炼、DeepSeek、硅基流动、智谱、Ollama、OpenAI 都提供
``/chat/completions`` 兼容端点，所以**只需要这一个实现**，
靠 ``base_url`` + ``api_key`` + ``model`` 区分厂商。
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI, OpenAIError

from app.ai.base import AIError, ChatResult, ProviderSettings
from app.core.config import settings

logger = logging.getLogger(__name__)

# 常见厂商的默认端点。配置里 base_url 留空时按 provider 回落。
DEFAULT_BASE_URLS: dict[str, str] = {
    "bailian": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "siliconflow": "https://api.siliconflow.cn/v1",
    "zhipu": "https://open.bigmodel.cn/api/paas/v4",
    "openai": "https://api.openai.com/v1",
    "ollama": "http://127.0.0.1:11434/v1",
}


def default_base_url(provider: str) -> str:
    return DEFAULT_BASE_URLS.get(provider.strip().lower(), DEFAULT_BASE_URLS["bailian"])


class OpenAICompatProvider:
    def __init__(self, cfg: ProviderSettings) -> None:
        self.cfg = cfg
        self.last_usage: tuple[int, int] = (0, 0)
        self.client = AsyncOpenAI(
            base_url=cfg.base_url,
            # 本地 Ollama 不需要鉴权，但 SDK 要求非空
            api_key=cfg.api_key or "not-needed",
            timeout=settings.AI_TIMEOUT_SECONDS,
            max_retries=settings.AI_MAX_RETRIES,
        )

    # ---------------------------------------------------------------- 内部
    def _payload(self, messages: list[dict[str, Any]], **overrides: Any) -> dict[str, Any]:
        params: dict[str, Any] = dict(self.cfg.parameters or {})
        params.update({k: v for k, v in overrides.items() if v is not None})
        # 兜底限制，避免单次调用把额度烧穿
        params.setdefault("max_tokens", settings.AI_MAX_TOKENS)
        return {"model": self.cfg.model, "messages": messages, **params}

    async def _call(self, messages: list[dict[str, Any]], **overrides: Any):
        try:
            return await self.client.chat.completions.create(
                **self._payload(messages, **overrides)
            )
        except OpenAIError as exc:
            logger.warning("upstream AI error (%s): %s", self.cfg.safe_repr, exc)
            raise AIError(f"模型服务调用失败：{exc}") from exc

    # ---------------------------------------------------------------- 对话
    async def chat(self, messages: list[dict[str, Any]], **overrides: Any) -> ChatResult:
        resp = await self._call(messages, **overrides)
        usage = resp.usage
        return ChatResult(
            content=resp.choices[0].message.content or "",
            model=resp.model or self.cfg.model,
            input_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
        )

    async def stream(self, messages: list[dict[str, Any]], **overrides: Any) -> AsyncIterator[str]:
        """流式对话。用量在流结束后从 ``last_usage`` 读取（部分厂商不返回则记 0）。"""
        payload = self._payload(messages, **overrides)
        payload["stream"] = True
        # 百炼 / OpenAI 支持在最后一个 chunk 带 usage；不支持的厂商会忽略该参数
        payload.setdefault("stream_options", {"include_usage": True})
        self.last_usage = (0, 0)
        try:
            stream = await self.client.chat.completions.create(**payload)
        except OpenAIError as exc:
            logger.warning("upstream AI stream error (%s): %s", self.cfg.safe_repr, exc)
            raise AIError(f"模型服务调用失败：{exc}") from exc

        try:
            async for chunk in stream:
                if chunk.usage:
                    self.last_usage = (
                        int(chunk.usage.prompt_tokens or 0),
                        int(chunk.usage.completion_tokens or 0),
                    )
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                text = getattr(delta, "content", None)
                if text:
                    yield text
        except OpenAIError as exc:
            logger.warning("upstream AI stream interrupted (%s): %s", self.cfg.safe_repr, exc)
            raise AIError(f"模型流式输出中断：{exc}") from exc

    # ---------------------------------------------------------------- 向量
    async def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            resp = await self.client.embeddings.create(model=self.cfg.model, input=texts)
        except OpenAIError as exc:
            raise AIError(f"向量化失败：{exc}") from exc
        return [item.embedding for item in resp.data]
