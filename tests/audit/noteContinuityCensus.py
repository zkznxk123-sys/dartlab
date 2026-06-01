"""주석 수평화 전수 census — 옛 "주석" 덩어리 de-chunk 가 2023 경계 넘어 정합되는지 검사.

2023 이전 보고서는 주석이 단일 "주석" 덩어리(disclosureKey 없음)였고, ``build.dechunkNotes`` 가 이를
항목별 ``NT_*`` 행으로 분해해 최근 itemized 주석과 같은 disclosureKey 로 수평화한다. 본 census 는
``data/dart/panel/{code}/`` 종목별로:
    - 과거 연간(2023 이전 Q4) period 수와 그 중 ``NT_*`` 주석 행을 가진 수 (de-chunk 적용률)
    - 잔여 미분해 덩어리 행 수 (sectionLeaf=="주석" & disclosureKey null — 헤더 미매칭분)
    - 재고자산 주석이 값을 갖는 연도 집합 (2023 경계 연속성 spot)

핵심 판정:
    - ``note_discontinuous``: 과거 연간이 있는데 ``NT_*`` 주석 0 = de-chunk 실패 (**버그 신호**, 0 이어야 정상).
    - ``residualChunks``: 잔여 덩어리 — 헤더 포맷 미매칭(소수 정상) 또는 택소노미 미등재.

사용법::

    uv run python -X utf8 tests/audit/noteContinuityCensus.py                 # 전종목
    uv run python -X utf8 tests/audit/noteContinuityCensus.py --codes 005930,000660
    uv run python -X utf8 tests/audit/noteContinuityCensus.py --limit 200 --workers 4

종료 코드: 0 (보고용). --strict 면 note_discontinuous 발견 시 1.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import sys
from pathlib import Path

import dartlab.config as _cfg


def _censusOne(code: str) -> dict:
    """종목 1개 census — period 별 NT_* 주석·잔여 덩어리·재고자산 연속성 집계."""
    import polars as pl

    panelDir = Path(_cfg.dataDir) / "dart" / "panel" / code
    files = sorted(panelDir.glob("*.parquet")) if panelDir.exists() else []
    rec: dict = {
        "code": code,
        "periods": len(files),
        "annualPre2023": 0,
        "ntPeriodsPre2023": 0,
        "residualChunks": 0,
        "notesTotal": 0,
        "invYears": [],
        "issues": [],
    }
    if not files:
        rec["issues"].append("no_panel")
        return rec

    invYears: set[int] = set()
    for f in files:
        period = f.stem  # 예: 2015Q4
        try:
            year = int(period[:4])
        except ValueError:
            continue
        df = pl.read_parquet(str(f), columns=["disclosureKey", "sectionLeaf", "blockLeaf"])
        nt = df.filter(pl.col("disclosureKey").str.starts_with("NT_"))
        rec["notesTotal"] += nt.height
        rec["residualChunks"] += df.filter((pl.col("sectionLeaf") == "주석") & pl.col("disclosureKey").is_null()).height
        if year < 2023 and period.endswith("Q4"):  # 과거 연간 (de-chunk 대상 구간)
            rec["annualPre2023"] += 1
            if nt.height > 0:
                rec["ntPeriodsPre2023"] += 1
        if nt.filter(pl.col("blockLeaf").str.contains("재고자산")).height:
            invYears.add(year)

    rec["invYears"] = sorted(invYears)
    # 과거 연간이 존재하는데 NT_* 주석이 전무 = de-chunk 미적용 (버그 신호)
    if rec["annualPre2023"] > 0 and rec["ntPeriodsPre2023"] == 0:
        rec["issues"].append("note_discontinuous")
    return rec


def _listCodes(limit: int | None) -> list[str]:
    base = Path(_cfg.dataDir) / "dart" / "panel"
    codes = sorted(d.name for d in base.iterdir() if d.is_dir() and d.name != "spine")
    return codes[:limit] if limit else codes


def main() -> int:
    ap = argparse.ArgumentParser(description="주석 수평화(de-chunk) 전수 census")
    ap.add_argument("--codes", type=str, default="", help="콤마구분 종목코드. 빈값=전종목")
    ap.add_argument("--limit", type=int, default=None, help="앞 N 종목만")
    ap.add_argument("--workers", type=int, default=4, help="multiprocessing workers")
    ap.add_argument("--out", type=str, default="dist/noteContinuity_census.json", help="결과 JSON")
    ap.add_argument("--strict", action="store_true", help="note_discontinuous 발견 시 exit 1")
    args = ap.parse_args()

    codes = [c.strip() for c in args.codes.split(",") if c.strip()] or _listCodes(args.limit)
    print(f"[noteCensus] {len(codes)} 종목, {args.workers} workers")

    if args.workers > 1 and len(codes) > 1:
        with mp.Pool(processes=args.workers) as pool:
            recs = pool.map(_censusOne, codes)
    else:
        recs = [_censusOne(c) for c in codes]

    discont = [r for r in recs if "note_discontinuous" in r["issues"]]
    noPanel = [r for r in recs if "no_panel" in r["issues"]]
    withPre = [r for r in recs if r["annualPre2023"] > 0]
    applied = [r for r in withPre if r["ntPeriodsPre2023"] > 0]
    notesTotal = sum(r["notesTotal"] for r in recs)
    residualTotal = sum(r["residualChunks"] for r in recs)

    print(f"\n=== 주석 수평화 census ({len(codes)} 종목) ===")
    print(f"  과거연간 보유 종목: {len(withPre)}")
    print(f"  de-chunk 적용(과거연간 NT_* 보유): {len(applied)}  ({100 * len(applied) / max(len(withPre), 1):.1f}%)")
    print(f"  note_discontinuous (과거연간 있는데 NT_* 0): {len(discont)}")
    print(f"  no_panel: {len(noPanel)}")
    print(f"  총 NT_* 주석 행: {notesTotal:,} | 잔여 미분해 덩어리: {residualTotal:,}")
    if discont:
        print(f"  ⚠ 불연속 종목(앞20): {[r['code'] for r in discont[:20]]}")

    outPath = Path(args.out)
    outPath.parent.mkdir(parents=True, exist_ok=True)
    outPath.write_text(
        json.dumps(
            {
                "total": len(codes),
                "withPre2023": len(withPre),
                "applied": len(applied),
                "discontinuous": [r["code"] for r in discont],
                "noPanel": [r["code"] for r in noPanel],
                "notesTotal": notesTotal,
                "residualTotal": residualTotal,
                "records": recs,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"  → {outPath}")

    return 1 if (args.strict and discont) else 0


if __name__ == "__main__":
    sys.exit(main())
