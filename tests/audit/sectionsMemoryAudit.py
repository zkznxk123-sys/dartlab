"""sections() 메모리 peak 측정 + baseline 회귀 가드.

tracemalloc (Python heap) + psutil RSS (전체 프로세스) 양쪽 측정.
baseline JSON 박제 후 회귀 tolerance 20% 차단.

실행:
    uv run python -X utf8 tests/audit/sectionsMemoryAudit.py --check
    uv run python -X utf8 tests/audit/sectionsMemoryAudit.py --write-baseline

종목당 ~10s + ~300MB 라 fast tier 부적합. nightly 게이트 예상.
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
import tracemalloc
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = REPO_ROOT / "tests" / "audit" / "_baselines" / "sectionsMemoryBaseline.json"
DEFAULT_STOCKS = ("005380", "005930", "000660")
REGRESSION_TOLERANCE = 0.20


def _rssMb() -> float:
    try:
        import psutil  # noqa: PLC0415
    except ImportError:
        return 0.0
    return psutil.Process().memory_info().rss / 1024 / 1024


def memoryAuditPerStock(stockCode: str) -> dict[str, float] | None:
    from dartlab.providers.dart.docs.sections.pipeline import clearPreparedCache, sections

    clearPreparedCache(stockCode)
    gc.collect()
    rssBefore = _rssMb()

    tracemalloc.start()
    df = sections(stockCode, topics=None)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    rssAfter = _rssMb()
    rows = df.height if df is not None else 0

    clearPreparedCache(stockCode)
    gc.collect()
    return {
        "rows": rows,
        "pythonPeakMb": round(peak / 1024 / 1024, 1),
        "pythonCurrentMb": round(current / 1024 / 1024, 1),
        "rssBeforeMb": round(rssBefore, 1),
        "rssAfterMb": round(rssAfter, 1),
        "rssGrowthMb": round(rssAfter - rssBefore, 1),
    }


def _loadBaseline() -> dict[str, dict] | None:
    if not BASELINE_PATH.exists():
        return None
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def _writeBaseline(report: dict[str, dict]) -> None:
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    sys.stderr.write(f"[sectionsMemoryAudit] baseline 박제 → {BASELINE_PATH.relative_to(REPO_ROOT)}\n")


def _checkAgainstBaseline(current: dict[str, dict], baseline: dict[str, dict]) -> list[str]:
    errors: list[str] = []
    for stockCode, cur in current.items():
        if stockCode not in baseline:
            sys.stderr.write(f"[sectionsMemoryAudit] WARN {stockCode}: baseline 부재\n")
            continue
        baseHeap = baseline[stockCode]["pythonPeakMb"]
        curHeap = cur["pythonPeakMb"]
        if baseHeap > 0 and curHeap > baseHeap * (1 + REGRESSION_TOLERANCE):
            errors.append(
                f"{stockCode}: pythonPeak {curHeap:.1f}MB > baseline {baseHeap:.1f}MB × (1+{REGRESSION_TOLERANCE})"
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stocks", default=",".join(DEFAULT_STOCKS), help="쉼표 구분 종목 코드")
    parser.add_argument("--write-baseline", action="store_true")
    parser.add_argument("--check", action="store_true", default=True)
    args = parser.parse_args()

    stocks = [s.strip() for s in args.stocks.split(",") if s.strip()]
    report: dict[str, dict] = {}

    for stockCode in stocks:
        try:
            result = memoryAuditPerStock(stockCode)
        except (FileNotFoundError, ValueError, OSError) as e:
            sys.stderr.write(f"[sectionsMemoryAudit] SKIP {stockCode}: {e}\n")
            continue
        if result is None:
            sys.stderr.write(f"[sectionsMemoryAudit] SKIP {stockCode}: 결과 None\n")
            continue
        report[stockCode] = result
        sys.stderr.write(
            f"[sectionsMemoryAudit] {stockCode}: rows={result['rows']} "
            f"pythonPeak={result['pythonPeakMb']}MB rssGrowth={result['rssGrowthMb']}MB\n"
        )

    if args.write_baseline:
        _writeBaseline(report)
        return 0
    if not report:
        sys.stderr.write("[sectionsMemoryAudit] WARN: 측정 0 건 — CI 미설치 가정 exit 0\n")
        return 0

    baseline = _loadBaseline()
    if baseline is None:
        sys.stderr.write("[sectionsMemoryAudit] WARN: baseline 부재 — --write-baseline 후 재실행\n")
        return 0

    errors = _checkAgainstBaseline(report, baseline)
    if errors:
        sys.stderr.write("[sectionsMemoryAudit] FAIL — 메모리 회귀:\n")
        for line in errors:
            sys.stderr.write(f"  - {line}\n")
        return 1
    sys.stderr.write(f"[sectionsMemoryAudit] PASS — {len(report)}/{len(stocks)} 종목 통과\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
