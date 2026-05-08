"""미매핑 account_id 진단 + nonstd_ fallback 검증.

usage: uv run python -X utf8 scripts/dev/dump_unmapped.py 000660
"""

from __future__ import annotations

import sys

import polars as pl  # noqa: F401

from dartlab.providers.dart.finance.mapper import AccountMapper
from dartlab.providers.dart.finance.pivot import _fallbackSnakeId, _loadAndNormalize, buildTimeseries, clearFinanceCache


def main() -> None:
    code = sys.argv[1] if len(sys.argv) > 1 else "000660"
    print(f"[dump_unmapped] target={code}")
    result = _loadAndNormalize(code)
    if result is None:
        print("  no finance data")
        return
    df, _periods = result
    mapper = AccountMapper.get()
    unmapped: dict[str, dict[str, int | str]] = {}
    for row in df.iter_rows(named=True):
        sj = row.get("sj_div", "")
        if sj == "CIS":
            sj = "IS"
        if sj not in {"BS", "IS", "CF"}:
            continue
        aid = row.get("account_id", "") or ""
        anm = row.get("account_nm", "") or ""
        snake = mapper.map(aid, anm)
        if snake is not None:
            continue
        key = f"{aid}|{anm}|{sj}"
        if key not in unmapped:
            unmapped[key] = {
                "account_id": aid,
                "account_nm": anm,
                "sj_div": sj,
                "count": 0,
                "sample_amount": row.get("_normalized_amount"),
            }
        unmapped[key]["count"] = int(unmapped[key]["count"]) + 1

    rows = sorted(unmapped.values(), key=lambda r: -int(r["count"]))
    print(f"\n[unmapped pre-fallback] {len(rows)} unique accounts")
    for r in rows:
        fallback = _fallbackSnakeId(str(r["account_nm"]))
        amt = r["sample_amount"]
        amt_str = f"{int(amt):,}" if isinstance(amt, (int, float)) else "—"
        print(
            f"  [{r['sj_div']}] count={r['count']:>3}  nm={r['account_nm']:<30}  → fallback={fallback}  sample={amt_str}"
        )

    # fallback 적용된 buildTimeseries 결과 검증 — nonstd_ 키가 살아나는지.
    clearFinanceCache()
    print(f"\n[buildTimeseries with fallback] target={code}")
    ts = buildTimeseries(code)
    if ts is None:
        print("  no result")
        return
    series, periods = ts
    for sj in ("BS", "IS", "CF"):
        nonstd = [k for k in series[sj] if k.startswith("nonstd_")]
        std = [k for k in series[sj] if not k.startswith("nonstd_")]
        print(f"  {sj}: std={len(std)} nonstd_={len(nonstd)}")
        for k in nonstd[:3]:
            non_null = sum(1 for v in series[sj][k] if v is not None)
            print(f"    {k} (values: {non_null}/{len(periods)})")


if __name__ == "__main__":
    main()
