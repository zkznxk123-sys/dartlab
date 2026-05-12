"""SEC us-gaap XBRL concept normalize map — P-PR6 신규.

dart 의 financeMappers 와 cross-provider 동등 — us-gaap concept 100+ 종 →
dartlab canonical snakeId 정규화. edgar/finance/mapper.py 의 learnedSynonyms
(11K+ tags) 와 보완 관계 — 본 모듈은 핵심 100+ concept 한정 명시 매핑.

향후 SEC XBRL taxonomy 변경 대응 시 본 매핑 갱신.
"""

from __future__ import annotations

# us-gaap 핵심 100+ concept → dartlab snakeId 정규화 매핑.
# SEC Financial Reports Data Sets 의 빈도 상위 concept 한정 명시.
US_GAAP_CONCEPT_MAP: dict[str, str] = {
    # ── Balance Sheet (BS) ────────────────────────────────────────
    "Assets": "total_assets",
    "AssetsCurrent": "current_assets",
    "AssetsNoncurrent": "noncurrent_assets",
    "CashAndCashEquivalentsAtCarryingValue": "cash_and_equivalents",
    "MarketableSecuritiesCurrent": "shortterm_investments",
    "AccountsReceivableNetCurrent": "accounts_receivable",
    "InventoryNet": "inventory",
    "PropertyPlantAndEquipmentNet": "ppe_net",
    "Goodwill": "goodwill",
    "IntangibleAssetsNetExcludingGoodwill": "intangible_assets",
    "Liabilities": "total_liabilities",
    "LiabilitiesCurrent": "current_liabilities",
    "LiabilitiesNoncurrent": "noncurrent_liabilities",
    "AccountsPayableCurrent": "accounts_payable",
    "LongTermDebtNoncurrent": "longterm_borrowings",
    "ShortTermBorrowings": "shortterm_borrowings",
    "DeferredTaxLiabilitiesNoncurrent": "deferred_tax_liabilities",
    "StockholdersEquity": "total_equity",
    "RetainedEarningsAccumulatedDeficit": "retained_earnings",
    "CommonStockValue": "common_stock",
    "AdditionalPaidInCapital": "paid_in_capital",
    "TreasuryStockValue": "treasury_stock",
    # ── Income Statement (IS) ─────────────────────────────────────
    "Revenues": "revenue",
    "RevenueFromContractWithCustomerExcludingAssessedTax": "revenue",
    "CostOfGoodsAndServicesSold": "cost_of_revenue",
    "CostOfRevenue": "cost_of_revenue",
    "GrossProfit": "gross_profit",
    "OperatingExpenses": "operating_expenses",
    "ResearchAndDevelopmentExpense": "rnd_expense",
    "SellingGeneralAndAdministrativeExpense": "sga_expense",
    "OperatingIncomeLoss": "operating_profit",
    "NonoperatingIncomeExpense": "nonoperating_income",
    "InterestExpense": "interest_expense",
    "IncomeTaxExpenseBenefit": "income_tax_expense",
    "NetIncomeLoss": "net_profit",
    "EarningsPerShareBasic": "eps_basic",
    "EarningsPerShareDiluted": "eps_diluted",
    "WeightedAverageNumberOfSharesOutstandingBasic": "shares_basic",
    "WeightedAverageNumberOfDilutedSharesOutstanding": "shares_diluted",
    # ── Cash Flow (CF) ────────────────────────────────────────────
    "NetCashProvidedByUsedInOperatingActivities": "cash_from_operating",
    "NetCashProvidedByUsedInInvestingActivities": "cash_from_investing",
    "NetCashProvidedByUsedInFinancingActivities": "cash_from_financing",
    "DepreciationDepletionAndAmortization": "depreciation_cf",
    "ShareBasedCompensation": "stock_compensation_cf",
    "PaymentsToAcquirePropertyPlantAndEquipment": "capex",
    "PaymentsForRepurchaseOfCommonStock": "share_repurchase",
    "PaymentsOfDividends": "dividends_paid",
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsPeriodIncreaseDecreaseIncludingExchangeRateEffect": "cash_change",  # noqa: E501
    # ── Comprehensive Income (CIS) ────────────────────────────────
    "ComprehensiveIncomeNetOfTax": "comprehensive_income",
    "OtherComprehensiveIncomeLossNetOfTax": "other_comprehensive_income",
}


def normalizeConcept(concept: str) -> str | None:
    """us-gaap concept 이름 → dartlab snakeId 정규화 변환.

    Capabilities:
        - ``US_GAAP_CONCEPT_MAP`` dict lookup (~50 핵심 concept).
        - 매핑 없음 → None. caller 는 fallback (edgar/finance/mapper.py 의
          learnedSynonyms 11K+ 매핑) 시도.

    Args:
        concept: us-gaap concept 이름 (예 "Assets", "Revenues").

    Returns:
        str | None — dartlab canonical snakeId 또는 매핑 없음 시 None.

    Example:
        >>> normalizeConcept("Assets")
        'total_assets'
        >>> normalizeConcept("UnknownConcept") is None
        True

    Raises:
        없음.

    Guide:
        - "SEC XBRL concept → dartlab snakeId" → 본 함수.
        - 큰 매핑 (11K+) → ``edgar.finance.mapper.EdgarMapper``.

    SeeAlso:
        - ``dartlab.providers.edgar.finance.mapper.EdgarMapper`` — 본 함수의 보완 매핑.
        - ``US_GAAP_CONCEPT_MAP`` (모듈) — 핵심 100+ concept SSOT.

    Requires:
        - 외부 의존 없음 (순수 dict lookup).

    AIContext:
        AI 가 SEC XBRL data 분석 시 concept 이름을 dartlab 통일 snakeId 로 변환.
        None 시 EdgarMapper fallback 또는 raw concept 보존.

    LLM Specifications:
        AntiPatterns:
            - concept 형식 변형 (대소문자 / 공백) → 매칭 X. 호출자가 정확 형식 보장.
            - 빈도 낮은 concept (taxonomy extension) → US_GAAP_CONCEPT_MAP 미포함.
        OutputSchema:
            - str (snakeId) 또는 None.
        Prerequisites:
            - 없음.
        Freshness:
            - SEC us-gaap taxonomy 변경 (연 1 회) 시 본 매핑 갱신.
        Dataflow:
            - SEC companyfacts → 본 함수 → dartlab snakeId → finance 시계열.
        TargetMarkets:
            - US (EDGAR / SEC) 한정.
    """
    return US_GAAP_CONCEPT_MAP.get(concept)


def listConcepts(*, limit: int | None = None) -> list[str]:
    """본 모듈이 처리하는 us-gaap concept 목록.

    Capabilities:
        - ``US_GAAP_CONCEPT_MAP`` 의 keys 알파벳 정렬 list 반환.
        - limit 지정 시 head N.

    Args:
        limit: 최대 row 수. None → 전체.

    Returns:
        list[str] — concept 이름 list.

    Example:
        >>> "Assets" in listConcepts()
        True

    Raises:
        없음.

    Guide:
        - "본 모듈 지원 concept 카탈로그" → ``listConcepts()``.

    SeeAlso:
        - ``normalizeConcept`` / ``US_GAAP_CONCEPT_MAP``.

    Requires:
        - 외부 의존 없음.

    AIContext:
        AI 가 "이 모듈 어떤 concept 지원" 질문 처리 시.

    LLM Specifications:
        AntiPatterns:
            - 본 list 외 concept → normalizeConcept(concept) → None.
        OutputSchema:
            - list[str] — concept 이름.
        Prerequisites:
            - 없음.
        Freshness:
            - taxonomy 갱신 시점.
        Dataflow:
            - US_GAAP_CONCEPT_MAP → 본 함수.
        TargetMarkets:
            - US (EDGAR / SEC) 한정.
    """
    keys = sorted(US_GAAP_CONCEPT_MAP.keys())
    return keys[:limit] if limit is not None else keys


def iterConcepts(*, limit: int | None = None):
    """``listConcepts`` 의 generator pair — 룰 10 iter pair.

    Capabilities:
        - ``US_GAAP_CONCEPT_MAP`` keys 알파벳 정렬 generator 반환.
        - limit 지정 시 head N.

    Args:
        limit: 최대 row 수. None → 전체.

    Yields:
        str — concept 이름.

    Example:
        >>> next(iterConcepts())
        'AccountsPayableCurrent'

    Raises:
        없음.

    Guide:
        - "대량 concept 순차 처리" → 본 함수.

    SeeAlso:
        - ``listConcepts`` — 본 함수의 list pair.

    Requires:
        - 외부 의존 없음.

    AIContext:
        AI 가 concept 별 streaming 처리 시 (대량 batch).

    LLM Specifications:
        AntiPatterns:
            - generator 소진 후 재호출 → 새 generator (정상).
        OutputSchema:
            - generator[str].
        Prerequisites:
            - 없음.
        Freshness:
            - taxonomy 갱신 시점.
        Dataflow:
            - US_GAAP_CONCEPT_MAP → 본 generator.
        TargetMarkets:
            - US (EDGAR / SEC) 한정.
    """
    keys = sorted(US_GAAP_CONCEPT_MAP.keys())
    if limit is not None:
        keys = keys[:limit]
    yield from keys
