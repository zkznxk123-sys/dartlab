"""scripts/audit/namingConsistency.py — 매개변수 표준 사전 검사 단위 테스트."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO = Path(__file__).resolve().parent.parent.parent
_SCRIPT = _REPO / "scripts" / "audit" / "namingConsistency.py"


def _loadModule():
    """scripts/audit/namingConsistency.py 를 모듈로 동적 로드.

    `sys.modules` 등록 필수 — @dataclass 가 cls.__module__ lookup 시 의존.
    """
    spec = importlib.util.spec_from_file_location("namingConsistencyMod", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_buildAliasIndexInverts():
    """`{stockIdentifier: {standard: stockCode, aliases: [code, ticker]}}` →
    `{code: (stockCode, stockIdentifier), ticker: (...)}`.
    """
    nc = _loadModule()
    aliases = {
        "stockIdentifier": {"standard": "stockCode", "aliases": ["code", "ticker"]},
        "limitInt": {"standard": "limit", "aliases": ["topK", "n"]},
    }
    idx = nc._buildAliasIndex(aliases)
    assert idx["code"] == ("stockCode", "stockIdentifier")
    assert idx["ticker"] == ("stockCode", "stockIdentifier")
    assert idx["topK"] == ("limit", "limitInt")


def test_scanFileDetectsAliasArg(tmp_path: Path):
    """함수 매개변수가 alias 사용 시 위반 검출."""
    nc = _loadModule()
    target = tmp_path / "sample.py"
    target.write_text(
        "def fetchPrice(code: str, topK: int = 10) -> None:\n    pass\n",
        encoding="utf-8",
    )
    aliasIndex = {
        "code": ("stockCode", "stockIdentifier"),
        "topK": ("limit", "limitInt"),
    }
    violations = nc._scanFile(target, aliasIndex)
    names = sorted([v.argName for v in violations])
    assert names == ["code", "topK"]


def test_scanFilePassesStandardName(tmp_path: Path):
    """표준 이름은 통과 — 위반 0."""
    nc = _loadModule()
    target = tmp_path / "sample.py"
    target.write_text(
        "def fetchPrice(stockCode: str, limit: int = 10) -> None:\n    pass\n",
        encoding="utf-8",
    )
    aliasIndex = {
        "code": ("stockCode", "stockIdentifier"),
        "topK": ("limit", "limitInt"),
    }
    assert nc._scanFile(target, aliasIndex) == []


def test_loadAliasesReturnsPopulatedDict():
    """aliases.json (P5 1.0.0) 은 10 표준 의미 채워진 사전.

    P4.1 (2026-05-11) 에서 'code' / 'corpCode' alias 는 의미 충돌로 분리됨
    ('code' = Python source code / OAuth code · 'corpCode' = DART API 8자리).
    'codeOrName' 은 유지 — 명시적 종목코드/회사명 통합 의도.
    """
    nc = _loadModule()
    aliases = nc._loadAliases()
    assert "stockIdentifier" in aliases
    assert aliases["stockIdentifier"]["standard"] == "stockCode"
    assert "codeOrName" in aliases["stockIdentifier"]["aliases"]
