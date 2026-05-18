"""Phase B/C/D — 처방 효과 *실측* 도구.

매직처닝하스 처방 전후 peak RSS 직접 측정. RSS gate 는 *시점 RSS* 만 보지만
본 도구는 OS 의 *peak working set* 을 회수해 진짜 최대값 확인.

도구 2 종:
  1. ``getPeakRssMb()`` — Windows PMC.PeakWorkingSetSize / Linux VmHWM
     (Polars Rust heap 포함)
  2. ``tracemalloc.get_traced_memory()`` — Python heap peak

용도:
  1. master checkout → 본 도구 실행 → baseline 기록
  2. branch checkout → 본 도구 실행 → after 기록
  3. delta = baseline - after = 처방 효과

c.story() 가 너무 오래 걸리므로 본 도구는 *대표 호출 path* 만:
  - c.show("IS"), c.show("BS"), c.show("CF") — finance build trigger
  - c.show("businessOverview") — sections build trigger
  - c.analysis("financial", "수익성") — calc cross-statement trigger 1개

마커: ``memory + slow + realData``. realData 부재 시 skip.

실행:
  bash tests/test-lock.sh tests/memory/measureFinancePeak.py -v -s
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
def test_measure_combined_peak_rss(stockCode: str, capsys) -> None:
    """주요 build path 의 peak RSS 측정 — 처방 효과의 직접 검증.

    Windows PMC.PeakWorkingSetSize 가 *프로세스 시작 이후 최대* working set.
    이전 호출의 잔여도 반영되므로 *세션 단위* peak.
    """
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
        c.show("IS")
        c.show("BS")
        c.show("CF")
    except Exception as exc:  # noqa: BLE001
        with capsys.disabled():
            print(f"\n[measureFinancePeak] {stockCode} c.show finance 실패: {exc}")

    try:
        c.show("businessOverview")
    except Exception as exc:  # noqa: BLE001
        with capsys.disabled():
            print(f"[measureFinancePeak] {stockCode} c.show sections 실패: {exc}")

    pyCurrent, pyPeak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    rssAfter = getMemoryMb()
    peakAfter = getPeakRssMb()
    pyPeakMb = pyPeak / (1024 * 1024)

    with capsys.disabled():
        print(f"\n[measureFinancePeak] {stockCode}")
        print(f"  RSS before        = {rssBefore:>8.1f} MB")
        print(f"  RSS after         = {rssAfter:>8.1f} MB  (delta {rssAfter - rssBefore:+.1f})")
        print(f"  Process peak RSS  = {peakAfter:>8.1f} MB  (since process start)")
        print(f"  Peak delta        = {peakAfter - peakBefore:>+8.1f} MB  (이 test 동안)")
        print(f"  Python heap peak  = {pyPeakMb:>8.1f} MB  (tracemalloc — Polars Rust heap 제외)")

    # 가드: peak RSS delta 12GB 이상이면 회귀.
    deltaPeak = peakAfter - peakBefore
    assert deltaPeak < 12_000, f"{stockCode} peak RSS delta {deltaPeak:.0f}MB ≥ 12000MB — 처방 회귀 의심"
