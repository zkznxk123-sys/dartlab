"""gather 엔진 전수 축 스모크 — 모든 visible axis 가 크래시 없이 실행.

axis 별 적절한 target 은 ``_AXIS_REGISTRY`` 의 ``targetType`` 으로 dispatch 된다 —
본 파일에 하드코딩 dict 유지 X (registry 가 SSOT).

네트워크 호출 포함. 오프라인/레이트리밋 시 해당 axis 만 skip.
``hidden=True`` axis (데이터 미준비) 는 ``dartlab.gather()`` 가이드에서 제외되므로
자동으로 parametrize 대상에서 빠진다.
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
}


def _hasRealKey(name: str) -> bool:
    val = os.environ.get(name, "")
    return bool(val) and val != "test_dummy"


def _resolveTarget(axis: str) -> str | None:
    """registry targetType 으로 axis-별 적절 target 결정.

    stockCode → SAMSUNG 종목코드
    columnName → "close" (모든 KRX axis 가 OHLCV 의 close 컬럼 지원)
    indicator → None (전체 거시지표 반환 가능)
    keyword → SAMSUNG (자유 문자열로 종목코드도 검색어로 작동)
    none → None
    """
    from dartlab.gather.entry import _AXIS_REGISTRY

    entry = _AXIS_REGISTRY[axis]
    if entry.targetType == "stockCode":
        return SAMSUNG
    if entry.targetType == "columnName":
        return "close"
    if entry.targetType == "indicator":
        return None
    if entry.targetType == "keyword":
        return SAMSUNG
    return None


@pytest.mark.realData
@pytest.mark.integration
@pytest.mark.parametrize("axis", GATHER_AXES)
def test_gatherAxis_runs(axis):
    """gather(axis, target) 이 각 축에서 크래시 없이 실행. axis-별 적절한 target 사용."""
    import dartlab

    reqs = _AXIS_KEY_REQS.get(axis, ())
    if reqs and not any(_hasRealKey(r) for r in reqs):
        pytest.skip(f"gather({axis!r}) API 키 없음: {reqs}")

    target = _resolveTarget(axis)
    try:
        result = dartlab.gather(axis, target) if target else dartlab.gather(axis)
    except (TimeoutError, ConnectionError, OSError) as e:
        pytest.skip(f"gather({axis!r}) 네트워크 실패: {type(e).__name__}")
    except Exception as e:
        pytest.fail(f"gather({axis!r}) 크래시: {type(e).__name__}: {e}")
    # 결과 None 허용 (flow 의 US 미지원 등) — 단 크래시는 FAIL
