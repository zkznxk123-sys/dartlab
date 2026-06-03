"""providers = Transform+Load 전용 — 외부 네트워크 fetch 0 강제 (수집 일원화 lock).

L1 ETL 재정의: **gather = Extract(네트워크 fetch → raw)**, **providers =
Transform(raw→parquet build) + Load(parquet→DataFrame read)**. DART/EDGAR 의 모든
SEC/OpenDART 네트워크 fetch 는 gather 가 전담하고, providers 는 HTTP 클라이언트를
import 하지 않는다. 본 가드는 그 단방향을 영구 lock 한다 (`gather/edgar/search`·
`gather/dart/*` 등으로 이관한 fetch 가 providers 로 회귀하면 즉시 fail).

스코프: ``providers/dart`` + ``providers/edgar`` (수집 일원화 대상). ``providers/edinet``
은 별도 제3 규제기관(EDINET, API 통신 불가 — engines.edinet)이라 본 가드 밖이다.

금지: ``httpx``·``requests``·``aiohttp``·``urllib3``·``urllib.request``·``http.client``
등 HTTP fetch 클라이언트 import (module-level + 함수 본문 lazy 모두). 허용: ``urllib.parse``
(URL 문자열 조립, 네트워크 0), endpoint URL 문자열 리터럴(표시·메타용 — fetch 아님).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_SRC = Path(__file__).resolve().parents[2] / "src" / "dartlab" / "providers"
_SCOPE = ("dart", "edgar")

# HTTP fetch 클라이언트 (top-level 패키지명 또는 정확한 dotted module).
_BANNED_TOP = frozenset({"httpx", "requests", "aiohttp", "urllib3", "pycurl", "websocket", "websockets"})
_BANNED_DOTTED = frozenset({"urllib.request", "http.client"})


def _isBanned(moduleName: str) -> bool:
    if not moduleName:
        return False
    if moduleName in _BANNED_DOTTED:
        return True
    return moduleName.split(".")[0] in _BANNED_TOP


def _scopedFiles() -> list[Path]:
    files: list[Path] = []
    for sub in _SCOPE:
        root = _SRC / sub
        if not root.exists():
            continue
        files.extend(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)
    return files


def test_providers_no_http_client_import() -> None:
    """providers/{dart,edgar} 의 어떤 파일도 HTTP fetch 클라이언트를 import 하지 않는다."""
    assert _SRC.exists(), f"providers source root not found: {_SRC}"
    violations: list[str] = []
    for pyFile in _scopedFiles():
        try:
            tree = ast.parse(pyFile.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        rel = pyFile.relative_to(_SRC.parent.parent.parent).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if _isBanned(alias.name):
                        violations.append(f"{rel}:{node.lineno}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if _isBanned(node.module or ""):
                    violations.append(f"{rel}:{node.lineno}: from {node.module}")
    assert not violations, (
        "providers = build+read 위반 — 네트워크 fetch 클라이언트 import 발견 "
        "(fetch 는 gather 전담; 수집 일원화 단방향 회귀):\n" + "\n".join(violations)
    )
