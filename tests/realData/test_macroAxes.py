"""macro 엔진 전수 축 스모크 — _AXIS_REGISTRY 의 12개 axis 모두 iterate.

ECOS_API_KEY 또는 FRED_API_KEY 필요. 키 없으면 전체 skip.
"""

from __future__ import annotations

import os

import pytest


def _macroAxes() -> list[str]:
    from dartlab.macro import _AXIS_REGISTRY

    return sorted(_AXIS_REGISTRY.keys())


MACRO_AXES = _macroAxes()


def _hasRealMacroKey() -> bool:
    for name in ("ECOS_API_KEY", "FRED_API_KEY"):
        val = os.environ.get(name, "")
        if val and val != "test_dummy":
            return True
    return False


@pytest.mark.realData
@pytest.mark.integration
@pytest.mark.parametrize("axis", MACRO_AXES)
def test_macroAxis_runs(axis):
    """dartlab.macro(axis) 가 각 축에서 크래시 없이 실행."""
    import dartlab

    if not _hasRealMacroKey():
        pytest.skip("ECOS/FRED 실제 키 없음")
    try:
        result = dartlab.macro(axis)
    except Exception as e:
        pytest.fail(f"macro({axis!r}) 크래시: {type(e).__name__}: {e}")
    assert result is not None, f"macro({axis!r}) None"
