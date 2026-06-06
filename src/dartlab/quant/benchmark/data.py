"""Benchmark data 호환 경로.

SSOT는 ``dartlab.synth.benchmarkData``에 있다.
"""

from __future__ import annotations

from dartlab.synth.benchmarkData import (
    benchmarkSnapshot,
    calcBenchmark,
    fetchBenchmarkOhlcv,
    resolveBenchmark,
    resolveBenchmarkStack,
)

__all__ = [
    "benchmarkSnapshot",
    "calcBenchmark",
    "fetchBenchmarkOhlcv",
    "resolveBenchmark",
    "resolveBenchmarkStack",
]
