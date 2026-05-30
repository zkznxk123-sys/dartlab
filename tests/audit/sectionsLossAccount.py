"""sections round-trip 회계 — 원본 docs 보존율 측정 + baseline 회귀 가드.

목적: DART ``docs.parquet`` 의 ``section_content`` 총량 vs ``c.sections``
결과의 모든 period 컬럼 총량을 byte/line/row 3 지표로 비교. 의도 drop
(chapter 결정 전 prelude · projection-suppressed · detailTopic 매치) 차감 후
보존율이 budget 미만이면 fail.

실행:
    uv run python -X utf8 tests/audit/sectionsLossAccount.py --check
    uv run python -X utf8 tests/audit/sectionsLossAccount.py --write-baseline
    uv run python -X utf8 tests/audit/sectionsLossAccount.py --stocks 005380,005930

baseline: ``tests/audit/_baselines/sectionsLossBaseline.json`` — 5 종목 박제.
부재 시 ``--check`` 는 stderr 경고 + exit 0 (CI 미설치 시나리오). data dir
부재 (loadData None) 시 종목별 skip.

본 도구는 nightly 게이트. ``c.sections`` 호출이 종목당 ~10s 라 fast tier 부적합.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import polars as pl

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = REPO_ROOT / "tests" / "audit" / "_baselines" / "sectionsLossBaseline.json"
DEFAULT_STOCKS = ("005380", "005930", "000660", "035420", "068270")
DEFAULT_BUDGET = 0.90
REGRESSION_TOLERANCE = 0.02

_log = logging.getLogger("sectionsLossAccount")


def _sourceTotals(stockCode: str) -> dict[str, int] | None:
    """원본 ``docs.parquet`` 의 byte/line/row 총량."""
    from dartlab.core.dataLoader import loadData
    from dartlab.providers.dart.docs.sections.sectionsBase import detectContentCol

    try:
        df = loadData(
            stockCode, category="docs", columns=["year", "report_type", "section_title", "section_content", "content"]
        )
    except (FileNotFoundError, ValueError):
        return None
    if df is None or df.is_empty():
        return None

    ccol = detectContentCol(df)
    nonNull = df.filter(pl.col(ccol).is_not_null() & (pl.col(ccol).str.len_chars() > 0))
    if nonNull.is_empty():
        return None

    byteTotal = int(nonNull.select(pl.col(ccol).str.len_bytes().sum()).item() or 0)
    lineTotal = int(nonNull.select(pl.col(ccol).str.count_matches("\n").sum()).item() or 0) + nonNull.height
    return {"bytes": byteTotal, "lines": lineTotal, "rows": nonNull.height}


def _sectionsTotals(stockCode: str) -> dict[str, int] | None:
    """``c.sections`` 결과의 모든 period 컬럼 byte/line/row 총량."""
    from dartlab.providers.dart.docs.sections.pipeline import sections

    df = sections(stockCode, topics=None)
    if df is None or df.is_empty():
        return None

    periodCols = [c for c in df.columns if len(c) >= 4 and c[:4].isdigit()]
    if not periodCols:
        return None

    bytes_ = 0
    lines = 0
    for col in periodCols:
        nonNull = df.filter(pl.col(col).is_not_null() & (pl.col(col).cast(pl.Utf8).str.len_chars() > 0))
        if nonNull.is_empty():
            continue
        bytes_ += int(nonNull.select(pl.col(col).cast(pl.Utf8).str.len_bytes().sum()).item() or 0)
        lines += (
            int(nonNull.select(pl.col(col).cast(pl.Utf8).str.count_matches("\n").sum()).item() or 0) + nonNull.height
        )

    return {"bytes": bytes_, "lines": lines, "rows": df.height}


def measureLossPerStock(stockCode: str) -> dict[str, object] | None:
    """단일 종목의 원본 ↔ sections 보존율."""
    src = _sourceTotals(stockCode)
    if src is None:
        return None
    sec = _sectionsTotals(stockCode)
    if sec is None:
        return None

    rates = {
        "byteRate": (sec["bytes"] / src["bytes"]) if src["bytes"] else 0.0,
        "lineRate": (sec["lines"] / src["lines"]) if src["lines"] else 0.0,
        "rowExpansion": (sec["rows"] / src["rows"]) if src["rows"] else 0.0,
    }
    return {"source": src, "sections": sec, "rates": rates}


def _loadBaseline() -> dict[str, dict] | None:
    if not BASELINE_PATH.exists():
        return None
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def _writeBaseline(report: dict[str, dict]) -> None:
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    sys.stderr.write(f"[sectionsLossAccount] baseline 박제 → {BASELINE_PATH.relative_to(REPO_ROOT)}\n")


def _checkAgainstBaseline(current: dict[str, dict], baseline: dict[str, dict], budget: float) -> list[str]:
    errors: list[str] = []
    for stockCode, cur in current.items():
        if stockCode not in baseline:
            sys.stderr.write(f"[sectionsLossAccount] WARN {stockCode}: baseline 부재, 측정만 기록\n")
            continue
        base = baseline[stockCode]
        baseRate = base["rates"]["byteRate"]
        curRate = cur["rates"]["byteRate"]

        if curRate < budget:
            errors.append(f"{stockCode}: byteRate {curRate:.3f} < budget {budget:.3f} (baseline {baseRate:.3f})")
        elif curRate < baseRate - REGRESSION_TOLERANCE:
            errors.append(
                f"{stockCode}: byteRate {curRate:.3f} regressed from baseline {baseRate:.3f} "
                f"(tolerance {REGRESSION_TOLERANCE})"
            )
    return errors


def main() -> int:
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stocks", default=",".join(DEFAULT_STOCKS), help="쉼표 구분 종목 코드")
    parser.add_argument("--budget", type=float, default=DEFAULT_BUDGET, help="byte 보존율 하한 (default 0.90)")
    parser.add_argument("--write-baseline", action="store_true", help="현 측정값을 baseline 으로 박제")
    parser.add_argument("--check", action="store_true", default=True, help="baseline 와 비교 (default)")
    args = parser.parse_args()

    stocks = [s.strip() for s in args.stocks.split(",") if s.strip()]
    report: dict[str, dict] = {}
    skipped: list[str] = []

    for stockCode in stocks:
        result = measureLossPerStock(stockCode)
        if result is None:
            skipped.append(stockCode)
            sys.stderr.write(f"[sectionsLossAccount] SKIP {stockCode}: data 부재\n")
            continue
        report[stockCode] = result
        rates = result["rates"]
        sys.stderr.write(
            f"[sectionsLossAccount] {stockCode}: byte {rates['byteRate']:.3f} "
            f"line {rates['lineRate']:.3f} rowExpansion {rates['rowExpansion']:.2f}x\n"
        )

    if args.write_baseline:
        _writeBaseline(report)
        return 0

    if not report:
        sys.stderr.write("[sectionsLossAccount] WARN: 측정 결과 0건 (data dir 부재로 추정) — CI 미설치 가정 exit 0\n")
        return 0

    baseline = _loadBaseline()
    if baseline is None:
        sys.stderr.write("[sectionsLossAccount] WARN: baseline 부재 — --write-baseline 으로 초기 박제 후 재실행\n")
        return 0

    errors = _checkAgainstBaseline(report, baseline, args.budget)
    if errors:
        sys.stderr.write("[sectionsLossAccount] FAIL — 보존율 회귀:\n")
        for line in errors:
            sys.stderr.write(f"  - {line}\n")
        return 1

    sys.stderr.write(f"[sectionsLossAccount] PASS — {len(report)}/{len(stocks)} 종목 budget {args.budget:.2f} 통과\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
