"""credit 엔진 전수 축 스모크 — 7개 신용 axis 모두 iterate."""

from __future__ import annotations

import pytest

from tests.conftest import SAMSUNG


def _creditAxes() -> list[str]:
    """dartlab.credit.axes() dict keys."""
    from dartlab.credit import axes

    return sorted(axes().keys())


CREDIT_AXES = _creditAxes()


@pytest.mark.realData
@pytest.mark.integration
@pytest.mark.parametrize("axis", CREDIT_AXES)
def test_creditAxis_runs(samsungRealData, axis):
    """dartlab.credit(code, axis) 가 각 축에서 None 없이 dict 반환."""
    import dartlab

    try:
        result = dartlab.credit(SAMSUNG, axis)
    except Exception as e:
        pytest.fail(f"credit({SAMSUNG!r}, {axis!r}) 크래시: {type(e).__name__}: {e}")
    assert result is not None, f"credit({axis!r}) None"
    assert isinstance(result, dict), f"credit({axis!r}) 반환 타입 예상 외: {type(result).__name__}"
    assert result, f"credit({axis!r}) 빈 dict"
