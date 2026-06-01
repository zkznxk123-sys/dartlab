"""panel 수평화 정밀 전수 census — 2단계 누락 0 검증 (zip→parquet→panel() 무손실).

사용자 요청: "zip 에 있는게 panel 파케로 갈 때 하나라도 빠진 게 있는지, panel 파케에서 panel 호출
수평화할 때 하나라도 빠진 게 있는지" 정밀 점검. 본 census 는 ``data/dart/panel/{code}/`` 종목별로:

    1. **parquet→grid 손실 (stage b)**: parquet 모든 행의 contentRaw(strip)가 ``readWide`` 격자에
       surface 하는지. 수평화 pivot 이 행을 묵음 드롭하면 검출. ``content_dropped`` = **버그 신호**.
    2. **주석 de-chunk 연속성**: 과거 연간(2023 이전 Q4)이 ``NT_*`` 주석을 갖는지 (옛 덩어리 분해 적용률).
       ``note_discontinuous`` (과거연간 있는데 NT_* 0) = **버그 신호**.
    3. **잔여 미분해 덩어리**: disclosureKey null 주석 섹션 수 (택소노미 미등재 헤더 — 소수 정상).

zip→parquet(stage a)는 walker 가 손실0 by construction(빈/rogue element 만 skip) + de-chunk 보존
99~102% 실측 — 전수 재현은 빌드 자체라, 본 census 는 그 산출물(parquet)의 무손실을 검증한다.

사용법::

    uv run python -X utf8 tests/audit/panelHorizonCensus.py                 # 전종목
    uv run python -X utf8 tests/audit/panelHorizonCensus.py --codes 005930,000660
    uv run python -X utf8 tests/audit/panelHorizonCensus.py --limit 200 --workers 4

종료 코드: 0 (보고용). --strict 면 content_dropped/note_discontinuous 발견 시 1.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import re
import sys
from pathlib import Path

import dartlab.config as _cfg

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_PROBE = 60  # surface 판정 prefix 길이
_MIN = 8  # 무시할 최소 strip 길이


def _strip(s: str | None) -> str:
    return _WS.sub(" ", _TAG.sub(" ", s or "")).strip()


def _censusOne(code: str) -> dict:
    """종목 1개 — parquet→grid 손실 + 주석 연속성 + 잔여 덩어리 집계."""
    import polars as pl

    from dartlab.providers.dart.panel import read as R

    panelDir = Path(_cfg.dataDir) / "dart" / "panel" / code
    files = sorted(panelDir.glob("*.parquet")) if panelDir.exists() else []
    rec: dict = {
        "code": code,
        "periods": len(files),
        "parquetRows": 0,
        "uncovered": 0,
        "annualPre2023": 0,
        "ntPeriodsPre2023": 0,
        "residualChunks": 0,
        "issues": [],
    }
    if not files:
        rec["issues"].append("no_panel")
        return rec

    grid = R.readWide(code, tag=False)
    if grid is None or grid.is_empty():
        rec["issues"].append("no_grid")
        return rec
    pcols = [c for c in grid.columns if c[:4].isdigit()]
    gridText = {p: " ".join(v for v in grid[p].to_list() if v) for p in pcols}

    sample: list[str] = []
    for f in files:
        period = f.stem
        try:
            year = int(period[:4])
        except ValueError:
            continue
        df = pl.read_parquet(str(f), columns=["contentRaw", "disclosureKey", "sectionLeaf"])
        nt = df.filter(pl.col("disclosureKey").str.starts_with("NT_"))
        rec["residualChunks"] += df.filter(
            pl.col("disclosureKey").is_null() & pl.col("sectionLeaf").str.contains("주석")
        ).height
        if year < 2023 and period.endswith("Q4"):
            rec["annualPre2023"] += 1
            if nt.height > 0:
                rec["ntPeriodsPre2023"] += 1
        # stage b — parquet 행 content 가 grid period 텍스트에 surface 하는지
        gt = gridText.get(period, "")
        for cr in df["contentRaw"].to_list():
            st = _strip(cr)
            if len(st) < _MIN:
                continue
            rec["parquetRows"] += 1
            if st[:_PROBE] not in gt:
                rec["uncovered"] += 1
                if len(sample) < 3:
                    sample.append(f"{period}:{st[:40]}")

    if rec["uncovered"] > 0:
        rec["issues"].append("content_dropped")
        rec["sample"] = sample
    if rec["annualPre2023"] > 0 and rec["ntPeriodsPre2023"] == 0:
        rec["issues"].append("note_discontinuous")
    return rec


def _listCodes(limit: int | None) -> list[str]:
    base = Path(_cfg.dataDir) / "dart" / "panel"
    codes = sorted(d.name for d in base.iterdir() if d.is_dir() and d.name != "spine")
    return codes[:limit] if limit else codes


def main() -> int:
    ap = argparse.ArgumentParser(description="panel 수평화 정밀 전수 census")
    ap.add_argument("--codes", type=str, default="", help="콤마구분 종목코드. 빈값=전종목")
    ap.add_argument("--limit", type=int, default=None, help="앞 N 종목만")
    ap.add_argument("--workers", type=int, default=4, help="multiprocessing workers")
    ap.add_argument("--out", type=str, default="dist/panelHorizon_census.json", help="결과 JSON")
    ap.add_argument("--strict", action="store_true", help="content_dropped/note_discontinuous 시 exit 1")
    args = ap.parse_args()

    codes = [c.strip() for c in args.codes.split(",") if c.strip()] or _listCodes(args.limit)
    print(f"[horizonCensus] {len(codes)} 종목, {args.workers} workers")

    if args.workers > 1 and len(codes) > 1:
        with mp.Pool(processes=args.workers) as pool:
            recs = pool.map(_censusOne, codes)
    else:
        recs = [_censusOne(c) for c in codes]

    dropped = [r for r in recs if "content_dropped" in r["issues"]]
    discont = [r for r in recs if "note_discontinuous" in r["issues"]]
    noPanel = [r for r in recs if "no_panel" in r["issues"] or "no_grid" in r["issues"]]
    withPre = [r for r in recs if r["annualPre2023"] > 0]
    applied = [r for r in withPre if r["ntPeriodsPre2023"] > 0]
    parquetRows = sum(r["parquetRows"] for r in recs)
    uncovered = sum(r["uncovered"] for r in recs)

    print(f"\n=== panel 수평화 census ({len(codes)} 종목) ===")
    print("  [stage b] parquet→grid:")
    print(
        f"    총 parquet 행 {parquetRows:,} | grid 미surface {uncovered:,} ({100 * uncovered / max(parquetRows, 1):.3f}%)"
    )
    print(f"    content_dropped 종목: {len(dropped)}")
    print("  [주석 de-chunk]:")
    print(f"    과거연간 보유 {len(withPre)} | 적용 {len(applied)} ({100 * len(applied) / max(len(withPre), 1):.1f}%)")
    print(f"    note_discontinuous: {len(discont)} | no_panel/grid: {len(noPanel)}")
    if dropped:
        print(f"  ⚠ content_dropped(앞10): {[(r['code'], r['uncovered']) for r in dropped[:10]]}")
    if discont:
        print(f"  ⚠ note_discontinuous(앞20): {[r['code'] for r in discont[:20]]}")

    outPath = Path(args.out)
    outPath.parent.mkdir(parents=True, exist_ok=True)
    outPath.write_text(
        json.dumps(
            {
                "total": len(codes),
                "parquetRows": parquetRows,
                "uncovered": uncovered,
                "contentDropped": [r["code"] for r in dropped],
                "noteDiscontinuous": [r["code"] for r in discont],
                "noPanel": [r["code"] for r in noPanel],
                "records": recs,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"  → {outPath}")

    return 1 if (args.strict and (dropped or discont)) else 0


if __name__ == "__main__":
    sys.exit(main())
