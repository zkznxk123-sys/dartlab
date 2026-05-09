"""xAI Grok provider adapter — uses OpenAI chat completions schema with xAI base_url."""

from __future__ import annotations

import os
from typing import Any

from dartlab.ai.providers.openai import OpenAIProvider

XAI_BASE_URL = "https://api.x.ai/v1"


class XAIProvider(OpenAIProvider):
    name = "xai"
    default_model = "grok-2-latest"

    def _client(self) -> Any:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai SDK 가 설치되지 않았다 — xAI adapter 가 의존한다") from exc
        api_key = self.config.api_key or os.getenv("XAI_API_KEY")
        if not api_key:
            raise RuntimeError("XAI_API_KEY 가 없다")
        return OpenAI(api_key=api_key, base_url=self.config.base_url or XAI_BASE_URL)

    def check_available(self) -> bool:
        if not (self.config.api_key or os.getenv("XAI_API_KEY")):
            return False
        try:
            from openai import OpenAI  # noqa: F401
        except ImportError:
            return False
        return True


__all__ = ["XAIProvider"]
