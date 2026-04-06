"""R27 audit 회귀 테스트 — scan 엔진.

R27 audit 결과 scan 엔진은 silent failure 0 건 — 이미 명시적 에러 처리.
회귀 방지용 source check.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_scan_unknown_axis_raises_value_error():
    """없는 축은 ValueError. silent None 이면 회귀."""
    import dartlab
    with pytest.raises(ValueError, match="알 수 없는 scan 축"):
        dartlab.scan('없는축')


def test_scan_empty_string_raises_value_error():
    """빈 문자열도 ValueError."""
    import dartlab
    with pytest.raises(ValueError, match="알 수 없는 scan 축"):
        dartlab.scan('')


def test_scan_none_returns_guide():
    """None 입력 = 무인자 = 가이드 DataFrame."""
    import dartlab
    import polars as pl
    r = dartlab.scan(None)
    assert isinstance(r, pl.DataFrame)
    assert "axis" in r.columns
    assert "label" in r.columns
    assert "description" in r.columns
    assert "example" in r.columns
    assert len(r) >= 15


def test_scan_no_args_returns_guide():
    """무인자 호출 = 가이드 DataFrame."""
    import dartlab
    import polars as pl
    r = dartlab.scan()
    assert isinstance(r, pl.DataFrame)
    assert len(r) >= 15
