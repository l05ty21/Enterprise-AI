from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

TokenType = Literal["access", "refresh"]

# argon2id，参数使用 pwdlib 的推荐值
password_hasher = PasswordHash.recommended()


@dataclass(slots=True)
class TokenPayload:
    """解码后的 JWT 内容。"""

    sub: str
    organization_id: int
    token_type: TokenType
    jti: str
    exp: datetime


def hash_password(raw_password: str) -> str:
    return password_hasher.hash(raw_password)


def verify_password(raw_password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(raw_password, password_hash)
    except Exception:  # 哈希损坏 / 算法不匹配时一律视为校验失败
        return False


def _encode(
    user_id: int,
    organization_id: int,
    token_type: TokenType,
    expires_delta: timedelta,
) -> tuple[str, TokenPayload]:
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    jti = uuid.uuid4().hex
    payload = {
        "sub": str(user_id),
        "org": organization_id,
        "typ": token_type,
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, TokenPayload(
        sub=str(user_id),
        organization_id=organization_id,
        token_type=token_type,
        jti=jti,
        exp=expire,
    )


def create_access_token(user_id: int, organization_id: int) -> tuple[str, TokenPayload]:
    return _encode(
        user_id,
        organization_id,
        "access",
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: int, organization_id: int) -> tuple[str, TokenPayload]:
    return _encode(
        user_id,
        organization_id,
        "refresh",
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str, *, expected_type: TokenType | None = None) -> TokenPayload:
    """解码并校验 JWT。无效、过期或类型不符时抛出 jwt 异常，由上层转换为 401。"""
    payload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
        options={"require": ["exp", "sub", "typ", "jti"]},
    )
    token_type = payload.get("typ")
    if expected_type and token_type != expected_type:
        raise jwt.InvalidTokenError(
            f"token type mismatch: expected {expected_type}, got {token_type}"
        )
    return TokenPayload(
        sub=str(payload["sub"]),
        organization_id=int(payload["org"]),
        token_type=token_type,
        jti=str(payload["jti"]),
        exp=datetime.fromtimestamp(int(payload["exp"]), tz=timezone.utc),
    )
