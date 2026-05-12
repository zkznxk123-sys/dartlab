"""채무증권 현황 추출 — XBRL Debt Securities 태그."""

from __future__ import annotations

from typing import TYPE_CHECKING

import polars as pl

if TYPE_CHECKING:
    from dartlab.providers.edgar.company import Company


def extractDebtSecurities(company: "Company") -> pl.DataFrame | None:
    """채무증권 발행/보유 현황 추출.

    Args:
        company: EDGAR Company 인스턴스.

    Returns:
        ``period/commercialPaper/shortTermDebt/availableForSaleDebt/heldToMaturity`` 컬럼 DataFrame 또는 None.

    Raises:
        없음.

    Example:
        >>> extractDebtSecurities(Company("AAPL"))

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - polars

    Capabilities:
        - <TODO: 함수 핵심 책임 요약>

    Guide:
        - <TODO: 사용 시나리오>

    AIContext:
        <TODO: AI 호출 컨텍스트>

    LLM Specifications:
        AntiPatterns:
            - <TODO: 안티패턴>
        OutputSchema:
            - <TODO: 출력 형태>
        Prerequisites:
            - <TODO: 사전조건>
        Freshness:
            - <TODO: 데이터 freshness>
        Dataflow:
            - <TODO: 데이터 흐름>
        TargetMarkets:
            - <TODO: 대상 시장>
    """
    from dartlab.providers.edgar.report import loadXbrlTags

    df = loadXbrlTags(
        company,
        "(?i)DebtSecurities|AvailableForSaleDebt|HeldToMaturitySecurities|"
        "CommercialPaper|ShortTermBorrowings|ShortTermDebt",
        unitFilter="(?i)USD",
    )
    if df is None:
        return None

    records: list[dict] = []
    for fy in df["fy"].unique().drop_nulls().sort().to_list():
        fyRows = df.filter(pl.col("fy") == fy).sort("filed", descending=True)
        record: dict = {"period": str(fy)}

        for row in fyRows.iter_rows(named=True):
            tag = str(row.get("tag") or "").lower()
            val = row.get("val")
            if val is None:
                continue
            if "commercialpaper" in tag and "proceeds" not in tag:
                record.setdefault("commercialPaper", val)
            elif "shorttermdebt" in tag or "shorttermborrowings" in tag:
                record.setdefault("shortTermDebt", val)
            elif "availableforsaledebt" in tag:
                record.setdefault("availableForSaleDebt", val)
            elif "heldtomaturity" in tag:
                record.setdefault("heldToMaturity", val)

        if len(record) > 1:
            records.append(record)

    return pl.DataFrame(records) if records else None
