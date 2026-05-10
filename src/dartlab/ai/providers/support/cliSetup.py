"""CLI environment probes for Ask Workbench provider setup."""

from __future__ import annotations

import shutil
import subprocess
from typing import Any

from .oauthToken import getAccountId, isAuthenticated


def detectCodex() -> dict[str, Any]:
    """Return local CLI availability without importing legacy AI code."""
    from .codexCli import inspectCodexCli

    info = inspectCodexCli()
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
    authenticated = isAuthenticated()
    return {
        "installed": executable is not None,
        "path": executable,
        "version": version or info.get("version"),
        "configuredModel": info.get("configuredModel"),
        "authenticated": authenticated,
        "authMode": "oauth" if authenticated else None,
        "loginStatus": "authenticated" if authenticated else "not_authenticated",
        "accountId": getAccountId() if authenticated else None,
        "supportsWorkspaceWrite": bool(
            info.get("supportsWorkspaceWrite") or "workspace-write" in (info.get("sandboxModes") or [])
        ),
    }


def getCodexInstallGuide() -> str:
    """getCodexInstallGuide — TODO 한국어 동작 설명."""
    return (
        "[ Codex CLI 설치 안내 ]\n\n"
        "1. npm install -g @openai/codex\n"
        "2. 처음 실행 시 로그인: codex\n"
        "3. 확인: codex --version\n"
    )
