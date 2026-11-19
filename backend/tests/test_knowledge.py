"""知识库与 RAG 的测试。

向量化全部用假实现替换（monkeypatch ``app.ai.gateway.embed``），
不依赖外部 API；向量的构造方式保证「含关键字的片段」必然被检索命中。
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.models.knowledge import Document, DocumentChunk

REIMBURSE = "公司差旅报销标准：市内交通每天不超过 80 元，住宿一线城市不超过 500 元。"
LEAVE = "年假规定：入职满一年享有 5 天带薪年假，满三年享有 10 天。"


@pytest.fixture(autouse=True)
def _isolate_uploads(tmp_path, monkeypatch):
    """把上传目录指到临时目录，避免测试污染仓库。"""
    target = tmp_path / "uploads"
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(target))
    return target


@pytest.fixture
def fake_embedding(monkeypatch):
    """把文本映射成 4 维向量：第 0 维表征「报销」，第 1 维表征「年假」。"""

    async def _embed(session, *, organization_id: int, texts: list[str]):
        vectors = []
        for text in texts:
            vectors.append(
                [
                    1.0 if "报销" in text else 0.0,
                    1.0 if "年假" in text else 0.0,
                    0.1,
                    0.1,
                ]
            )
        return vectors

    monkeypatch.setattr("app.ai.gateway.embed", _embed)
    return _embed


async def _create_kb(client, headers, name: str = "制度库") -> int:
    resp = await client.post(
        "/api/v1/knowledge-bases",
        json={"name": name, "description": "人事行政制度", "visibility": "org"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _upload(client, headers, kb_id: int, filename: str, content: str):
    return await client.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents",
        files={"file": (filename, content.encode("utf-8"), "text/plain")},
        headers=headers,
    )


# ------------------------------------------------------------------ 权限
async def test_employee_cannot_create_kb(client, employee_headers) -> None:
    resp = await client.post(
        "/api/v1/knowledge-bases", json={"name": "x"}, headers=employee_headers
    )
    assert resp.status_code == 403


# ------------------------------------------------------------------ CRUD
async def test_kb_crud_and_duplicate_name(client, admin_headers) -> None:
    kb_id = await _create_kb(client, admin_headers)

    dup = await client.post(
        "/api/v1/knowledge-bases", json={"name": "制度库"}, headers=admin_headers
    )
    assert dup.status_code == 409

    detail = await client.get(f"/api/v1/knowledge-bases/{kb_id}", headers=admin_headers)
    assert detail.status_code == 200
    assert detail.json()["name"] == "制度库"

    updated = await client.put(
        f"/api/v1/knowledge-bases/{kb_id}",
        json={"description": "更新后的描述"},
        headers=admin_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["description"] == "更新后的描述"

    deleted = await client.delete(
        f"/api/v1/knowledge-bases/{kb_id}", headers=admin_headers
    )
    assert deleted.status_code == 200
    assert (
        await client.get(f"/api/v1/knowledge-bases/{kb_id}", headers=admin_headers)
    ).status_code == 404


async def test_cross_org_isolation(client, admin_headers, other_admin_headers) -> None:
    await _create_kb(client, admin_headers)
    listing = await client.get("/api/v1/knowledge-bases", headers=other_admin_headers)
    assert listing.status_code == 200
    assert listing.json() == []


# ------------------------------------------------------------------ 入库
async def test_upload_document_chunks_and_embeds(
    client, admin_headers, session_factory, fake_embedding
) -> None:
    kb_id = await _create_kb(client, admin_headers)
    resp = await _upload(client, admin_headers, kb_id, "制度.txt", f"{REIMBURSE}\n\n{LEAVE}")
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "ready"
    assert body["chunk_count"] >= 1

    async with session_factory() as session:
        chunks = list(await session.scalars(select(DocumentChunk)))
        assert len(chunks) == body["chunk_count"]
        assert all(chunk.embedding is not None for chunk in chunks)
        assert all(chunk.embedding_dim == 4 for chunk in chunks)
        # 向量是 float32 字节串：4 维 * 4 字节
        assert len(chunks[0].embedding) == 16


async def test_upload_rejects_unsupported_type(client, admin_headers, fake_embedding) -> None:
    kb_id = await _create_kb(client, admin_headers)
    resp = await client.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents",
        files={"file": ("evil.exe", b"MZ...", "application/octet-stream")},
        headers=admin_headers,
    )
    assert resp.status_code == 400
    assert "不支持" in resp.json()["message"]


async def test_upload_failure_marks_document_failed(
    client, admin_headers, session_factory, monkeypatch
) -> None:
    async def _boom(session, *, organization_id: int, texts: list[str]):
        raise RuntimeError("上游向量化失败")

    monkeypatch.setattr("app.ai.gateway.embed", _boom)
    kb_id = await _create_kb(client, admin_headers)

    with pytest.raises(RuntimeError):
        await _upload(client, admin_headers, kb_id, "a.txt", REIMBURSE)

    async with session_factory() as session:
        document = await session.scalar(select(Document))
        assert document is not None
        assert document.status == "failed"
        assert "向量化失败" in (document.error_message or "")


# ------------------------------------------------------------------ 检索
async def test_search_hits_relevant_chunk(
    client, admin_headers, fake_embedding
) -> None:
    kb_id = await _create_kb(client, admin_headers)
    await _upload(client, admin_headers, kb_id, "制度.txt", f"{REIMBURSE}\n\n{LEAVE}")

    resp = await client.post(
        "/api/v1/knowledge-bases/search/query",
        json={"query": "报销标准是多少", "top_k": 3},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    hits = resp.json()
    assert hits, "应当至少命中一条"
    assert "报销" in hits[0]["content"]
    # 两段内容被合并进同一个切片，假向量同时含「报销」「年假」两个维度，
    # 余弦相似度约 0.71，不是 1.0 —— 这里只验证「明显高于无关片段」
    assert hits[0]["score"] > 0.6


async def test_search_scope_by_kb(client, admin_headers, fake_embedding) -> None:
    kb_a = await _create_kb(client, admin_headers, "制度库A")
    kb_b = await _create_kb(client, admin_headers, "制度库B")
    await _upload(client, admin_headers, kb_a, "a.txt", REIMBURSE)
    await _upload(client, admin_headers, kb_b, "b.txt", LEAVE)

    resp = await client.post(
        "/api/v1/knowledge-bases/search/query",
        json={"query": "报销", "kb_ids": [kb_b]},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json() == []


# ------------------------------------------------------------------ RAG
async def test_chat_with_knowledge_base_returns_citations(
    client, admin_headers, employee_headers, fake_embedding, monkeypatch
) -> None:
    from app.ai.base import ChatResult

    captured: dict = {}

    class FakeProvider:
        last_usage = (20, 10)

        async def chat(self, messages, **overrides):
            captured["messages"] = messages
            return ChatResult(content="报销上限为 500 元 [1]", model="qwen-plus",
                              input_tokens=20, output_tokens=10)

    monkeypatch.setattr("app.ai.gateway.build_provider", lambda cfg: FakeProvider())

    # 企业配置一个模型（chat 需要）
    await client.post(
        "/api/v1/ai/models",
        json={"model_name": "qwen-plus", "provider": "bailian", "is_default": True},
        headers=admin_headers,
    )

    kb_id = await _create_kb(client, admin_headers)
    await _upload(client, admin_headers, kb_id, "制度.txt", REIMBURSE)

    resp = await client.post(
        "/api/v1/ai/chat",
        json={
            "messages": [{"role": "user", "content": "住宿报销上限是多少"}],
            "knowledge_base_ids": [kb_id],
        },
        headers=employee_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["citations"], "应当返回引用"
    assert body["citations"][0]["filename"] == "制度.txt"

    # 检索到的内容确实被塞进了 system 提示词
    system_messages = [m for m in captured["messages"] if m["role"] == "system"]
    assert system_messages
    assert "500 元" in system_messages[0]["content"]


async def test_chat_without_knowledge_base_has_no_citations(
    client, admin_headers, employee_headers, fake_embedding, monkeypatch
) -> None:
    from app.ai.base import ChatResult

    class FakeProvider:
        last_usage = (5, 5)

        async def chat(self, messages, **overrides):
            return ChatResult(content="直接回答", model="qwen-plus")

    monkeypatch.setattr("app.ai.gateway.build_provider", lambda cfg: FakeProvider())
    await client.post(
        "/api/v1/ai/models",
        json={"model_name": "qwen-plus", "provider": "bailian", "is_default": True},
        headers=admin_headers,
    )

    resp = await client.post(
        "/api/v1/ai/chat",
        json={"messages": [{"role": "user", "content": "你好"}]},
        headers=employee_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["citations"] == []


# ------------------------------------------------------------------ 联动删除
async def test_delete_document_removes_chunks(
    client, admin_headers, session_factory, fake_embedding
) -> None:
    kb_id = await _create_kb(client, admin_headers)
    created = await _upload(client, admin_headers, kb_id, "制度.txt", REIMBURSE)
    document_id = created.json()["id"]

    resp = await client.delete(
        f"/api/v1/knowledge-bases/{kb_id}/documents/{document_id}",
        headers=admin_headers,
    )
    assert resp.status_code == 200

    async with session_factory() as session:
        remaining = await session.scalar(
            select(func.count()).select_from(DocumentChunk)
        )
    assert remaining == 0
