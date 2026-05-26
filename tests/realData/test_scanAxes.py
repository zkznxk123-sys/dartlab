"""scan 엔진 전수 축 스모크 — available_scans() 의 20개 axis 모두 iterate.

scan 은 프리빌드 parquet 기반이므로 실제 데이터가 로컬에 있어야 한다.
parquet 부재 시 개별 axis 자동 skip.
"""

from __future__ import annotations

import pytest


def _scanAxes() -> list[str]:
    import dartlab

    return sorted(dartlab.scan.availableScans())


SCAN_AXES = _scanAxes()


# fixture 환경에서 scan 프리빌드 데이터 제한으로 인해 빈 DF 가 날 수 있는 축
# (로컬 실데이터 환경에서는 엄격 검증).
# 2026-04-21 Phase E: debt ComputeError 수정 완료 → 목록에서 제거.
_FIXTURE_KNOWN_ISSUES: frozenset[str] = frozenset(
    {
        "disclosureRisk",  # fixture 에 disclosureRisk 프리빌드 (changes.parquet) 부재
        "macroBeta",  # macro 데이터 의존, fixture 는 macro 없음
    }
)


@pytest.mark.realData
@pytest.mark.integration
@pytest.mark.parametrize("axis", SCAN_AXES)
def test_scanAxis_runs(axis):
    """dartlab.scan(axis=...) 가 각 축에서 DataFrame 반환. parquet 없으면 skip."""
    import os

    import dartlab

    inFixtureEnv = "fixtures" in os.environ.get("DARTLAB_DATA_DIR", "")

    try:
        result = dartlab.scan(axis=axis)
    except FileNotFoundError:
        pytest.skip(f"scan({axis!r}) parquet 없음")
    except Exception as e:
        if inFixtureEnv and axis in _FIXTURE_KNOWN_ISSUES:
            pytest.xfail(f"scan({axis!r}) fixture 환경 제약: {type(e).__name__}")
        pytest.fail(f"scan({axis!r}) 크래시: {type(e).__name__}: {e}")

    if result is None:
        if inFixtureEnv and axis in _FIXTURE_KNOWN_ISSUES:
            pytest.xfail(f"scan({axis!r}) fixture 환경 None")
        pytest.fail(f"scan({axis!r}) None — 프리빌드 누락 또는 silent fail")

    # DataFrame 인 경우 비어있지 않아야 함.
    # macroBeta·disclosureRisk 처럼 prebuild 데이터 의존 axis 는 CI realdata 환경
    # (huggingface seed) 에도 데이터 없을 수 있어 xfail (환경 무관 known data gap).
    if hasattr(result, "height") and result.height == 0:
        if axis in _FIXTURE_KNOWN_ISSUES:
            pytest.xfail(f"scan({axis!r}) 빈 DF — known data gap")
        pytest.fail(f"scan({axis!r}) 빈 DataFrame")
