"""YoY delta 사전 계산 — 전 종목 × 최신년 대비 전년 재무 지표 변화.

산업지도 회사 카드의 **delta badge** (예: "ROE 12.4% · YoY +1.8%p ▲") 용.

Returns
-------
dict[str, dict]
    stockCode → {
        roeDelta: float | None,             # %p (최신년 ROE - 전년 ROE)
        opMarginDelta: float | None,        # %p
        netMarginDelta: float | None,       # %p
        revenueYoyPct: float | None,        # % (전년 대비 증감률)
        debtRatioDelta: float | None,       # %p (부채비율)
        asOfYear: int | None,               # 최신년
        priorYear: int | None,              # 전년
    }

설계 결정
---------
- finance.parquet 1회 로드 → 최신·전년 2개 연도 동시 계산
- 음수/0 분모 방어
- 업데이트 직후 전년 데이터 없는 신규 상장사 → None (필드 스킵)
"""

from __future__ import annotations

import logging
from typing import Any

import polars as pl

logger = logging.getLogger(__name__)


def _extract_by_ids(row_sub: pl.DataFrame, id_list, nm_list) -> float | None:
    """단일 연도 subset 에서 계정값 추출 (scan extractAccount 재사용)."""
    from dartlab.scan._helpers import extractAccount
    return extractAccount(row_sub, list(id_list), list(nm_list))


def computeYoyDelta() -> dict[str, dict[str, Any]]:
    """finance.parquet 에서 최신·전년 2개 연도 × 전종목 × 핵심 비율 delta 계산.

    Returns
    -------
    dict[stockCode → {roeDelta, opMarginDelta, netMarginDelta, revenueYoyPct, debtRatioDelta, asOfYear, priorYear}]
    """
    from pathlib import Path

    from dartlab.scan._helpers import _ensureScanData
    from dartlab.scan.profitability import (
        _EQ_IDS, _EQ_NMS,
        _NI_IDS, _NI_NMS,
        _OP_IDS, _OP_NMS,
        _REVENUE_IDS, _REVENUE_NMS,
        _TA_IDS, _TA_NMS,
    )
    # 부채 계정 — scan.debt 에서 재사용 (없으면 fallback)
    try:
        from dartlab.scan.debt.risk import _LIABILITY_IDS, _LIABILITY_NMS  # type: ignore
    except Exception:
        _LIABILITY_IDS = {"ifrs-full_Liabilities", "ifrs_Liabilities"}
        _LIABILITY_NMS = {"부채총계", "총부채"}

    scanDir = _ensureScanData()
    scanPath = Path(scanDir) / "finance.parquet"
    if not scanPath.exists():
        logger.warning(f"finance.parquet 없음: {scanPath}")
        return {}

    # 로드 — scanProfitability 와 동일 필터
    allIds = list(_REVENUE_IDS | _OP_IDS | _NI_IDS | _TA_IDS | _EQ_IDS | _LIABILITY_IDS)
    allNms = list(_REVENUE_NMS | _OP_NMS | _NI_NMS | _TA_NMS | _EQ_NMS | _LIABILITY_NMS)
    schemaNames = pl.scan_parquet(str(scanPath)).collect_schema().names()
    scCol = "stockCode" if "stockCode" in schemaNames else "stock_code"

    df = (
        pl.scan_parquet(str(scanPath))
        .filter(
            pl.col("sj_div").is_in(["IS", "CIS", "BS"])
            & (pl.col("fs_nm").str.contains("연결") | pl.col("fs_nm").str.contains("재무제표"))
            & (pl.col("account_id").is_in(allIds) | pl.col("account_nm").is_in(allNms))
        )
        .collect()
    )
    # 연결 우선
    cfs = df.filter(pl.col("fs_nm").str.contains("연결"))
    if not cfs.is_empty():
        df = cfs
    if df.is_empty():
        return {}
    years = sorted(df["bsns_year"].unique().to_list(), reverse=True)
    if len(years) < 2:
        logger.warning("YoY delta 계산 불가 — 연도 2개 미만")
        return {}

    latestYear = years[0]
    priorYear = years[1]
    latest = df.filter(pl.col("bsns_year") == latestYear)
    prior = df.filter(pl.col("bsns_year") == priorYear)

    def _ratios(sub: pl.DataFrame) -> tuple:
        from dartlab.scan.profitability import (
            _EQ_IDS as EQ_IDS, _EQ_NMS as EQ_NMS,
            _NI_IDS as NI_IDS, _NI_NMS as NI_NMS,
            _OP_IDS as OP_IDS, _OP_NMS as OP_NMS,
            _REVENUE_IDS as R_IDS, _REVENUE_NMS as R_NMS,
        )
        rev = _extract_by_ids(sub, R_IDS, R_NMS)
        op = _extract_by_ids(sub, OP_IDS, OP_NMS)
        ni = _extract_by_ids(sub, NI_IDS, NI_NMS)
        eq = _extract_by_ids(sub, EQ_IDS, EQ_NMS)
        li = _extract_by_ids(sub, _LIABILITY_IDS, _LIABILITY_NMS)

        opMargin = (op / rev * 100) if rev and rev != 0 and op is not None else None
        netMargin = (ni / rev * 100) if rev and rev != 0 and ni is not None else None
        roe = (ni / eq * 100) if eq and eq != 0 and ni is not None else None
        debtRatio = (li / eq * 100) if eq and eq != 0 and li is not None else None
        return rev, opMargin, netMargin, roe, debtRatio

    out: dict[str, dict[str, Any]] = {}
    codes = set(latest[scCol].unique().to_list())

    for code in codes:
        lsub = latest.filter(pl.col(scCol) == code)
        psub = prior.filter(pl.col(scCol) == code)
        if psub.is_empty():
            continue

        lrev, lop, lnm, lroe, ldebt = _ratios(lsub)
        prev, pop, pnm, proe, pdebt = _ratios(psub)

        def _diff(a, b, digits=1):
            if a is None or b is None:
                return None
            return round(a - b, digits)

        def _pct_change(a, b, digits=1):
            if a is None or b is None or b == 0:
                return None
            return round((a - b) / abs(b) * 100, digits)

        entry = {
            "roeDelta": _diff(lroe, proe),
            "opMarginDelta": _diff(lop, pop),
            "netMarginDelta": _diff(lnm, pnm),
            "revenueYoyPct": _pct_change(lrev, prev),
            "debtRatioDelta": _diff(ldebt, pdebt),
            "asOfYear": int(latestYear) if latestYear else None,
            "priorYear": int(priorYear) if priorYear else None,
        }

        # 모든 필드가 None 이면 저장하지 않음
        if all(v is None for k, v in entry.items() if k not in ("asOfYear", "priorYear")):
            continue

        out[code] = entry

    logger.info(f"YoY delta 계산 완료: {len(out)} 종목 (latest={latestYear}, prior={priorYear})")
    return out
