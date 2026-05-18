"""c.story() peak RSS 측정 — 진짜 13GB 시나리오 검증.

audit 2026-04-22 의 13GB peak 는 c.story() 14축 cross-statement 시나리오.
본 도구가 그 시나리오를 직접 호출 + peak 측정.

마커: ``memory + slow + realData``.
실행: bash tests/test-lock.sh tests/memory/measureStoryPeak.py -v -s
"""

from __future__ import annotations

import gc
import tracemalloc

import pytest

pytestmark = [pytest.mark.memory, pytest.mark.slow, pytest.mark.realData]


def _hasFinanceParquet(stockCode: str) -> bool:
    from dartlab.core.dataLoader import _dataDir

    return (_dataDir("finance") / f"{stockCode}.parquet").exists()


@pytest.mark.parametrize("stockCode", ["005930"])
def test_story_peak_rss(stockCode: str, capsys) -> None:
    """c.story() 호출 시 peak RSS 측정."""
    if not _hasFinanceParquet(stockCode):
        pytest.skip(f"finance parquet 부재: {stockCode}")

    from dartlab import Company
    from dartlab.core.memory import getMemoryMb, getPeakRssMb

    gc.collect()
    rssBefore = getMemoryMb()
    peakBefore = getPeakRssMb()
    tracemalloc.start()

    c = Company(stockCode)
    try:
        c.story()
    except Exception as exc:  # noqa: BLE001
        with capsys.disabled():
            print(f"\n[measureStoryPeak] {stockCode} c.story() 실패: {type(exc).__name__}: {exc}")

    pyCurrent, pyPeak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    rssAfter = getMemoryMb()
    peakAfter = getPeakRssMb()
    pyPeakMb = pyPeak / (1024 * 1024)

    with capsys.disabled():
        print(f"\n[measureStoryPeak] {stockCode} c.story()")
        print(f"  RSS before        = {rssBefore:>8.1f} MB")
        print(f"  RSS after         = {rssAfter:>8.1f} MB  (delta {rssAfter - rssBefore:+.1f})")
        print(f"  Process peak RSS  = {peakAfter:>8.1f} MB  (since process start)")
        print(f"  Peak delta        = {peakAfter - peakBefore:>+8.1f} MB  (이 test 동안)")
        print(f"  Python heap peak  = {pyPeakMb:>8.1f} MB  (tracemalloc)")

    # 가드 - 8GB 이상이면 회귀 (audit 13GB 보다 5GB 여유)
    deltaPeak = peakAfter - peakBefore
    assert deltaPeak < 8000, f"{stockCode} c.story() peak delta {deltaPeak:.0f}MB ≥ 8000MB — 회귀 의심"
