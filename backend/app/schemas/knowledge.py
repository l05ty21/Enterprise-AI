from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# ---------------------------------------------------------------- 知识库
class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2000)
    visibility: str = Field(default="org", pattern="^(private|department|org)$")


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2000)
    visibility: str | None = Field(default=None, pattern="^(private|department|org)$")
    status: int | None = Field(default=None, ge=0, le=1)


class KnowledgeBaseRead(BaseModel):
    id: int
    name: str
    description: str | None = None
    owner_id: int
    visibility: str
    status: int
    document_count: int = 0
    chunk_count: int = 0
    created_at: datetime | None = None


# ---------------------------------------------------------------- 文档
class DocumentRead(BaseModel):
    id: int
    kb_id: int
    filename: str
    file_type: str | None = None
    file_size: int | None = None
    status: str
    chunk_count: int = 0
    error_message: str | None = None
    created_at: datetime | None = None


# ---------------------------------------------------------------- 检索
class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    kb_ids: list[int] | None = Field(
        default=None, description="限定在哪些知识库内检索；不传则全企业范围"
    )
    top_k: int = Field(default=5, ge=1, le=20)


class SearchHit(BaseModel):
    chunk_id: int
    document_id: int
    filename: str
    content: str
    score: float


class Citation(BaseModel):
    """回答里引用的来源片段，前端展示用。"""

    document_id: int
    filename: str
    chunk_id: int
    score: float
    snippet: str
