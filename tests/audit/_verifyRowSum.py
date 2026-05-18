"""Ad-hoc — bento dashboard 모든 row col 합 == 12 검증.

[[feedback_row_fills_12col_no_gap]] 룰 강행 검증 도구. financial section split
후 빈 공간 회귀 차단.
"""

from __future__ import annotations

from dartlab.viz import planTabLayout


def main() -> int:
    rows: dict[int, list[tuple[str, int]]] = {}
    for p in planTabLayout("financial", sub=None):
        rows.setdefault(p["y"], []).append((p["cardKey"], p["w"]))

    allPass = True
    print(f"total rows = {len(rows)}")
    for y in sorted(rows):
        ws = [w for _, w in rows[y]]
        s = sum(ws)
        keys = " · ".join(f"{k}({w})" for k, w in rows[y])
        status = "OK" if s == 12 else f"FAIL ({s})"
        if s != 12:
            allPass = False
        print(f"  y={y:2}  sum={s:2}  {status}  : {keys}")

    print(f"\nall row sum == 12: {allPass}")
    return 0 if allPass else 1


if __name__ == "__main__":
    raise SystemExit(main())
