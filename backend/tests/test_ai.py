"""第二阶段 AI 模型网关的测试。

真实网络调用统一用 FakeProvider 替换（monkeypatch ``gateway.build_provider``），
测试不依赖任何外部 API，也不需要 Key。
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.ai.base import AIError, ChatResult
from app.ai.crypto import decrypt_api_key, encrypt_api_key, mask_api_key
from app.models.chat import AIModelConfig, AIUsageLog
from app.schemas.ai import AIModelConfigCreate, ChatMessageIn, ChatRequest
from app.services.ai import AIService

API_KEY = "sk-test-1234567890abcdef"


class FakeProvider:
    """模拟 OpenAI 兼容客户端。"""

    last_usage: tuple[int, int] = (12, 34)

    def __init__(self) -> None:
        self.calls: list[list[dict]] = []

    async def chat(self, messages, **overrides):
        self.calls.append(messages)
        return ChatResult(
            content="你好，我是百炼",
            model="qwen-plus",
            input_tokens=12,
            output_tokens=34,
        )

    async def stream(self, messages, **overrides):
        self.calls.append(messages)
        for piece in ("你", "好"):
            yield piece


@pytest.fixture
def fake_provider(monkeypatch) -> FakeProvider:
    provider = FakeProvider()
    monkeypatch.setattr("app.ai.gateway.build_provider", lambda cfg: provider)
    return provider


# ---------------------------------------------------------------- 加密
def test_api_key_roundtrip_and_mask() -> None:
    token = encrypt_api_key(API_KEY)
    assert token != API_KEY
    assert decrypt_api_key(token) == API_KEY
    assert mask_api_key(API_KEY) == "sk-t****cdef"


# ---------------------------------------------------------------- 权限
async def test_employee_cannot_manage_models(client, employee_headers) -> None:
    resp = await client.post(
        "/api/v1/ai/models",
        json={"model_name": "qwen-plus", "provider": "bailian"},
        headers=employee_headers,
    )
    assert resp.status_code == 403


async def test_list_models_requires_config_permission(client, manager_headers) -> None:
    resp = await client.get("/api/v1/ai/models", headers=manager_headers)
    assert resp.status_code == 403


# ---------------------------------------------------------------- CRUD
async def test_create_config_encrypts_key(client, admin_headers, session_factory) -> None:
    resp = await client.post(
        "/api/v1/ai/models",
        json={
            "model_name": "qwen-plus",
            "provider": "bailian",
            "model_type": "llm",
            "api_key": API_KEY,
            "is_default": True,
            "parameters": {"temperature": 0.3},
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["has_api_key"] is True
    assert body["api_key_masked"] == "sk-t****cdef"
    assert "api_key" not in body
    # 响应里不允许出现完整 Key
    assert API_KEY not in resp.text

    async with session_factory() as session:
        config = await session.scalar(select(AIModelConfig))
        assert config is not None
        assert config.api_key_encrypted != API_KEY
        assert decrypt_api_key(config.api_key_encrypted) == API_KEY


async def test_duplicate_model_name_conflicts(client, admin_headers) -> None:
    payload = {"model_name": "qwen-plus", "provider": "bailian"}
    first = await client.post("/api/v1/ai/models", json=payload, headers=admin_headers)
    assert first.status_code == 201
    second = await client.post("/api/v1/ai/models", json=payload, headers=admin_headers)
    assert second.status_code == 409


async def test_default_switch_is_exclusive(client, admin_headers) -> None:
    first = await client.post(
        "/api/v1/ai/models",
        json={"model_name": "qwen-plus", "provider": "bailian", "is_default": True},
        headers=admin_headers,
    )
    second = await client.post(
        "/api/v1/ai/models",
        json={"model_name": "qwen-max", "provider": "bailian", "is_default": True},
        headers=admin_headers,
    )
    assert first.status_code == second.status_code == 201

    listing = await client.get("/api/v1/ai/models", headers=admin_headers)
    defaults = [item for item in listing.json() if item["is_default"]]
    assert len(defaults) == 1
    assert defaults[0]["model_name"] == "qwen-max"


async def test_update_and_delete_config(client, admin_headers) -> None:
    created = await client.post(
        "/api/v1/ai/models",
        json={"model_name": "qwen-plus", "provider": "bailian", "api_key": API_KEY},
        headers=admin_headers,
    )
    config_id = created.json()["id"]

    updated = await client.put(
        f"/api/v1/ai/models/{config_id}",
        json={"model_name": "qwen-turbo", "api_key": ""},
        headers=admin_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["model_name"] == "qwen-turbo"
    # 传空字符串表示清空 Key
    assert updated.json()["has_api_key"] is False

    deleted = await client.delete(f"/api/v1/ai/models/{config_id}", headers=admin_headers)
    assert deleted.status_code == 200
    missing = await client.get(f"/api/v1/ai/models/{config_id}", headers=admin_headers)
    assert missing.status_code == 404


async def test_cross_org_isolation(client, admin_headers, other_admin_headers) -> None:
    await client.post(
        "/api/v1/ai/models",
        json={"model_name": "qwen-plus", "provider": "bailian"},
        headers=admin_headers,
    )
    other_listing = await client.get("/api/v1/ai/models", headers=other_admin_headers)
    assert other_listing.status_code == 200
    assert other_listing.json() == []


# ---------------------------------------------------------------- 对话
async def test_chat_without_any_config_returns_400(client, employee_headers) -> None:
    resp = await client.post(
        "/api/v1/ai/chat",
        json={"messages": [{"role": "user", "content": "你好"}]},
        headers=employee_headers,
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "ai_not_configured"


async def test_chat_uses_config_and_logs_usage(
    client, admin_headers, employee_headers, fake_provider
) -> None:
    await client.post(
        "/api/v1/ai/models",
        json={"model_name": "qwen-plus", "provider": "bailian", "is_default": True},
        headers=admin_headers,
    )

    resp = await client.post(
        "/api/v1/ai/chat",
        json={
            "messages": [{"role": "user", "content": "介绍一下你自己"}],
            "system_prompt": "你是企业助手",
            "max_tokens": 256,
        },
        headers=employee_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["content"] == "你好，我是百炼"
    assert body["input_tokens"] == 12
    assert body["output_tokens"] == 34

    # system_prompt 被拼到最前面
    assert fake_provider.calls[0][0]["role"] == "system"

    usage = await client.get("/api/v1/ai/usage", headers=admin_headers)
    assert usage.status_code == 200
    payload = usage.json()
    assert payload["calls"] == 1
    assert payload["input_tokens"] == 12
    assert payload["output_tokens"] == 34


async def test_usage_is_org_scoped(
    client, admin_headers, employee_headers, other_admin_headers, fake_provider
) -> None:
    await client.post(
        "/api/v1/ai/models",
        json={"model_name": "qwen-plus", "provider": "bailian", "is_default": True},
        headers=admin_headers,
    )
    await client.post(
        "/api/v1/ai/chat",
        json={"messages": [{"role": "user", "content": "hi"}]},
        headers=employee_headers,
    )

    other_usage = await client.get("/api/v1/ai/usage", headers=other_admin_headers)
    assert other_usage.status_code == 200
    assert other_usage.json()["calls"] == 0


async def test_stream_chat_yields_and_logs(
    session_factory, seeded, fake_provider
) -> None:
    async with session_factory() as session:
        service = AIService(session)
        await service.create_config(
            seeded.org_id,
            AIModelConfigCreate(model_name="qwen-plus", provider="bailian", is_default=True),
        )
        chunks = [
            chunk
            async for chunk in service.stream_chat(
                seeded.org_id,
                seeded.admin_id,
                ChatRequest(messages=[ChatMessageIn(role="user", content="hi")]),
            )
        ]
    assert "".join(chunks) == "你好"

    async with session_factory() as session:
        logs = list(await session.scalars(select(AIUsageLog)))
    assert len(logs) == 1
    assert logs[0].status == "success"
    assert logs[0].input_tokens == 12
    assert logs[0].output_tokens == 34


async def test_providers_endpoint_lists_bailian(client, employee_headers) -> None:
    resp = await client.get("/api/v1/ai/providers", headers=employee_headers)
    assert resp.status_code == 200
    providers = {item["provider"]: item for item in resp.json()}
    assert providers["bailian"]["base_url"].startswith("https://dashscope")


async def test_failed_call_is_still_logged(
    client, admin_headers, employee_headers, monkeypatch
) -> None:
    """上游失败也必须留下审计记录，不能被异常回滚掉。"""

    class FailingProvider:
        last_usage = (0, 0)

        async def chat(self, messages, **overrides):
            raise AIError("上游鉴权失败")

    monkeypatch.setattr("app.ai.gateway.build_provider", lambda cfg: FailingProvider())

    await client.post(
        "/api/v1/ai/models",
        json={"model_name": "qwen-plus", "provider": "bailian", "is_default": True},
        headers=admin_headers,
    )
    resp = await client.post(
        "/api/v1/ai/chat",
        json={"messages": [{"role": "user", "content": "hi"}]},
        headers=employee_headers,
    )
    assert resp.status_code == 502

    usage = await client.get("/api/v1/ai/usage", headers=admin_headers)
    payload = usage.json()
    assert payload["calls"] == 1
    assert payload["items"][0]["status"] == "error"
