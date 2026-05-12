"""임원 보수 추출 — XBRL 보상 관련 태그."""

from __future__ import annotations

from typing import TYPE_CHECKING

import polars as pl

if TYPE_CHECKING:
    from dartlab.providers.edgar.company import Company


def extractExecutivePay(company: "Company") -> pl.DataFrame | None:
    """임원 보수 관련 XBRL 데이터 추출.

    Args:
        company: EDGAR Company 인스턴스.

    Returns:
        ``period/shareBasedComp/cashBonus/optionsGranted`` 컬럼 DataFrame 또는 None.

    Raises:
        없음.

    Example:
        >>> extractExecutivePay(Company("AAPL"))

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
        "(?i)ShareBasedCompensation|StockBasedCompensation|"
        "AllocatedShareBasedCompensationExpense|"
        "DefinedBenefitPlanNetPeriodicBenefitCost",
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
            if "stockbasedcompensation" in tag or "sharebasedcompensation" in tag:
                record.setdefault("stockBasedCompensation", val)
            elif "definedbenefit" in tag:
                record.setdefault("pensionCost", val)

        if len(record) > 1:
            records.append(record)

    return pl.DataFrame(records) if records else None
