"""Phase B-3 — Finance build *peak* RSS 회귀 가드 (peak 추적, baseline 가설).

매직처닝하스 처방 후 단순 호출 (c.show 4번) peak RSS < 1000MB, c.story()
peak RSS < 4000MB 목표. Windows PMC.PeakWorkingSetSize / Linux VmHWM 으로
*프로세스 시작 이후 최대* working set 추적 — 이전 commit (b51a2a91b) 의
시점 RSS 만 비교한 거짓 검증 정정.

Baseline 13GB (audit 2026-04-22) 는 *과거 측정* — 현 처방 후 직접 측정으로
대조. realData fixture 부재 시 skip.

CI gate: ``nightly`` matrix 의 ``memory + slow + realData``.
"""

from __future__ import annotations

import gc

import pytest

pytestmark = [pytest.mark.memory, pytest.mark.slow, pytest.mark.realData]


def _hasFinanceParquet(stockCode: str) -> bool:
    """로컬 finance parquet 존재 확인 — 없으면 skip."""
    from dartlab.core.dataLoader import _dataDir

    return (_dataDir("finance") / f"{stockCode}.parquet").exists()


@pytest.mark.parametrize("stockCode", ["005380", "005930"])
def test_simple_show_peak_rss_under_1000mb(stockCode: str) -> None:
    """단순 호출 4 번 (c.show IS/BS/CF/businessOverview) peak RSS < 1000MB.

    peak = Windows PMC.PeakWorkingSetSize / Linux VmHWM — *시작 이후 최대*.
    """
    if not _hasFinanceParquet(stockCode):
        pytest.skip(f"finance parquet 부재: {stockCode}")

    from dartlab import Company
    from dartlab.core.memory import getPeakRssMb

    gc.collect()
    peakBefore = getPeakRssMb()
    if peakBefore < 0:
        pytest.skip("peak RSS 측정 불가 (OS 미지원)")

    c = Company(stockCode)
    c.panel("IS")
    c.panel("BS")
    c.panel("CF")
    try:
        c.panel("businessOverview")
    except Exception:  # noqa: BLE001 — sections 없으면 finance 만으로 검증
        pass

    peakAfter = getPeakRssMb()
    deltaPeak = peakAfter - peakBefore

    assert deltaPeak < 1000, (
        f"{stockCode} c.show 4번 peak RSS delta {deltaPeak:.0f}MB > 1000MB — Phase B/D 처방 회귀 의심"
    )


def test_repeated_company_sweep_rss_drift_under_500mb() -> None:
    """5 회사 sweep peak delta < 500MB — 캐시 evict + IPC mmap reclaim 정상성."""
    candidates = ["005380", "005930", "000660", "035420", "068270"]
    available = [c for c in candidates if _hasFinanceParquet(c)]
    if len(available) < 2:
        pytest.skip(f"realData 부족: {len(available)} 회사")

    from dartlab import Company
    from dartlab.core.memory import cleanupBetweenCompanies, getPeakRssMb

    gc.collect()
    peakStart = getPeakRssMb()
    if peakStart < 0:
        pytest.skip("peak RSS 측정 불가")

    for stockCode in available:
        c = Company(stockCode)
        c.panel("IS")
        cleanupBetweenCompanies(label=stockCode)

    peakEnd = getPeakRssMb()
    deltaPeak = peakEnd - peakStart

    assert deltaPeak < 500, (
        f"{len(available)} 회사 sweep peak delta {deltaPeak:.0f}MB > 500MB — "
        f"BoundedCache evict / IPC mmap reclaim 회귀 의심"
    )
