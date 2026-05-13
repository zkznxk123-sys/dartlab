"""scan finance account labels and extraction helpers."""

from __future__ import annotations

import polars as pl

from dartlab.core.utils.helpers import parseNumStr

# 같은 회계 개념의 snake_id / 표시명 변형을 한 곳에 통합.
# 신규 변형 발견 시 여기서만 추가 → scan/{efficiency,growth,profitability,valuation} 자동 반영.

REVENUE_IDS = {"Revenue", "revenue", "ifrs-full_Revenue", "dart_Revenue"}
REVENUE_NMS = {"매출액", "수익(매출액)", "영업수익"}

OP_IDS = {
    "ProfitLossFromOperatingActivities",
    "operatingIncome",
    "ifrs-full_ProfitLossFromOperatingActivities",
    "dart_OperatingIncomeLoss",
}
OP_NMS = {"영업이익", "영업이익(손실)"}

NI_IDS = {
    "ProfitLoss",
    "netIncome",
    "ifrs-full_ProfitLoss",
    "dart_ProfitLoss",
    "ProfitLossAttributableToOwnersOfParent",
}
NI_NMS = {"당기순이익", "당기순이익(손실)"}

TA_IDS = {"Assets", "totalAssets", "ifrs-full_Assets", "dart_Assets"}
TA_NMS = {"자산총계", "자산 총계"}

EQ_IDS = {
    "Equity",
    "equity",
    "ifrs-full_Equity",
    "EquityAttributableToOwnersOfParent",
    "ifrs-full_EquityAttributableToOwnersOfParent",
}
EQ_NMS = {"자본총계", "자본 총계", "지배기업 소유주지분"}

LIABILITY_IDS = {"Liabilities", "ifrs-full_Liabilities", "ifrs_Liabilities", "dart_Liabilities"}
LIABILITY_NMS = {"부채총계", "총부채", "부채 총계"}


def extractAccount(sub: pl.DataFrame, ids: set[str], nms: set[str], amtCol: str = "thstrm_amount") -> float | None:
    """DataFrame에서 account_id/account_nm 매칭 → 금액 추출.

    Parameters
    ----------
    sub : pl.DataFrame
        단일 종목의 재무 데이터.
    ids : set[str]
        매칭할 account_id 집합.
    nms : set[str]
        매칭할 account_nm 집합.
    amtCol : str
        금액 컬럼명 (기본 "thstrm_amount").

    Returns
    -------
    float | None
        첫 매칭 계정의 금액 (원). 매칭 없으면 None.

    Raises
    ------
    없음 — row.get 기본값 + parseNumStr None 폴백.

    Examples
    --------
    >>> from dartlab.scan.io.parquet import extractAccount
    >>> rev = extractAccount(subDf, {"Revenue"}, {"매출액"})

    Guide:
        account_id (XBRL tag) 또는 account_nm (한글 표시명) 매칭 row 중 첫 유효 amount 반환.

    Capabilities:
        ``parseNumStr`` 로 콤마/문자열 정수 변환.

    AIContext:
        scan financial 7 axis 의 per-file fallback 경로가 본 함수로 단일 종목 단면에서 계정 값 추출.

    When:
        scan/finance.parquet 합본 없거나 종목별 처리 필요할 때.

    How:
        row iterate → 첫 매칭 row 의 amount → parseNumStr → 반환.

    Requires:
        ``account_id`` · ``account_nm`` · ``amtCol`` 컬럼.

    SeeAlso:
        ``scanFinanceParquets`` — 횡단 합본 dict 반환.
    """
    for row in sub.iter_rows(named=True):
        aid = row.get("account_id", "")
        anm = row.get("account_nm", "")
        if aid in ids or anm in nms:
            val = parseNumStr(row.get(amtCol))
            if val is not None:
                return val
    return None
