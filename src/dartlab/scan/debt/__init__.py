"""부채 구조 전수 스캔 — 사채 만기, 부채비율, ICR, 위험등급.

Public API:
    scan_debt()  → pl.DataFrame (전체 상장사 부채 현황)
"""

from __future__ import annotations

import polars as pl

from dartlab.core.logger import getLogger

_log = getLogger(__name__)


from dartlab.scan.debt.risk import classifyRisk, scanIcr
from dartlab.scan.debt.scanner import scanBonds, scanDebtMix, scanShortDebt


def scanDebt(*, verbose: bool = True) -> pl.DataFrame:
    """전체 상장사 부채 스캔 → 종합 DataFrame.

    컬럼: 종목코드, 사채잔액, 단기잔액, 단기비중, 단기사채잔액, CP잔액,
          단기채무합계, 총부채, 부채비율, ICR, 위험등급
    """

    def _say(msg: str) -> None:
        if verbose:
            _log.info(msg)

    _say("1/4 사채 만기...")
    bond_map = scanBonds()
    _say(f"  -> {len(bond_map)}종목")

    _say("2/4 단기사채/CP...")
    short_map = scanShortDebt()
    _say(f"  -> {len(short_map)}종목")

    _say("3/4 부채비율...")
    debt_map = scanDebtMix()
    _say(f"  -> {len(debt_map)}종목")

    _say("4/4 이자보상배율...")
    icr_map = scanIcr()
    _say(f"  -> {len(icr_map)}종목")

    all_codes = set(bond_map) | set(debt_map) | set(icr_map) | set(short_map)

    results = []
    for code in all_codes:
        b = bond_map.get(code, {})
        s = short_map.get(code, {})
        d = debt_map.get(code, {})
        icr = icr_map.get(code)

        shortRatio = b.get("단기비중")
        shortDebtTotal = s.get("단기채무합계")
        risk = classifyRisk(icr, shortRatio, shortDebtTotal) if (b or s or icr is not None) else None

        results.append(
            {
                "stockCode": code,
                "사채잔액": b.get("사채잔액"),
                "단기잔액": b.get("단기잔액"),
                "단기비중": shortRatio,
                "단기사채잔액": s.get("단기사채잔액"),
                "CP잔액": s.get("CP잔액"),
                "단기채무합계": shortDebtTotal,
                "총부채": d.get("총부채"),
                "부채비율": d.get("부채비율"),
                "ICR": icr,
                "위험등급": risk,
            }
        )

    # infer_schema_length=None: 전체 행 스캔 (기본 100행 추론이 큰 금액에서 overflow
    # 유발. "ComputeError: could not append value 1.2e11 of type f64" 재발 방지.
    df = pl.DataFrame(results, infer_schema_length=None)
    _say(f"부채 스캔 완료: {df.shape[0]}종목")
    return df


__all__ = ["scan_debt"]
