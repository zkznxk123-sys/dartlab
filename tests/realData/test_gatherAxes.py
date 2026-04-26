"""gather 엔진 전수 축 스모크 — 8개 gather axis 모두 iterate.

네트워크 호출 포함. 오프라인/레이트리밋 시 해당 axis 만 skip.
"""

from __future__ import annotations

import os

import pytest

from tests.conftest import SAMSUNG


def _gatherAxes() -> list[str]:
    import dartlab

    df = dartlab.gather()
    return sorted(df["axis"].to_list())


GATHER_AXES = _gatherAxes()


# 외부 API 키 필요한 axis — 키 없으면 skip
_AXIS_KEY_REQS: dict[str, tuple[str, ...]] = {
    "macro": ("ECOS_API_KEY", "FRED_API_KEY"),
    "insider": ("DART_API_KEY",),
    "krxindex": ("KRX_API_KEY",),  # idx 카테고리 권한 별도 신청 필요
}

# axis 별 적절한 target — 모든 axis 가 stockCode 받지 않음.
# krx/krxindex 는 column 명 (close/open/rsi14/...), macro 는 series id 또는 None,
# news 는 검색어 (선택). 명시 안 한 axis 는 SAMSUNG 종목코드 사용.
_AXIS_TARGET: dict[str, str | None] = {
    "macro": None,
    "krx": "close",
    "krxindex": "close",
}


def _hasRealKey(name: str) -> bool:
    val = os.environ.get(name, "")
    return bool(val) and val != "test_dummy"


@pytest.mark.realData
@pytest.mark.integration
@pytest.mark.parametrize("axis", GATHER_AXES)
def test_gatherAxis_runs(axis):
    """gather(axis, target) 이 각 축에서 크래시 없이 실행. axis-별 적절한 target 사용."""
    import dartlab

    reqs = _AXIS_KEY_REQS.get(axis, ())
    if reqs and not any(_hasRealKey(r) for r in reqs):
        pytest.skip(f"gather({axis!r}) API 키 없음: {reqs}")

    target = _AXIS_TARGET[axis] if axis in _AXIS_TARGET else SAMSUNG
    try:
        result = dartlab.gather(axis, target) if target else dartlab.gather(axis)
    except (TimeoutError, ConnectionError, OSError) as e:
        pytest.skip(f"gather({axis!r}) 네트워크 실패: {type(e).__name__}")
    except Exception as e:
        pytest.fail(f"gather({axis!r}) 크래시: {type(e).__name__}: {e}")
    # 결과 None 허용 (flow 의 US 미지원 등) — 단 크래시는 FAIL
