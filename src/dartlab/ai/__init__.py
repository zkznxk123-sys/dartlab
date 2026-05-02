"""DartLab Ask Workbench Kernel package."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .kernel import ask, create_task, runAsk
from .providers import create_provider, get_config

__all__ = [
    "ask",
    "runAsk",
    "create_task",
    "get_config",
    "configure",
    "status",
    "templates",
    "saveTemplate",
]


def configure(
    *,
    provider: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Update the shared AI profile without touching legacy runtime code."""

    try:
        from dartlab.core.ai.profile import get_profile_manager

        profile = get_profile_manager()
        if api_key and provider:
            profile.save_api_key(provider, api_key, updated_by="api")
        updated = profile.update(provider=provider, model=model, base_url=base_url, updated_by="api")
        return {"ok": True, "defaultProvider": updated.default_provider}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def status(provider: str | None = None, **kwargs: Any) -> dict[str, Any]:
    """Return provider availability for CLI/UI compatibility."""

    config = get_config(provider=provider, **kwargs)
    prov = create_provider(config)
    available = bool(getattr(prov, "check_available", lambda: False)())
    result: dict[str, Any] = {
        "provider": config.provider,
        "model": getattr(prov, "resolved_model", None) or config.model,
        "available": available,
    }
    if config.provider == "oauth-codex":
        try:
            from .providers.support.oauth_token import get_account_id, is_authenticated, load_token

            token = load_token()
            result["oauth-codex"] = {
                "tokenStored": bool(token and token.get("access_token")),
                "authenticated": is_authenticated(),
                "accountId": get_account_id(),
                "baseUrlConfigured": bool(config.base_url),
            }
        except Exception:
            result["oauth-codex"] = {
                "tokenStored": False,
                "authenticated": False,
                "accountId": None,
                "baseUrlConfigured": bool(config.base_url),
            }
    elif config.provider == "codex":
        from .providers.support.cli_setup import detect_codex

        result["codex"] = detect_codex()
    elif config.provider == "ollama":
        from .providers.support.ollama_setup import detect_ollama

        result["ollama"] = detect_ollama()
    return result


def templates(name: str | None = None):
    base = Path.home() / ".dartlab" / "templates"
    if name is None:
        if not base.exists():
            return []
        return sorted(path.stem for path in base.glob("*.md"))
    path = base / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"template not found: {name}")
    return path.read_text(encoding="utf-8")


def saveTemplate(name: str, *, content: str | None = None, file: str | None = None):
    if not content and not file:
        raise ValueError("content or file is required")
    base = Path.home() / ".dartlab" / "templates"
    base.mkdir(parents=True, exist_ok=True)
    text = Path(file).read_text(encoding="utf-8") if file else str(content)
    path = base / f"{name}.md"
    path.write_text(text, encoding="utf-8")
    return str(path)
