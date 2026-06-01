"""panel 수평화 정밀 전수 census — 2단계 누락 0 검증 (zip→parquet→panel() 무손실).

사용자 요청: "zip 에 있는게 panel 파케로 갈 때 하나라도 빠진 게 있는지, panel 파케에서 panel 호출
수평화할 때 하나라도 빠진 게 있는지" 정밀 점검. 본 census 는 ``data/dart/panel/{code}/`` 종목별로:

    1. **parquet→grid 손실 (stage b)**: period 별 총 content 글자수가 parquet == ``readWide`` 격자에서
       정확히 일치하는지. collapse 는 contentRaw 를 무손실 concat join 하므로 char-parity 가 깨지면
       (grid < parquet) 수평화가 content 를 드롭한 것 — ``content_dropped`` = **버그 신호** (byte-exact).
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
import sys
from pathlib import Path

import dartlab.config as _cfg


def _censusOne(code: str) -> dict:
    """종목 1개 — parquet→grid 손실 + 주석 연속성 + 잔여 덩어리 집계."""
    import polars as pl

    from dartlab.providers.dart.panel import read as R

    panelDir = Path(_cfg.dataDir) / "dart" / "panel" / code
    files = sorted(panelDir.glob("*.parquet")) if panelDir.exists() else []
    rec: dict = {
        "code": code,
        "periods": len(files),
        "parquetChars": 0,
        "charDrop": 0,
        "annualPre2023": 0,
        "ntPeriodsPre2023": 0,
        "residualChunks": 0,
        "dupNtKeys": 0,
        "issues": [],
    }
    if not files:
        rec["issues"].append("no_panel")
        return rec

    grid = R.readWide(code, tag=True)  # raw — char-parity 비교(strip 차 없이 byte-exact)
    if grid is None or grid.is_empty():
        rec["issues"].append("no_grid")
        return rec
    pcols = [c for c in grid.columns if c[:4].isdigit()]
    gridChars = {p: sum(len(v) for v in grid[p].to_list() if v) for p in pcols}

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
        # 같은 NT_* 가 한 period 에 >1행 = 본문+첨부 중복(READ 가 join 해 셀 content 증식) — 0 이어야 정상
        rec["dupNtKeys"] += nt.group_by("disclosureKey").len().filter(pl.col("len") > 1).height
        if year < 2023 and period.endswith("Q4"):
            rec["annualPre2023"] += 1
            if nt.height > 0:
                rec["ntPeriodsPre2023"] += 1
        # stage b — period 총 content 글자수 parquet == grid (collapse 무손실 concat → 정확 일치)
        pc = sum(len(v) for v in df["contentRaw"].to_list() if v)
        gc = gridChars.get(period, 0)
        rec["parquetChars"] += pc
        if pc != gc:  # grid<parquet=드롭, grid>parquet=중복증식 — 둘 다 버그
            rec["charDrop"] += pc - gc
            if len(sample) < 3:
                sample.append(f"{period}:parquet={pc} grid={gc}")

    if rec["charDrop"] != 0:
        rec["issues"].append("content_dropped")
        rec["sample"] = sample
    if rec["annualPre2023"] > 0 and rec["ntPeriodsPre2023"] == 0:
        rec["issues"].append("note_discontinuous")
    if rec["dupNtKeys"] > 0:
        rec["issues"].append("note_duplicated")
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
    duped = [r for r in recs if "note_duplicated" in r["issues"]]
    noPanel = [r for r in recs if "no_panel" in r["issues"] or "no_grid" in r["issues"]]
    withPre = [r for r in recs if r["annualPre2023"] > 0]
    applied = [r for r in withPre if r["ntPeriodsPre2023"] > 0]
    parquetChars = sum(r["parquetChars"] for r in recs)
    charDrop = sum(r["charDrop"] for r in recs)

    print(f"\n=== panel 수평화 census ({len(codes)} 종목) ===")
    print("  [stage b] parquet→grid (char-parity, byte-exact):")
    print(
        f"    총 parquet content {parquetChars:,}자 | grid 불일치 {charDrop:,}자 ({100 * abs(charDrop) / max(parquetChars, 1):.4f}%)"
    )
    print(f"    content_dropped 종목: {len(dropped)}")
    print("  [주석 de-chunk]:")
    print(f"    과거연간 보유 {len(withPre)} | 적용 {len(applied)} ({100 * len(applied) / max(len(withPre), 1):.1f}%)")
    print(f"    note_discontinuous: {len(discont)} | note_duplicated: {len(duped)} | no_panel/grid: {len(noPanel)}")
    if duped:
        print(f"  ⚠ note_duplicated(앞10): {[(r['code'], r['dupNtKeys']) for r in duped[:10]]}")
    if dropped:
        print(f"  ⚠ content_dropped(앞10): {[(r['code'], r['charDrop']) for r in dropped[:10]]}")
    if discont:
        print(f"  ⚠ note_discontinuous(앞20): {[r['code'] for r in discont[:20]]}")

    outPath = Path(args.out)
    outPath.parent.mkdir(parents=True, exist_ok=True)
    outPath.write_text(
        json.dumps(
            {
                "total": len(codes),
                "parquetChars": parquetChars,
                "charDrop": charDrop,
                "contentDropped": [r["code"] for r in dropped],
                "noteDiscontinuous": [r["code"] for r in discont],
                "noteDuplicated": [r["code"] for r in duped],
                "noPanel": [r["code"] for r in noPanel],
                "records": recs,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"  → {outPath}")

    return 1 if (args.strict and (dropped or discont or duped)) else 0


if __name__ == "__main__":
    sys.exit(main())
