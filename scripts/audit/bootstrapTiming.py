"""Company 첫 호출 5초 약속 — wall-clock regression 검증.

Company 편의성 3원칙 중 "첫 호출 5초 이내" 가 실제로 지켜지는지 측정.
여러 종목을 cold-start 로 생성해 p50 / p95 를 stderr 로 출력하고, 임계치
초과 시 exit 1 로 CI gate 역할 수행.

사용법::

    # 기본 (KR 5 종목 cold start 측정, 임계치 5.0s)
    uv run python -X utf8 scripts/audit/bootstrapTiming.py

    # 임계치 조정
    uv run python -X utf8 scripts/audit/bootstrapTiming.py --threshold 3.0

    # 특정 종목만
    uv run python -X utf8 scripts/audit/bootstrapTiming.py --codes 005930 000660

Returns
-------
    exit 0 — p95 < threshold.
    exit 1 — p95 >= threshold (회귀).
"""

from __future__ import annotations

import argparse
import sys
import time

DEFAULT_CODES = ["005930", "000660", "035720", "035420", "051910"]


def measureOne(stockCode: str) -> float:
    """Company(stockCode) 1회 wall-clock 측정 (초)."""
    import dartlab

    t0 = time.perf_counter()
    dartlab.Company(stockCode)
    return time.perf_counter() - t0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--codes",
        nargs="+",
        default=DEFAULT_CODES,
        help="측정할 종목 리스트 (default: 시총 상위 5)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=5.0,
        help="p95 임계치 (초, default 5.0)",
    )
    args = parser.parse_args()

    print(f"Company 첫 호출 wall-clock 측정 — {len(args.codes)} 종목", file=sys.stderr)

    times: list[float] = []
    for code in args.codes:
        try:
            elapsed = measureOne(code)
            times.append(elapsed)
            print(f"  {code}: {elapsed:.2f}s", file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            print(f"  {code}: FAIL — {type(e).__name__}: {e}", file=sys.stderr)

    if not times:
        print("측정 실패 — 모든 종목에서 예외 발생", file=sys.stderr)
        return 2

    times.sort()
    n = len(times)
    p50 = times[n // 2]
    p95 = times[min(n - 1, int(n * 0.95))]
    mean = sum(times) / n

    print(file=sys.stderr)
    print(
        f"결과: mean={mean:.2f}s · p50={p50:.2f}s · p95={p95:.2f}s · threshold={args.threshold}s",
        file=sys.stderr,
    )

    if p95 >= args.threshold:
        print(
            f"[FAIL] p95 ({p95:.2f}s) >= threshold ({args.threshold}s) — 성능 회귀.",
            file=sys.stderr,
        )
        return 1

    print(f"[OK] p95 {p95:.2f}s < threshold {args.threshold}s", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
