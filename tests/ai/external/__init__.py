"""외부 한국 금융 benchmark runner 모음 (cryptic-discovering-kettle G 트랙).

- KRX-Bench (ACL 2024) — dialect-lab/KRX-Bench
- WON (arXiv 2503.17963, 2025-03) — Korean financial benchmark
- KFinEval-Pilot (arXiv 2504.13216, 2025-04) — Korean finance evaluation

자체 KoFinanceBench 출시 X — 위 3 개가 이미 존재 → dartlab 가 통합 측정. 본 모듈은
각 benchmark 의 dataset path + sample N 인자를 받아 dartlab AI 답변 → string-match
scoring → 기준선 (externalBenchBaseline.json) append. 임계값 없음 — 단순 측정 기록.
"""

from __future__ import annotations

__all__ = ["runBenchmark", "BenchmarkResult"]

from ._common import BenchmarkResult, runBenchmark
