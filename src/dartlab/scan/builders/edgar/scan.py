"""EDGAR XBRL 기반 전종목 scan — 7축 (profitability~dividendTrend).

DART scan이 프리빌드 parquet에서 읽듯이,
EDGAR scan은 개별 CIK parquet에서 전종목 계정을 스캔하여
비율/등급을 계산한다.

사용법::

    from dartlab.scan.builders.edgar.scan import edgarScan
    df = edgarScan("profitability")  # → stockCode | opMargin | netMargin | roe | roa | grade
"""

from __future__ import annotations

import polars as pl

from dartlab.scan.builders.edgar.helpers import pct, safeDiv, scanEdgarAccounts


def edgarScan(axis: str, **kwargs) -> pl.DataFrame:
    """EDGAR 전종목 scan 디스패치.

    Parameters
    ----------
    axis : str
        scan 축 이름 (예: "profitability", "growth", "debt").
    **kwargs
        축별 추가 인자.

    Returns
    -------
    pl.DataFrame
        축별 전종목 스캔 결과. 미구현 축이면 info 컬럼 1행 DataFrame.
    """
    fn = _DISPATCH.get(axis)
    if fn is None:
        return pl.DataFrame({"info": [f"EDGAR scan '{axis}' 미구현"]})
    return fn(**kwargs)


# ── profitability ──


def _scanProfitability(**_kw) -> pl.DataFrame:
    """수익성 — 영업이익률/순이익률/ROE/ROA + 등급.

    Returns
    -------
    pl.DataFrame
        stockCode : str — 종목코드
        corpName : str — 회사명
        opMargin : float — 영업이익률 (%)
        netMargin : float — 순이익률 (%)
        roe : float — 자기자본이익률 (%)
        roa : float — 총자산이익률 (%)
        grade : str — 등급 (우수/양호/보통/저수익/적자)
    """
    df = scanEdgarAccounts(
        ["sales", "operating_profit", "net_profit", "total_assets", "total_stockholders_equity"],
    )
    if df.is_empty():
        return df
    result = df.with_columns(
        pct(pl.col("operating_profit"), pl.col("sales")).alias("opMargin"),
        pct(pl.col("net_profit"), pl.col("sales")).alias("netMargin"),
        pct(pl.col("net_profit"), pl.col("total_stockholders_equity")).alias("roe"),
        pct(pl.col("net_profit"), pl.col("total_assets")).alias("roa"),
    )
    result = result.with_columns(
        pl.when(pl.max_horizontal("opMargin", "roe") >= 20)
        .then(pl.lit("우수"))
        .when(pl.max_horizontal("opMargin", "roe") >= 10)
        .then(pl.lit("양호"))
        .when(pl.max_horizontal("opMargin", "roe") >= 5)
        .then(pl.lit("보통"))
        .when(pl.max_horizontal("opMargin", "roe") >= 0)
        .then(pl.lit("저수익"))
        .otherwise(pl.lit("적자"))
        .alias("grade"),
    )
    return result.select(
        "stockCode",
        "corpName",
        "opMargin",
        "netMargin",
        "roe",
        "roa",
        "grade",
    ).sort("roe", descending=True, nulls_last=True)


# ── growth ──


def _scanGrowth(**_kw) -> pl.DataFrame:
    """성장성 — 매출/영업이익/순이익 YoY + 패턴 분류.

    Returns
    -------
    pl.DataFrame
        stockCode : str — 종목코드
        corpName : str — 회사명
        revenueYoy : float — 매출 전년대비 (%)
        opYoy : float — 영업이익 전년대비 (%)
        niYoy : float — 순이익 전년대비 (%)
        pattern : str — 패턴 (고성장/성장/정체/역성장/급감)
    """
    df = scanEdgarAccounts(["sales", "operating_profit", "net_profit"])
    if df.is_empty():
        return df
    result = df.with_columns(
        pct(pl.col("sales") - pl.col("sales_prev"), pl.col("sales_prev")).alias("revenueYoy"),
        pct(pl.col("operating_profit") - pl.col("operating_profit_prev"), pl.col("operating_profit_prev")).alias(
            "opYoy"
        ),
        pct(pl.col("net_profit") - pl.col("net_profit_prev"), pl.col("net_profit_prev")).alias("niYoy"),
    )
    result = result.with_columns(
        pl.when(pl.col("revenueYoy") >= 20)
        .then(pl.lit("고성장"))
        .when(pl.col("revenueYoy") >= 5)
        .then(pl.lit("성장"))
        .when(pl.col("revenueYoy") >= -5)
        .then(pl.lit("정체"))
        .when(pl.col("revenueYoy") >= -20)
        .then(pl.lit("역성장"))
        .otherwise(pl.lit("급감"))
        .alias("pattern"),
    )
    return result.select(
        "stockCode",
        "corpName",
        "revenueYoy",
        "opYoy",
        "niYoy",
        "pattern",
    ).sort("revenueYoy", descending=True, nulls_last=True)


# ── quality ──


def _scanQuality(**_kw) -> pl.DataFrame:
    """이익의 질 — Accrual Ratio + CF/NI.

    Returns
    -------
    pl.DataFrame
        stockCode : str — 종목코드
        corpName : str — 회사명
        cfToNi : float — 영업CF/순이익 (배), 극단값(±20 초과) 제거
        accrualRatio : float — 발생액비율 (NI-OCF)/총자산
        grade : str — 등급 (우수/양호/보통/주의/위험)
    """
    df = scanEdgarAccounts(["net_profit", "operating_cashflow", "total_assets"])
    if df.is_empty():
        return df
    result = df.with_columns(
        safeDiv(pl.col("operating_cashflow"), pl.col("net_profit")).round(2).alias("cfToNi"),
        safeDiv(
            pl.col("net_profit") - pl.col("operating_cashflow"),
            pl.col("total_assets"),
        )
        .round(4)
        .alias("accrualRatio"),
    )
    # cfToNi 극단값 제거 (±20 초과 → None)
    result = result.with_columns(
        pl.when(pl.col("cfToNi").abs() > 20).then(None).otherwise(pl.col("cfToNi")).alias("cfToNi"),
    )
    result = result.with_columns(
        pl.when((pl.col("cfToNi") >= 0.8) & (pl.col("accrualRatio").abs() < 0.05))
        .then(pl.lit("우수"))
        .when((pl.col("cfToNi") >= 0.5) & (pl.col("accrualRatio").abs() < 0.10))
        .then(pl.lit("양호"))
        .when(pl.col("cfToNi") >= 0)
        .then(pl.lit("보통"))
        .when(pl.col("cfToNi") < 0)
        .then(pl.lit("주의"))
        .otherwise(pl.lit("위험"))
        .alias("grade"),
    )
    return result.select(
        "stockCode",
        "corpName",
        "cfToNi",
        "accrualRatio",
        "grade",
    ).sort("cfToNi", descending=True, nulls_last=True)


# ── liquidity ──


def _scanLiquidity(**_kw) -> pl.DataFrame:
    """유동성 — 유동비율 + 당좌비율.

    Returns
    -------
    pl.DataFrame
        stockCode : str — 종목코드
        corpName : str — 회사명
        currentRatio : float — 유동비율 (%)
        quickRatio : float — 당좌비율 (%)
        grade : str — 등급 (우수/양호/보통/주의/위험)
    """
    df = scanEdgarAccounts(["current_assets", "current_liabilities", "inventories"])
    if df.is_empty():
        return df
    result = df.with_columns(
        pct(pl.col("current_assets"), pl.col("current_liabilities")).alias("currentRatio"),
        pct(
            pl.col("current_assets") - pl.col("inventories").fill_null(0),
            pl.col("current_liabilities"),
        ).alias("quickRatio"),
    )
    result = result.with_columns(
        pl.when(pl.col("currentRatio") >= 200)
        .then(pl.lit("우수"))
        .when(pl.col("currentRatio") >= 150)
        .then(pl.lit("양호"))
        .when(pl.col("currentRatio") >= 100)
        .then(pl.lit("보통"))
        .when(pl.col("currentRatio") >= 50)
        .then(pl.lit("주의"))
        .otherwise(pl.lit("위험"))
        .alias("grade"),
    )
    return result.select(
        "stockCode",
        "corpName",
        "currentRatio",
        "quickRatio",
        "grade",
    ).sort("currentRatio", descending=True, nulls_last=True)


# ── efficiency ──


def _scanEfficiency(**_kw) -> pl.DataFrame:
    """효율성 — 자산회전율 + CCC.

    Returns
    -------
    pl.DataFrame
        stockCode : str — 종목코드
        corpName : str — 회사명
        assetTurnover : float — 총자산회전율 (배)
        ccc : float — 현금전환주기 (일)
        grade : str — 등급 (우수/양호/보통/비효율)
    """
    df = scanEdgarAccounts(
        [
            "sales",
            "total_assets",
            "inventories",
            "trade_and_other_receivables",
            "trade_and_other_payables",
        ]
    )
    if df.is_empty():
        return df
    result = df.with_columns(
        safeDiv(pl.col("sales"), pl.col("total_assets")).round(2).alias("assetTurnover"),
        # CCC = 재고일수 + 매출채권일수 - 매입채무일수
        (
            safeDiv(pl.col("inventories").fill_null(0) * 365, pl.col("sales"))
            + safeDiv(pl.col("trade_and_other_receivables").fill_null(0) * 365, pl.col("sales"))
            - safeDiv(pl.col("trade_and_other_payables").fill_null(0) * 365, pl.col("sales"))
        )
        .round(0)
        .alias("ccc"),
    )
    result = result.with_columns(
        pl.when(pl.col("assetTurnover") >= 1.5)
        .then(pl.lit("우수"))
        .when(pl.col("assetTurnover") >= 1.0)
        .then(pl.lit("양호"))
        .when(pl.col("assetTurnover") >= 0.5)
        .then(pl.lit("보통"))
        .otherwise(pl.lit("비효율"))
        .alias("grade"),
    )
    return result.select(
        "stockCode",
        "corpName",
        "assetTurnover",
        "ccc",
        "grade",
    ).sort("assetTurnover", descending=True, nulls_last=True)


# ── cashflow ──


def _scanCashflow(**_kw) -> pl.DataFrame:
    """현금흐름 — OCF/ICF/FCF + 패턴 분류.

    Returns
    -------
    pl.DataFrame
        stockCode : str — 종목코드
        corpName : str — 회사명
        operating_cashflow : float — 영업활동 현금흐름 (USD)
        investing_cashflow : float — 투자활동 현금흐름 (USD)
        fcf : float — 잉여현금흐름 OCF+CAPEX (USD)
        ocfMargin : float — OCF/매출 (%)
        pattern : str — 패턴 (성장투자형/공격성장형/외부의존형/축소정리형/현금위기형/기타)
    """
    df = scanEdgarAccounts(
        [
            "operating_cashflow",
            "investing_cashflow",
            "financing_cash_flow",
            "capex",
            "sales",
        ]
    )
    if df.is_empty():
        return df
    result = df.with_columns(
        (pl.col("operating_cashflow") + pl.col("capex").fill_null(0)).alias("fcf"),
    )
    result = result.with_columns(
        pct(pl.col("operating_cashflow"), pl.col("sales")).alias("ocfMargin"),
    )
    # 현금흐름 패턴 분류 (OCF+/-, ICF+/-, FCF+/-)
    result = result.with_columns(
        pl.when(
            (pl.col("operating_cashflow") > 0)
            & (pl.col("investing_cashflow") < 0)
            & (pl.col("financing_cash_flow") < 0)
        )
        .then(pl.lit("성장투자형"))
        .when(
            (pl.col("operating_cashflow") > 0)
            & (pl.col("investing_cashflow") < 0)
            & (pl.col("financing_cash_flow") > 0)
        )
        .then(pl.lit("공격성장형"))
        .when((pl.col("operating_cashflow") < 0) & (pl.col("financing_cash_flow") > 0))
        .then(pl.lit("외부의존형"))
        .when(
            (pl.col("operating_cashflow") > 0)
            & (pl.col("investing_cashflow") > 0)
            & (pl.col("financing_cash_flow") < 0)
        )
        .then(pl.lit("축소정리형"))
        .when((pl.col("operating_cashflow") < 0) & (pl.col("investing_cashflow") > 0))
        .then(pl.lit("현금위기형"))
        .otherwise(pl.lit("기타"))
        .alias("pattern"),
    )
    return result.select(
        "stockCode",
        "corpName",
        "operating_cashflow",
        "investing_cashflow",
        "fcf",
        "ocfMargin",
        "pattern",
    ).sort("fcf", descending=True, nulls_last=True)


# ── dividendTrend ──


def _scanDividendTrend(**_kw) -> pl.DataFrame:
    """배당추이 — 배당금액 + 배당성향 + 등급.

    Returns
    -------
    pl.DataFrame
        stockCode : str — 종목코드
        corpName : str — 회사명
        dividendAmount : float — 배당금 절대값 (USD)
        payoutRatio : float — 배당성향 (%), 극단값(±200% 초과) 제거
        grade : str — 등급 (양호/보통/주의/무배당)
    """
    df = scanEdgarAccounts(["dividends_paid", "net_profit"])
    if df.is_empty():
        return df
    result = df.with_columns(
        pl.col("dividends_paid").abs().alias("dividendAmount"),
        pct(pl.col("dividends_paid").abs(), pl.col("net_profit")).alias("payoutRatio"),
    )
    # payoutRatio 극단값 제거
    result = result.with_columns(
        pl.when(pl.col("payoutRatio").abs() > 200).then(None).otherwise(pl.col("payoutRatio")).alias("payoutRatio"),
    )
    result = result.with_columns(
        pl.when(pl.col("dividendAmount").is_null() | (pl.col("dividendAmount") == 0))
        .then(pl.lit("무배당"))
        .when(pl.col("payoutRatio").is_not_null() & (pl.col("payoutRatio") >= 30))
        .then(pl.lit("양호"))
        .when(pl.col("payoutRatio").is_not_null() & (pl.col("payoutRatio") >= 10))
        .then(pl.lit("보통"))
        .otherwise(pl.lit("주의"))
        .alias("grade"),
    )
    return result.select(
        "stockCode",
        "corpName",
        "dividendAmount",
        "payoutRatio",
        "grade",
    ).sort("dividendAmount", descending=True, nulls_last=True)


# ── Dispatch Table ──

# ── capital ──


def _scanCapital(**_kw) -> pl.DataFrame:
    """주주환원 — 배당 + 자사주 + 분류.

    Returns
    -------
    pl.DataFrame
        stockCode : str — 종목코드
        corpName : str — 회사명
        dividendAmount : float — 배당금 절대값 (USD)
        payoutRatio : float — 배당성향 (%), 극단값 제거
        treasury_stock : float — 자기주식 (USD)
        classification : str — 분류 (적극환원/환원형/자사주/중립)
    """
    df = scanEdgarAccounts(["dividends_paid", "net_profit", "treasury_stock"])
    if df.is_empty():
        return df
    result = df.with_columns(
        pl.col("dividends_paid").abs().alias("dividendAmount"),
        pct(pl.col("dividends_paid").abs(), pl.col("net_profit")).alias("payoutRatio"),
    )
    result = result.with_columns(
        pl.when(pl.col("payoutRatio").abs() > 200).then(None).otherwise(pl.col("payoutRatio")).alias("payoutRatio"),
    )
    result = result.with_columns(
        pl.when(
            (pl.col("dividendAmount") > 0)
            & (pl.col("treasury_stock").is_not_null())
            & (pl.col("treasury_stock").abs() > 0)
        )
        .then(pl.lit("적극환원"))
        .when(pl.col("dividendAmount") > 0)
        .then(pl.lit("환원형"))
        .when(pl.col("treasury_stock").is_not_null() & (pl.col("treasury_stock").abs() > 0))
        .then(pl.lit("자사주"))
        .otherwise(pl.lit("중립"))
        .alias("classification"),
    )
    return result.select(
        "stockCode",
        "corpName",
        "dividendAmount",
        "payoutRatio",
        "treasury_stock",
        "classification",
    ).sort("dividendAmount", descending=True, nulls_last=True)


# ── debt ──


def _scanDebt(**_kw) -> pl.DataFrame:
    """부채구조 — 부채비율 + ICR + 차입금 구조.

    Returns
    -------
    pl.DataFrame
        stockCode : str — 종목코드
        corpName : str — 회사명
        debtRatio : float — 부채비율 (%)
        icr : float — 이자보상배율 (배)
        shortTermRatio : float — 단기차입금 비중 (%)
        riskLevel : str — 위험등급 (안전/주의/관찰/고위험)
    """
    df = scanEdgarAccounts(
        [
            "total_liabilities",
            "total_stockholders_equity",
            "shortterm_borrowings",
            "longterm_borrowings",
            "operating_profit",
            "interest_expense",
        ]
    )
    if df.is_empty():
        return df
    result = df.with_columns(
        pct(pl.col("total_liabilities"), pl.col("total_stockholders_equity")).alias("debtRatio"),
        safeDiv(pl.col("operating_profit"), pl.col("interest_expense").abs()).round(2).alias("icr"),
        pct(
            pl.col("shortterm_borrowings").fill_null(0),
            pl.col("shortterm_borrowings").fill_null(0) + pl.col("longterm_borrowings").fill_null(0),
        ).alias("shortTermRatio"),
    )
    result = result.with_columns(
        pl.when(pl.col("debtRatio") < 100)
        .then(pl.lit("안전"))
        .when(pl.col("debtRatio") < 200)
        .then(pl.lit("주의"))
        .when(pl.col("debtRatio") < 400)
        .then(pl.lit("관찰"))
        .otherwise(pl.lit("고위험"))
        .alias("riskLevel"),
    )
    return result.select(
        "stockCode",
        "corpName",
        "debtRatio",
        "icr",
        "shortTermRatio",
        "riskLevel",
    ).sort("debtRatio", nulls_last=True)


# ── valuation ──


def _scanValuation(**_kw) -> pl.DataFrame:
    """밸류에이션 — EBITDA + 자기자본승수 + ROE.

    Returns
    -------
    pl.DataFrame
        stockCode : str — 종목코드
        corpName : str — 회사명
        ebitda : float — EBITDA (USD)
        equityMultiplier : float — 자기자본승수 총자산/자본 (배)
        roe : float — 자기자본이익률 (%)
    """
    df = scanEdgarAccounts(
        [
            "net_profit",
            "total_stockholders_equity",
            "total_assets",
            "total_liabilities",
            "cash_and_cash_equivalents",
            "operating_profit",
            "depreciation_amortization",
        ],
    )
    if df.is_empty():
        return df

    # shares outstanding 추가
    result = df.with_columns(
        (pl.col("operating_profit").fill_null(0) + pl.col("depreciation_amortization").fill_null(0)).alias("ebitda"),
    )

    # PER/PBR은 시가총액 필요 — 현재는 기본 재무비율만 제공
    result = result.with_columns(
        safeDiv(pl.col("total_assets"), pl.col("total_stockholders_equity")).round(2).alias("equityMultiplier"),
        pct(pl.col("net_profit"), pl.col("total_stockholders_equity")).alias("roe"),
    )

    return result.select(
        "stockCode",
        "corpName",
        "ebitda",
        "equityMultiplier",
        "roe",
    ).sort("ebitda", descending=True, nulls_last=True)


# ── audit ──


def _scanAudit(**_kw) -> pl.DataFrame:
    """감사 — XBRL 감사/비감사 보수.

    Returns
    -------
    pl.DataFrame
        stockCode : str — 종목코드
        corpName : str — 회사명
        AuditFees : float — 감사보수 (USD)
        NonAuditServicesFees : float — 비감사 보수 (USD)
        AllOtherFees : float — 기타 보수 (USD)
        TaxFees : float — 세무 보수 (USD)
    """
    df = scanEdgarAccounts(
        ["sales"],  # 기본 계정으로 종목 목록 획득
    )
    if df.is_empty():
        return df

    # XBRL 감사비용 태그 직접 스캔
    from dartlab.scan.builders.edgar.helpers import scanEdgarRawTags

    auditDf = scanEdgarRawTags(
        ["AuditFees", "NonAuditServicesFees", "AllOtherFees", "TaxFees"],
    )
    if auditDf.is_empty():
        return auditDf

    return auditDf.sort("AuditFees", descending=True, nulls_last=True)


_DISPATCH = {
    "profitability": _scanProfitability,
    "growth": _scanGrowth,
    "quality": _scanQuality,
    "liquidity": _scanLiquidity,
    "efficiency": _scanEfficiency,
    "cashflow": _scanCashflow,
    "dividendTrend": _scanDividendTrend,
    "capital": _scanCapital,
    "debt": _scanDebt,
    "valuation": _scanValuation,
    "audit": _scanAudit,
}
