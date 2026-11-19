"""API Key 的对称加解密。

``ai_model_configs.api_key_encrypted`` 只允许存密文。密钥来源优先级：

1. 环境变量 ``AI_KEY_ENCRYPTION_KEY``（生产环境必须显式配置）
2. 回落用 ``SECRET_KEY`` 派生 —— 保证本地开发不用额外配一个变量也能跑，
   但生产环境两者分离更安全。
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.core.exceptions import AppError


def _fernet() -> Fernet:
    raw = settings.AI_KEY_ENCRYPTION_KEY or settings.SECRET_KEY
    # 任何长度的配置都能派生出合法的 32 字节 Fernet 密钥
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_api_key(plain: str) -> str:
    return _fernet().encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt_api_key(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError) as exc:
        raise AppError(
            "API Key 解密失败，请重新保存模型配置",
            code="ai_key_decrypt_failed",
        ) from exc


def mask_api_key(plain: str) -> str:
    """只回显首尾各 4 位，日志和接口响应都不允许出现完整 Key。"""
    if len(plain) <= 8:
        return "****"
    return f"{plain[:4]}****{plain[-4:]}"
