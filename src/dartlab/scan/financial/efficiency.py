"""운영 효율 스캔 -- 자산/재고/매출채권 회전율 + CCC(현금전환주기)."""

from __future__ import annotations

import polars as pl

from dartlab.core.logger import getLogger

_log = getLogger(__name__)


from dartlab.scan.parquetLoad import (
    NI_IDS as _NI_IDS,  # noqa: F401 (호환 alias 일부 호출 대비)
)
from dartlab.scan.parquetLoad import (
    OP_IDS as _OP_IDS,  # noqa: F401
)
from dartlab.scan.parquetLoad import (
    REVENUE_IDS as _REVENUE_IDS,
)
from dartlab.scan.parquetLoad import (
    REVENUE_NMS as _REVENUE_NMS,
)
from dartlab.scan.parquetLoad import (
    TA_IDS as _TA_IDS,
)
from dartlab.scan.parquetLoad import (
    TA_NMS as _TA_NMS,
)
from dartlab.scan.parquetLoad import (
    scanFinanceParquets,
)

# ── 계정 매핑 (모듈 고유) ──

_INV_IDS = {"Inventories", "inventories", "ifrs-full_Inventories", "dart_Inventories"}
_INV_NMS = {"재고자산"}

_AR_IDS = {
    "ShortTermTradeReceivables",
    "TradeAndOtherCurrentReceivables",
    "ifrs-full_TradeAndOtherCurrentReceivables",
}
_AR_NMS = {"매출채권"}

_PPE_IDS = {"PropertyPlantAndEquipment", "ifrs-full_PropertyPlantAndEquipment"}
_PPE_NMS = {"유형자산"}

_COGS_IDS = {"CostOfSales", "ifrs-full_CostOfSales", "dart_CostOfGoodsAndServicesSold"}
_COGS_NMS = {"매출원가"}

_AP_IDS = {"TradeAndOtherCurrentPayables", "ifrs-full_TradeAndOtherCurrentPayables"}
_AP_NMS = {"매입채무"}

_MIN_REVENUE = 1e8  # 매출 1억 미만 제외
_CCC_CAP = 3000.0  # CCC +-3000일 초과 클램핑


def _gradeEfficiency(ccc: float | None) -> str:
    """현금전환주기(CCC) → 운영 효율 등급 변환.

    우수(90일 미만) / 양호(180일 미만) / 보통(365일 미만) / 비효율(365일 이상).
    None이면 '해당없음'을 반환한다.

    Parameters
    ----------
    ccc : float | None
        현금전환주기 (일)

    Returns
    -------
    str
        효율 등급 (우수 | 양호 | 보통 | 비효율 | 해당없음)
    """
    if ccc is None:
        return "해당없음"
    if ccc < 90:
        return "우수"
    if ccc < 180:
        return "양호"
    if ccc < 365:
        return "보통"
    return "비효율"


def scanEfficiency(*, verbose: bool = True) -> pl.DataFrame:
    """전종목 운영 효율 스캔 -- 회전율 + CCC + 등급."""
    if verbose:
        _log.info("효율성 스캔: 계정 수집 중...")

    revMap = scanFinanceParquets("IS", _REVENUE_IDS, _REVENUE_NMS)
    taMap = scanFinanceParquets("BS", _TA_IDS, _TA_NMS)
    invMap = scanFinanceParquets("BS", _INV_IDS, _INV_NMS)
    arMap = scanFinanceParquets("BS", _AR_IDS, _AR_NMS)
    ppeMap = scanFinanceParquets("BS", _PPE_IDS, _PPE_NMS)
    cogsMap = scanFinanceParquets("IS", _COGS_IDS, _COGS_NMS)
    apMap = scanFinanceParquets("BS", _AP_IDS, _AP_NMS)

    allCodes = set(revMap) | set(taMap) | set(invMap) | set(arMap)

    rows: list[dict] = []
    for code in allCodes:
        rev = revMap.get(code)
        if not rev or rev < _MIN_REVENUE:
            continue

        ta = taMap.get(code)
        inv = invMap.get(code)
        ar = arMap.get(code)
        ppe = ppeMap.get(code)
        cogs = cogsMap.get(code)
        ap = apMap.get(code)

        assetTurnover = round(rev / ta, 2) if ta and ta > 0 else None
        invTurnover = round(rev / inv, 2) if inv and inv > 0 else None
        arTurnover = round(rev / ar, 2) if ar and ar > 0 else None
        ppeTurnover = round(rev / ppe, 2) if ppe and ppe > 0 else None

        invDays = round(365 / invTurnover) if invTurnover and invTurnover > 0 else None
        arDays = round(365 / arTurnover) if arTurnover and arTurnover > 0 else None
        apDays = round(365 * ap / cogs) if ap and cogs and cogs > 0 else None

        ccc = None
        if invDays is not None and arDays is not None:
            rawCcc = invDays + arDays - (apDays or 0)
            ccc = max(-_CCC_CAP, min(_CCC_CAP, rawCcc))

        rows.append(
            {
                "stockCode": code,
                "assetTurnover": assetTurnover,
                "invTurnover": invTurnover,
                "arTurnover": arTurnover,
                "ppeTurnover": ppeTurnover,
                "invDays": invDays,
                "arDays": arDays,
                "ccc": ccc,
                "grade": _gradeEfficiency(ccc),
            }
        )

    if verbose:
        _log.info(f"효율성 스캔 완료: {len(rows)}종목")

    if not rows:
        return pl.DataFrame()

    schema = {
        "stockCode": pl.Utf8,
        "assetTurnover": pl.Float64,
        "invTurnover": pl.Float64,
        "arTurnover": pl.Float64,
        "ppeTurnover": pl.Float64,
        "invDays": pl.Float64,
        "arDays": pl.Float64,
        "ccc": pl.Float64,
        "grade": pl.Utf8,
    }
    return pl.DataFrame(rows, schema=schema)


__all__ = ["scanEfficiency"]
