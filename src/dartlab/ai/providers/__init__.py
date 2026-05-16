"""Provider boundary for Ask Workbench.

The kernel owns workbench actions and verification.  Providers only decide the
next action or final draft by using a small tool-calling surface.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from typing import Any, Protocol

from dartlab.ai.settings.modelResolver import resolveDefaultModel


@dataclass(frozen=True)
class ProviderConfig:
    """LLM provider 설정 — provider/model/baseUrl/apiKey/temperature 통합."""

    provider: str | None = None
    model: str | None = None
    baseUrl: str | None = None
    apiKey: str | None = None
    temperature: float | None = None
    maxTokens: int | None = None
    systemPrompt: str | None = None

    def merge(self, overrides: dict[str, Any]) -> ProviderConfig:
        """기존 필드 위에 None 이 아닌 overrides 만 덮어쓴 새 ProviderConfig."""
        values = asdict(self)
        values.update({key: value for key, value in overrides.items() if key in values and value is not None})
        return ProviderConfig(**values)


def getConfig(provider: str | None = None, **kwargs: Any) -> ProviderConfig:
    """provider 결정 → profile/env/kwargs 합성 → ProviderConfig 반환."""
    normalized = _normalizeProvider(provider or kwargs.get("provider"))
    profile = _resolveProfile(normalized, kwargs.get("role"))
    if normalized is None:
        normalized = _normalizeProvider(profile.get("provider"))
    explicitModel = kwargs.get("model")
    explicit_base = kwargs.get("base_url") or kwargs.get("baseUrl")
    explicit_key = kwargs.get("api_key") or kwargs.get("apiKey")
    env_key = _envKeyFor(normalized)
    apiKey = explicit_key or profile.get("api_key") or (os.environ.get(env_key) if env_key else None)
    baseUrl = explicit_base or profile.get("base_url") or _baseUrlFor(normalized)
    if normalized == "oauth-codex" and explicitModel is None:
        model = _oauthDefaultModel(configuredModel=profile.get("model"))
    else:
        model = resolveDefaultModel(
            normalized,
            explicitModel=explicitModel,
            configuredModel=profile.get("model"),
            fallbackModel=_defaultModelFor(normalized),
        )
    if normalized in {"oauth-codex", "chatgpt", "gpt"} and not apiKey:
        apiKey = _oauthAccessToken()
    if normalized == "ollama" and not apiKey:
        apiKey = "ollama"
    return ProviderConfig(
        provider=normalized,
        model=model,
        baseUrl=baseUrl,
        apiKey=apiKey,
        temperature=kwargs.get("temperature") if kwargs.get("temperature") is not None else profile.get("temperature"),
    )


def _normalizeProvider(provider: str | None) -> str | None:
    if not provider:
        return None
    lowered = provider.strip().lower()
    if lowered in {"chatgpt", "gpt", "oauth"}:
        return "oauth-codex"
    if lowered in {"openai-compatible", "openai_compat"}:
        return "custom"
    return lowered


def _resolveProfile(provider: str | None, role: str | None) -> dict[str, Any]:
    try:
        from dartlab.ai.settings.profile import getProfileManager

        return getProfileManager().resolve(provider=provider, role=role)
    except Exception:
        return {}


def _envKeyFor(provider: str | None) -> str | None:
    return {
        "openai": "OPENAI_API_KEY",
        "custom": "OPENAI_API_KEY",
        "groq": "GROQ_API_KEY",
        "cerebras": "CEREBRAS_API_KEY",
        "mistral": "MISTRAL_API_KEY",
    }.get(provider or "")


def _baseUrlFor(provider: str | None) -> str | None:
    if provider == "custom":
        return os.environ.get("DARTLAB_OPENAI_COMPAT_BASE_URL") or os.environ.get("OPENAI_BASE_URL")
    if provider == "groq":
        return os.environ.get("GROQ_BASE_URL") or "https://api.groq.com/openai/v1"
    if provider == "cerebras":
        return os.environ.get("CEREBRAS_BASE_URL") or "https://api.cerebras.ai/v1"
    if provider == "mistral":
        return os.environ.get("MISTRAL_BASE_URL") or "https://api.mistral.ai/v1"
    if provider == "oauth-codex":
        return (
            os.environ.get("DARTLAB_OAUTH_BASE_URL")
            or os.environ.get("DARTLAB_OAUTH_API_BASE_URL")
            or "https://chatgpt.com/backend-api"
        )
    if provider == "ollama":
        return (
            os.environ.get("OLLAMA_OPENAI_BASE_URL") or os.environ.get("OLLAMA_BASE_URL") or "http://127.0.0.1:11434/v1"
        )
    return os.environ.get("OPENAI_BASE_URL") if provider == "openai" else None


def _defaultModelFor(provider: str | None) -> str | None:
    env_model = os.environ.get("DARTLAB_DEFAULT_MODEL")
    if env_model and provider not in {"openai", "oauth-codex", None}:
        return env_model
    if provider in {"openai", "oauth-codex", None}:
        return resolveDefaultModel(provider)
    if provider == "groq":
        return os.environ.get("GROQ_MODEL") or "llama-3.3-70b-versatile"
    if provider == "cerebras":
        return os.environ.get("CEREBRAS_MODEL") or "llama3.3-70b"
    if provider == "mistral":
        return os.environ.get("MISTRAL_MODEL") or "mistral-large-latest"
    if provider == "ollama":
        return os.environ.get("OLLAMA_MODEL") or "qwen3:14b"
    return None


def _oauthAccessToken() -> str | None:
    try:
        from .support.oauthToken import getValidToken, loadToken

        value = getValidToken()
        if isinstance(value, str) and value:
            return value
        token = loadToken()
        if isinstance(token, dict):
            value = token.get("access_token")
            if isinstance(value, str) and value:
                return value
    except Exception:
        return None
    return None


def _oauthDefaultModel(*, configuredModel: str | None = None) -> str | None:
    if configuredModel and os.environ.get("DARTLAB_ALLOW_STALE_OAUTH_MODEL") == "1":
        return configuredModel
    try:
        from .oauthCodex import availableModels

        models = availableModels()
        if models:
            return models[0]
    except Exception:
        pass
    return resolveDefaultModel("oauth-codex")


@dataclass(frozen=True)
class ToolCall:
    """LLM 응답의 tool 호출 한 건 — id + 함수명 + 인자 dict."""

    id: str
    name: str
    args: dict[str, Any]


@dataclass(frozen=True)
class ProviderTurn:
    """provider 한 턴 응답 — content + toolCalls + (선택) raw payload."""

    content: str
    toolCalls: list[ToolCall]
    raw: dict[str, Any] | None = None


@dataclass(frozen=True)
class StreamChunk:
    """LLM streaming 델타. text 는 신규 부분만 (누적 X). final=True 가 종료 신호."""

    text: str = ""
    final: bool = False
    turn: ProviderTurn | None = None


class WorkbenchProvider(Protocol):
    """LLM provider 가 충족해야 할 최소 Protocol — config + generate()."""

    config: ProviderConfig

    def generate(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ProviderTurn:
        """messages + tools → ProviderTurn 생성. provider 별 LLM 호출 본체."""
        ...


def streamProvider(
    provider: Any, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
) -> "Iterator[StreamChunk]":
    """Provider 의 generate_stream 사용. 미지원 provider 는 generate() wrap fallback.

    chatNative / agent loop 가 본 helper 호출. UI 가 typing 효과 받음 (지원 provider).
    """
    from collections.abc import Iterator  # noqa: F401 — typing only

    if hasattr(provider, "generateStream") and callable(getattr(provider, "generateStream")):
        yield from provider.generateStream(messages, tools)
        return
    turn = provider.generate(messages, tools)
    yield StreamChunk(text=turn.content, final=True, turn=turn)


class UnavailableProvider:
    """provider 미구성 시 placeholder — generate() 호출 시 즉시 RuntimeError."""

    def __init__(self, config: ProviderConfig | None = None) -> None:
        self.config = config or ProviderConfig()
        self.resolvedModel = self.config.model

    def generate(self, *_args: Any, **_kwargs: Any) -> ProviderTurn:
        """항상 RuntimeError — provider 구성 누락 명시."""
        raise RuntimeError("provider adapter is not configured for Ask Workbench Kernel v1")

    def checkAvailable(self) -> bool:
        """항상 False — placeholder 라 사용 불가."""
        return False


class OpenAICompatibleProvider:
    """OpenAI-compatible chat-completions adapter for workbench actions."""

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config
        self.resolvedModel = config.model or _defaultModelFor(config.provider)

    def checkAvailable(self) -> bool:
        """provider 별 자격 (api_key/base_url) 보유 여부 검증."""
        provider = (self.config.provider or "").lower()
        if provider == "oauth-codex":
            return bool(self.config.apiKey and self.config.baseUrl)
        if provider in {"custom", "ollama"}:
            return bool(self.config.baseUrl and self.config.apiKey)
        return bool(self.config.apiKey)

    def generate(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ProviderTurn:
        """messages + tools → OpenAI responses 또는 chat.completions 호출 → ProviderTurn."""
        try:
            from openai import OpenAI
        except Exception as exc:  # pragma: no cover - environment dependent
            raise RuntimeError("openai package is required for tool-calling provider mode") from exc

        client = self._client(OpenAI)
        if (self.config.provider or "").lower() in {"openai", "oauth-codex"}:
            try:
                return self._generateResponses(client, messages, tools)
            except Exception as exc:
                if not _isResponsesUnsupported(exc):
                    raise
        return self._generateChatCompletions(client, messages, tools)

    def _client(self, clientCls: Any) -> Any:
        client_kwargs: dict[str, Any] = {}
        if self.config.apiKey:
            client_kwargs["api_key"] = self.config.apiKey
        if self.config.baseUrl:
            client_kwargs["base_url"] = self.config.baseUrl
        return clientCls(**client_kwargs)

    def _generateResponses(
        self, client: Any, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> ProviderTurn:
        response = client.responses.create(
            model=self.resolvedModel,
            input=_responsesInput(messages),
            tools=_responsesTools(tools),
            toolChoice="auto",
        )
        toolCalls: list[ToolCall] = []
        output_items = getattr(response, "output", None) or []
        for item in output_items:
            item_type = getattr(item, "type", None) or (item.get("type") if isinstance(item, dict) else None)
            if item_type != "function_call":
                continue
            name = getattr(item, "name", None) or (item.get("name") if isinstance(item, dict) else "")
            call_id = (
                getattr(item, "call_id", None)
                or getattr(item, "id", None)
                or (item.get("call_id") or item.get("id") if isinstance(item, dict) else "")
            )
            rawArgs = getattr(item, "arguments", None) or (item.get("arguments") if isinstance(item, dict) else "{}")
            toolCalls.append(ToolCall(id=str(call_id), name=str(name), args=_parseToolArgs(rawArgs)))
        raw: dict[str, Any] | None = None
        try:
            raw = response.model_dump()
        except Exception:
            raw = None
        return ProviderTurn(content=getattr(response, "output_text", "") or "", toolCalls=toolCalls, raw=raw)

    def _generateChatCompletions(
        self, client: Any, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> ProviderTurn:
        response = client.chat.completions.create(
            model=self.resolvedModel,
            messages=messages,
            tools=tools,
            toolChoice="auto",
        )
        message = response.choices[0].message
        toolCalls: list[ToolCall] = []
        for call in message.toolCalls or []:
            rawArgs = getattr(call.function, "arguments", "") or "{}"
            args = _parseToolArgs(rawArgs)
            toolCalls.append(ToolCall(id=call.id, name=call.function.name, args=args))
        raw: dict[str, Any] | None = None
        try:
            raw = response.model_dump()
        except Exception:
            raw = None
        return ProviderTurn(content=message.content or "", toolCalls=toolCalls, raw=raw)

    def generateStream(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]):
        """Token-level streaming via OpenAI chat.completions stream=True.

        text 델타를 즉시 yield → UI typing 효과. 마지막 chunk 는 final=True + ProviderTurn.
        tool_calls streaming 처리는 Phase E 에서 — 현재는 final ProviderTurn 에서 한 번에.
        """
        try:
            from openai import OpenAI
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("openai package is required for tool-calling provider mode") from exc

        client = self._client(OpenAI)
        kwargs: dict[str, Any] = {
            "model": self.resolvedModel,
            "messages": messages,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        accumulated = ""
        tool_calls_partial: dict[int, dict[str, Any]] = {}
        try:
            stream = client.chat.completions.create(**kwargs)
        except Exception:
            # streaming 미지원 provider (custom base_url 등) — non-stream fallback
            turn = self._generateChatCompletions(client, messages, tools)
            yield StreamChunk(text=turn.content, final=True, turn=turn)
            return

        for chunk in stream:
            choices = getattr(chunk, "choices", None) or []
            if not choices:
                continue
            delta = getattr(choices[0], "delta", None)
            if delta is None:
                continue
            text = getattr(delta, "content", None) or ""
            if text:
                accumulated += text
                yield StreamChunk(text=text)
            for call_delta in getattr(delta, "tool_calls", None) or []:
                idx = getattr(call_delta, "index", 0) or 0
                slot = tool_calls_partial.setdefault(idx, {"id": None, "name": None, "args": ""})
                if getattr(call_delta, "id", None):
                    slot["id"] = call_delta.id
                fn = getattr(call_delta, "function", None)
                if fn is not None:
                    if getattr(fn, "name", None):
                        slot["name"] = fn.name
                    if getattr(fn, "arguments", None):
                        slot["args"] += fn.arguments

        toolCalls: list[ToolCall] = []
        for slot in tool_calls_partial.values():
            if slot.get("name"):
                toolCalls.append(
                    ToolCall(
                        id=str(slot.get("id") or ""),
                        name=str(slot["name"]),
                        args=_parseToolArgs(slot.get("args") or "{}"),
                    )
                )

        yield StreamChunk(
            final=True,
            turn=ProviderTurn(content=accumulated, toolCalls=toolCalls, raw=None),
        )


def _parseToolArgs(rawArgs: Any) -> dict[str, Any]:
    if isinstance(rawArgs, dict):
        return rawArgs
    if isinstance(rawArgs, str):
        import json

        try:
            parsed = json.loads(rawArgs or "{}")
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {"_raw": rawArgs}
    return {}


def _responsesTools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for tool in tools:
        function = tool.get("function") if isinstance(tool, dict) else None
        if not isinstance(function, dict):
            continue
        out.append(
            {
                "type": "function",
                "name": function.get("name"),
                "description": function.get("description", ""),
                "parameters": function.get("parameters", {"type": "object", "properties": {}}),
            }
        )
    return out


def _responsesInput(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for message in messages:
        role = message.get("role")
        if role == "tool":
            items.append(
                {
                    "type": "function_call_output",
                    "call_id": message.get("tool_call_id"),
                    "output": str(message.get("content") or ""),
                }
            )
            continue
        content = message.get("content")
        if not content:
            continue
        items.append({"role": role or "user", "content": str(content)})
    return items


def _isResponsesUnsupported(exc: Exception) -> bool:
    status_code = getattr(exc, "status_code", None)
    if status_code in {400, 404, 405}:
        text = str(exc).lower()
        return any(
            marker in text for marker in ("responses", "unknown", "unsupported", "not found", "invalid endpoint")
        )
    return isinstance(exc, (AttributeError, TypeError, ValueError))


def createProvider(*args: Any, **kwargs: Any) -> WorkbenchProvider:
    """ProviderConfig/dict → 적합한 WorkbenchProvider 어댑터 반환 (oauth-codex/openai-compat/...)."""
    raw_provider = (
        getattr(args[0], "provider", None) if args and hasattr(args[0], "provider") else kwargs.get("provider")
    )
    if isinstance(raw_provider, str) and raw_provider.strip().lower() == "chatgpt":
        raise ValueError("지원하지 않는 provider: chatgpt")
    if args and isinstance(args[0], ProviderConfig):
        config = args[0]
    elif args and hasattr(args[0], "provider"):
        raw = args[0]
        config = getConfig(
            provider=getattr(raw, "provider", None),
            model=getattr(raw, "model", None),
            baseUrl=getattr(raw, "base_url", None) or getattr(raw, "baseUrl", None),
            apiKey=getattr(raw, "api_key", None) or getattr(raw, "apiKey", None),
            temperature=getattr(raw, "temperature", None),
        )
    else:
        config = getConfig(**kwargs)
    provider = (config.provider or "").lower()
    factory = _PROVIDER_FACTORIES.get(provider)
    if factory is None:
        return UnavailableProvider(config)
    return factory(config)


def _makeOauthCodex(config: ProviderConfig) -> WorkbenchProvider:
    from .oauthCodex import OAuthCodexProvider

    return OAuthCodexProvider(config)


def _makeCodex(config: ProviderConfig) -> WorkbenchProvider:
    from .codex import CodexProvider

    return CodexProvider(config)


def _makeGemini(config: ProviderConfig) -> WorkbenchProvider:
    from .gemini import GeminiProvider

    return GeminiProvider(config)


def _makeOpenaiCompat(config: ProviderConfig) -> WorkbenchProvider:
    return OpenAICompatibleProvider(config)


# Provider id → factory. provider_catalog._PROVIDERS 와 1:1 일치해야 한다.
# wiredProviderIds() 가 본 dict 의 keys 와 catalog keys 의 정합을 보장.
_PROVIDER_FACTORIES: dict[str, Any] = {
    "oauth-codex": _makeOauthCodex,
    "codex": _makeCodex,
    "gemini": _makeGemini,
    "openai": _makeOpenaiCompat,
    "custom": _makeOpenaiCompat,
    "groq": _makeOpenaiCompat,
    "cerebras": _makeOpenaiCompat,
    "mistral": _makeOpenaiCompat,
    "ollama": _makeOpenaiCompat,
    # legacy aliases — get_config normalizes but kept for safety.
    "openai-compatible": _makeOpenaiCompat,
    "openai_compat": _makeOpenaiCompat,
}


def availableProviders() -> list[str]:
    """카탈로그 등록 provider id 목록. legacy alias 제외."""
    from ..settings.providerCatalog import wiredProviderIds

    return sorted(wiredProviderIds())


from .base import BaseProvider, LLMEvent, LLMProvider, Msg, RateLimitError

__all__ = [
    "BaseProvider",
    "LLMEvent",
    "LLMProvider",
    "Msg",
    "ProviderConfig",
    "ProviderTurn",
    "RateLimitError",
    "StreamChunk",
    "ToolCall",
    "WorkbenchProvider",
    "availableProviders",
    "createProvider",
    "get_config",
    "stream_provider",
]
