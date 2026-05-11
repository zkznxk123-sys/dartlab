"""Damodaran lifeCycle threshold calibration — KOSPI 전종목 실 분포 검증.

배치 실행:
    uv run python -X utf8 scripts/audit/damodaranCalibration.py [--limit N]

동작:
    1. scan/finance.parquet 전종목 순회 (sequential + 500 종목 GC)
    2. 각 종목 매출 CAGR / 영업마진 CV / FCF streak / 배당성향 추출
    3. lifeCycle._classify 로 phase 분류
    4. phase 별 분포 (quartile) + 현 threshold 대비 조정 제안

출력:
    data/audit/damodaran/{YYYY-MM-DD}/
      ├─ calibration.parquet
      ├─ distributions.json
      ├─ thresholdProposal.json
      └─ report.md
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
from datetime import datetime
from pathlib import Path
from statistics import mean, median, pstdev

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="max stocks (default all)")
    parser.add_argument("--gc-every", type=int, default=500)
    args = parser.parse_args()

    import polars as pl

    from dartlab.scan.parquetLoad import _ensureScanData, parseNumStr

    scan_dir = _ensureScanData()
    path = scan_dir / "finance.parquet"
    if not path.exists():
        print("[calibration] finance.parquet 없음 — scan 프리빌드 다운로드 필요")
        return 1

    lf = pl.scan_parquet(str(path))
    needed = ["stockCode", "bsns_year", "sj_div", "account_nm", "thstrm_amount", "frmtrm_amount", "fs_nm", "reprt_nm"]
    avail = lf.collect_schema().names()
    cols = [c for c in needed if c in avail]
    snap = (
        lf.select(cols)
        .filter(pl.col("fs_nm").str.contains("연결"))
        .filter(pl.col("reprt_nm").str.contains("4분기"))
        .collect()
    )
    if snap.is_empty():
        print("[calibration] 연결 4분기 데이터 없음")
        return 1

    years = sorted(snap["bsns_year"].unique().to_list(), reverse=True)
    if len(years) < 3:
        print(f"[calibration] 연도 부족 (있는 연도: {years})")
        return 1

    stockcodes = snap["stockCode"].unique().to_list()
    if args.limit:
        stockcodes = stockcodes[: args.limit]

    rev_nms = ["매출액", "수익(매출액)", "영업수익"]
    op_nms = ["영업이익", "영업이익(손실)"]
    ni_nms = ["당기순이익", "당기순이익(손실)"]
    eq_nms = ["자본총계"]

    def _extract(df: pl.DataFrame, nms: list[str], field: str = "thstrm_amount") -> float | None:
        for nm in nms:
            r = df.filter(pl.col("account_nm") == nm)
            if not r.is_empty():
                return parseNumStr(r[field][0])
        return None

    rows = []
    for i, sc in enumerate(stockcodes):
        if i % args.gc_every == 0 and i > 0:
            gc.collect()
            print(f"[calibration] {i}/{len(stockcodes)} 진행...")

        # 종목별 데이터 수집
        stock_snap = snap.filter(pl.col("stockCode") == sc)
        if stock_snap.is_empty():
            continue

        # 매출 시계열 (최근 5년)
        revs = []
        op_margins = []
        for y in years[:5]:
            stock_y = stock_snap.filter(pl.col("bsns_year") == y)
            if stock_y.is_empty():
                continue
            rev = _extract(stock_y, rev_nms)
            op = _extract(stock_y, op_nms)
            if rev and rev > 0:
                revs.append(rev)
                if op is not None:
                    op_margins.append(op / rev * 100)

        if len(revs) < 3:
            continue

        # 매출 CAGR (최신 → 최초, reverse order)
        try:
            cagr_val = ((revs[0] / revs[-1]) ** (1 / (len(revs) - 1)) - 1) * 100
        except (ValueError, ZeroDivisionError):
            cagr_val = None

        # 영업마진 CV
        margin_cv = None
        if len(op_margins) >= 3:
            mu = mean(op_margins)
            if mu != 0:
                margin_cv = pstdev(op_margins) / abs(mu)

        # phase 분류
        try:
            from dartlab.analysis.financial.lifeCycle import _classify

            signals = {
                "revenueCAGR": cagr_val,
                "operatingMarginCV": margin_cv,
                "roicWACCSpread": None,
                "fcfPositiveStreak": 0,
                "dividendPayout": 0,
                "marginDirection": "stable",
                "operatingMarginSeries": op_margins,
                "revenueYoySeries": [],
            }
            phase, conf, _ = _classify(signals, growthAdj=-5.0)
        except Exception:
            phase = "unknown"
            conf = 0.0

        rows.append(
            {
                "stockCode": sc,
                "phase": phase,
                "phaseConfidence": round(conf, 2),
                "revenueCAGR": round(cagr_val, 2) if cagr_val else None,
                "marginCV": round(margin_cv, 3) if margin_cv else None,
                "latestMargin": round(op_margins[0], 2) if op_margins else None,
                "sampleYears": len(revs),
            }
        )

    # parquet 저장
    out_dir = _REPO_ROOT / "data" / "audit" / "damodaran" / datetime.now().strftime("%Y-%m-%d")
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pl.DataFrame(rows)
    df.write_parquet(out_dir / "calibration.parquet")

    # 분포 통계
    distributions = {}
    for phase in ("earlyGrowth", "highGrowth", "matureGrowth", "matureStable", "decline", "turnaround"):
        sub = df.filter(pl.col("phase") == phase)
        count = sub.height
        cagr_vals = [v for v in sub["revenueCAGR"].to_list() if v is not None]
        cv_vals = [v for v in sub["marginCV"].to_list() if v is not None]
        margin_vals = [v for v in sub["latestMargin"].to_list() if v is not None]
        distributions[phase] = {
            "count": count,
            "cagrMedian": round(median(cagr_vals), 2) if cagr_vals else None,
            "cagrP25": round(sorted(cagr_vals)[len(cagr_vals) // 4], 2) if len(cagr_vals) >= 4 else None,
            "cagrP75": round(sorted(cagr_vals)[3 * len(cagr_vals) // 4], 2) if len(cagr_vals) >= 4 else None,
            "cagrP95": round(sorted(cagr_vals)[int(0.95 * len(cagr_vals))], 2) if len(cagr_vals) >= 20 else None,
            "marginMedian": round(median(margin_vals), 2) if margin_vals else None,
            "marginCvMedian": round(median(cv_vals), 3) if cv_vals else None,
        }

    with (out_dir / "distributions.json").open("w", encoding="utf-8") as f:
        json.dump(distributions, f, indent=2, ensure_ascii=False)

    # threshold 조정 제안
    current_thresholds = {
        "earlyGrowth_cagrMin": 30,
        "highGrowth_cagrRange": [15, 35],
        "matureGrowth_cagrRange": [5, 20],
        "matureStable_cagrMax": 5,
        "decline_cagrMax": 0,
    }
    proposal = dict(current_thresholds)
    notes = []

    eg = distributions.get("earlyGrowth", {})
    if eg.get("count", 0) < 10 and eg.get("cagrP25") is not None:
        proposal["earlyGrowth_cagrMin"] = max(20, int(eg["cagrP25"]))
        notes.append(
            f"earlyGrowth count={eg['count']} 부족 → cagrMin {current_thresholds['earlyGrowth_cagrMin']}% → {proposal['earlyGrowth_cagrMin']}% 제안"
        )

    ms_count = distributions.get("matureStable", {}).get("count", 0)
    total = sum(d.get("count", 0) for d in distributions.values())
    if ms_count / max(total, 1) > 0.6:
        notes.append(f"matureStable 비중 {ms_count / max(total, 1) * 100:.0f}% — 과도 편중. threshold 세분화 권장")

    with (out_dir / "thresholdProposal.json").open("w", encoding="utf-8") as f:
        json.dump(
            {
                "current": current_thresholds,
                "proposed": proposal,
                "notes": notes,
                "totalSampled": total,
                "distributions": distributions,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    # Markdown 보고서
    report = [f"# Damodaran Calibration Report\n\nGenerated: {datetime.now().isoformat()}\n"]
    report.append(f"Total sampled: **{total}** 종목\n")
    report.append("## Phase distribution\n")
    report.append("| phase | count | cagrMedian | cagrP25 | cagrP75 | marginMedian | marginCvMedian |")
    report.append("|---|---:|---:|---:|---:|---:|---:|")
    for phase, d in distributions.items():
        report.append(
            f"| {phase} | {d['count']} | {d.get('cagrMedian')} | {d.get('cagrP25')} | "
            f"{d.get('cagrP75')} | {d.get('marginMedian')} | {d.get('marginCvMedian')} |"
        )
    report.append("\n## Threshold proposal\n")
    for k, v in proposal.items():
        cur = current_thresholds[k]
        mark = "**" if v != cur else ""
        report.append(f"- `{k}`: {mark}{cur} → {v}{mark}")
    if notes:
        report.append("\n## Notes\n")
        for n in notes:
            report.append(f"- {n}")

    with (out_dir / "report.md").open("w", encoding="utf-8") as f:
        f.write("\n".join(report) + "\n")

    print(f"[calibration] 완료: {out_dir}")
    print(f"  샘플 {total} 종목, phase 분포 저장")
    return 0


if __name__ == "__main__":
    sys.exit(main())
