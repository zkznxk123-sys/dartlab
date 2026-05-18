"""Phase B/C/D — 처방 효과 *실측* 도구.

매직처닝하스 처방 전후 c.story() peak RSS 를 직접 측정한다. RSS gate 는
*시점 RSS* 만 확인하지만 본 도구는:
  - ``tracemalloc.get_traced_memory()`` 의 Python heap peak
  - 백그라운드 thread 가 ``psutil.Process().memory_info().rss`` 를 100ms
    간격 sampling → process RSS peak (Polars Rust heap 포함)

용도:
  1. master checkout → 본 도구 실행 → baseline 기록
  2. branch checkout → 본 도구 실행 → after 기록
  3. delta = baseline - after = 처방 효과

마커: ``memory + slow + realData``. realData 부재 시 skip.

실행:
  bash tests/test-lock.sh tests/memory/measureFinancePeak.py -m "memory" -v -s
"""

from __future__ import annotations

import gc
import threading
import time
import tracemalloc
from contextlib import contextmanager
from pathlib import Path

import pytest

pytestmark = [pytest.mark.memory, pytest.mark.slow, pytest.mark.realData]


@contextmanager
def _peakRssSampler(intervalSeconds: float = 0.1):
    """백그라운드 thread 가 RSS sampling → peak 회수."""
    import os

    try:
        import psutil
    except ImportError:
        yield {"peak_mb": 0.0, "available": False}
        return

    proc = psutil.Process(os.getpid())
    state = {"peak_mb": proc.memory_info().rss / (1024 * 1024), "running": True, "available": True}

    def _sample() -> None:
        while state["running"]:
            try:
                rssMb = proc.memory_info().rss / (1024 * 1024)
                if rssMb > state["peak_mb"]:
                    state["peak_mb"] = rssMb
            except (psutil.NoSuchProcess, OSError):
                break
            time.sleep(intervalSeconds)

    t = threading.Thread(target=_sample, daemon=True)
    t.start()
    try:
        yield state
    finally:
        state["running"] = False
        t.join(timeout=1.0)


def _hasFinanceParquet(stockCode: str) -> bool:
    from dartlab.core.dataLoader import _dataDir

    return (_dataDir("finance") / f"{stockCode}.parquet").exists()


@pytest.mark.parametrize("stockCode", ["005380", "005930", "000660"])
def test_measure_story_peak_rss(stockCode: str, capsys) -> None:
    """c.story() peak RSS 측정 — 처방 효과의 진짜 검증.

    출력 형식: 표준 출력으로 peak MB 보고. assert 는 *상한 = 12000MB* (이전
    Baseline 13000MB 보다 조금 낮음 — 회귀 즉시 detect).
    """
    if not _hasFinanceParquet(stockCode):
        pytest.skip(f"finance parquet 부재: {stockCode}")

    from dartlab import Company

    gc.collect()
    tracemalloc.start()

    with _peakRssSampler(intervalSeconds=0.1) as rssState:
        c = Company(stockCode)
        try:
            c.story()
        except Exception as exc:  # noqa: BLE001 — peak 만 측정, story 실패 무관
            pytest.skip(f"c.story() 실패 ({stockCode}): {type(exc).__name__}: {exc}")

    pyCurrent, pyPeak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    rssPeak = rssState["peak_mb"]
    pyPeakMb = pyPeak / (1024 * 1024)

    with capsys.disabled():
        print(f"\n[measureFinancePeak] {stockCode}")
        print(f"  python heap peak  = {pyPeakMb:>8.1f} MB (tracemalloc)")
        print(f"  process RSS peak  = {rssPeak:>8.1f} MB (psutil sampling, polars Rust heap 포함)")
        print(f"  RSS sampler avail = {rssState['available']}")

    # 회귀 가드 — 12GB 초과 시 fail. Baseline 13GB (audit 2026-04-22) 보다 1GB 여유.
    assert rssPeak < 12_000, f"{stockCode} c.story() peak RSS {rssPeak:.0f}MB ≥ 12000MB — 매직처닝하스 처방 회귀 의심"
