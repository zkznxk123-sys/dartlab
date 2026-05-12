"""dartlab.gather.entry.dispatch real unit test (A 트랙 T1).

AXIS_REGISTRY 일관성 + AXIS_ALIASES + _resolveAxis + INDEX_SYMBOLS self-map +
_fetchNaverIndex HTTP 실패 빈 DataFrame 검증.
"""

from __future__ import annotations

import importlib

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def test_smoke_import() -> None:
    """``dartlab.gather.entry.dispatch`` 모듈 import 가능 — 모듈 구조 회귀 차단."""
    importlib.import_module("dartlab.gather.entry.dispatch")


def test_resolveAxis_registry() -> None:
    """registry key 직접 지정 시 그대로 반환 — case-sensitive."""
    from dartlab.gather.entry.dispatch import AXIS_REGISTRY, _resolveAxis

    for key in AXIS_REGISTRY:
        assert _resolveAxis(key) == key


def test_resolveAxis_alias() -> None:
    """AXIS_ALIASES 매핑 — 한글/별칭 → registry key 정상 변환."""
    from dartlab.gather.entry.dispatch import AXIS_ALIASES, _resolveAxis

    for alias, target in AXIS_ALIASES.items():
        assert _resolveAxis(alias) == target


def test_resolveAxis_unknown_raises() -> None:
    """미등록 축 / case 불일치 → ValueError."""
    from dartlab.gather.entry.dispatch import _resolveAxis

    with pytest.raises(ValueError, match="알 수 없는 gather 축"):
        _resolveAxis("nonexistent_axis")
    # case-sensitive 검증 — "Price" 는 registry key 가 아님
    with pytest.raises(ValueError):
        _resolveAxis("Price")


def test_INDEX_SYMBOLS_self_map() -> None:
    """INDEX_SYMBOLS — 정식 외부 API 심볼은 self-map (KOSPI/KOSDAQ/KPI200)."""
    from dartlab.gather.entry.dispatch import INDEX_SYMBOLS

    assert INDEX_SYMBOLS["KOSPI"] == "KOSPI"
    assert INDEX_SYMBOLS["KOSDAQ"] == "KOSDAQ"
    assert INDEX_SYMBOLS["KPI200"] == "KPI200"
    # 한글 alias
    assert INDEX_SYMBOLS["코스피"] == "KOSPI"
    assert INDEX_SYMBOLS["코스닥"] == "KOSDAQ"


def test_fetchNaverIndex_empty_on_http_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    """_fetchNaverIndex — httpx response 가 빈 텍스트면 빈 DataFrame."""
    from dartlab.gather.entry import dispatch as dispatchMod

    class FakeResp:
        text = ""

    monkeypatch.setattr("httpx.get", lambda *a, **kw: FakeResp())

    df = dispatchMod._fetchNaverIndex("KOSPI", limit=10)
    assert isinstance(df, pl.DataFrame)
    assert df.is_empty()
