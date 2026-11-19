from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ModelType = Literal["llm", "embedding", "rerank"]
MessageRole = Literal["system", "user", "assistant", "tool"]


# ---------------------------------------------------------------- 模型配置
class AIModelConfigCreate(BaseModel):
    model_name: str = Field(min_length=1, max_length=128, description="如 qwen-plus")
    provider: str = Field(default="bailian", min_length=1, max_length=64)
    model_type: ModelType = "llm"
    base_url: str | None = Field(
        default=None, max_length=512, description="留空则按 provider 取默认端点"
    )
    api_key: str | None = Field(
        default=None, max_length=512, description="明文 Key，落库前立即加密"
    )
    is_default: bool = False
    is_enabled: bool = True
    parameters: dict[str, Any] | None = Field(
        default=None, description="透传给模型服务的参数，如 temperature"
    )


class AIModelConfigUpdate(BaseModel):
    model_name: str | None = Field(default=None, min_length=1, max_length=128)
    provider: str | None = Field(default=None, min_length=1, max_length=64)
    base_url: str | None = Field(default=None, max_length=512)
    api_key: str | None = Field(
        default=None, description="不传=保持不变；传空字符串=清空"
    )
    is_default: bool | None = None
    is_enabled: bool | None = None
    parameters: dict[str, Any] | None = None


class AIModelConfigRead(BaseModel):
    id: int
    organization_id: int
    model_name: str
    provider: str
    model_type: str
    base_url: str | None = None
    api_key_masked: str | None = None
    has_api_key: bool = False
    is_default: bool = False
    is_enabled: bool = True
    parameters: dict[str, Any] | None = None
    created_at: datetime | None = None


class ProviderOption(BaseModel):
    provider: str
    label: str
    base_url: str
    default_model: str
    requires_api_key: bool = True


# ---------------------------------------------------------------- 对话
class ChatMessageIn(BaseModel):
    role: MessageRole
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    messages: list[ChatMessageIn] = Field(min_length=1)
    model_config_id: int | None = Field(
        default=None, description="不传则用企业默认模型"
    )
    system_prompt: str | None = Field(default=None, max_length=8000)
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=8192)


class ChatResponse(BaseModel):
    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0


# ---------------------------------------------------------------- 用量
class AIUsageRow(BaseModel):
    model_name: str | None = None
    status: str | None = None
    calls: int
    input_tokens: int
    output_tokens: int
    avg_latency_ms: int


class AIUsageSummary(BaseModel):
    days: int
    calls: int
    input_tokens: int
    output_tokens: int
    items: list[AIUsageRow]
