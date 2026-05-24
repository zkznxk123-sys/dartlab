"""Benchmark 시나리오 5 — 디스크 캐시 5 baseline disk-hit 1.0s/corp 회귀 가드 (T3-1).

git log 502fbc601 "디스크 캐시 5 baseline disk-hit 1.0s/corp 마법 수준" 달성 후
회귀 차단. 디스크 캐시 정착 후 같은 종목 재로드 시 1초 이내 P50 보장.
"""

from __future__ import annotations

import pytest


@pytest.mark.benchmark
@pytest.mark.serial
class TestDiskHit:
    """warm 디스크 캐시 P50 ≤ 1.0s/corp 회귀 가드."""

    def test_warm_disk_hit_per_corp(self, benchmark) -> None:
        try:
            import dartlab

            # 1 회 콜드 호출로 디스크 캐시 정착
            _ = dartlab.Company("005930")
        except (ImportError, AttributeError, RuntimeError):
            pytest.skip("dartlab 또는 데이터 미설치")
            return

        def warmLoad() -> object:
            return dartlab.Company("005930")

        # baseline: disk-hit 1.0s/corp (commit 502fbc601 달성)
        # ±10% 임계는 별도 audit (tests/audit/_baselines/benchmarks.json) 가 강제
        benchmark(warmLoad)
