"""전 엔진 데이터 전수조사 — 208호출 품질 검증.

모든 엔진의 모든 축을 실제로 호출하여 반환값의
품질, 이상, 컬럼 일관성, None 패턴을 체계적으로 검증.

실행:
    uv run python -X utf8 tests/audit/dataQualityAudit.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# ── 설정 ──

STOCKS = ["005930", "005380", "035420"]  # 삼성전자, 현대차, NAVER

TOPICS_FINANCE = ["IS", "BS", "CF", "CIS", "SCE", "ratios"]  # ratioSeries는 의도적 None (dict 구조)
TOPICS_NOTES = [
    "inventory",
    "borrowings",
    "tangibleAsset",
    "intangibleAsset",
    "receivables",
    "provisions",
    "eps",
    "lease",
    "costByNature",
    "segments",
    "affiliates",
]

ANALYSIS_AXES = [
    "수익구조",
    "자금조달",
    "자산구조",
    "현금흐름",
    "수익성",
    "성장성",
    "안정성",
    "효율성",
    "종합평가",
    "이익품질",
    "비용구조",
    "자본배분",
    "투자효율",
    "재무정합성",
]

REVIEW_SECTIONS = [
    "수익구조",
    "성장성",
    "수익성",
    "비용구조",
    "현금흐름",
    "이익품질",
    "자금조달",
    "안정성",
    "자산구조",
    "효율성",
    "종합평가",
    "자본배분",
    "투자효율",
    "재무정합성",
    "가치평가",
    "매출전망",
    "비교분석",
    "시장분석",
    "신용평가",
    "지배구조",
]

SCAN_AXES = [
    "profitability",
    "growth",
    "quality",
    "liquidity",
    "efficiency",
    "cashflow",
    "dividendTrend",
    "capital",
    "debt",
    "valuation",
]

MACRO_AXES = ["사이클", "금리", "자산", "심리", "유동성", "종합"]

OUT_DIR = Path(__file__).resolve().parent
REPORT_PATH = OUT_DIR / "dataQualityReport.json"
ISSUES_PATH = OUT_DIR / "dataQualityIssues.json"


# ── 유틸 ──


def _inspectResult(result) -> dict:
    """반환값 메트릭 추출."""
    import polars as pl

    if result is None:
        return {"returnType": "None", "rowCount": 0, "colCount": 0, "noneRatio": 1.0, "noneKeys": []}

    if isinstance(result, pl.DataFrame):
        rows, cols = result.shape
        noneCount = 0
        totalCells = rows * cols
        noneCols = []
        for c in result.columns:
            nulls = result[c].null_count()
            noneCount += nulls
            if nulls == rows and rows > 0:
                noneCols.append(c)
        noneRatio = noneCount / totalCells if totalCells > 0 else 0.0
        return {
            "returnType": "DataFrame",
            "rowCount": rows,
            "colCount": cols,
            "noneRatio": round(noneRatio, 4),
            "noneKeys": noneCols,
            "columns": result.columns[:20],
        }

    if isinstance(result, dict):
        totalKeys = len(result)
        noneKeys = [k for k, v in result.items() if v is None]
        noneRatio = len(noneKeys) / totalKeys if totalKeys > 0 else 0.0

        # 재귀적 None 탐지 (1 depth)
        deepNone = []
        for k, v in result.items():
            if isinstance(v, dict):
                for sk, sv in v.items():
                    if sv is None:
                        deepNone.append(f"{k}.{sk}")

        return {
            "returnType": "dict",
            "rowCount": totalKeys,
            "colCount": 0,
            "noneRatio": round(noneRatio, 4),
            "noneKeys": noneKeys[:20],
            "deepNoneKeys": deepNone[:20],
            "topKeys": list(result.keys())[:20],
        }

    if isinstance(result, list):
        return {"returnType": "list", "rowCount": len(result), "colCount": 0, "noneRatio": 0.0, "noneKeys": []}

    return {"returnType": type(result).__name__, "rowCount": 0, "colCount": 0, "noneRatio": 0.0, "noneKeys": []}


def _detectAnomalies(metrics: dict) -> list[str]:
    """이상 패턴 자동 탐지."""
    anomalies = []
    if metrics.get("noneRatio", 0) > 0.5:
        anomalies.append("data_sparse")
    if metrics.get("rowCount", 0) == 0 and metrics.get("returnType") not in ("None",):
        anomalies.append("empty_result")
    if metrics.get("returnType") == "None":
        anomalies.append("null_return")
    return anomalies


def _grade(metrics: dict, anomalies: list[str], engine: str = "") -> str:
    """PASS / WARN / FAIL 등급."""
    if "call_error" in anomalies:
        return "FAIL"
    # notes null_return = 해당 종목에 데이터 없음 (WARN, 버그 아님)
    if "null_return" in anomalies:
        return "WARN" if "notes" in engine or "company" in engine else "FAIL"
    if "empty_result" in anomalies:
        return "FAIL"
    if "data_sparse" in anomalies:
        return "WARN"
    if metrics.get("noneRatio", 0) > 0.3:
        return "WARN"
    return "PASS"


def _callSafe(fn, *args, engine: str = "", **kwargs) -> dict:
    """안전한 호출 + 메트릭 수집."""
    start = time.monotonic()
    try:
        result = fn(*args, **kwargs)
        elapsed = time.monotonic() - start
        metrics = _inspectResult(result)
        anomalies = _detectAnomalies(metrics)
        grade = _grade(metrics, anomalies, engine=engine)
        return {
            "status": "ok" if result is not None else "none",
            **metrics,
            "duration": round(elapsed, 2),
            "error": None,
            "anomalies": anomalies,
            "grade": grade,
        }
    except Exception as e:
        elapsed = time.monotonic() - start
        return {
            "status": "error",
            "returnType": "error",
            "rowCount": 0,
            "colCount": 0,
            "noneRatio": 0,
            "noneKeys": [],
            "duration": round(elapsed, 2),
            "error": f"{type(e).__name__}: {e}",
            "anomalies": ["call_error"],
            "grade": "FAIL",
        }


# ── 엔진별 수집 ──


def auditCompany(stockCode: str) -> list[dict]:
    """Company show/select 전수조사."""
    import dartlab

    results = []
    c = dartlab.Company(stockCode)

    # finance topics
    for topic in TOPICS_FINANCE:
        r = _callSafe(c.show, topic, engine="company.show")
        results.append({"engine": "company.show", "axis": topic, "stockCode": stockCode, **r})

    # notes topics
    for topic in TOPICS_NOTES:
        r = _callSafe(c.show, topic, engine="company.notes")
        results.append({"engine": "company.notes", "axis": topic, "stockCode": stockCode, **r})

    return results


def auditAnalysis(stockCode: str) -> list[dict]:
    """Analysis financial 전수조사."""
    import dartlab

    results = []
    c = dartlab.Company(stockCode)

    for axis in ANALYSIS_AXES:
        r = _callSafe(c.analysis, "financial", axis)
        results.append({"engine": "analysis.financial", "axis": axis, "stockCode": stockCode, **r})

    # forecast + valuation
    for group, axis in [("forecast", "매출전망"), ("valuation", "가치평가")]:
        r = _callSafe(c.analysis, group, axis)
        results.append({"engine": f"analysis.{group}", "axis": axis, "stockCode": stockCode, **r})

    return results


def auditStory(stockCode: str) -> list[dict]:
    """Story 섹션별 전수조사."""
    import dartlab

    results = []
    c = dartlab.Company(stockCode)

    for section in REVIEW_SECTIONS:
        r = _callSafe(c.story, section)
        results.append({"engine": "story", "axis": section, "stockCode": stockCode, **r})

    return results


CREDIT_AXES = ["공시리스크", "사업안정성", "유동성", "자본구조", "재무신뢰성", "채무상환", "현금흐름"]
QUANT_AXES = ["indicators", "volatility", "momentum", "OBV", "beta"]


def auditCredit(stockCode: str) -> list[dict]:
    """Credit 전수조사."""
    import dartlab

    results = []
    c = dartlab.Company(stockCode)

    # 종합
    r = _callSafe(c.credit)
    results.append({"engine": "credit", "axis": "종합", "stockCode": stockCode, **r})

    # 7축 상세
    for axis in CREDIT_AXES:
        r = _callSafe(c.credit, axis)
        results.append({"engine": "credit", "axis": axis, "stockCode": stockCode, **r})

    return results


def auditQuant(stockCode: str) -> list[dict]:
    """Quant 전수조사."""
    import dartlab

    results = []
    c = dartlab.Company(stockCode)

    # 종합
    r = _callSafe(c.quant)
    results.append({"engine": "quant", "axis": "종합", "stockCode": stockCode, **r})

    # 개별 축
    for axis in QUANT_AXES:
        r = _callSafe(c.quant, axis)
        results.append({"engine": "quant", "axis": axis, "stockCode": stockCode, **r})

    return results


def auditGather(stockCode: str) -> list[dict]:
    """Gather 전수조사."""
    import dartlab

    results = []
    c = dartlab.Company(stockCode)

    for axis in ["price", "flow"]:
        r = _callSafe(c.gather, axis)
        results.append({"engine": "gather", "axis": axis, "stockCode": stockCode, **r})

    return results


def auditScan() -> list[dict]:
    """Scan 전수조사 (시장 레벨)."""
    import dartlab

    results = []
    for axis in SCAN_AXES:
        r = _callSafe(dartlab.scan, axis)
        results.append({"engine": "scan", "axis": axis, "stockCode": "market", **r})

    return results


def auditMacro() -> list[dict]:
    """Macro 전수조사 (종목 불필요)."""
    import dartlab

    results = []
    for axis in MACRO_AXES:
        r = _callSafe(dartlab.macro, axis)
        results.append({"engine": "macro", "axis": axis, "stockCode": "market", **r})

    return results


# ── 메인 ──


def main():
    """그룹별 실행. --group + --engine으로 분리.

    전체 (subprocess 분리): python dataQualityAudit.py
    단일 그룹: python dataQualityAudit.py --group 005930 --engine company
    """
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default="all")
    ap.add_argument("--engine", default="all")
    args = ap.parse_args()

    # all → subprocess 분리 실행
    if args.group == "all":
        import subprocess

        script = str(Path(__file__).resolve())
        partial = OUT_DIR / "_partial"
        partial.mkdir(exist_ok=True)

        # 실행 단위 정의
        units = [
            ("market", "scan"),
            ("market", "macro"),
        ]
        for stock in STOCKS:
            for eng in ["company", "analysis", "story", "credit", "quant", "gather"]:
                units.append((stock, eng))

        allResults: list[dict] = []
        for grp, eng in units:
            print(f"=== {grp} / {eng} ===")
            out = partial / f"{grp}_{eng}.json"
            cmd = [sys.executable, "-X", "utf8", script, "--group", grp, "--engine", eng]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if out.exists():
                chunk = json.loads(out.read_text(encoding="utf-8"))
                allResults.extend(chunk)
                print(f"  {len(chunk)}건 수집")
            else:
                print(f"  실패: {proc.stderr[-200:] if proc.stderr else 'no output'}")

        _writeResults(allResults)
        return

    # 단일 그룹+엔진 실행
    results: list[dict] = []

    if args.group == "market":
        if args.engine in ("all", "scan"):
            results.extend(auditScan())
        if args.engine in ("all", "macro"):
            results.extend(auditMacro())
    else:
        stockCode = args.group
        if args.engine in ("all", "company"):
            results.extend(auditCompany(stockCode))
        if args.engine in ("all", "analysis"):
            results.extend(auditAnalysis(stockCode))
        if args.engine in ("all", "story"):
            results.extend(auditStory(stockCode))
        if args.engine in ("all", "credit"):
            results.extend(auditCredit(stockCode))
        if args.engine in ("all", "quant"):
            results.extend(auditQuant(stockCode))
        if args.engine in ("all", "gather"):
            results.extend(auditGather(stockCode))

    # partial 저장
    partial = OUT_DIR / "_partial"
    partial.mkdir(exist_ok=True)
    outFile = partial / f"{args.group}_{args.engine}.json"
    outFile.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  {len(results)}건 → {outFile.name}")


def _writeResults(allResults: list[dict]):
    """최종 결과 저장 + 요약."""
    total = len(allResults)

    # 결과 저장
    REPORT_PATH.write_text(json.dumps(allResults, ensure_ascii=False, indent=2), encoding="utf-8")

    # 이슈만 추출
    issues = [r for r in allResults if r["grade"] != "PASS"]
    ISSUES_PATH.write_text(json.dumps(issues, ensure_ascii=False, indent=2), encoding="utf-8")

    # 요약
    print(f"\n{'=' * 60}")
    print(f"전수조사 완료: {total}건")
    grades = {"PASS": 0, "WARN": 0, "FAIL": 0}
    for r in allResults:
        grades[r["grade"]] = grades.get(r["grade"], 0) + 1
    print(f"  PASS: {grades['PASS']}")
    print(f"  WARN: {grades['WARN']}")
    print(f"  FAIL: {grades['FAIL']}")

    # 엔진별 요약
    engines: dict[str, dict[str, int]] = {}
    for r in allResults:
        eng = r["engine"]
        if eng not in engines:
            engines[eng] = {"PASS": 0, "WARN": 0, "FAIL": 0}
        engines[eng][r["grade"]] = engines[eng].get(r["grade"], 0) + 1

    print("\n엔진별:")
    for eng, g in sorted(engines.items()):
        print(f"  {eng:25s}  PASS={g['PASS']:3d}  WARN={g['WARN']:3d}  FAIL={g['FAIL']:3d}")

    # FAIL 상세
    fails = [r for r in allResults if r["grade"] == "FAIL"]
    if fails:
        print(f"\n FAIL 상세 ({len(fails)}건):")
        for f in fails[:30]:
            err = f.get("error", "")
            anoms = ", ".join(f.get("anomalies", []))
            print(f"  {f['engine']:25s} {f['axis']:15s} {f['stockCode']}  {anoms}  {err[:60] if err else ''}")

    print(f"\n결과: {REPORT_PATH}")
    print(f"이슈: {ISSUES_PATH}")


if __name__ == "__main__":
    main()
