"""계정 정규화 추출 — DART finance.parquet + EDGAR 직접 컬럼.

`_ACCOUNT_PATTERNS` 정규식 + `_ACCOUNT_SJ` sj_div 후보로 단일 종목/단일 기간
DataFrame 에서 표준 계정 (sales/operating_profit 등) 의 값 추출.
"""

from __future__ import annotations

from dartlab.core.polarsUtil import isEmptyDf

_ACCOUNT_PATTERNS: dict[str, list[str]] = {
    "sales": [
        r"^매출액$",
        r"^수익\(매출액\)$",
        r"^수익$",
        r"^영업수익$",
        r"^매출$",
        r"매출액",
    ],
    "operating_profit": [
        r"^영업이익$",
        r"^영업이익\(손실\)$",
        r"^영업손익$",
        r"영업이익",
    ],
    "net_income": [
        r"^당기순이익$",
        r"^당기순이익\(손실\)$",
        r"^당기순손익$",
        r"^연결당기순이익$",
        r"^지배기업소유주지분순이익$",
        r"^지배기업의?\s*소유주에?\s*귀속되는?\s*당기순이익$",
        r"당기순이익",
    ],
    "total_assets": [r"^자산총계$"],
    "total_liabilities": [r"^부채총계$"],
    "total_equity": [
        r"^자본총계$",
        r"^지배기업소유주지분$",
    ],
    "operating_cf": [
        r"^영업활동현금흐름$",
        r"^영업활동으로?\s*인한?\s*현금흐름$",
        r"영업활동.*현금흐름",
    ],
    "investing_cf": [
        r"^투자활동현금흐름$",
        r"투자활동.*현금흐름",
    ],
    "financing_cf": [
        r"^재무활동현금흐름$",
        r"재무활동.*현금흐름",
    ],
    "current_assets": [r"^유동자산$", r"유동자산"],
    "current_liabilities": [r"^유동부채$", r"유동부채"],
    "retained_earnings": [
        r"^이익잉여금$",
        r"^이익잉여금\(결손금\)$",
        r"이익잉여금",
    ],
    "gross_profit": [r"^매출총이익$", r"^매출총손익$", r"매출총이익"],
    "cost_of_sales": [r"^매출원가$", r"매출원가"],
    "inventory": [r"^재고자산$", r"재고자산"],
    "accounts_receivable": [
        r"^매출채권$",
        r"^매출채권\s*및?\s*기타채권$",
        r"매출채권",
    ],
    "depreciation": [
        r"^감가상각비$",
        r"감가상각비",
        r"^감가상각및?\s*무형자산상각비$",
    ],
    "selling_admin": [
        r"^판매비와?\s*관리비$",
        r"^판매관리비$",
        r"판매비.*관리비",
    ],
}

_ACCOUNT_SJ: dict[str, list[str]] = {
    "sales": ["IS", "CIS"],
    "operating_profit": ["IS", "CIS"],
    "net_income": ["IS", "CIS"],
    "total_assets": ["BS"],
    "total_liabilities": ["BS"],
    "total_equity": ["BS"],
    "operating_cf": ["CF"],
    "investing_cf": ["CF"],
    "financing_cf": ["CF"],
    "current_assets": ["BS"],
    "current_liabilities": ["BS"],
    "retained_earnings": ["BS"],
    "gross_profit": ["IS", "CIS"],
    "cost_of_sales": ["IS", "CIS"],
    "inventory": ["BS"],
    "accounts_receivable": ["BS"],
    "depreciation": ["IS", "CIS", "CF"],
    "selling_admin": ["IS", "CIS"],
}


def extractAccount(df, key: str) -> float | None:
    """단일 종목/단일 기간 DataFrame에서 표준 계정 추출 — DART/EDGAR 자동 분기.

    Capabilities:
        - DART finance.parquet: ``_ACCOUNT_PATTERNS`` 정규식 + ``_ACCOUNT_SJ`` sj_div 순회 매칭
        - EDGAR: ``ACCOUNT_MAP`` 직접 컬럼 + net_profit/total_stockholders_equity 별칭 처리
        - ``parseNumStr`` 로 thstrm_amount 문자열 → float 안전 변환

    Args:
        df: pl.DataFrame — DART (sj_div/account_nm/thstrm_amount) 또는 EDGAR (직접 컬럼).
        key: 표준 키 (``"sales"``, ``"operating_profit"``, ``"net_income"``, ``"total_assets"`` ...).

    Returns:
        float | None — DART 는 패턴 매칭, EDGAR 는 직접 컬럼. 매칭 실패 시 None.

    Guide:
        Quant factor (PER/ROE) 의 계정 정규화 SSOT. 새 계정 추가 시 ``_ACCOUNT_PATTERNS`` +
        ``_ACCOUNT_SJ`` 에 함께 등록.

    When:
        Cross-sectional factor 계산 + AI 회계 항목 답변.

    How:
        EDGAR 분기: fy 컬럼 존재 + sj_div 부재 판정 → ACCOUNT_MAP. DART 분기: sj_div × 패턴
        순회 → 첫 매칭.

    Requires:
        DART: sj_div/account_nm/thstrm_amount 컬럼. EDGAR: ``synth.scanBridge.ACCOUNT_MAP``.

    Raises:
        없음 — ComputeError/ValueError/TypeError 는 skip + None.

    Example:
        >>> extractAccount(df, "sales")
        279600000000.0

    See Also:
        - extractAccounts : 여러 키 일괄
        - _ACCOUNT_PATTERNS : 정규식 SSOT
        - synth.scanBridge.ACCOUNT_MAP : EDGAR 매핑

    AIContext:
        AI 가 "매출/영업이익" 류 질문 답변 시 본 함수로 단일 값 추출 → factor 계산 전 정규화.
    """
    import polars as pl

    if isEmptyDf(df):
        return None

    if "fy" in df.columns and "sj_div" not in df.columns:
        from dartlab.synth.scanBridge import ACCOUNT_MAP

        col = ACCOUNT_MAP.get(key, key)
        if col == "net_income" and "net_profit" in df.columns:
            col = "net_profit"
        if col == "total_equity" and "total_stockholders_equity" in df.columns:
            col = "total_stockholders_equity"
        if col not in df.columns:
            return None
        try:
            v = df[col][0]
            return float(v) if v is not None else None
        except (ValueError, TypeError, IndexError):
            return None

    patterns = _ACCOUNT_PATTERNS.get(key)
    sj_list = _ACCOUNT_SJ.get(key)
    if patterns is None or sj_list is None:
        return None

    for sj in sj_list:
        base = df.filter(pl.col("sj_div") == sj)
        if base.is_empty():
            continue
        for pat in patterns:
            try:
                rows = base.filter(pl.col("account_nm").str.contains(pat))
            except (pl.exceptions.ComputeError, AttributeError):
                continue
            if len(rows) == 0:
                continue
            amounts = rows.get_column("thstrm_amount").to_list()
            from dartlab.core.utils.helpers import parseNumStr

            for amt in amounts:
                v = parseNumStr(amt) if not isinstance(amt, (int, float)) else float(amt)
                if v is not None:
                    return v
    return None


def extractAccounts(df, keys: list[str]) -> dict[str, float | None]:
    """여러 표준 계정 일괄 추출 — DART finance.parquet 용.

    Parameters
    ----------
    df : pl.DataFrame
        DART finance.parquet 의 단일 종목/단일 기간 DataFrame.
        sj_div, account_nm, thstrm_amount 컬럼 보유.
    keys : list[str]
        표준 계정 키 리스트
        ("sales", "operating_profit", "net_income", "total_assets",
         "total_liabilities", "total_equity", "operating_cf",
         "investing_cf", "financing_cf").

    Returns
    -------
    dict[str, float | None]
        키별 금액 (원). 매칭 실패 시 해당 키 = None.

    Examples
    --------
    >>> extractAccounts(df, ["sales", "net_income"])

    Requires:
        df 의 sj_div / account_nm / thstrm_amount 컬럼 존재.

    Raises:
        없음 — 매칭 실패는 None 값.
    """
    return {k: extractAccount(df, k) for k in keys}
