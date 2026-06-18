"""credit gather 표준 axis-first — 옛 id-first ≡ 신 axis-first (swap + DeprecationWarning).

credit(stockCode, axis) id-first → gather 표준 credit(axis, target) axis-first 전환.
옛 형식은 자동 swap + 경고로 흡수(quant 패턴).
"""

from __future__ import annotations

import warnings

import pytest

from dartlab.credit import credit


def test_guide_no_args():
    """credit() 무인자 → 축 가이드 DataFrame (불변)."""
    g = credit()
    assert "axis" in g.columns


@pytest.mark.requires_data
def test_axis_first_equals_old_swap():
    """신 credit("repayment","005930") ≡ 옛 credit("005930","repayment")(swap+경고)."""
    new = credit("repayment", "005930")  # gather 표준 axis-first
    assert isinstance(new, dict) and new.get("axis")

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        old = credit("005930", "repayment")  # 옛 id-first
        assert any(issubclass(x.category, DeprecationWarning) for x in w), "옛 order 는 DeprecationWarning"
    assert new == old


@pytest.mark.requires_data
def test_axis_first_no_warning():
    """신 axis-first 는 경고 없음 + 종합등급 단축 동치."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        graded = credit("등급", "005930")  # 신: 명시 grade 축
        assert not any(issubclass(x.category, DeprecationWarning) for x in w)
    short = credit("005930")  # 단축 (stockCode-first, 경고 없음)
    assert graded == short and isinstance(graded, dict) and graded.get("grade")
