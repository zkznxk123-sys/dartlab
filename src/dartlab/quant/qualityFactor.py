"""퀄리티 팩터 — Asness Quality Minus Junk 단순 복합.

학술 근거: Asness, Frazzini, Pedersen (2019) — Quality Minus Junk.

데이터: scan 프리빌드 finance.parquet 직접 읽기. analysis(L2) import 금지.

코드는 Asness 4축(profitability/growth/safety/payout) 중 profitability + safety만
구현. growth/payout은 추가 데이터(전기 비교, 배당)가 필요하여 후순위.

금융업(은행/보험/증권)은 부채 구조가 사업 본질이므로 grade 산출에서 제외하고
"finance" 태그만 부여한다.
"""

from __future__ import annotations

import logging

import polars as pl

from dartlab.core.cross.scanBridge import extractAnnualConsolidated, isEdgarSchema
from dartlab.quant._helpers import extract_account, load_scan_parquet, resolve_market

log = logging.getLogger(__name__)


# 금융업 종목코드 (KOSPI 주요) — 추후 sector 매핑으로 교체
_KR_FINANCIAL = {
    "105560",  # KB금융
    "055550",  # 신한금융
    "086790",  # 하나금융
    "316140",  # 우리금융
    "138930",  # BNK금융
    "024110",  # 기업은행
    "323410",  # 카카오뱅크
    "071050",  # 한국금융지주
    "030200",  # KT
    "000810",  # 삼성화재
    "032830",  # 삼성생명
    "088350",  # 한화생명
    "001450",  # 현대해상
    "005830",  # DB손해보험
    "006800",  # 미래에셋증권
    "016360",  # 삼성증권
    "039490",  # 키움증권
    "078930",  # GS
    "138040",  # 메리츠금융지주
    "029780",  # 삼성카드
}


def _is_financial(stockCode: str) -> bool:
    return stockCode in _KR_FINANCIAL


def _crosssec_zscore(value: float, all_values: list[float]) -> float:
    """횡단면 z-score (winsorized clip ±3)."""
    import numpy as np

    arr = np.array([v for v in all_values if v is not None and not np.isnan(v)])
    if len(arr) < 10:
        return 0.0
    mu = float(np.mean(arr))
    sigma = float(np.std(arr, ddof=1))
    if sigma == 0:
        return 0.0
    z = (value - mu) / sigma
    return float(max(-3, min(3, z)))


def calcQuality(stockCode: str, *, market: str = "auto", **kwargs) -> dict:
    """Asness 퀄리티 팩터 — 횡단면 z-score 기반.

    Args:
        stockCode: 종목코드 또는 ticker.
        market: "KR" | "US" | "auto".

    Returns:
        dict with qualityScore, profitabilityZ, safetyZ, grade, sector tag.
    """
    market = resolve_market(stockCode, market)
    result: dict = {"stockCode": stockCode, "market": market}

    if _is_financial(stockCode):
        result["sector"] = "financial"
        result["grade"] = None
        result["info"] = "금융업은 부채 구조가 사업 본질이라 일반 quality 산식 부적절"
        return result

    lf = load_scan_parquet("finance", market)
    if lf is None:
        return {**result, "error": "finance.parquet 없음"}

    # 전체 universe 스냅샷 (연간 연결재무) — 횡단면 z 계산용
    try:
        snap = extractAnnualConsolidated(lf.collect())
    except (pl.exceptions.ColumnNotFoundError, pl.exceptions.ComputeError) as e:
        return {**result, "error": str(e)}
    if snap.is_empty():
        return {**result, "error": "연결 4분기 데이터 없음"}

    edgar = isEdgarSchema(snap)
    year_col = "fy" if edgar else "bsns_year"

    # 가장 최근 충분한 데이터를 가진 연도
    year_counts = snap.group_by(year_col).len().sort(year_col, descending=True)
    yr = None
    for row in year_counts.iter_rows(named=True):
        if row["len"] >= 1000:
            yr = row[year_col]
            break
    if yr is None:
        return {**result, "error": "충분한 universe 연도 없음"}

    snap_yr = snap.filter(pl.col(year_col) == yr)
    result["year"] = str(yr)

    # universe metric 캐시 (연도별)
    universe_metrics = _get_universe_metrics_cached(market, str(yr))
    if universe_metrics is None:
        universe_metrics = _build_universe_metrics(snap_yr)
        _set_universe_metrics_cached(market, str(yr), universe_metrics)

    # 단일 종목 추출
    stock = snap_yr.filter(pl.col("stockCode") == stockCode)
    if stock.is_empty():
        # 회계연도 비표준 종목 (예: NVDA fy=2026, 1월결산) — 해당 종목의 최신 fy 로 fallback.
        company_years = snap.filter(pl.col("stockCode") == stockCode).select(year_col).unique().to_series().to_list()
        if not company_years:
            return {**result, "error": f"{stockCode} scan parquet 데이터 없음"}
        yr = max(company_years)
        snap_yr = snap.filter(pl.col(year_col) == yr)
        stock = snap_yr.filter(pl.col("stockCode") == stockCode)
        result["year"] = str(yr)
        if stock.is_empty():
            return {**result, "error": f"{yr} 데이터 없음"}
    sales = extract_account(stock, "sales")
    op = extract_account(stock, "operating_profit")
    ni = extract_account(stock, "net_income")
    assets = extract_account(stock, "total_assets")
    debt = extract_account(stock, "total_liabilities")
    equity = extract_account(stock, "total_equity")

    metrics: dict = {}
    if sales and sales > 0 and op is not None:
        metrics["operatingMargin"] = round(op / sales * 100, 2)
    if assets and assets > 0 and ni is not None:
        metrics["ROA"] = round(ni / assets * 100, 2)
    if equity and equity > 0 and ni is not None:
        metrics["ROE"] = round(ni / equity * 100, 2)
    if assets and assets > 0 and debt is not None:
        metrics["debtRatio"] = round(debt / assets * 100, 2)

    result["metrics"] = metrics

    prof_zs = []
    if "operatingMargin" in metrics:
        prof_zs.append(_crosssec_zscore(metrics["operatingMargin"], universe_metrics["operatingMargin"]))
    if "ROA" in metrics:
        prof_zs.append(_crosssec_zscore(metrics["ROA"], universe_metrics["ROA"]))
    if "ROE" in metrics:
        prof_zs.append(_crosssec_zscore(metrics["ROE"], universe_metrics["ROE"]))

    if prof_zs:
        prof_z = sum(prof_zs) / len(prof_zs)
    else:
        prof_z = 0.0

    safety_z = 0.0
    if "debtRatio" in metrics:
        # 부채 낮을수록 안전 → z의 부호 반전
        raw = _crosssec_zscore(metrics["debtRatio"], universe_metrics["debtRatio"])
        safety_z = -raw

    composite = prof_z * 0.6 + safety_z * 0.4
    result["profitabilityZ"] = round(float(prof_z), 4)
    result["safetyZ"] = round(float(safety_z), 4)
    result["qualityScore"] = round(float(composite), 4)

    if composite >= 1.5:
        result["grade"] = "A"
    elif composite >= 0.5:
        result["grade"] = "B"
    elif composite >= -0.5:
        result["grade"] = "C"
    elif composite >= -1.5:
        result["grade"] = "D"
    else:
        result["grade"] = "F"

    return result


_UNIVERSE_CACHE: dict[tuple[str, str], dict[str, list[float]]] = {}


def _get_universe_metrics_cached(market: str, year: str):
    return _UNIVERSE_CACHE.get((market, year))


def _set_universe_metrics_cached(market: str, year: str, metrics):
    _UNIVERSE_CACHE[(market, year)] = metrics


def _build_universe_metrics(snap_yr: pl.DataFrame) -> dict[str, list[float]]:
    """연도 스냅샷에서 모든 종목의 4지표 분포 빌드."""
    result: dict[str, list[float]] = {
        "operatingMargin": [],
        "ROA": [],
        "ROE": [],
        "debtRatio": [],
    }
    codes = snap_yr.get_column("stockCode").unique().to_list()
    for code in codes:
        if not isinstance(code, str):
            continue
        if _is_financial(code):
            continue
        stock = snap_yr.filter(pl.col("stockCode") == code)
        sales = extract_account(stock, "sales")
        op = extract_account(stock, "operating_profit")
        ni = extract_account(stock, "net_income")
        assets = extract_account(stock, "total_assets")
        debt = extract_account(stock, "total_liabilities")
        equity = extract_account(stock, "total_equity")

        if sales and sales > 0 and op is not None:
            result["operatingMargin"].append(op / sales * 100)
        if assets and assets > 0 and ni is not None:
            result["ROA"].append(ni / assets * 100)
        if equity and equity > 0 and ni is not None:
            result["ROE"].append(ni / equity * 100)
        if assets and assets > 0 and debt is not None:
            result["debtRatio"].append(debt / assets * 100)
    return result
