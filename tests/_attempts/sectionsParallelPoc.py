"""POC — sections build 병렬 처리 가능성 검증.

사용자 (2026-05-23): "3은 테스트로 확실히가능한건지 확인하고 본진투입결정"

가설:
1. ProcessPoolExecutor 로 N corps 동시 build → N× 빠른 batch
2. ThreadPoolExecutor 로 _normalizeRowspanShift 등 hot 함수 병렬 → 하나의 corp 도 빠름

본 POC 는 가설 1 검증 — 5 baseline 종목을 5 process 로 병렬 vs 직렬 비교.

본진 투입 결정 기준:
- 5 corps 직렬 30s → 병렬 < 10s 면 본진 ProcessPoolExecutor API 추가 결정
- 안전성: 5 baseline parity 회귀 0 확인 (각 corp 독립)
- 메모리: 5 process × 200MB = 1GB peak — 일반 PC 대응 가능
"""

from __future__ import annotations

import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))


def _buildOne(code: str) -> tuple[str, float, tuple[int, int]]:
    """단일 corp sections build. process 안에서 실행."""
    from dartlab.providers.dart import Company

    t0 = time.time()
    sec = Company(code).sections
    elapsed = time.time() - t0
    shape = sec.shape if sec is not None else (0, 0)
    return (code, elapsed, shape)


def benchSerial(codes: list[str]) -> tuple[float, list[tuple[str, float, tuple[int, int]]]]:
    """직렬 build — process 안에서 5 corps 차례로."""
    results = []
    t0 = time.time()
    for code in codes:
        from dartlab.providers.dart.docs.sections.diskCache import clearDiskCache
        from dartlab.providers.dart.docs.sections.pipeline import clearPreparedCache
        from dartlab.providers.dart.docs.sections.textStructure import _detectHeading, _normalizeHeadingText

        clearPreparedCache()
        clearDiskCache(code)
        _detectHeading.cache_clear()
        _normalizeHeadingText.cache_clear()
        results.append(_buildOne(code))
    total = time.time() - t0
    return total, results


def benchParallel(codes: list[str], workers: int) -> tuple[float, list[tuple[str, float, tuple[int, int]]]]:
    """병렬 build — ProcessPool workers process."""
    # Pre-clear disk cache to force cold builds
    from dartlab.providers.dart.docs.sections.diskCache import clearDiskCache

    for code in codes:
        clearDiskCache(code)

    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(_buildOne, codes))
    total = time.time() - t0
    return total, results


def main() -> int:
    codes = ["005380", "005930", "035720", "207940", "000660"]

    print("=== 직렬 (current best) ===")
    serial_total, serial_results = benchSerial(codes)
    for code, elapsed, shape in serial_results:
        print(f"  {code}: {elapsed:.2f}s, rows={shape[0]}")
    print(f"TOTAL serial: {serial_total:.2f}s")

    print("\n=== 병렬 (workers=5) ===")
    par_total, par_results = benchParallel(codes, workers=5)
    for code, elapsed, shape in par_results:
        print(f"  {code}: {elapsed:.2f}s, rows={shape[0]}")
    print(f"TOTAL parallel: {par_total:.2f}s")

    print(f"\n=== speedup: {serial_total / par_total:.2f}× ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
