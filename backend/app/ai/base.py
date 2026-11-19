"""AI 网关的公共类型与异常。

设计原则：业务层只依赖这里的 ``ChatResult`` / ``ProviderSettings``，
不直接接触任何厂商 SDK，换模型只改配置不改业务代码。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from app.core.exceptions import AppError

ModelType = Literal["llm", "embedding", "rerank"]


class AIError(AppError):
    """上游模型服务调用失败（超时、鉴权失败、限流等）。"""

    status_code = 502
    code = "ai_upstream_error"


class AINotConfiguredError(AppError):
    """企业和平台都没有可用模型配置。"""

    status_code = 400
    code = "ai_not_configured"


@dataclass(slots=True)
class ProviderSettings:
    """一次调用所需的全部连接信息，已解密。"""

    provider: str
    model: str
    base_url: str
    api_key: str
    parameters: dict[str, Any] = field(default_factory=dict)

    @property
    def safe_repr(self) -> str:
        return f"{self.provider}/{self.model} @ {self.base_url}"


@dataclass(slots=True)
class ChatResult:
    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
