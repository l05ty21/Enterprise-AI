"""Provider 工厂。单独抽出来是为了测试里能一行 monkeypatch 掉真实网络调用。"""

from __future__ import annotations

from app.ai.base import ProviderSettings
from app.ai.openai_compat import OpenAICompatProvider


def build_provider(cfg: ProviderSettings) -> OpenAICompatProvider:
    return OpenAICompatProvider(cfg)
