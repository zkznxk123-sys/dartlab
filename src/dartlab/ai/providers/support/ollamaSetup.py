"""Ollama setup probes used by server setup/status surfaces."""

from __future__ import annotations

import shutil
import subprocess
from typing import Any


def _detectGpu() -> dict[str, Any]:
    """GPU 가용성 + VRAM 감지 (간단 휴리스틱).

    nvidia-smi 사용 (NVIDIA). 미설치/실패 시 CPU 전용 가정.
    """
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        return {"available": False, "vram_mb": 0}
    try:
        result = subprocess.run(
            [nvidia_smi, "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        if result.returncode != 0:
            return {"available": False, "vram_mb": 0}
        line = (result.stdout or "").strip().splitlines()
        if not line:
            return {"available": False, "vram_mb": 0}
        # 첫 GPU 의 VRAM
        vram_mb = int(line[0].strip())
        return {"available": True, "vram_mb": vram_mb}
    except (OSError, subprocess.SubprocessError, ValueError):
        return {"available": False, "vram_mb": 0}


def detectOllama() -> dict[str, Any]:
    """ollama CLI 설치/버전/실행 상태 + 설치된 모델 목록 점검."""
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


def getInstallGuide() -> str:
    """Ollama 설치 안내 한 줄 — 외부 사용자 에러 메시지에 포함됨."""
    return "Ollama가 필요하면 https://ollama.com 에서 설치한 뒤 다시 시도하세요."
