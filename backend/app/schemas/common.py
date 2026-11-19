from __future__ import annotations

from math import ceil
from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field

T = TypeVar("T")


class PageParams(BaseModel):
    """分页参数。page 从 1 开始，page_size 上限 200，避免一次拉全表。"""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int

    @property
    def pages(self) -> int:
        return ceil(self.total / self.page_size) if self.page_size else 0

    def to_dict(self) -> dict:
        return {
            "items": [item.model_dump() if isinstance(item, BaseModel) else item for item in self.items],
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "pages": self.pages,
        }


def page_params(
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(20, ge=1, le=200, description="每页条数，最大 200"),
) -> PageParams:
    """FastAPI 依赖，用于解析统一的分页参数。"""
    return PageParams(page=page, page_size=page_size)


class MessageResponse(BaseModel):
    message: str = "操作成功"
