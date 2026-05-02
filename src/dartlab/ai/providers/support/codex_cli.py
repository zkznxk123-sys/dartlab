"""Local CLI compatibility helpers for provider setup surfaces."""

from __future__ import annotations

import shutil
import subprocess

from dartlab.core.ai.model_resolver import fallback_models


def get_codex_model_catalog() -> list[str]:
    return fallback_models("oauth-codex")


def logout_codex_cli() -> None:
    executable = shutil.which("codex")
    if not executable:
        raise FileNotFoundError("codex CLI is not installed")
    subprocess.run([executable, "logout"], check=False, timeout=15)
