"""scan 엔진 전수 축 스모크 — available_scans() 의 20개 axis 모두 iterate.

scan 은 프리빌드 parquet 기반이므로 실제 데이터가 로컬에 있어야 한다.
parquet 부재 시 개별 axis 자동 skip.
"""

from __future__ import annotations

import pytest


def _scanAxes() -> list[str]:
    import dartlab

    return sorted(dartlab.scan.available_scans())


SCAN_AXES = _scanAxes()


@pytest.mark.realData
@pytest.mark.integration
@pytest.mark.parametrize("axis", SCAN_AXES)
def test_scanAxis_runs(axis):
    """dartlab.scan(axis=...) 가 각 축에서 DataFrame 반환. parquet 없으면 skip."""
    import dartlab

    try:
        result = dartlab.scan(axis=axis)
    except FileNotFoundError:
        pytest.skip(f"scan({axis!r}) parquet 없음")
    except Exception as e:
        pytest.fail(f"scan({axis!r}) 크래시: {type(e).__name__}: {e}")

    if result is None:
        pytest.fail(f"scan({axis!r}) None — 프리빌드 누락 또는 silent fail")

    # DataFrame 인 경우 비어있지 않아야 함
    if hasattr(result, "height"):
        assert result.height > 0, f"scan({axis!r}) 빈 DataFrame"
