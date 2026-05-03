"""Provider boundary for Ask Workbench.

The kernel owns workbench actions and verification.  Providers only decide the
next action or final draft by using a small tool-calling surface.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Any, Protocol

from dartlab.core.ai.model_resolver import resolve_default_model


@dataclass(frozen=True)
class ProviderConfig:
    provider: str | None = None
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    system_prompt: str | None = None

    def merge(self, overrides: dict[str, Any]) -> ProviderConfig:
        values = asdict(self)
        values.update({key: value for key, value in overrides.items() if key in values and value is not None})
        return ProviderConfig(**values)


def get_config(provider: str | None = None, **kwargs: Any) -> ProviderConfig:
    normalized = _normalize_provider(provider or kwargs.get("provider"))
    profile = _resolve_profile(normalized, kwargs.get("role"))
    if normalized is None:
        normalized = _normalize_provider(profile.get("provider"))
    explicit_model = kwargs.get("model")
    explicit_base = kwargs.get("base_url") or kwargs.get("baseUrl")
    explicit_key = kwargs.get("api_key") or kwargs.get("apiKey")
    env_key = _env_key_for(normalized)
    api_key = explicit_key or profile.get("api_key") or (os.environ.get(env_key) if env_key else None)
    base_url = explicit_base or profile.get("base_url") or _base_url_for(normalized)
    if normalized == "oauth-codex" and explicit_model is None:
        model = _oauth_default_model(configured_model=profile.get("model"))
    else:
        model = resolve_default_model(
            normalized,
            explicit_model=explicit_model,
            configured_model=profile.get("model"),
            fallback_model=_default_model_for(normalized),
        )
    if normalized in {"oauth-codex", "chatgpt", "gpt"} and not api_key:
        api_key = _oauth_access_token()
    if normalized == "ollama" and not api_key:
        api_key = "ollama"
    return ProviderConfig(
        provider=normalized,
        model=model,
        base_url=base_url,
        api_key=api_key,
        temperature=kwargs.get("temperature") if kwargs.get("temperature") is not None else profile.get("temperature"),
    )


def _normalize_provider(provider: str | None) -> str | None:
    if not provider:
        return None
    lowered = provider.strip().lower()
    if lowered in {"chatgpt", "gpt", "oauth"}:
        return "oauth-codex"
    if lowered in {"openai-compatible", "openai_compat"}:
        return "custom"
    return lowered


def _resolve_profile(provider: str | None, role: str | None) -> dict[str, Any]:
    try:
        from dartlab.core.ai.profile import get_profile_manager

        return get_profile_manager().resolve(provider=provider, role=role)
    except Exception:
        return {}


def _env_key_for(provider: str | None) -> str | None:
    return {
        "openai": "OPENAI_API_KEY",
        "custom": "OPENAI_API_KEY",
        "groq": "GROQ_API_KEY",
        "cerebras": "CEREBRAS_API_KEY",
        "mistral": "MISTRAL_API_KEY",
    }.get(provider or "")


def _base_url_for(provider: str | None) -> str | None:
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


def _default_model_for(provider: str | None) -> str | None:
    env_model = os.environ.get("DARTLAB_DEFAULT_MODEL")
    if env_model and provider not in {"openai", "oauth-codex", None}:
        return env_model
    if provider in {"openai", "oauth-codex", None}:
        return resolve_default_model(provider)
    if provider == "groq":
        return os.environ.get("GROQ_MODEL") or "llama-3.3-70b-versatile"
    if provider == "cerebras":
        return os.environ.get("CEREBRAS_MODEL") or "llama3.3-70b"
    if provider == "mistral":
        return os.environ.get("MISTRAL_MODEL") or "mistral-large-latest"
    if provider == "ollama":
        return os.environ.get("OLLAMA_MODEL") or "qwen3:14b"
    return None


def _oauth_access_token() -> str | None:
    try:
        from .support.oauth_token import get_valid_token, load_token

        value = get_valid_token()
        if isinstance(value, str) and value:
            return value
        token = load_token()
        if isinstance(token, dict):
            value = token.get("access_token")
            if isinstance(value, str) and value:
                return value
    except Exception:
        return None
    return None


def _oauth_default_model(*, configured_model: str | None = None) -> str | None:
    if configured_model and os.environ.get("DARTLAB_ALLOW_STALE_OAUTH_MODEL") == "1":
        return configured_model
    try:
        from .oauth_codex import availableModels

        models = availableModels()
        if models:
            return models[0]
    except Exception:
        pass
    return resolve_default_model("oauth-codex")


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    args: dict[str, Any]


@dataclass(frozen=True)
class ProviderTurn:
    content: str
    tool_calls: list[ToolCall]
    raw: dict[str, Any] | None = None


class WorkbenchProvider(Protocol):
    config: ProviderConfig

    def generate(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ProviderTurn: ...


class UnavailableProvider:
    def __init__(self, config: ProviderConfig | None = None) -> None:
        self.config = config or ProviderConfig()
        self.resolved_model = self.config.model

    def generate(self, *_args: Any, **_kwargs: Any) -> ProviderTurn:
        raise RuntimeError("provider adapter is not configured for Ask Workbench Kernel v1")

    def check_available(self) -> bool:
        return False


class OpenAICompatibleProvider:
    """OpenAI-compatible chat-completions adapter for workbench actions."""

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config
        self.resolved_model = config.model or _default_model_for(config.provider)

    def check_available(self) -> bool:
        provider = (self.config.provider or "").lower()
        if provider == "oauth-codex":
            return bool(self.config.api_key and self.config.base_url)
        if provider in {"custom", "ollama"}:
            return bool(self.config.base_url and self.config.api_key)
        return bool(self.config.api_key)

    def generate(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ProviderTurn:
        try:
            from openai import OpenAI
        except Exception as exc:  # pragma: no cover - environment dependent
            raise RuntimeError("openai package is required for tool-calling provider mode") from exc

        client = self._client(OpenAI)
        if (self.config.provider or "").lower() in {"openai", "oauth-codex"}:
            try:
                return self._generate_responses(client, messages, tools)
            except Exception as exc:
                # Some OpenAI-compatible deployments and older SDKs do not expose
                # Responses API semantics. Chat Completions remains the adapter
                # fallback; the kernel still sees one provider boundary.
                if not _is_responses_unsupported(exc):
                    raise
        return self._generate_chat_completions(client, messages, tools)

    def _client(self, client_cls: Any) -> Any:
        client_kwargs: dict[str, Any] = {}
        if self.config.api_key:
            client_kwargs["api_key"] = self.config.api_key
        if self.config.base_url:
            client_kwargs["base_url"] = self.config.base_url
        return client_cls(**client_kwargs)

    def _generate_responses(
        self, client: Any, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> ProviderTurn:
        response = client.responses.create(
            model=self.resolved_model,
            input=_responses_input(messages),
            tools=_responses_tools(tools),
            tool_choice="auto",
        )
        tool_calls: list[ToolCall] = []
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
            raw_args = getattr(item, "arguments", None) or (item.get("arguments") if isinstance(item, dict) else "{}")
            tool_calls.append(ToolCall(id=str(call_id), name=str(name), args=_parse_tool_args(raw_args)))
        raw: dict[str, Any] | None = None
        try:
            raw = response.model_dump()
        except Exception:
            raw = None
        return ProviderTurn(content=getattr(response, "output_text", "") or "", tool_calls=tool_calls, raw=raw)

    def _generate_chat_completions(
        self, client: Any, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> ProviderTurn:
        response = client.chat.completions.create(
            model=self.resolved_model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        message = response.choices[0].message
        tool_calls: list[ToolCall] = []
        for call in message.tool_calls or []:
            raw_args = getattr(call.function, "arguments", "") or "{}"
            args = _parse_tool_args(raw_args)
            tool_calls.append(ToolCall(id=call.id, name=call.function.name, args=args))
        raw: dict[str, Any] | None = None
        try:
            raw = response.model_dump()
        except Exception:
            raw = None
        return ProviderTurn(content=message.content or "", tool_calls=tool_calls, raw=raw)


def _parse_tool_args(raw_args: Any) -> dict[str, Any]:
    if isinstance(raw_args, dict):
        return raw_args
    if isinstance(raw_args, str):
        import json

        try:
            parsed = json.loads(raw_args or "{}")
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {"_raw": raw_args}
    return {}


def _responses_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
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


def _responses_input(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
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


def _is_responses_unsupported(exc: Exception) -> bool:
    status_code = getattr(exc, "status_code", None)
    if status_code in {400, 404, 405}:
        text = str(exc).lower()
        return any(
            marker in text for marker in ("responses", "unknown", "unsupported", "not found", "invalid endpoint")
        )
    return isinstance(exc, (AttributeError, TypeError, ValueError))


def create_provider(*args: Any, **kwargs: Any) -> WorkbenchProvider:
    raw_provider = (
        getattr(args[0], "provider", None) if args and hasattr(args[0], "provider") else kwargs.get("provider")
    )
    if isinstance(raw_provider, str) and raw_provider.strip().lower() == "chatgpt":
        raise ValueError("지원하지 않는 provider: chatgpt")
    if args and isinstance(args[0], ProviderConfig):
        config = args[0]
    elif args and hasattr(args[0], "provider"):
        raw = args[0]
        config = get_config(
            provider=getattr(raw, "provider", None),
            model=getattr(raw, "model", None),
            base_url=getattr(raw, "base_url", None) or getattr(raw, "baseUrl", None),
            api_key=getattr(raw, "api_key", None) or getattr(raw, "apiKey", None),
            temperature=getattr(raw, "temperature", None),
        )
    else:
        config = get_config(**kwargs)
    provider = (config.provider or "").lower()
    if provider == "oauth-codex":
        from .oauth_codex import OAuthCodexProvider

        return OAuthCodexProvider(config)
    if provider == "codex":
        from .codex import CodexProvider

        return CodexProvider(config)
    if provider in {"openai", "custom", "openai-compatible", "openai_compat", "groq", "cerebras", "mistral", "ollama"}:
        return OpenAICompatibleProvider(config)
    return UnavailableProvider(config)


def available_providers() -> list[str]:
    return [
        "openai",
        "claude",
        "ollama",
        "custom",
        "codex",
        "oauth-codex",
        "gemini",
        "groq",
        "cerebras",
        "mistral",
    ]


__all__ = [
    "ProviderConfig",
    "ProviderTurn",
    "ToolCall",
    "WorkbenchProvider",
    "create_provider",
    "get_config",
    "available_providers",
]
