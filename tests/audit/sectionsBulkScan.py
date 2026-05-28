"""sections 이상 종목 빠른 점검 — 100 종목 sample 의 parity + row metric 자동 식별.

목적: 30 종목 sectionsParity 통과 후 *그 외* 종목 에서 회귀/이상 패턴 잡기.

검사:
1. parity 3 검사 (fragmentHeadings / chapterMix / koreanInversions) — 회귀 = fail
2. row count outlier — companyOverview / businessOverview 별 row 수가
   median 의 3× 이상 / 0.3× 이하
3. dup excess outlier — group_by (path, blockType) 의 같은-row 중복이 비정상

실행: uv run python -X utf8 tests/audit/sectionsBulkScan.py --sample 100 --seed 42

성공 = parity 0 violations 전 종목 + row outlier 0 (정상 분포).
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path
from statistics import median, quantiles

import polars as pl

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

DOCS_DIR = REPO_ROOT / "data" / "dart" / "docs"


def discoverCodes() -> list[str]:
    return sorted(p.stem for p in DOCS_DIR.glob("*.parquet"))


def measureCode(code: str) -> dict:
    from dartlab.providers.dart import Company
    from dartlab.providers.dart.docs.sectionsLegacy.pipeline import clearPreparedCache
    from tests.audit.sectionsParity import auditCode

    try:
        t0 = time.time()
        result = auditCode(code)
        elapsed = time.time() - t0

        c = Company(code)
        sec = c.sections
        if sec is None:
            return {"code": code, "elapsed": elapsed, "error": "sections None"}

        topicMetrics: dict[str, dict[str, int]] = {}
        for topic in ["companyOverview", "businessOverview"]:
            df = sec.filter(pl.col("topic") == topic)
            if df.shape[0] == 0:
                topicMetrics[topic] = {"rows": 0, "dupExcess": 0}
                continue
            g = (
                df.group_by(["textSemanticPathKey", "blockType", "textNodeType"])
                .agg(pl.len().alias("n"))
                .filter(pl.col("n") > 1)
            )
            excess = g.select(pl.col("n").sum() - pl.len()).item() if g.shape[0] > 0 else 0
            topicMetrics[topic] = {"rows": df.shape[0], "dupExcess": int(excess)}

        clearPreparedCache(code)

        return {
            "code": code,
            "elapsed": elapsed,
            "totalRows": sec.height,
            "fragmentHeadings": len(result.get("fragmentHeadings", []) or []),
            "chapterMixes": len(result.get("chapterMixes", []) or []),
            "koreanInversions": len(result.get("koreanInversions", []) or []),
            "companyOverviewRows": topicMetrics["companyOverview"]["rows"],
            "companyOverviewDup": topicMetrics["companyOverview"]["dupExcess"],
            "businessOverviewRows": topicMetrics["businessOverview"]["rows"],
            "businessOverviewDup": topicMetrics["businessOverview"]["dupExcess"],
        }
    except Exception as exc:
        return {"code": code, "error": str(exc)[:100]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--codes", type=str, default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.codes:
        codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    else:
        allCodes = discoverCodes()
        random.seed(args.seed)
        codes = random.sample(allCodes, min(args.sample, len(allCodes)))

    print(f"[scan] {len(codes)} 종목 sample (seed={args.seed})")
    results: list[dict] = []
    t0 = time.time()
    for i, code in enumerate(codes, 1):
        r = measureCode(code)
        results.append(r)
        elapsed = time.time() - t0
        eta = elapsed / i * (len(codes) - i)
        status = (
            "ERR"
            if "error" in r
            else "OK"
            if (
                r.get("fragmentHeadings", 0) == 0
                and r.get("chapterMixes", 0) == 0
                and r.get("koreanInversions", 0) == 0
            )
            else "FAIL"
        )
        print(
            f"  [{i:>3}/{len(codes)}] {code} {status} ({r.get('elapsed', 0):.1f}s) total={r.get('totalRows', '-')} ETA={eta:.0f}s"
        )
        sys.stdout.flush()

    # 분석
    fail = [
        r
        for r in results
        if r.get("fragmentHeadings", 0) > 0 or r.get("chapterMixes", 0) > 0 or r.get("koreanInversions", 0) > 0
    ]
    errors = [r for r in results if "error" in r]
    ok = [r for r in results if "error" not in r and r not in fail]

    print(f"\n=== SUMMARY ({len(codes)} codes) ===")
    print(f"OK: {len(ok)}, FAIL (parity): {len(fail)}, ERROR: {len(errors)}")

    if fail:
        print("\n[parity FAIL]")
        for r in fail[:10]:
            print(
                f"  {r['code']}: F={r.get('fragmentHeadings', 0)} C={r.get('chapterMixes', 0)} K={r.get('koreanInversions', 0)}"
            )

    if errors:
        print("\n[ERROR]")
        for r in errors[:10]:
            print(f"  {r['code']}: {r.get('error', '?')}")

    # row outlier
    if ok:
        coRows = [r["companyOverviewRows"] for r in ok if r.get("companyOverviewRows", 0) > 0]
        boRows = [r["businessOverviewRows"] for r in ok if r.get("businessOverviewRows", 0) > 0]
        if coRows:
            q1, q2, q3 = quantiles(coRows, n=4)
            iqr = q3 - q1
            upper = q3 + 3 * iqr
            lower = max(0, q1 - 3 * iqr)
            outliers = [
                r
                for r in ok
                if r.get("companyOverviewRows", 0) > upper
                or (r.get("companyOverviewRows", 0) > 0 and r["companyOverviewRows"] < lower)
            ]
            print(
                f"\n[companyOverview rows] median={int(q2)}, iqr=[{int(q1)},{int(q3)}], outlier bounds=[{int(lower)},{int(upper)}]"
            )
            if outliers:
                print(f"  outliers ({len(outliers)}):")
                for r in sorted(outliers, key=lambda x: -x["companyOverviewRows"])[:10]:
                    print(
                        f"    {r['code']}: {r['companyOverviewRows']} rows, dupExcess={r.get('companyOverviewDup', 0)}"
                    )
        if boRows:
            q1, q2, q3 = quantiles(boRows, n=4)
            iqr = q3 - q1
            upper = q3 + 3 * iqr
            lower = max(0, q1 - 3 * iqr)
            outliers = [
                r
                for r in ok
                if r.get("businessOverviewRows", 0) > upper
                or (r.get("businessOverviewRows", 0) > 0 and r["businessOverviewRows"] < lower)
            ]
            print(
                f"\n[businessOverview rows] median={int(q2)}, iqr=[{int(q1)},{int(q3)}], outlier bounds=[{int(lower)},{int(upper)}]"
            )
            if outliers:
                print(f"  outliers ({len(outliers)}):")
                for r in sorted(outliers, key=lambda x: -x["businessOverviewRows"])[:10]:
                    print(
                        f"    {r['code']}: {r['businessOverviewRows']} rows, dupExcess={r.get('businessOverviewDup', 0)}"
                    )

    # dup excess outlier
    if ok:
        dupExcessHigh = sorted(ok, key=lambda r: -(r.get("companyOverviewDup", 0) + r.get("businessOverviewDup", 0)))[
            :10
        ]
        print("\n[dup excess high-10]")
        for r in dupExcessHigh:
            print(f"  {r['code']}: co dup={r.get('companyOverviewDup', 0)}, bo dup={r.get('businessOverviewDup', 0)}")

    if args.json:
        outPath = REPO_ROOT / "tests" / "_attempts" / f"sectionsBulkScan_{args.seed}.json"
        outPath.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nJSON saved: {outPath}")

    return 0 if not fail and not errors else 1


if __name__ == "__main__":
    sys.exit(main())
