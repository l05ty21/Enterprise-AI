"""向量存取抽象层。

默认实现把向量直接存在 MySQL 的 ``document_chunks.embedding`` 列（float32 字节串），
检索时在应用层用 numpy 算余弦相似度。这样做的理由：

* 1 GiB 内存的机器跑不动 Milvus（standalone 常驻 4 GB+）
* 几万条切片以内，numpy 暴力检索是毫秒级，完全够用
* 接口固定，将来换成 Milvus 只需新增一个实现类

数据量到十万级以上、或需要多进程共享索引时，再实现 ``MilvusVectorStore``。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import Document, DocumentChunk

# 单次检索最多扫描的切片数，防止知识库变大后一次查爆内存
MAX_SCAN_ROWS = 5000


@dataclass(slots=True)
class ScoredChunk:
    chunk: DocumentChunk
    score: float
    filename: str


def encode_vector(vector: list[float]) -> bytes:
    return np.asarray(vector, dtype=np.float32).tobytes()


def decode_vector(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)


def _normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


class MySQLVectorStore:
    """基于 MySQL + numpy 的向量存储实现。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def search(
        self,
        organization_id: int,
        query_vector: list[float],
        *,
        kb_ids: list[int] | None = None,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[ScoredChunk]:
        stmt = (
            select(DocumentChunk, Document.filename)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(
                DocumentChunk.organization_id == organization_id,
                DocumentChunk.embedding.is_not(None),
                Document.status == "ready",
            )
        )
        if kb_ids:
            stmt = stmt.where(Document.kb_id.in_(kb_ids))
        stmt = stmt.order_by(DocumentChunk.id).limit(MAX_SCAN_ROWS)

        rows = (await self.session.execute(stmt)).all()
        if not rows:
            return []

        matrix = np.vstack([decode_vector(row[0].embedding) for row in rows])
        query = np.asarray(query_vector, dtype=np.float32)

        if matrix.shape[1] != query.shape[0]:
            # 换过 embedding 模型时维度会不一致，直接视为不可比
            return []

        scores = _normalize(matrix) @ (query / (np.linalg.norm(query) or 1.0))
        order = np.argsort(scores)[::-1][:top_k]

        results: list[ScoredChunk] = []
        for index in order:
            score = float(scores[index])
            if score < min_score:
                continue
            chunk, filename = rows[int(index)]
            results.append(ScoredChunk(chunk=chunk, score=score, filename=filename))
        return results
