"""CLI environment probes for Ask Workbench provider setup."""

from __future__ import annotations

import shutil
import subprocess
from typing import Any

from .oauth_token import get_account_id, is_authenticated


def detect_codex() -> dict[str, Any]:
    """Return local CLI availability without importing legacy AI code."""
    executable = shutil.which("codex")
    version: str | None = None
    if executable:
        try:
            result = subprocess.run(
                [executable, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            version = (result.stdout or result.stderr).strip() or None
        except (OSError, subprocess.SubprocessError):
            version = None
    authenticated = is_authenticated()
    return {
        "installed": executable is not None,
        "path": executable,
        "version": version,
        "authenticated": authenticated,
        "authMode": "oauth" if authenticated else None,
        "loginStatus": "authenticated" if authenticated else "not_authenticated",
        "accountId": get_account_id() if authenticated else None,
    }
