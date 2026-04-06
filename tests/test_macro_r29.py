"""R29 audit 회귀 테스트 — macro 엔진 (첫 audit).

R29-1: macro('사이클', market='XX') 잘못된 market 이 silent fallback → ValueError.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_macro_no_args_returns_guide():
    """무인자 → DataFrame 가이드."""
    import polars as pl

    import dartlab

    r = dartlab.macro()
    assert isinstance(r, pl.DataFrame)
    assert "axis" in r.columns
    assert len(r) >= 10


def test_macro_unknown_axis_raises():
    """없는 축은 명시적 에러."""
    import dartlab

    with pytest.raises((KeyError, ValueError), match="없는축|찾을 수 없"):
        dartlab.macro("없는축")


def test_macro_invalid_market_raises():
    """R29-1: 잘못된 market 은 silent 가 아닌 ValueError."""
    import dartlab

    with pytest.raises(ValueError, match="market.*US.*KR"):
        dartlab.macro("사이클", market="XX")


def test_macro_invalid_market_lowercase_raises():
    """R29-1: 'us' 같은 소문자도 차단 (대소문자 구분)."""
    import dartlab

    with pytest.raises(ValueError):
        dartlab.macro("사이클", market="us")


def test_macro_valid_kr_market():
    """KR market 정상 동작 (회귀 보호)."""
    import dartlab

    r = dartlab.macro("사이클", market="KR")
    assert isinstance(r, dict)
    assert r.get("market") == "KR"
