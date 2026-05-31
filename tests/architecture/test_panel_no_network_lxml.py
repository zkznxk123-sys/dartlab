"""panel BUILD/READ 물리 분리 강제 (R2) — 패키지 내부 서브트리 lxml/zipfile/network 가드.

PRD jazzy-napping-seal R2. panel 도메인이 ``providers/dart/panel`` 한 패키지로 통합돼도
build(무거움, lxml/zipfile)·read(가벼움, scan_parquet)의 물리 분리는 **패키지 내부 서브트리
경계**로 유지한다 (layer 분리 → import 격리로 전환):

- ``providers/dart/panel/build`` (write 서브트리): lxml·zipfile 허용(zip→14col 빌드 owner).
  단 **network 0** — 빌드는 로컬 zip 또는 openapi 가 넘긴 bytes 만(직접 fetch 금지).
- ``providers/dart/panel`` (build 제외 = read 표면 panel.py·schema·mapper·bridge·_period):
  lxml·zipfile·network 0. scan_parquet 로컬 read 만 → 콜드 <1s.

핵심: read 표면(panel.py)이 build/ 를 import 하지 않으므로 ``import providers.dart.panel.panel``
시 lxml 이 안 딸려온다 (openapi 가 providers 에서 httpx 쓰면서 c.show 안 느린 원리와 동일).
위반 = 메모리 회귀(read 에 lxml → 콜드 1s 깨짐) 또는 build 가 network 직접 획득.
dartlabGuard census 가 못 잡는 panel 물리분리를 AST 전수로 강제.
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

# (서브트리 상대경로, 금지 모듈 튜플, 제외 하위경로, 사유)
_RULES: tuple[tuple[str, tuple[str, ...], str | None, str], ...] = (
    (
        "providers/dart/panel/build",
        _NETWORK,
        None,
        "build 서브트리 — network 0 (로컬 zip / openapi bytes, 직접 fetch 금지)",
    ),
    (
        "providers/dart/panel",
        _BUILD_ONLY + _NETWORK,
        "providers/dart/panel/build",
        "read 표면 — lxml/zipfile/network 0 (scan_parquet 로컬, 콜드 <1s)",
    ),
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
    for subtree, forbidden, excludeSub, reason in _RULES:
        base = ROOT / subtree
        if not base.exists():
            continue
        excludeBase = (ROOT / excludeSub) if excludeSub else None
        for pyFile in base.rglob("*.py"):
            if "__pycache__" in pyFile.parts:
                continue
            if excludeBase is not None and excludeBase in pyFile.parents:
                continue  # read 표면 규칙은 build/ 서브트리 제외 (build 는 자기 규칙)
            for lineno, module in _importedModules(pyFile):
                if _isForbidden(module, forbidden):
                    rel = pyFile.relative_to(ROOT.parent.parent).as_posix()
                    violations.append(f"{rel}:{lineno}: import '{module}' 금지 — {subtree} = {reason}")
    assert not violations, "panel BUILD/READ 물리 분리(R2) 위반:\n" + "\n".join(violations)
