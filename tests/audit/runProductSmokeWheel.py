"""Build wheel and run product smoke from an installed venv.

This helper keeps the ``product-smoke-wheel`` gate shell-agnostic.  The old
gate used POSIX variable assignment and ``/tmp/.../bin/python``, which breaks
on Windows local runs.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "dist"
VENV = ROOT / ".tmp" / "dartlab-product-smoke"


def _pythonPath(venv: Path) -> Path:
    if sys.platform == "win32":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def _safeRemoveTree(path: Path) -> None:
    resolved = path.resolve()
    root = ROOT.resolve()
    if not str(resolved).startswith(str(root)):
        raise RuntimeError(f"refusing to remove outside repo: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)


def _latestWheel() -> Path:
    wheels = sorted(DIST.glob("dartlab-*.whl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not wheels:
        raise RuntimeError("no dartlab wheel found under dist/")
    return wheels[0]


def main() -> int:
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")

    subprocess.check_call(
        ["uv", "run", "--with", "build", "python", "-m", "build", "--wheel", "--outdir", "dist"],
        cwd=ROOT,
        env=env,
    )

    _safeRemoveTree(VENV)
    subprocess.check_call(["uv", "venv", str(VENV), "--python", "3.12"], cwd=ROOT, env=env)

    python = _pythonPath(VENV)
    wheel = _latestWheel()
    subprocess.check_call(["uv", "pip", "install", "--python", str(python), str(wheel)], cwd=ROOT, env=env)
    subprocess.check_call(
        [
            str(python),
            "-X",
            "utf8",
            "tests/audit/productSmoke.py",
            "--suite",
            "release",
            "--data-mode",
            "fixtures",
            "--import-mode",
            "installed",
            "--json-out",
            "product-smoke-wheel-release.json",
        ],
        cwd=ROOT,
        env=env,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
