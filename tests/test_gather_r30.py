"""R30 audit 회귀 테스트 — gather 엔진."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_gather_no_args_returns_guide():
    """무인자 → DataFrame 가이드."""
    import polars as pl

    import dartlab

    r = dartlab.gather()
    assert isinstance(r, pl.DataFrame)
    assert "axis" in r.columns
    assert len(r) >= 5


def test_gather_unknown_axis_raises():
    """없는 축은 ValueError."""
    import dartlab

    with pytest.raises(ValueError, match="알 수 없는 gather 축"):
        dartlab.gather("없는axis")


def test_gather_empty_axis_raises():
    """빈 문자열 ValueError."""
    import dartlab

    with pytest.raises(ValueError, match="알 수 없는 gather 축"):
        dartlab.gather("")


def test_gather_price_empty_result_has_validation():
    """R30-1: gather entry.py 에 빈 DataFrame 검증 코드 있음."""
    import inspect

    from dartlab.gather.entry import GatherEntry

    src = inspect.getsource(GatherEntry._run)
    assert "ValueError" in src
    assert "비어" in src or "empty" in src.lower()
