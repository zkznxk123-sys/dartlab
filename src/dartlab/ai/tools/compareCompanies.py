"""다중 종목 비교 — Track C (peer-matrix 1 회 답변).

여러 stockCode (max 3) 을 받아 핵심 metrics 를 wide table 로 반환. 각 회사 마다 dCR
badge + industry 정보 + 매출/이익/부채 비율 등 동일 metric 셀.

UI 측 workspaceSlots 다중 슬롯 마이그레이션 없이 한 도구 결과 안에 비교를 담아 답변 본문에
표 1 개로 노출. 향후 다중 슬롯 UI (별도 PR) 의 데이터 백본도 본 함수 그대로.

신뢰도 80 (ratio method) — 결정적 비율 계산.
"""

from __future__ import annotations

from typing import Any

import polars as pl

from dartlab.ai.contracts import Ref
from dartlab.core.confidence import baseScore

from .companyResolve import resolveCompanyOrNone
from .creditBadge import getDcrBadge
from .industryContext import getIndustryBadge
from .types import ToolResult

_MAX_SLOTS = 3
_DEFAULT_METRICS = (
    "revenue",
    "operatingProfit",
    "netIncome",
    "totalAssets",
    "totalEquity",
    "totalLiabilities",
)

# snakeId 별칭 — Company.panel 의 실제 키. 사용자 친화 metric 키 ↔ snakeId 매핑.
_METRIC_TO_SNAKE = {
    "revenue": "sales",
    "operatingProfit": "operating_profit",
    "netIncome": "net_incomenet_loss_for_the_year_attributable_toowners_of_parent_equity",
    "totalAssets": "total_assets",
    "totalEquity": "total_stockholders_equity",
    "totalLiabilities": "total_liabilities",
}


def _latestValueFromShow(table: pl.DataFrame, snakeId: str) -> float | None:
    """Company.panel 결과에서 (snakeId, latest period) 셀 값."""
    if not isinstance(table, pl.DataFrame) or table.is_empty():
        return None
    if "snakeId" not in table.columns:
        return None
    periods = [c for c in table.columns if c[:4].isdigit()]
    if not periods:
        return None
    latest = periods[0]
    sub = table.filter(pl.col("snakeId") == snakeId)
    if sub.is_empty():
        return None
    val = sub[0, latest]
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def _companyMetrics(company: Any) -> dict[str, Any]:
    """단일 Company → 비교용 metric dict.

    IS/BS 각각 1 회 panel 호출. _METRIC_TO_SNAKE 매핑으로 실제 snakeId 추출.
    """
    metrics: dict[str, Any] = {}
    if company is None:
        return metrics
    is_df = _safe(lambda: company.panel("IS"))
    bs_df = _safe(lambda: company.panel("BS"))
    is_metrics = ("revenue", "operatingProfit", "netIncome")
    bs_metrics = ("totalAssets", "totalEquity", "totalLiabilities")
    for key in is_metrics:
        snake = _METRIC_TO_SNAKE[key]
        metrics[key] = _latestValueFromShow(is_df, snake) if is_df is not None else None
    for key in bs_metrics:
        snake = _METRIC_TO_SNAKE[key]
        metrics[key] = _latestValueFromShow(bs_df, snake) if bs_df is not None else None
    eq = metrics.get("totalEquity")
    liab = metrics.get("totalLiabilities")
    ni = metrics.get("netIncome")
    metrics["debtRatio"] = round(liab / eq * 100, 2) if eq and liab is not None else None
    metrics["roe"] = round(ni / eq * 100, 2) if eq and ni is not None else None
    return metrics


def compareCompanies(stockCodes: list[str] | str | None = None) -> ToolResult:
    """다중 종목 wide-format 비교.

    Parameters
    ----------
    stockCodes : list[str] | str
        2~3 개 종목 코드. 문자열 1 개도 list 1 짜리로 처리.
    """
    if isinstance(stockCodes, str):
        stockCodes = [stockCodes]
    codes = [str(c).strip() for c in (stockCodes or []) if str(c).strip()]
    if not codes:
        return ToolResult(False, "stockCodes 필수 (2~3 개).", error="missing_stock_codes")
    if len(codes) > _MAX_SLOTS:
        codes = codes[:_MAX_SLOTS]
    rows: list[dict[str, Any]] = []
    badges: list[dict[str, Any]] = []
    for code in codes:
        company = resolveCompanyOrNone(code)
        if company is None:
            rows.append({"stockCode": code, "corpName": None, "error": "company_not_resolved"})
            continue
        corpName = str(getattr(company, "corpName", None) or "")
        row: dict[str, Any] = {"stockCode": code, "corpName": corpName}
        row.update(_companyMetrics(company))
        rows.append(row)
        badges.append(
            {
                "stockCode": code,
                "corpName": corpName,
                "dcr": getDcrBadge(company),
                "industry": getIndustryBadge(company),
            }
        )
    confidence = baseScore("ratio")
    payload = {
        "stockCodes": codes,
        "metrics": list(_DEFAULT_METRICS) + ["debtRatio", "roe"],
        "rows": rows,
        "badges": badges,
        "confidence": confidence,
        "confidenceMethod": "ratio",
    }
    ref = Ref(
        id=f"compare:{':'.join(codes)}",
        kind="tableRef",
        title=f"{len(codes)} 종목 비교 · {', '.join(c.get('corpName') or c['stockCode'] for c in rows)}",
        source="compareCompanies",
        payload=payload,
    )
    return ToolResult(
        True,
        f"{len(codes)} 종목 비교 완료 — 매출·영업이익·순이익·총자산·자기자본·부채·debtRatio·ROE.",
        refs=[ref],
        data=payload,
    )


__all__ = ["compareCompanies"]
