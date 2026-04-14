"""Engine audit — dartlab 엔진 end-to-end 기능 점검.

사용법::

    uv run python -X utf8 scripts/audit/engineAudit.py              # 전체 종목
    uv run python -X utf8 scripts/audit/engineAudit.py --stock 005930
    uv run python -X utf8 scripts/audit/engineAudit.py --quick      # 핵심만

규격: ops/engineAudit.md
결과: data/audit/engine/{YYYY-MM-DD}/{stockCode}.json + report.md
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

logging.getLogger().setLevel(logging.ERROR)

# 표준 종목 세트 (ops/engineAudit.md 규격)
_STOCKS = [
    ("005930", "삼성전자", "KR"),
    ("047040", "대우건설", "KR"),
    ("003230", "삼양식품", "KR"),
    ("AAPL", "Apple", "US"),
    ("MSFT", "Microsoft", "US"),
]

# 핵심 analysis 축 (전체는 14개지만 quick 모드용 대표 4개)
_CORE_AXES = ["수익성", "성장성", "안정성", "현금흐름"]
_ALL_AXES = [
    "수익성",
    "성장성",
    "안정성",
    "현금흐름",
    "비용구조",
    "효율성",
    "자산구조",
    "수익구조",
    "자금조달",
    "이익품질",
    "자본배분",
    "투자효율",
    "재무정합성",
    "종합평가",
]


def _safe_call(fn, *args, **kwargs) -> tuple[str, str]:
    """호출 결과를 (status, detail)로 반환. Pass/Warning/Fail."""
    try:
        result = fn(*args, **kwargs)
        if result is None:
            return "Warning", "returned None"
        if hasattr(result, "is_empty") and result.is_empty():
            return "Warning", "empty DataFrame"
        if hasattr(result, "__len__") and len(result) == 0:
            return "Warning", "empty result"
        return "Pass", ""
    except Exception as e:
        return "Fail", f"{type(e).__name__}: {str(e)[:200]}"


def auditCompany(stockCode: str, *, quick: bool = False) -> dict[str, Any]:
    """단일 종목 전체 엔진 점검."""
    import dartlab

    dartlab.verbose = False
    start = time.monotonic()
    results: dict[str, str] = {}

    # 1. Company 생성
    try:
        c = dartlab.Company(stockCode)
        results["Company.create"] = "Pass"
    except Exception as e:
        results["Company.create"] = f"Fail: {type(e).__name__}: {e}"
        return {
            "stockCode": stockCode,
            "results": results,
            "duration_sec": round(time.monotonic() - start, 2),
            "overall": "Fail",
        }

    # 2. 메타 속성
    for attr in ["market", "currency", "topics", "index"]:
        status, detail = _safe_call(lambda a=attr: getattr(c, a))
        results[f"Company.{attr}"] = f"{status}{': ' + detail if detail else ''}"

    status, detail = _safe_call(c.filings)
    results["Company.filings"] = f"{status}{': ' + detail if detail else ''}"

    # 3. show/select 재무제표
    for stmt in ["IS", "BS", "CF"]:
        status, detail = _safe_call(c.show, stmt)
        results[f"show.{stmt}"] = f"{status}{': ' + detail if detail else ''}"

    if not quick:
        for stmt in ["CIS", "SCE"]:
            status, detail = _safe_call(c.show, stmt)
            results[f"show.{stmt}"] = f"{status}{': ' + detail if detail else ''}"

        # Notes (대표 2개)
        for topic in ["inventory", "borrowings"]:
            status, detail = _safe_call(c.show, topic)
            results[f"show.{topic}"] = f"{status}{': ' + detail if detail else ''}"

        # Report topic (KR only)
        if getattr(c, "market", "KR") == "KR":
            status, detail = _safe_call(c.show, "dividend")
            results["show.dividend"] = f"{status}{': ' + detail if detail else ''}"

    # select
    status, detail = _safe_call(c.select, "IS", ["매출액"])
    results["select.IS"] = f"{status}{': ' + detail if detail else ''}"

    # 4. analysis
    axes = _CORE_AXES if quick else _ALL_AXES
    for axis in axes:
        status, detail = _safe_call(c.analysis, axis)
        results[f"analysis.{axis}"] = f"{status}{': ' + detail if detail else ''}"

    # 5. credit
    status, detail = _safe_call(c.credit, "등급")
    results["credit.등급"] = f"{status}{': ' + detail if detail else ''}"

    # 6. quant
    status, detail = _safe_call(c.quant, "종합")
    results["quant.종합"] = f"{status}{': ' + detail if detail else ''}"

    # 7. gather (가벼운 것만)
    if not quick:
        status, detail = _safe_call(c.gather, "price")
        results["gather.price"] = f"{status}{': ' + detail if detail else ''}"

    # 8. review (단일 섹션)
    if not quick:
        status, detail = _safe_call(c.review, "수익성")
        results["review.수익성"] = f"{status}{': ' + detail if detail else ''}"

    # 9. 집계
    fail_count = sum(1 for v in results.values() if v.startswith("Fail"))
    warn_count = sum(1 for v in results.values() if v.startswith("Warning"))
    if fail_count == 0 and warn_count <= 1:
        overall = "Pass"
    elif fail_count >= 4:
        overall = "Fail"
    else:
        overall = "Warning"

    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "stockCode": stockCode,
        "market": getattr(c, "market", "KR"),
        "results": results,
        "counts": {"fail": fail_count, "warning": warn_count, "total": len(results)},
        "duration_sec": round(time.monotonic() - start, 2),
        "overall": overall,
    }


def auditMarketLevel(*, quick: bool = False) -> dict[str, Any]:
    """Company 불필요한 시장 레벨 엔진 점검."""
    import dartlab

    dartlab.verbose = False
    results: dict[str, str] = {}

    # scan
    status, detail = _safe_call(dartlab.scan)
    results["scan.guide"] = f"{status}{': ' + detail if detail else ''}"

    for axis in ["profitability"] if quick else ["profitability", "growth", "cashflow", "governance"]:
        status, detail = _safe_call(dartlab.scan, axis)
        results[f"scan.{axis}"] = f"{status}{': ' + detail if detail else ''}"

    # macro
    status, detail = _safe_call(dartlab.macro)
    results["macro.guide"] = f"{status}{': ' + detail if detail else ''}"
    for axis in ["사이클"] if quick else ["사이클", "금리", "종합"]:
        status, detail = _safe_call(dartlab.macro, axis)
        results[f"macro.{axis}"] = f"{status}{': ' + detail if detail else ''}"

    # search
    if not quick:
        status, detail = _safe_call(dartlab.search, "유상증자")
        results["search"] = f"{status}{': ' + detail if detail else ''}"

    # SuperMaster
    try:
        from dartlab.ai.superfeature import getSuperMaster

        master = getSuperMaster()
        api_text, example_text = master.gather("삼성전자 수익성")
        if api_text and "dartlab API" in api_text:
            results["SuperMaster.capability"] = "Pass"
        else:
            results["SuperMaster.capability"] = "Warning: empty"
        # experience는 처음엔 비어있을 수 있음
        results["SuperMaster.experience"] = "Pass" if example_text else "Warning: empty"
    except Exception as e:
        results["SuperMaster"] = f"Fail: {type(e).__name__}: {e}"

    fail_count = sum(1 for v in results.values() if v.startswith("Fail"))
    warn_count = sum(1 for v in results.values() if v.startswith("Warning"))
    overall = "Fail" if fail_count >= 2 else ("Warning" if fail_count + warn_count > 0 else "Pass")

    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "scope": "market",
        "results": results,
        "counts": {"fail": fail_count, "warning": warn_count, "total": len(results)},
        "overall": overall,
    }


def writeReport(outDir: Path, allResults: list[dict]) -> None:
    """JSON + 요약 md 저장."""
    outDir.mkdir(parents=True, exist_ok=True)
    # JSON
    (outDir / "results.json").write_text(
        json.dumps(allResults, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 요약 md
    lines = [
        "# Engine Audit Report\n",
        f"**실행 시각**: {datetime.now().isoformat(timespec='seconds')}\n",
        f"**점검 대상**: {len(allResults)}개\n\n",
        "## 종합 등급\n",
        "| 대상 | overall | Fail | Warn | Duration |",
        "|---|:---:|---:|---:|---:|",
    ]
    for r in allResults:
        name = r.get("stockCode") or r.get("scope", "unknown")
        counts = r.get("counts", {})
        dur = r.get("duration_sec", 0)
        lines.append(f"| {name} | **{r['overall']}** | {counts.get('fail', 0)} | {counts.get('warning', 0)} | {dur}s |")

    lines.append("\n## 실패/경고 상세\n")
    for r in allResults:
        name = r.get("stockCode") or r.get("scope", "unknown")
        failures = {k: v for k, v in r["results"].items() if v.startswith(("Fail", "Warning"))}
        if failures:
            lines.append(f"### {name}\n")
            for k, v in failures.items():
                lines.append(f"- **{k}**: {v}")
            lines.append("")

    (outDir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="dartlab 엔진 기능 점검")
    parser.add_argument("--stock", help="단일 종목만 점검")
    parser.add_argument("--quick", action="store_true", help="핵심 체크만")
    parser.add_argument("--skip-market", action="store_true", help="시장 레벨 엔진 생략")
    args = parser.parse_args()

    allResults: list[dict] = []

    # 종목별 점검 (순차 — dartlab import 메모리 이슈)
    stocks = [(args.stock, "-", "-")] if args.stock else _STOCKS
    for code, name, market in stocks:
        print(f"\n=== {code} ({name}, {market}) ===")
        try:
            result = auditCompany(code, quick=args.quick)
            allResults.append(result)
            print(
                f"  {result['overall']} — fail={result['counts']['fail']}, warn={result['counts']['warning']}, {result['duration_sec']}s"
            )
        except Exception as e:
            print(f"  CRITICAL: {type(e).__name__}: {e}")
            allResults.append(
                {
                    "stockCode": code,
                    "results": {"Company.create": f"Fail: {type(e).__name__}: {e}"},
                    "counts": {"fail": 1, "warning": 0, "total": 1},
                    "overall": "Fail",
                }
            )

    # 시장 레벨
    if not args.skip_market:
        print("\n=== Market-level (scan/macro/search/SuperMaster) ===")
        try:
            market_result = auditMarketLevel(quick=args.quick)
            allResults.append(market_result)
            print(
                f"  {market_result['overall']} — fail={market_result['counts']['fail']}, warn={market_result['counts']['warning']}"
            )
        except Exception as e:
            print(f"  CRITICAL: {type(e).__name__}: {e}")

    # 저장
    date = datetime.now().strftime("%Y-%m-%d")
    outDir = Path("data/audit/engine") / date
    writeReport(outDir, allResults)
    print(f"\n리포트: {outDir / 'report.md'}")

    # exit code: Fail 있으면 1
    overall_fail = any(r["overall"] == "Fail" for r in allResults)
    return 1 if overall_fail else 0


if __name__ == "__main__":
    sys.exit(main())
