"""Phase B-3 — Finance build peak RSS 회귀 가드.

매직처닝하스 처방 후 005380 (현대차) 첫 콜 peak RSS ≤ 1500MB 목표 (Baseline
~13GB → 11.5× 감소). realData fixture 부재 시 skip.

CI gate: ``nightly`` matrix 의 ``memory + slow + realData``.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytestmark = [pytest.mark.memory, pytest.mark.slow, pytest.mark.realData]


def _hasFinanceParquet(stockCode: str) -> bool:
    """로컬 finance parquet 존재 확인 — 없으면 skip (CI fast path)."""
    from dartlab.core.dataLoader import _dataDir

    return (_dataDir("finance") / f"{stockCode}.parquet").exists()


@pytest.mark.parametrize("stockCode", ["005380", "005930"])
def test_first_call_peak_rss_under_1500mb(stockCode: str) -> None:
    """첫 콜 peak RSS ≤ 1500MB — Phase B 의 DuckDB pivot + Phase D 의 IPC mmap 효과."""
    if not _hasFinanceParquet(stockCode):
        pytest.skip(f"finance parquet 부재: {stockCode}")

    from dartlab import Company
    from dartlab.core.memory import getMemoryMb

    rssBefore = getMemoryMb()
    if rssBefore <= 0:
        pytest.skip("RSS 측정 불가 (psutil 미설치 또는 OS 미지원)")

    c = Company(stockCode)
    c.show("IS")  # finance build 트리거
    c.show("BS")
    c.show("CF")

    rssAfter = getMemoryMb()
    peakDelta = rssAfter - rssBefore

    # 회귀 가드 — 13GB → ≤1500MB 목표. 측정 노이즈 + Polars Rust heap 변동 고려.
    assert peakDelta < 1500, (
        f"{stockCode} 첫 콜 peak RSS delta {peakDelta:.0f}MB 가 1500MB 초과 — "
        f"Phase B/D 회귀 의심 (DuckDB pivot 또는 IPC mmap path 미작동)"
    )


def test_repeated_company_sweep_rss_drift_under_200mb() -> None:
    """5 회사 sweep 후 RSS drift ≤ 200MB — 캐시 evict 후 mmap reload 정상성."""
    candidates = ["005380", "005930", "000660", "035420", "068270"]
    available = [c for c in candidates if _hasFinanceParquet(c)]
    if len(available) < 2:
        pytest.skip(f"realData 부족: {len(available)} 회사")

    from dartlab import Company
    from dartlab.core.memory import cleanupBetweenCompanies, getMemoryMb

    rssStart = getMemoryMb()
    if rssStart <= 0:
        pytest.skip("RSS 측정 불가")

    for stockCode in available:
        c = Company(stockCode)
        c.show("IS")
        cleanupBetweenCompanies(label=stockCode)

    rssEnd = getMemoryMb()
    drift = rssEnd - rssStart

    assert drift < 200, (
        f"{len(available)} 회사 sweep 후 RSS drift {drift:.0f}MB > 200MB — "
        f"BoundedCache evict / IPC mmap reclaim 회귀 의심"
    )
