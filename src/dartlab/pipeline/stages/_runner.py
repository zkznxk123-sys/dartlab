"""스크립트 시퀀스 실행 헬퍼 — 통합 진입점이 검증된 sync 스크립트를 동형 호출.

⚠️ 전환기(transitional) 메커니즘. 통합 SSOT 진입점(`dartlab sync`·`python -m
dartlab.pipeline`)이 *지금* 동작하되 동작은 검증된 ``.github/scripts/sync/*`` 와 byte
동형이도록, stage 가 그 스크립트를 ``-X utf8`` 서브프로세스로 순차 호출한다. 후속
웨이브에서 본체를 stage 모듈로 인라인하며 스크립트는 shim 으로 역전한다.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def repoRoot() -> Path:
    """dartlab repo 루트(``.github/scripts`` 보유) 탐색.

    Returns:
        repo 루트 ``Path``.

    Raises:
        RuntimeError: .github/scripts 를 못 찾으면.

    Example:
        >>> (repoRoot() / ".github" / "scripts").exists()
        True
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".github" / "scripts" / "sync").is_dir():
            return parent
    cwd = Path(os.getcwd())
    if (cwd / ".github" / "scripts" / "sync").is_dir():
        return cwd
    raise RuntimeError(".github/scripts/sync 를 찾을 수 없음 — repo 루트에서 실행 필요")


def runScript(relPath: str, *args: str, env: dict[str, str] | None = None) -> int:
    """sync 스크립트를 UTF-8 서브프로세스로 실행.

    Args:
        relPath: repo 기준 스크립트 상대경로(예 ``.github/scripts/sync/syncRecent.py``).
        *args: 스크립트 인자.
        env: 추가 환경변수(현 환경에 덮어씀).

    Returns:
        프로세스 종료코드.

    Raises:
        RuntimeError: 스크립트 부재.

    Example:
        >>> runScript(".github/scripts/sync/uploadData.py", "--target", "hf")  # doctest: +SKIP
        0
    """
    root = repoRoot()
    script = root / relPath
    if not script.exists():
        raise RuntimeError(f"스크립트 없음: {script}")
    runEnv = dict(os.environ)
    if env:
        runEnv.update(env)
    runEnv.setdefault("DARTLAB_DATA_DIR", str(root / "data"))
    cmd = [sys.executable, "-X", "utf8", str(script), *args]
    print(f"[pipeline] $ {' '.join(cmd[2:])}", flush=True)
    proc = subprocess.run(cmd, env=runEnv, cwd=str(root))
    return proc.returncode
