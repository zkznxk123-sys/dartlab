"""Central model resolution for DartLab AI surfaces.

This is the only production source for OpenAI-family default model selection.
Stored profile models are preferences, not the default for frontier providers:
unless a caller explicitly passes a model for one request, DartLab uses the
current official latest frontier model. Resolution priority:

  1. ``DARTLAB_LATEST_OPENAI_MODEL`` environment override
  2. backend ``/codex/models`` endpoint via ``oauth_codex.availableModels``
     (cached upstream, version-desc sorted)
  3. ``_FALLBACK_LATEST_MODEL`` static value

Static fallback is updated periodically; backend response always wins when
available, so a stale constant cannot pin DartLab to an old model.
"""

from __future__ import annotations

import os
import re

# Updated periodically. Backend fetch overrides this when reachable.
_FALLBACK_LATEST_MODEL = "gpt-5.5"

# Backwards-compat alias for callers that imported the constant directly.
LATEST_OPENAI_MODEL = _FALLBACK_LATEST_MODEL

_OPENAI_FAMILY_PROVIDERS = {
    "openai",
    "oauth-codex",
    "chatgpt",
    "gpt",
    "oauth",
    "codex",
}

_OPENAI_MODEL_PREFIXES = ("gpt-", "o")
_EXCLUDED_MODEL_PARTS = (
    "audio",
    "babbage",
    "davinci",
    "dall-e",
    "embedding",
    "instruct",
    "realtime",
    "search",
    "tts",
    "transcribe",
    "whisper",
)


def normalize_provider_id(provider: str | None) -> str | None:
    if not provider:
        return None
    lowered = provider.strip().lower()
    if lowered in {"chatgpt", "gpt", "oauth"}:
        return "oauth-codex"
    return lowered


def is_openai_family_provider(provider: str | None) -> bool:
    normalized = normalize_provider_id(provider)
    return normalized in _OPENAI_FAMILY_PROVIDERS or normalized is None


def _versionKey(name: str) -> tuple[int, ...]:
    """Numeric version tuple for descending sort. Newer versions sort first."""
    parts = tuple(int(part) for part in re.findall(r"\d+", name))
    return tuple(-part for part in parts)


def _resolveBackendLatest() -> str | None:
    """Query the cached backend model catalog and return the highest version.

    Returns None when the backend is unreachable, no token is stored, or
    importing the OAuth helper raises (during isolated tests, for example).
    """
    try:
        from dartlab.ai.providers.oauth_codex import availableModels
    except Exception:  # noqa: BLE001
        return None
    try:
        models = availableModels()
    except Exception:  # noqa: BLE001
        return None
    if not models:
        return None
    chat_models = [m for m in models if is_openai_chat_model(m)]
    if not chat_models:
        return None
    chat_models.sort(key=_versionKey)
    return chat_models[0]


def latest_openai_model() -> str:
    """Return the default frontier model used by DartLab.

    Resolution: env override → backend latest → static fallback.
    """

    override = os.environ.get("DARTLAB_LATEST_OPENAI_MODEL")
    if override and override.strip():
        return override.strip()
    backend_latest = _resolveBackendLatest()
    if backend_latest:
        return backend_latest
    return _FALLBACK_LATEST_MODEL


def resolve_default_model(
    provider: str | None,
    *,
    explicit_model: str | None = None,
    configured_model: str | None = None,
    fallback_model: str | None = None,
) -> str | None:
    """Resolve the effective model for a provider.

    Explicit per-call input wins. For OpenAI-family providers, stale profile
    defaults are ignored so web/status cannot keep showing an old model.
    """

    if explicit_model:
        return explicit_model
    if is_openai_family_provider(provider):
        return latest_openai_model()
    return configured_model or fallback_model


def fallback_models(provider: str | None) -> list[str]:
    if is_openai_family_provider(provider):
        return [latest_openai_model()]
    return []


def is_openai_chat_model(model_id: str) -> bool:
    lowered = model_id.lower()
    return lowered.startswith(_OPENAI_MODEL_PREFIXES) and not any(part in lowered for part in _EXCLUDED_MODEL_PARTS)


def sort_openai_models(model_ids: list[str]) -> list[str]:
    """Sort available OpenAI chat models by version (newest first).

    The static fallback is appended only when the input list is missing it,
    so a stale fallback constant never pushes a newer backend model to the
    back of the list.
    """

    unique = sorted(set(model_ids))
    sorted_models = sorted(unique, key=_versionKey)
    fallback = _FALLBACK_LATEST_MODEL
    if fallback and fallback not in sorted_models:
        sorted_models.append(fallback)
    return sorted_models
