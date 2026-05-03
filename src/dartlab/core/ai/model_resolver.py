"""Central model resolution for DartLab AI surfaces.

This is the only production source for OpenAI-family default model selection.
Stored profile models are preferences, not the default for frontier providers:
unless a caller explicitly passes a model for one request, DartLab uses the
current official latest frontier model.
"""

from __future__ import annotations

import os
import re

LATEST_OPENAI_MODEL = "gpt-5.4"

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


def latest_openai_model() -> str:
    """Return the default frontier model used by DartLab.

    The environment override is intentionally specific. Generic profile/model
    settings do not downgrade OpenAI-family defaults.
    """

    override = os.environ.get("DARTLAB_LATEST_OPENAI_MODEL")
    return override.strip() if override and override.strip() else LATEST_OPENAI_MODEL


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
    """Sort available OpenAI chat models with DartLab's latest default first."""

    latest = latest_openai_model()
    unique = sorted(set(model_ids))

    def key(name: str) -> tuple[int, tuple[int, ...], str]:
        if name == latest:
            return (0, (), name)
        parts = tuple(int(part) for part in re.findall(r"\d+", name))
        # Negative numbers sort larger versions first while staying deterministic.
        return (1, tuple(-part for part in parts), name)

    sorted_models = sorted(unique, key=key)
    if latest not in sorted_models:
        sorted_models.insert(0, latest)
    return sorted_models
