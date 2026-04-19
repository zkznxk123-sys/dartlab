"""analysis 엔진 전수 축 스모크 — _AXIS_REGISTRY 에 등록된 모든 axis 를 iterate.

c.analysis(axis) 가 각 22개 한글 axis 에서 크래시/None 없이 dict 반환하는지.
"""

from __future__ import annotations

import pytest


def _analysisAxes() -> list[str]:
    """analysis.financial._AXIS_REGISTRY 에서 자동 수집."""
    from dartlab.analysis.financial import _AXIS_REGISTRY

    return sorted(_AXIS_REGISTRY.keys())


ANALYSIS_AXES = _analysisAxes()


# 데이터 부재 시 None 허용 axis (과거 기간 부족 등)
_NONE_ALLOWED: frozenset[str] = frozenset(
    {
        "예측신호",        # 예측 모델 입력 부족 가능
        "매크로민감도",   # 매크로 데이터 없음 시 skip
    }
)


@pytest.mark.realData
@pytest.mark.integration
@pytest.mark.parametrize("axis", ANALYSIS_AXES)
def test_analysisAxis_runs(samsungRealData, axis):
    """c.analysis(axis) 가 각 축에서 dict/DataFrame 반환."""
    try:
        result = samsungRealData.analysis(axis)
    except NotImplementedError:
        pytest.skip(f"analysis({axis}) 미구현")
    except Exception as e:
        pytest.fail(f"analysis({axis!r}) 크래시: {type(e).__name__}: {e}")

    if result is None:
        if axis in _NONE_ALLOWED:
            return
        pytest.fail(f"analysis({axis!r}) None — 화이트리스트 외")

    # dict 또는 DataFrame 중 하나
    assert hasattr(result, "__len__") or hasattr(result, "height"), (
        f"analysis({axis!r}) 반환 타입 예상 외: {type(result).__name__}"
    )
