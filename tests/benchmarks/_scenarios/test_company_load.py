"""Benchmark 시나리오 1 — Company("005930") 콜드 + 웜 (T3-1).

P50/P95 측정 + 메모리 peak. baseline: tests/audit/_baselines/benchmarks.json.

실행::
    bash tests/test-lock.sh tests/benchmarks/_scenarios/test_company_load.py -m benchmark --benchmark-only
"""

from __future__ import annotations

import pytest


@pytest.mark.benchmark
@pytest.mark.serial  # T3-3 — Company 인스턴스 + Polars 힙, 단일 worker 강행
class TestCompanyLoad:
    """Company.panel 의 콜드/웜 latency baseline."""

    def test_company_load_cold(self, benchmark) -> None:
        """첫 호출 (cache miss) — 디스크 hit 1.0s/corp 목표."""

        def loadCompany() -> object:
            try:
                import dartlab

                return dartlab.Company("005930")
            except (ImportError, AttributeError, RuntimeError):
                pytest.skip("dartlab 또는 데이터 미설치")

        benchmark(loadCompany)

    def test_company_show_is_warm(self, benchmark) -> None:
        """warm cache 후 panel('IS') P50 ≤ 0.1s 목표."""

        try:
            import dartlab

            company = dartlab.Company("005930")
        except (ImportError, AttributeError, RuntimeError):
            pytest.skip("dartlab 또는 데이터 미설치")
            return

        def showIs() -> object:
            return company.panel("IS")

        benchmark(showIs)
