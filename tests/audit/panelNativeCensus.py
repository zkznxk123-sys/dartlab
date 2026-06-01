"""panel native 전수 census — panel.parquet 단일 artifact 에서 native is/bs/cf/ratios 가 나오는지 검사.

panelCell 별 artifact 없이 ``c.panel("is")``/``c.panel("ratios")`` 는 panel.parquet 의 5표 contentRaw 를
read-time 분해(``cell._cellsFromPanel``)한다. 본 census 는 ``data/dart/panel/{code}/`` 종목별로:
    - panel.parquet period 수
    - 재무 5표(BS/IS2/IS3/CF/EF) 셀 커버 (in-memory 분해 결과)
    - ``readRatios`` 비율 행 수 (native 비율 산출 성공)
    - ``readStatement("IS2")`` 최소 연도 (과거 연장 도달)

결손 종목(셀 0 / 5표 결손 / 비율 0)을 리포트하고 ``dist/panelNative_census.json`` 으로 영속화.
panel.parquet stale(옛 disclosureKey)이면 5표 셀 0 → 본 census 가 즉시 검출.

사용법::

    uv run python -X utf8 tests/audit/panelNativeCensus.py            # 전종목
    uv run python -X utf8 tests/audit/panelNativeCensus.py --codes 005930,000660
    uv run python -X utf8 tests/audit/panelNativeCensus.py --limit 100  # 표본

종료 코드: 0 (보고용). --strict 면 결손 발견 시 1.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import polars as pl

import dartlab.config as _cfg
from dartlab.providers.dart.panel.cell import _cellsFromPanel, cellStatements, readRatios, readStatement

_FIVE = cellStatements()  # {BS, IS2, IS3, CF, EF}


def _censusOne(code: str) -> dict:
    """종목 1개 census — panel period/5표커버/비율행/최소연도 (panel.parquet 단일)."""
    panelDir = Path(_cfg.dataDir) / "dart" / "panel" / code
    files = sorted(panelDir.glob("*.parquet")) if panelDir.exists() else []
    rec: dict = {"code": code, "periods": len(files), "statements": [], "ratioRows": 0, "isMinYear": None, "issues": []}
    if not files:
        rec["issues"].append("no_panel")
        return rec
    cells = _cellsFromPanel(code)  # panel.parquet 5표 contentRaw → in-memory 셀
    if cells is None:
        rec["issues"].append("no_cells")  # 5표 행 0 (stale disclosureKey 등)
        return rec
    rec["statements"] = sorted(s for s in cells["statement"].unique().to_list() if s in _FIVE)
    missing = sorted(_FIVE - set(rec["statements"]))
    if missing:
        rec["issues"].append(f"missing_statements:{','.join(missing)}")
    ratios = readRatios(code, freq="year")
    rec["ratioRows"] = 0 if ratios is None else ratios.height
    if rec["ratioRows"] == 0:
        rec["issues"].append("no_ratios")
    isw = readStatement(code, statement="IS2", freq="year")
    if isw is not None:
        years = [int(c) for c in isw.columns if c.isdigit()]
        rec["isMinYear"] = min(years) if years else None
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(description="panel native 전수 census")
    ap.add_argument("--codes", type=str, default="", help="콤마구분 종목. 빈값=전종목")
    ap.add_argument("--limit", type=int, default=0, help="표본 N 종목 (0=전체)")
    ap.add_argument("--out", type=str, default="dist/panelNative_census.json", help="JSON 출력 경로")
    ap.add_argument("--strict", action="store_true", help="결손 발견 시 exit 1")
    args = ap.parse_args()

    base = Path(_cfg.dataDir) / "dart" / "panel"
    if args.codes:
        codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    elif base.exists():
        codes = sorted(d.name for d in base.iterdir() if d.is_dir() and d.name != "spine")
    else:
        codes = []
    if args.limit > 0:
        codes = codes[: args.limit]

    records = [_censusOne(c) for c in codes]
    withCells = [r for r in records if r["statements"]]
    withRatios = [r for r in records if r["ratioRows"] > 0]
    issues = [r for r in records if r["issues"]]

    print(
        f"[panelNative-census] {len(codes)}종목 — 셀보유 {len(withCells)}, 비율보유 {len(withRatios)}, 결손 {len(issues)}"
    )
    for r in issues[:50]:
        print(f"  {r['code']}: {'; '.join(r['issues'])}")
    if len(issues) > 50:
        print(f"  ... +{len(issues) - 50} more")

    outPath = Path(args.out)
    outPath.parent.mkdir(parents=True, exist_ok=True)
    outPath.write_text(
        json.dumps(
            {
                "total": len(codes),
                "withCells": len(withCells),
                "withRatios": len(withRatios),
                "issueCount": len(issues),
                "records": records,
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"[panelNative-census] → {outPath}")
    return 1 if (args.strict and issues) else 0


if __name__ == "__main__":
    sys.exit(main())
