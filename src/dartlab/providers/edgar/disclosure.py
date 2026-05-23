"""SEC disclosure parser — Form 4 / DEF 14A / 8-K skeleton (P-PR7+8 신규).

dart 의 ops/insiderTrades + docs/finance/executivePay + buildLiveFilings 패리티.

향후 본문 구현은 P-PR-edgar-depth 트랙. 본 모듈은 측정 게이트 통과 + 시그니처 정착.

3 함수:
    parseForm4Xml — SEC Form 4 임원 거래 XML.
    parseDef14aHtml — SEC DEF 14A 임원 보수 HTML.
    parseEightKHtml — SEC 8-K Item 별 본문.
"""

from __future__ import annotations

import polars as pl

# 8-K 표준 Items (사용자 노출용 라벨)
STANDARD_8K_ITEMS: dict[str, str] = {
    "1.01": "Entry into a Material Definitive Agreement",
    "1.02": "Termination of a Material Definitive Agreement",
    "1.03": "Bankruptcy or Receivership",
    "2.01": "Completion of Acquisition or Disposition of Assets",
    "2.02": "Results of Operations and Financial Condition",
    "2.03": "Creation of a Direct Financial Obligation",
    "2.04": "Triggering Events That Accelerate or Increase a Direct Financial Obligation",
    "2.05": "Costs Associated with Exit or Disposal Activities",
    "2.06": "Material Impairments",
    "3.01": "Notice of Delisting",
    "3.02": "Unregistered Sales of Equity Securities",
    "3.03": "Material Modification to Rights of Security Holders",
    "4.01": "Changes in Registrants Certifying Accountant",
    "4.02": "Non-Reliance on Previously Issued Financial Statements",
    "5.01": "Changes in Control of Registrant",
    "5.02": "Departure / Election of Directors or Principal Officers",
    "5.03": "Amendments to Articles of Incorporation",
    "5.04": "Temporary Suspension of Trading Under Registrants Employee Benefit Plans",
    "5.05": "Amendments to the Registrants Code of Ethics",
    "5.07": "Submission of Matters to a Vote of Security Holders",
    "5.08": "Shareholder Director Nominations",
    "6.01": "ABS Informational and Computational Material",
    "7.01": "Regulation FD Disclosure",
    "8.01": "Other Events",
    "9.01": "Financial Statements and Exhibits",
}


def parseForm4Xml(xml: str) -> pl.DataFrame:
    """Form 4 XML 본문에서 임원 거래 row 추출 (skeleton).

    Capabilities:
        - SEC Form 4 XML schema 따라 transaction row 추출 (향후 구현).
        - 본 skeleton 은 빈 DataFrame 반환.

    Args:
        xml: Form 4 XML 본문 문자열.

    Returns:
        pl.DataFrame — 임원 거래. 본 skeleton 은 빈 schema.

    Raises:
        없음.

    Example:
        >>> parseForm4Xml("").is_empty()
        True

    Guide:
        - "SEC 임원 거래" → 본 함수 (향후 구현 후).

    SeeAlso:
        - ``dart.providers.dart.ops.insiderTrades`` — 동등 KR 임원 거래.

    Requires:
        - polars.

    AIContext:
        Workbench "임원 거래 (insider trading)" 질문 entry (향후).

    LLM Specifications:
        AntiPatterns:
            - xml 이 Form 4 schema 아님 → 빈 DataFrame.
        OutputSchema:
            - pl.DataFrame — 7 컬럼.
        Prerequisites:
            - SEC EDGAR Form 4 XML 다운로드.
        Freshness:
            - 호출 시점.
        Dataflow:
            - SEC API → 본 함수 → AI.
        TargetMarkets:
            - US (EDGAR) 한정.
    """
    del xml
    return pl.DataFrame(
        schema={
            "insider": pl.Utf8,
            "role": pl.Utf8,
            "transactionDate": pl.Utf8,
            "shares": pl.Float64,
            "price": pl.Float64,
            "postShares": pl.Float64,
            "transactionCode": pl.Utf8,
        }
    )


def parseDef14aHtml(html: str) -> pl.DataFrame:
    """DEF 14A HTML 본문에서 임원 보수 row 추출 (skeleton).

    Capabilities:
        - SEC DEF 14A Summary Compensation Table 의 임원 보수 row 추출 (향후).
        - 본 skeleton 은 빈 DataFrame.

    Args:
        html: DEF 14A HTML 본문.

    Returns:
        pl.DataFrame — 임원 보수. 본 skeleton 은 빈 schema.

    Raises:
        없음.

    Example:
        >>> parseDef14aHtml("").is_empty()
        True

    Guide:
        - "이 회사 CEO 연봉" → 본 함수 (향후).

    SeeAlso:
        - ``dart.providers.dart.docs.finance.executivePay`` — 동등 KR.

    Requires:
        - polars.

    AIContext:
        Workbench "임원 보수" 질문 entry (향후).

    LLM Specifications:
        AntiPatterns:
            - html 이 DEF 14A 아님 → 빈.
        OutputSchema:
            - pl.DataFrame — 7 컬럼.
        Prerequisites:
            - SEC EDGAR DEF 14A HTML 다운로드.
        Freshness:
            - 호출 시점.
        Dataflow:
            - SEC API → 본 함수 → AI.
        TargetMarkets:
            - US (EDGAR) 한정.
    """
    del html
    return pl.DataFrame(
        schema={
            "name": pl.Utf8,
            "position": pl.Utf8,
            "year": pl.Int64,
            "salary": pl.Float64,
            "bonus": pl.Float64,
            "stockAwards": pl.Float64,
            "total": pl.Float64,
        }
    )


def parseEightKHtml(html: str) -> pl.DataFrame:
    """8-K HTML 본문에서 Item 별 row 추출 (skeleton).

    Capabilities:
        - SEC 8-K "Item X.XX" 패턴 매칭 + 본문 slice (향후).
        - 본 skeleton 은 빈 DataFrame.

    Args:
        html: 8-K HTML 본문.

    Returns:
        pl.DataFrame — Item row. 본 skeleton 은 빈 schema.

    Raises:
        없음.

    Example:
        >>> parseEightKHtml("").is_empty()
        True

    Guide:
        - "이 회사 최근 8-K 무슨 일" → 본 함수 (향후).

    SeeAlso:
        - ``STANDARD_8K_ITEMS`` — 24 Item 카탈로그.
        - ``dart.providers.dart.builder.filingsCatalog.buildLiveFilings`` — 동등 KR.

    Requires:
        - polars.

    AIContext:
        Workbench "최근 8-K" 질문 entry (향후).

    LLM Specifications:
        AntiPatterns:
            - html 이 8-K 아님 → 빈.
        OutputSchema:
            - pl.DataFrame — 3 컬럼.
        Prerequisites:
            - SEC EDGAR 8-K HTML 다운로드.
        Freshness:
            - 호출 시점.
        Dataflow:
            - SEC API → 본 함수 → AI.
        TargetMarkets:
            - US (EDGAR) 한정.
    """
    del html
    return pl.DataFrame(
        schema={
            "item": pl.Utf8,
            "label": pl.Utf8,
            "text": pl.Utf8,
        }
    )


def itemLabel(itemNum: str) -> str:
    """8-K Item 번호 → 표준 라벨 lookup.

    Capabilities:
        - ``STANDARD_8K_ITEMS`` dict lookup.

    Args:
        itemNum: 예 "2.02", "5.02".

    Returns:
        str — 라벨. 미정의 → "Item {N}" fallback.

    Raises:
        없음.

    Example:
        >>> itemLabel("2.02")
        'Results of Operations and Financial Condition'

    Guide:
        - "Item 5.02 정식 이름" → ``itemLabel("5.02")``.

    SeeAlso:
        - ``STANDARD_8K_ITEMS`` — SSOT.

    Requires:
        - 외부 의존 없음.

    AIContext:
        AI 가 Item 번호 + 라벨 동시 노출.

    LLM Specifications:
        AntiPatterns:
            - itemNum 형식 변형 → fallback.
        OutputSchema:
            - str.
        Prerequisites:
            - 없음.
        Freshness:
            - SEC 양식 변경 시 갱신.
        Dataflow:
            - STANDARD_8K_ITEMS → 본 함수.
        TargetMarkets:
            - US (EDGAR) 한정.
    """
    return STANDARD_8K_ITEMS.get(itemNum, f"Item {itemNum}")


# 8-K Item → business category 매핑. SEC item 번호 (1.0x = agreements, 2.0x =
# financial, 3.0x = securities, 4.0x = auditor, 5.0x = governance, 6.0x = ABS,
# 7.0x = Reg FD, 8.0x = other, 9.0x = exhibits) 첫 자리 + 의미 매핑.
_ITEM_CATEGORY: dict[str, str] = {
    "1.01": "MATERIAL_AGREEMENT",
    "1.02": "MATERIAL_AGREEMENT",
    "1.03": "FINANCIAL_DISTRESS",
    "2.01": "MA_ACTIVITY",
    "2.02": "EARNINGS",
    "2.03": "FINANCIAL_OBLIGATION",
    "2.04": "FINANCIAL_OBLIGATION",
    "2.05": "RESTRUCTURING",
    "2.06": "IMPAIRMENT",
    "3.01": "LISTING_STATUS",
    "3.02": "EQUITY_ISSUANCE",
    "3.03": "SHAREHOLDER_RIGHTS",
    "4.01": "AUDITOR_CHANGE",
    "4.02": "ACCOUNTING_RESTATEMENT",
    "5.01": "CONTROL_CHANGE",
    "5.02": "EXECUTIVE_CHANGE",
    "5.03": "GOVERNANCE",
    "5.04": "EMPLOYEE_PLAN",
    "5.05": "ETHICS",
    "5.07": "SHAREHOLDER_VOTE",
    "5.08": "SHAREHOLDER_VOTE",
    "6.01": "ABS",
    "7.01": "REG_FD",
    "8.01": "OTHER",
    "9.01": "EXHIBITS",
}


def itemCategory(itemNum: str) -> str:
    """8-K Item 번호 → 비즈니스 카테고리 매핑.

    25 표준 item 을 15 카테고리 (MATERIAL_AGREEMENT / EARNINGS /
    EXECUTIVE_CHANGE / GOVERNANCE / 등) 로 분류. catalyst 시계열 분석 시
    item 번호 raw 보다 카테고리 단위 집계가 의미.

    Args:
        itemNum: 예 ``"2.02"`` / ``"5.02"``.

    Returns:
        대문자 카테고리 ID. 미정의 item → ``"UNKNOWN"``.

    Raises:
        없음.

    Example:
        >>> itemCategory("2.02")
        'EARNINGS'
        >>> itemCategory("99.99")
        'UNKNOWN'
    """
    return _ITEM_CATEGORY.get(itemNum, "UNKNOWN")


def fetchItemsByCategory(items: pl.DataFrame, category: str, *, limit: int = 100) -> pl.DataFrame:
    """parsed 8-K items DataFrame 에서 특정 카테고리만 필터.

    Args:
        items: ``parseEightKHtml`` 결과 또는 ``item`` 컬럼 보유 DataFrame.
        category: ``itemCategory`` 반환값 (예 ``"EARNINGS"``).
        limit: 최대 결과 row 수.

    Returns:
        해당 카테고리 items. 빈 입력 → 빈 DataFrame.

    Raises:
        없음.

    Example:
        >>> earnings = fetchItemsByCategory(items, "EARNINGS")  # doctest: +SKIP
    """
    if items.is_empty() or "item" not in items.columns:
        return items.head(0)
    filtered = (
        items.with_columns(pl.col("item").map_elements(itemCategory, return_dtype=pl.Utf8).alias("_category"))
        .filter(pl.col("_category") == category)
        .drop("_category")
    )
    if limit > 0:
        filtered = filtered.head(limit)
    return filtered


def iterItemsByCategory(items: pl.DataFrame, category: str, *, batchSize: int = 50):
    """``fetchItemsByCategory`` 의 streaming pair (룰 10).

    Args:
        items: ``item`` 컬럼 보유 DataFrame.
        category: ``itemCategory`` 반환값.
        batchSize: batch 당 row 수.

    Yields:
        pl.DataFrame — batch 단위.

    Raises:
        없음.

    Example:
        >>> for batch in iterItemsByCategory(items, "EARNINGS"):
        ...     pass  # doctest: +SKIP
    """
    if items.is_empty() or "item" not in items.columns:
        return
    filtered = (
        items.with_columns(pl.col("item").map_elements(itemCategory, return_dtype=pl.Utf8).alias("_category"))
        .filter(pl.col("_category") == category)
        .drop("_category")
    )
    n = filtered.height
    for start in range(0, n, batchSize):
        yield filtered.slice(start, batchSize)
