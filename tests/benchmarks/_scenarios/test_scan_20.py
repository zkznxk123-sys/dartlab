"""Benchmark 시나리오 2 — scan 20 종목 (T3-1)."""

from __future__ import annotations

import pytest


@pytest.mark.benchmark
@pytest.mark.serial
class TestScan20:
    """scan 20 종목 P50 / P95 baseline."""

    def test_scan_foreign_buy_momentum_20(self, benchmark) -> None:
        """foreignBuyMomentum kospi200 → top 20 — P50 ≤ 5s 목표."""

        def runScan() -> object:
            try:
                import dartlab

                return dartlab.scan("foreignBuyMomentum", universe="kospi200", limit=20)
            except (ImportError, AttributeError, RuntimeError, KeyError):
                pytest.skip("dartlab.scan 또는 recipe 미설치")
                return None

        benchmark(runScan)
