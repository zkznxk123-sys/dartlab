"""Ollama 로컬 LLM provider."""

from __future__ import annotations

from typing import Generator

from dartlab.ai.providers.base import BaseProvider
from dartlab.ai.types import LLMConfig, LLMResponse, ToolCall, ToolResponse

OLLAMA_DEFAULT_URL = "http://localhost:11434"


def _buildInferenceOptions() -> dict:
    """GPU VRAM 기반 Ollama 추론 옵션 자동 결정."""
    from dartlab.ai.providers.support.ollama_setup import _detect_gpu

    gpu = _detect_gpu()
    options: dict = {"num_gpu": 999 if gpu["available"] else 0}

    vram = gpu.get("vram_mb") or 0
    if vram >= 12000:
        options["num_ctx"] = 8192
        options["num_batch"] = 1024
    elif vram >= 6000:
        options["num_ctx"] = 4096
        options["num_batch"] = 512
    else:
        options["num_ctx"] = 2048
        options["num_batch"] = 256

    options["flash_attn"] = True
    return options


_VRAM_MODEL_TIERS: list[tuple[int, str, str]] = [
    (24000, "qwen3:32b-q4_K_M", "32B 4bit — 최고 품질"),
    (12000, "qwen3:14b-q4_K_M", "14B 4bit — 고품질"),
    (8000, "qwen3:8b-q4_K_M", "8B 4bit — 균형"),
    (6000, "qwen3:4b-q4_K_M", "4B 4bit — 경량"),
    (4000, "qwen3:1.7b-q4_K_M", "1.7B 4bit — 최경량"),
    (0, "qwen3:0.6b", "0.6B — CPU 전용"),
]


def recommendModel(vramMb: int | None = None) -> dict:
    if vramMb is None:
        from dartlab.ai.providers.support.ollama_setup import _detect_gpu

        gpu = _detect_gpu()
        vramMb = gpu.get("vram_mb") or 0

    for minVram, model, desc in _VRAM_MODEL_TIERS:
        if vramMb >= minVram:
            return {"model": model, "description": desc, "vram_mb": vramMb}
    return {"model": _VRAM_MODEL_TIERS[-1][1], "description": _VRAM_MODEL_TIERS[-1][2], "vram_mb": vramMb}


class OllamaProvider(BaseProvider):
    """Ollama 로컬 provider."""

    @property
    def supports_native_tools(self) -> bool:
        return True

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = None
        self._base_url = config.base_url or f"{OLLAMA_DEFAULT_URL}/v1"

    @property
    def default_model(self) -> str:
        models = self.get_installed_models()
        if models:
            return models[0]
        return "llama3.1"

    def check_available(self) -> bool:
        import httpx

        try:
            resp = httpx.get(f"{OLLAMA_DEFAULT_URL}/api/tags", timeout=2)
            return resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    def get_installed_models(self) -> list[str]:
        import httpx

        try:
            resp = httpx.get(f"{OLLAMA_DEFAULT_URL}/api/tags", timeout=2)
            data = resp.json()
            names = []
            for m in data.get("models", []):
                name = m["name"]
                if name.endswith(":latest"):
                    name = name[:-7]
                names.append(name)
            return names
        except (httpx.HTTPError, AttributeError, KeyError, OSError, TypeError, ValueError):
            return []

    def preload(self, *, keepAliveMinutes: int = 30) -> bool:
        import httpx

        options = _buildInferenceOptions()
        keepAlive = f"{keepAliveMinutes}m" if keepAliveMinutes > 0 else -1
        try:
            resp = httpx.post(
                f"{OLLAMA_DEFAULT_URL}/api/generate",
                json={
                    "model": self.resolved_model,
                    "prompt": "",
                    "keep_alive": keepAlive,
                    "stream": False,
                    "options": options,
                },
                timeout=120,
            )
            return resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    def unload(self) -> bool:
        import httpx

        try:
            resp = httpx.post(
                f"{OLLAMA_DEFAULT_URL}/api/generate",
                json={"model": self.resolved_model, "prompt": "", "keep_alive": 0, "stream": False},
                timeout=10,
            )
            return resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    def serverVersion(self) -> str | None:
        import httpx

        try:
            resp = httpx.get(f"{OLLAMA_DEFAULT_URL}/api/version", timeout=2)
            if resp.status_code == 200:
                return resp.json().get("version")
        except (httpx.HTTPError, ValueError, KeyError, OSError):
            pass
        return None

    def _ensure_available(self):
        if not self.check_available():
            from dartlab.ai.providers.support.ollama_setup import get_install_guide

            raise ConnectionError(f"Ollama 서버에 접근할 수 없습니다 ({OLLAMA_DEFAULT_URL}).\n\n{get_install_guide()}")

    def _get_client(self):
        if self._client is None:
            self._ensure_available()
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError("openai 패키지가 필요합니다.\n  pip install --upgrade dartlab")
            self._client = OpenAI(base_url=self._base_url, api_key="ollama")
        return self._client

    def complete(self, messages: list[dict[str, str]]) -> LLMResponse:
        client = self._get_client()
        response = client.chat.completions.create(
            model=self.resolved_model,
            messages=messages,
            temperature=self.config.temperature,
        )
        return LLMResponse(
            answer=response.choices[0].message.content or "",
            provider="ollama",
            model=self.resolved_model,
        )

    def stream(self, messages: list[dict[str, str]]) -> Generator[str, None, None]:
        client = self._get_client()
        stream = client.chat.completions.create(
            model=self.resolved_model,
            messages=messages,
            temperature=self.config.temperature,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def complete_json(
        self,
        messages: list[dict[str, str]],
        schema: dict | None = None,
    ) -> LLMResponse:
        client = self._get_client()
        if schema:
            response_format = {
                "type": "json_schema",
                "json_schema": {"name": "analysis", "schema": schema},
            }
        else:
            response_format = {"type": "json_object"}

        response = client.chat.completions.create(
            model=self.resolved_model,
            messages=messages,
            temperature=self.config.temperature,
            response_format=response_format,
        )
        return LLMResponse(
            answer=response.choices[0].message.content or "",
            provider="ollama",
            model=self.resolved_model,
        )

    def complete_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        *,
        tool_choice: str | None = None,
    ) -> ToolResponse:
        import json

        client = self._get_client()
        kwargs: dict = {
            "model": self.resolved_model,
            "messages": messages,
            "temperature": self.config.temperature,
        }
        if tools:
            kwargs["tools"] = tools

        response = client.chat.completions.create(**kwargs)
        choice = response.choices[0]

        tool_calls = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=json.loads(tc.function.arguments),
                    )
                )

        return ToolResponse(
            answer=choice.message.content or "",
            provider="ollama",
            model=self.resolved_model,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
        )
