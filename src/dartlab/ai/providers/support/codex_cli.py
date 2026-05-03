"""Local CLI compatibility helpers for provider setup surfaces."""

from __future__ import annotations

import shutil
import subprocess
from importlib import util
from pathlib import Path
from typing import Any

from dartlab.core.ai.model_resolver import fallback_models

_BACKUP_SOURCE = Path(__file__).resolve().parents[3] / "ai_backup" / "providers" / "support" / "codex_cli.py"
_BACKUP_SPEC = util.spec_from_file_location("_dartlab_ai_backup_providers_support_codex_cli", _BACKUP_SOURCE)
if _BACKUP_SPEC is None or _BACKUP_SPEC.loader is None:
    _BACKUP_MODULE = None
else:
    _BACKUP_MODULE = util.module_from_spec(_BACKUP_SPEC)
    _BACKUP_SPEC.loader.exec_module(_BACKUP_MODULE)


def get_codex_model_catalog() -> list[str]:
    return fallback_models("oauth-codex")


def get_codex_configured_model() -> str | None:
    if _BACKUP_MODULE is None:
        return None
    return _BACKUP_MODULE.get_codex_configured_model()


def inspect_codex_cli() -> dict[str, Any]:
    if _BACKUP_MODULE is None:
        return {
            "installed": False,
            "authenticated": False,
            "configuredModel": None,
            "version": None,
            "sandboxModes": [],
        }
    return _BACKUP_MODULE.inspect_codex_cli()


def run_codex_exec(
    prompt: str,
    *,
    model: str | None = None,
    sandbox: str = "read-only",
    cwd: str | None = None,
    timeout: int = 300,
) -> tuple[str, dict[str, int] | None]:
    if _BACKUP_MODULE is None:
        raise FileNotFoundError("codex CLI helper source is unavailable")
    return _BACKUP_MODULE.run_codex_exec(prompt, model=model, sandbox=sandbox, cwd=cwd, timeout=timeout)


def infer_codex_sandbox(messages: list[dict[str, str]], override: str | None = None) -> str:
    if override:
        return override
    text = "\n".join(str(message.get("content", "")) for message in messages).lower()
    code_markers = (
        "src/",
        ".py",
        ".ts",
        ".js",
        ".svelte",
        "버그",
        "수정",
        "구현",
        "패치",
        "fix",
        "implement",
        "refactor",
    )
    if any(marker in text for marker in code_markers):
        return "workspace-write"
    if _BACKUP_MODULE is None:
        return "read-only"
    return _BACKUP_MODULE.infer_codex_sandbox(messages, override=override)


def build_codex_exec_command(*, model: str | None = None, sandbox: str = "read-only") -> list[str]:
    if _BACKUP_MODULE is None:
        executable = shutil.which("codex")
        if not executable:
            raise FileNotFoundError("codex CLI is not installed")
        cmd = [executable, "exec", "--json", "--sandbox", sandbox]
        if model:
            cmd.extend(["--model", model])
        return cmd
    return _BACKUP_MODULE.build_codex_exec_command(model=model, sandbox=sandbox)


def __getattr__(name: str) -> Any:
    if _BACKUP_MODULE is not None and hasattr(_BACKUP_MODULE, name):
        return getattr(_BACKUP_MODULE, name)
    raise AttributeError(name)


def logout_codex_cli() -> None:
    executable = shutil.which("codex")
    if not executable:
        raise FileNotFoundError("codex CLI is not installed")
    subprocess.run([executable, "logout"], check=False, timeout=15)
