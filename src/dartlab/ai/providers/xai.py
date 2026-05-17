"""xAI Grok provider adapter — uses OpenAI chat completions schema with xAI base_url."""

from __future__ import annotations

import os
from typing import Any

from dartlab.ai.providers.openai import OpenAIProvider

XAI_BASE_URL = "https://api.x.ai/v1"


class XAIProvider(OpenAIProvider):
    """xAI Grok provider — OpenAI 스키마 + x.ai baseUrl 재사용."""

    name = "xai"
    defaultModel = "grok-2-latest"

    def _client(self) -> Any:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai SDK 가 설치되지 않았다 — xAI adapter 가 의존한다") from exc
        apiKey = self.config.apiKey or os.getenv("XAI_API_KEY")
        if not apiKey:
            raise RuntimeError("XAI_API_KEY 가 없다")
        return OpenAI(apiKey=apiKey, baseUrl=self.config.baseUrl or XAI_BASE_URL)

    def checkAvailable(self) -> bool:
        """XAI_API_KEY + openai SDK 동시 보유 여부."""
        if not (self.config.apiKey or os.getenv("XAI_API_KEY")):
            return False
        try:
            from openai import OpenAI  # noqa: F401
        except ImportError:
            return False
        return True


__all__ = ["XAIProvider"]
