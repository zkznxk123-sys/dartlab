"""Ollama setup probes used by server setup/status surfaces."""

from __future__ import annotations

import shutil
import subprocess
from typing import Any


def detect_ollama() -> dict[str, Any]:
    executable = shutil.which("ollama")
    version = None
    models: list[str] = []
    running = False
    if executable:
        try:
            result = subprocess.run([executable, "--version"], capture_output=True, text=True, timeout=5, check=False)
            version = (result.stdout or result.stderr).strip() or None
        except (OSError, subprocess.SubprocessError):
            version = None
        try:
            result = subprocess.run([executable, "list"], capture_output=True, text=True, timeout=5, check=False)
            running = result.returncode == 0
            if running:
                lines = (result.stdout or "").splitlines()[1:]
                models = [line.split()[0] for line in lines if line.strip()]
        except (OSError, subprocess.SubprocessError):
            running = False
    return {
        "installed": executable is not None,
        "path": executable,
        "version": version,
        "running": running,
        "models": models,
    }


def get_install_guide() -> str:
    return "Ollama가 필요하면 https://ollama.com 에서 설치한 뒤 다시 시도하세요."
