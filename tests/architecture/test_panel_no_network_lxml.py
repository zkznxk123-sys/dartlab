"""panel BUILD/READ 물리 분리 강제 (R2) — lxml/zipfile/network import 위치 가드.

plan snazzy-wibbling-origami R2. panel 은 build(무거움)·read(가벼움)를 물리적으로
가른다:

- ``core/panel`` (L0 계약): lxml·zipfile·network 0. 순수 schema/period/bridge 계약만.
- ``gather/dart/panel`` (L1 write): lxml·zipfile 허용(zip→14col 빌드 owner). 단 **network 0**
  — 빌드는 로컬 zip 만 소비(수집은 CI entry layer-밖). requests/httpx/socket 등 금지.
- ``providers/dart/panel`` (L1 read): lxml·zipfile·network 0. scan_parquet 로컬 read 만.

위반 = 메모리 회귀(read 에 lxml 들어오면 콜드 1s·G4 깨짐) 또는 layer 오염(read 가
network 획득). dartlabGuard 의 census 가 못 잡는 panel 특이 물리분리를 AST 로 강제.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2] / "src" / "dartlab"

# build 전용 (무거운 XML 파싱·zip 해제) — read·계약 층 진입 금지.
_BUILD_ONLY = ("lxml", "zipfile")

# network 획득 — panel 어디에도 금지(build 는 로컬 zip, read 는 로컬 parquet).
_NETWORK = ("requests", "httpx", "aiohttp", "socket", "urllib", "http.client")

# (서브트리 상대경로, 금지 모듈 튜플, 사유)
_RULES: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("core/panel", _BUILD_ONLY + _NETWORK, "L0 계약 — lxml/zipfile/network 0 (순수)"),
    ("gather/dart/panel", _NETWORK, "L1 write — network 0 (로컬 zip 소비, 수집은 CI entry)"),
    ("providers/dart/panel", _BUILD_ONLY + _NETWORK, "L1 read — lxml/zipfile/network 0 (scan_parquet 로컬)"),
)


def _importedModules(pyFile: Path) -> list[tuple[int, str]]:
    """파일의 모든 import 대상 모듈을 (lineno, module) 로 — module+function body 전수."""
    try:
        tree = ast.parse(pyFile.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return []
    out: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.extend((node.lineno, a.name) for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                out.append((node.lineno, node.module))
    return out


def _isForbidden(module: str, forbidden: tuple[str, ...]) -> bool:
    return any(module == f or module.startswith(f + ".") for f in forbidden)


def test_panel_build_read_physical_separation() -> None:
    """panel 서브트리별 금지 모듈 import 0 강제 (R2)."""
    violations: list[str] = []
    for subtree, forbidden, reason in _RULES:
        base = ROOT / subtree
        if not base.exists():
            continue
        for pyFile in base.rglob("*.py"):
            if "__pycache__" in pyFile.parts:
                continue
            for lineno, module in _importedModules(pyFile):
                if _isForbidden(module, forbidden):
                    rel = pyFile.relative_to(ROOT.parent.parent).as_posix()
                    violations.append(f"{rel}:{lineno}: import '{module}' 금지 — {subtree} = {reason}")
    assert not violations, "panel BUILD/READ 물리 분리(R2) 위반:\n" + "\n".join(violations)
