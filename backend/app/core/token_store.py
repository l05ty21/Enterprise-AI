from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Protocol

from app.core.config import settings


class TokenStore(Protocol):
    """Token 吊销名单。退出登录 / 强制下线时把 jti 写入。"""

    async def revoke(self, jti: str, expires_at: datetime) -> None: ...

    async def is_revoked(self, jti: str) -> bool: ...


class InMemoryTokenStore:
    """单进程内存实现，仅适合本地开发与测试。多实例部署必须使用 Redis。"""

    def __init__(self) -> None:
        self._items: dict[str, float] = {}

    async def revoke(self, jti: str, expires_at: datetime) -> None:
        self._items[jti] = expires_at.timestamp()

    async def is_revoked(self, jti: str) -> bool:
        now = time.time()
        expired = [key for key, exp in self._items.items() if exp <= now]
        for key in expired:
            self._items.pop(key, None)
        return jti in self._items


class RedisTokenStore:
    """使用 Redis 存储吊销名单，key 自动随 token 过期时间过期。"""

    def __init__(self, url: str) -> None:
        from redis.asyncio import Redis  # 延迟导入，避免无 Redis 时的启动失败

        self._redis = Redis.from_url(url, encoding="utf-8", decode_responses=True)
        self._fallback = InMemoryTokenStore()

    async def revoke(self, jti: str, expires_at: datetime) -> None:
        ttl = max(int(expires_at.timestamp() - time.time()), 1)
        try:
            await self._redis.setex(f"token:revoked:{jti}", ttl, "1")
        except Exception:  # Redis 不可用时退化为进程内黑名单
            await self._fallback.revoke(jti, expires_at)

    async def is_revoked(self, jti: str) -> bool:
        try:
            if await self._redis.exists(f"token:revoked:{jti}"):
                return True
        except Exception:
            return await self._fallback.is_revoked(jti)
        return await self._fallback.is_revoked(jti)


_store: TokenStore | None = None


def get_token_store() -> TokenStore:
    global _store
    if _store is None:
        if settings.REDIS_URL:
            _store = RedisTokenStore(settings.REDIS_URL)
        else:
            _store = InMemoryTokenStore()
    return _store


def set_token_store(store: TokenStore | None) -> None:
    """测试用：替换全局实现。"""
    global _store
    _store = store


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
