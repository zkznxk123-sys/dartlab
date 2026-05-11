"""EDGAR 엔진 내부 Company 본체.

DART Company와 동일한 구조를 제공한다.

사용법::

    from dartlab import Company

    c = Company("AAPL")
    c.corpName             # "Apple Inc."
    c.index                # 수평화 보드 DataFrame
    c.show("BS")           # 재무상태표 DataFrame
    c.show("item1Business")        # docs topic DataFrame
    c.trace("BS")          # source provenance
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from dartlab.core.logger import getLogger

_log = getLogger(__name__)


import polars as pl

from dartlab.core.polarsUtil import isEmptyDf
from dartlab.providers.edgar.accessor.docsAccessor import _DocsAccessor
from dartlab.providers.edgar.accessor.financeAccessor import _FinanceAccessor
from dartlab.providers.edgar.accessor.profileAccessor import _ProfileAccessor
from dartlab.providers.edgar.openapi.submissions import SUPPORTED_REGULAR_FORMS
from dartlab.providers.filingHelpers import filingRecord, filterFilingsByKeyword, resolveDateWindow, truncateText

_PERIOD_COLUMN_RE = re.compile(r"^\d{4}(Q[1-4])?$")

_FINANCE_TOPICS = frozenset({"BS", "IS", "CF", "CIS"})


class _EdgarNotesWrapper:
    """DART Notes 객체와 동일 인터페이스를 제공하는 EDGAR notes 래퍼.

    c.notes("inventory") → 카테고리별 구조화 DataFrame
    c.notes.inventory → 동일
    c.notes.keys() → 데이터 있는 카테고리 목록
    c.notes() → TextBlock 원본 검색 (query=None이면 전체)
    """

    def __init__(self, company):
        self._company = company

    def __call__(self, query: str | None = None) -> pl.DataFrame | None:
        # 카테고리명이면 구조화 Notes 반환
        from dartlab.providers.edgar.docs.notesParsers import availableCategories

        if query and query in availableCategories():
            return self._company.docs.notesByCategory(query)
        # 그 외는 TextBlock 원본 검색
        return self._company.docs.notes(query)

    def __getattr__(self, name: str) -> pl.DataFrame | None:
        if name.startswith("_"):
            raise AttributeError(name)
        from dartlab.providers.edgar.docs.notesParsers import availableCategories

        if name in availableCategories():
            return self._company.docs.notesByCategory(name)
        raise AttributeError(f"EDGAR notes에 '{name}' 카테고리 없음. 지원: {availableCategories()}")

    def all(self) -> pl.DataFrame | None:
        """all — TODO 한국어 동작 설명."""
        return self._company.docs.notes(None)

    def keys(self) -> list[str]:
        """데이터가 있는 카테고리 목록."""
        return self._company.docs.noteCategories()

    def keysKr(self) -> list[str]:
        """한국어 카테고리 목록."""
        from dartlab.providers.edgar.docs.notesParsers import CATEGORY_LABELS

        return [CATEGORY_LABELS.get(k, k) for k in self.keys()]

    def quarterly(self, query: str | None = None) -> pl.DataFrame | None:
        """quarterly — TODO 한국어 동작 설명."""
        return self._company.docs.notes(query)


# ── topic 단축 alias ────────────────────────────────────────────
_TOPIC_ALIASES: dict[str, str] = {
    # 10-K 주요 항목 짧은 이름
    "business": "item1Business",
    "riskFactors": "item1ARiskFactors",
    "risk": "item1ARiskFactors",
    "cybersecurity": "item1CCybersecurity",
    "properties": "item2Properties",
    "legal": "item3LegalProceedings",
    "mdna": "item7Mdna",
    "marketRisk": "item7AMarketRiskDisclosures",
    "governance": "item10DirectorsAndCorporateGovernance",
    "compensation": "item11ExecutiveCompensation",
    "ownership": "item12SecurityOwnership",
    "relatedTx": "item13RelatedTransactions",
    "summary": "fsSummary",
}

# topic → chapter / label 매핑 (DART index와 구조 통일)
_FINANCE_LABELS: dict[str, tuple[str, str]] = {
    "BS": ("Financial Statements", "Balance Sheet"),
    "IS": ("Financial Statements", "Income Statement"),
    "CF": ("Financial Statements", "Cash Flow"),
    "CIS": ("Financial Statements", "Comprehensive Income"),
    "ratios": ("Financial Statements", "Financial Ratios"),
}

# 10-K Item → (chapter, label)
_10K_ITEM_LABELS: dict[str, tuple[str, str]] = {
    "item1Business": ("Part I", "Business"),
    "item1ARiskFactors": ("Part I", "Risk Factors"),
    "item1BUnresolvedStaffComments": ("Part I", "Unresolved Staff Comments"),
    "item1CCybersecurity": ("Part I", "Cybersecurity"),
    "item1DExecutiveOfficers": ("Part I", "Executive Officers"),
    "item2Properties": ("Part I", "Properties"),
    "item3LegalProceedings": ("Part I", "Legal Proceedings"),
    "item4MineSafetyDisclosures": ("Part I", "Mine Safety Disclosures"),
    "item4AExecutiveOfficersOfTheRegistrant": ("Part I", "Executive Officers"),
    "item5MarketForCommonEquity": ("Part II", "Market for Common Equity"),
    "item6Reserved": ("Part II", "Reserved"),
    "item7Mdna": ("Part II", "MD&A"),
    "item7AMarketRiskDisclosures": ("Part II", "Market Risk Disclosures"),
    "item8FinancialStatements": ("Part II", "Financial Statements"),
    "item9ChangesInAccountants": ("Part III", "Changes in Accountants"),
    "item9AControlsAndProcedures": ("Part III", "Controls and Procedures"),
    "item9BOtherInformation": ("Part III", "Other Information"),
    "item9CForeignJurisdictionDisclosures": ("Part III", "Foreign Jurisdiction Disclosures"),
    "item10DirectorsAndCorporateGovernance": ("Part III", "Directors & Corporate Governance"),
    "item11ExecutiveCompensation": ("Part III", "Executive Compensation"),
    "item12SecurityOwnership": ("Part III", "Security Ownership"),
    "item13RelatedTransactions": ("Part III", "Related Transactions"),
    "item14PrincipalAccountantFees": ("Part III", "Principal Accountant Fees"),
    "item15ExhibitsAndSchedules": ("Part IV", "Exhibits & Schedules"),
    "item16Form10KSummary": ("Part IV", "Form 10-K Summary"),
    "item103EnvironmentalDisclosure": ("Regulation S-K", "Environmental Disclosure"),
    "item405RegulationSKDisclosure": ("Regulation S-K", "Regulation S-K Disclosure"),
    "item406RegulationSKCodeOfEthics": ("Regulation S-K", "Code of Ethics"),
}

# 10-Q Part/Item → (chapter, label)
_10Q_ITEM_LABELS: dict[str, tuple[str, str]] = {
    "partIItem1FinancialStatements": ("Part I", "Financial Statements"),
    "partIItem2Mdna": ("Part I", "MD&A"),
    "partIItem3MarketRisk": ("Part I", "Market Risk Disclosures"),
    "partIItem4ControlsAndProcedures": ("Part I", "Controls and Procedures"),
    "partIIItem1LegalProceedings": ("Part II", "Legal Proceedings"),
    "partIIItem1ARiskFactors": ("Part II", "Risk Factors"),
    "partIIItem2UnregisteredSalesAndUseOfProceeds": ("Part II", "Unregistered Sales"),
    "partIIItem3DefaultsUponSeniorSecurities": ("Part II", "Defaults Upon Senior Securities"),
    "partIIItem4MineSafetyDisclosures": ("Part II", "Mine Safety Disclosures"),
    "partIIItem5OtherInformation": ("Part II", "Other Information"),
    "partIIItem6Exhibits": ("Part II", "Exhibits"),
}


_FORM_ORDER = {"10-K": 0, "10-Q": 1, "20-F": 2, "40-F": 3}

# 10-K item 정렬 순서 (SEC 양식 순)
_10K_ORDER: dict[str, int] = {
    "item1Business": 1,
    "item1ARiskFactors": 2,
    "item1BUnresolvedStaffComments": 3,
    "item1CCybersecurity": 4,
    "item1DExecutiveOfficers": 5,
    "item103EnvironmentalDisclosure": 6,
    "item405RegulationSKDisclosure": 7,
    "item406RegulationSKCodeOfEthics": 8,
    "item2Properties": 10,
    "item3LegalProceedings": 11,
    "item4MineSafetyDisclosures": 12,
    "item4AExecutiveOfficersOfTheRegistrant": 13,
    "item5MarketForCommonEquity": 20,
    "item6Reserved": 21,
    "item7Mdna": 22,
    "item7AMarketRiskDisclosures": 23,
    "item8FinancialStatements": 24,
    "item8ASupplementalFinancialInformation": 25,
    "item9ChangesInAccountants": 30,
    "item9AControlsAndProcedures": 31,
    "item9BOtherInformation": 32,
    "item9CForeignJurisdictionDisclosures": 33,
    "item10DirectorsAndCorporateGovernance": 40,
    "item11ExecutiveCompensation": 41,
    "item12SecurityOwnership": 42,
    "item13RelatedTransactions": 43,
    "item14PrincipalAccountantFees": 44,
    "item15ExhibitsAndSchedules": 50,
    "item16Form10KSummary": 51,
}

# 10-Q item 정렬 순서
_10Q_ORDER: dict[str, int] = {
    "partIItem1FinancialStatements": 1,
    "partIItem2Mdna": 2,
    "partIItem3MarketRisk": 3,
    "partIItem4ControlsAndProcedures": 4,
    "partIIItem1LegalProceedings": 10,
    "partIIItem1ARiskFactors": 11,
    "partIIItem2UnregisteredSalesAndUseOfProceeds": 12,
    "partIIItem2CIssuerPurchaseOfEquitySecurities": 13,
    "partIIItem3DefaultsUponSeniorSecurities": 14,
    "partIIItem4MineSafetyDisclosures": 15,
    "partIIItem5OtherInformation": 16,
    "partIIItem6Exhibits": 17,
}


def _sortDocTopics(topics: list[str]) -> list[str]:
    """docs topics를 form별 → item 순으로 정렬."""

    def sortKey(topic: str) -> tuple[int, int, str]:
        """sortKey — TODO 한국어 동작 설명."""
        if "::" not in topic:
            return (99, 0, topic)
        formType, itemId = topic.split("::", 1)
        formOrder = _FORM_ORDER.get(formType, 9)
        if formType == "10-K":
            itemOrder = _10K_ORDER.get(itemId, 99)
        elif formType == "10-Q":
            itemOrder = _10Q_ORDER.get(itemId, 99)
        else:
            # 20-F, 40-F 등 — itemId에서 숫자 추출하여 정렬
            itemOrder = _extractItemNumber(itemId)
        return (formOrder, itemOrder, itemId)

    return sorted(topics, key=sortKey)


def _extractItemNumber(itemId: str) -> int:
    """itemId에서 item 번호를 추출. "item5AOperatingResults" → 5."""
    m = re.match(r"item(\d+)", itemId)
    if m:
        num = int(m.group(1))
        # sub-item은 부모 뒤에 (item5A → 5*100+1, item16K → 16*100+11)
        subMatch = re.match(r"item\d+([A-Z])", itemId)
        if subMatch:
            return num * 100 + (ord(subMatch.group(1)) - ord("A") + 1)
        return num * 100
    return 9999


def _topicChapterLabel(topic: str) -> tuple[str, str]:
    """topic에서 chapter와 label을 추출."""
    if topic in _FINANCE_LABELS:
        return _FINANCE_LABELS[topic]

    # "10-K::item1Business" → formType="10-K", itemId="item1Business"
    if "::" in topic:
        formType, itemId = topic.split("::", 1)
        if formType == "10-K" and itemId in _10K_ITEM_LABELS:
            return _10K_ITEM_LABELS[itemId]
        if formType == "10-Q" and itemId in _10Q_ITEM_LABELS:
            return _10Q_ITEM_LABELS[itemId]
        # 20-F, 기타 → sectionMappings.json에서 label 역추출
        label = _itemIdToLabel(itemId)
        return (formType, label)

    return ("", topic)


def _itemIdToLabel(itemId: str) -> str:
    """camelCase itemId → 읽기 쉬운 label. "item5AOperatingResults" → "Operating Results"."""
    # prefix 제거: "item5A" + 대문자시작 or "item1" + 대문자시작
    # sub-item letter: 숫자 뒤 대문자 1개 + 바로 뒤가 대문자 (item5AO → A는 sub-item)
    # 단어 시작: 숫자 뒤 대문자 + 소문자 (item1Id → I는 단어 시작)
    m = re.match(r"^(?:partI{1,2})?[Ii]tem(\d+)([A-Z]?)(.*)$", itemId)
    if not m:
        return itemId
    subLetter = m.group(2)
    rest = m.group(3)
    if subLetter and rest and rest[0].isupper():
        # item5A + OperatingResults → sub-item, rest = OperatingResults
        pass
    elif subLetter:
        # item1I + dentity → I는 단어 시작, 붙여야 함
        rest = subLetter + rest
    if not rest:
        return itemId
    # camelCase → spaces
    label = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", rest)
    label = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", label)
    return label


_RATIO_FIELD_LABELS: dict[str, str] = {
    "roe": "ROE (%)",
    "roa": "ROA (%)",
    "operatingMargin": "Operating Margin (%)",
    "netMargin": "Net Margin (%)",
    "grossMargin": "Gross Margin (%)",
    "ebitdaMargin": "EBITDA Margin (%)",
    "costOfSalesRatio": "COGS Ratio (%)",
    "sgaRatio": "SG&A Ratio (%)",
    "debtRatio": "Debt Ratio (%)",
    "currentRatio": "Current Ratio (%)",
    "quickRatio": "Quick Ratio (%)",
    "equityRatio": "Equity Ratio (%)",
    "interestCoverage": "Interest Coverage (x)",
    "netDebtRatio": "Net Debt Ratio (%)",
    "noncurrentRatio": "Non-current Ratio (%)",
    "revenueGrowth": "Revenue YoY (%)",
    "operatingProfitGrowth": "Operating Profit YoY (%)",
    "netProfitGrowth": "Net Profit YoY (%)",
    "assetGrowth": "Asset YoY (%)",
    "equityGrowthRate": "Equity YoY (%)",
    "totalAssetTurnover": "Asset Turnover (x)",
    "inventoryTurnover": "Inventory Turnover (x)",
    "receivablesTurnover": "Receivables Turnover (x)",
    "payablesTurnover": "Payables Turnover (x)",
    "fcf": "FCF",
    "operatingCfMargin": "Operating CF Margin (%)",
    "operatingCfToNetIncome": "Operating CF / Net Income (%)",
    "capexRatio": "Capex Ratio (%)",
    "dividendPayoutRatio": "Dividend Payout Ratio (%)",
    "revenue": "Revenue",
    "operatingProfit": "Operating Profit",
    "netProfit": "Net Profit",
    "totalAssets": "Total Assets",
    "totalEquity": "Total Equity",
    "operatingCashflow": "Operating Cashflow",
}

_RATIO_CATEGORY_LABELS: dict[str, str] = {
    "profitability": "Profitability",
    "stability": "Stability",
    "growth": "Growth",
    "efficiency": "Efficiency",
    "cashflow": "Cashflow",
    "absolute": "Absolute",
}


def _ratioSeriesToDataFrame(
    series: dict[str, dict[str, list[Any | None]]],
    years: list[str],
) -> pl.DataFrame | None:
    ratioData = series.get("RATIO")
    if not ratioData:
        return None

    from dartlab.core.ratioCategories import RATIO_CATEGORIES

    rows: list[dict[str, Any]] = []
    for category, fields in RATIO_CATEGORIES:
        for fieldName in fields:
            values = ratioData.get(fieldName)
            if not values or not any(v is not None for v in values):
                continue
            row: dict[str, Any] = {
                "분류": _RATIO_CATEGORY_LABELS.get(category, category),
                "항목": _RATIO_FIELD_LABELS.get(fieldName, fieldName),
                "_field": fieldName,
            }
            for idx, year in enumerate(years):
                row[str(year)] = values[idx] if idx < len(values) else None
            rows.append(row)

    if not rows:
        return None
    return pl.DataFrame(rows).drop("_field")


def _isPeriodColumn(col: str) -> bool:
    return bool(_PERIOD_COLUMN_RE.fullmatch(col))


def _filterPeriodColumnsByAsOf(df: "pl.DataFrame", asOf: str) -> "pl.DataFrame":
    """asOf 이후 fiscal period 컬럼 drop — look-ahead bias 방지 (DART 와 동일 패턴).

    EDGAR finance topic 의 horizontal view 는 컬럼명이 fiscal period
    (예: "2024", "2024Q3"). asOf 이후 컬럼 drop 으로 미래 정보 누설 차단.
    """
    asof_year, asof_quarter = _parseAsof(asOf)
    if asof_year is None:
        return df
    keepCols: list[str] = []
    for col in df.columns:
        col_year, col_quarter = _parseAsof(col)
        if col_year is None:
            keepCols.append(col)
            continue
        if col_year < asof_year:
            keepCols.append(col)
        elif col_year == asof_year and (col_quarter is None or asof_quarter is None or col_quarter <= asof_quarter):
            keepCols.append(col)
    return df.select(keepCols) if len(keepCols) < len(df.columns) else df


def _parseAsof(value: str) -> tuple[int | None, int | None]:
    """fiscal period or ISO date → (year, quarter or None). 미인식 → (None, None)."""
    raw = str(value or "").strip()
    if not raw:
        return None, None
    m = re.match(r"^(\d{4})[Qq]([1-4])$", raw)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.match(r"^(\d{4})-(\d{1,2})-\d{1,2}$", raw)
    if m:
        month = int(m.group(2))
        return int(m.group(1)), (month - 1) // 3 + 1
    m = re.match(r"^(\d{4})$", raw)
    if m:
        return int(m.group(1)), None
    return None, None


class Company:
    """SEC EDGAR 기반 미국 기업 진입점.

    Example::

        c = Company("AAPL")
        c.show("BS")           # 연도별 재무상태표
        c.show("IS")           # 연도별 손익계산서
        c.show("CF")           # 연도별 현금흐름표
        c.show("CIS")          # 연도별 포괄손익계산서
        c.show("ratios")       # 재무비율 시계열
        c.show("item1Business")  # docs topic
        c.sections             # docs.sections 바로가기
        c.topics               # 전체 topic 목록
    """

    @staticmethod
    def canHandle(code: str) -> bool:
        """US ticker (영문 1~5자) 또는 CIK (숫자) 판별."""
        s = code.strip()
        if s.isdigit() and len(s) <= 10:
            return True
        return bool(re.match(r"^[A-Za-z]{1,5}$", s))

    @staticmethod
    def priority() -> int:
        """provider 우선순위 — 낮을수록 먼저 시도. EDGAR=20."""
        return 20

    def __init__(self, ticker: str):
        if not ticker or not isinstance(ticker, str):
            raise ValueError("ticker는 비어있지 않은 문자열이어야 합니다.")
        cleaned = ticker.strip().upper()
        # CIK (순수 숫자) 또는 ticker (영문+숫자, 1-10자)
        if not (cleaned.isdigit() and len(cleaned) <= 10) and not re.match(r"^[A-Z][A-Z0-9./-]{0,9}$", cleaned):
            raise ValueError(f"올바르지 않은 ticker/CIK: '{ticker}' (예: 'AAPL', '0000320193')")
        self.ticker = cleaned
        from dartlab.core.memory import BoundedCache

        self._cache: BoundedCache = BoundedCache(maxEntries=30)

        tickerRow = self._resolveTickerRow(self.ticker)
        if tickerRow is None:
            raise ValueError(
                f"'{ticker}'에 해당하는 종목을 찾을 수 없습니다.\n"
                f"\n"
                f"  가능한 원인:\n"
                f"  • ticker 심볼이 올바른지 확인하세요 (예: 'AAPL', 'MSFT')\n"
                f"  • SEC EDGAR에 등록되지 않은 종목일 수 있습니다\n"
                f"  • 인터넷 연결을 확인하세요 (SEC API 조회 필요)"
            )
        self.cik = tickerRow["cik"]
        self.corpName = tickerRow.get("title") or self.ticker

        # public namespace 모두 제거 (P3a/b/c)
        self._docs = _DocsAccessor(self)
        self._finance = _FinanceAccessor(self)
        self._profileAccessor = _ProfileAccessor(self)
        self._reportAccessor = None  # lazy init

    def _resolveTickerRow(self, ticker: str) -> dict | None:
        tickerPath = self._getTickerPath()
        tickerUpper = ticker.upper()
        if tickerPath is not None and tickerPath.exists():
            df = pl.read_parquet(tickerPath)
            row = df.filter(pl.col("ticker") == ticker)
            if row.is_empty():
                row = df.filter(pl.col("ticker") == tickerUpper)
            if not row.is_empty():
                r = row.row(0, named=True)
                r["cik"] = str(r["cik"]).zfill(10)
                return r

        try:
            from dartlab.core.dataLoader import loadEdgarListedUniverse

            listed = loadEdgarListedUniverse()
            row = listed.filter(pl.col("ticker") == tickerUpper)
            if not row.is_empty():
                r = row.row(0, named=True)
                r["cik"] = str(r["cik"]).zfill(10)
                return r
        except (FileNotFoundError, OSError, RuntimeError):
            pass

        try:
            from dartlab.providers.edgar.openapi.identity import resolveIssuer

            return resolveIssuer(tickerUpper)
        except ValueError:
            return None

    def _getTickerPath(self) -> Path | None:
        from dartlab import config

        return Path(config.dataDir) / "edgar" / "tickers.parquet"

    def __repr__(self):
        from dartlab.core.htmlRenderer import getHtmlRenderer

        renderer = getHtmlRenderer()
        if renderer is not None:
            text = renderer.renderCompany(self)
            if text is not None:
                return text
        return f"Company('{self.ticker}', {self.corpName})"

    # ── P7: Company context manager + 메모리-safe surface (룰 11 + MemorySafeProvider) ──

    def __enter__(self) -> "Company":
        """context manager 진입 — Company 인스턴스 그대로 반환.

        Example:
            with Company("AAPL") as c:
                c.show("IS").head()

        Returns:
            self.

        Raises:
            없음.
        """
        return self

    def __exit__(self, _excType: object, _excVal: object, _excTb: object) -> None:
        """context manager 종료 — BoundedCache evict + RSS 회수.

        Args:
            excType: 예외 type.
            excVal: 예외 인스턴스.
            excTb: traceback.

        Raises:
            없음.
        """
        try:
            self.cleanupCache()
        except (AttributeError, KeyError, RuntimeError):
            pass

    def cleanupCache(self) -> int:
        """BoundedCache evict + cleanupBetweenCompanies.

        Returns:
            evict 된 entry 수.

        Example:
            >>> c = Company("AAPL")
            >>> c.show("IS")
            >>> n = c.cleanupCache()

        Raises:
            없음.
        """
        from dartlab.core.memory import cleanupBetweenCompanies

        evicted = len(self._cache)
        self._cache.clear()
        cleanupBetweenCompanies(label=f"{self.ticker}_exit")
        return evicted

    def memorySnapshot(self) -> dict[str, int]:
        """캐시 size + 현 RSS snapshot.

        Returns:
            keys: "cacheSize", "rssMb".

        Example:
            >>> c = Company("AAPL")
            >>> c.memorySnapshot()
            {'cacheSize': 5, 'rssMb': 300}

        Raises:
            없음.
        """
        from dartlab.core.memory import getMemoryMb

        return {"cacheSize": len(self._cache), "rssMb": int(getMemoryMb())}

    @property
    def fiscalYearEnd(self) -> str | None:
        """회계연도 종료 월-일 (예: AAPL → '09-26', MSFT → '06-30').

        XBRL companyfacts 의 fp='FY' end 날짜에서 가장 자주 등장하는 month-day 추출.
        DART 종목은 12-31 표준 (한국 회계 관습).

        calendar year vs fiscal year 매칭 명시. 회사 간 연도 비교 시 fiscal
        year-end 가 다른 회사를 calendar year 로 매칭하면 잘못된 비교가 된다.

        Returns:
            "MM-DD" 형식 문자열, 데이터 없으면 None.

        Example::

            c = Company("AAPL")
            c.fiscalYearEnd  # "09-26" (마지막 토요일 변형 가능)
        """
        cacheKey = "_fiscalYearEnd"
        if cacheKey in self._cache:
            return self._cache[cacheKey]
        try:
            from pathlib import Path

            import polars as pl

            cik = str(self.cik).zfill(10)
            path = Path(f"data/edgar/finance/{cik}.parquet")
            if not path.exists():
                self._cache[cacheKey] = None
                return None
            # fy 별 mode (가장 많이 등장하는) end 가 진짜 FY 종료일.
            # 그 중에서 가장 흔한 month-day 가 fiscal year-end.
            lf = pl.scan_parquet(str(path))
            modeEnds = (
                lf.filter(pl.col("fp") == "FY")
                .filter(pl.col("end").is_not_null())
                .filter(pl.col("fy").is_not_null())
                .group_by(["fy", "end"])
                .len()
                .sort(["fy", "len"], descending=[False, True])
                .group_by("fy")
                .head(1)
            )
            df = (
                modeEnds.with_columns(
                    (pl.col("end").dt.month().cast(pl.Int32) * 100 + pl.col("end").dt.day().cast(pl.Int32)).alias("md")
                )
                .group_by("md")
                .len()
                .sort("len", descending=True)
                .head(1)
                .collect()
            )
            if df.height == 0:
                self._cache[cacheKey] = None
                return None
            md = df.row(0)[0]
            result = f"{md // 100:02d}-{md % 100:02d}"
            self._cache[cacheKey] = result
            return result
        except (FileNotFoundError, OSError, ValueError):
            self._cache[cacheKey] = None
            return None

    @property
    def stockCode(self) -> str:
        """서버 API 호환용 ticker 식별자.

        Capabilities:
            - DART Company와 동일한 stockCode 인터페이스 제공
            - 서버 API, export, AI 컨텍스트에서 종목 식별에 사용

        Requires:
            데이터: 없음 (인스턴스 속성)

        AIContext:
            - 서버 API/export에서 종목 식별 키로 사용

        Guide:
            - "이 기업 ticker가 뭐야?" → c.stockCode

        SeeAlso:
            - market: 시장 식별자
            - currency: 통화 식별자

        Returns:
            str — ticker 심볼 (예: "AAPL").

        Example::

            c = Company("AAPL")
            c.stockCode  # "AAPL"
        """
        return self.ticker

    @property
    def market(self) -> str:
        """거래소 시장 식별자.

        Capabilities:
            - 미국 시장 "US" 고정 반환
            - 멀티마켓 분기 로직에서 시장 판별에 사용

        Requires:
            데이터: 없음 (상수)

        AIContext:
            - 시장 구분에 따른 분석 분기 판별에 사용

        Guide:
            - "이 기업 시장이 어디야?" → c.market

        SeeAlso:
            - stockCode: ticker 식별자
            - currency: 통화 식별자

        Returns:
            str — "US".

        Example::

            c = Company("AAPL")
            c.market  # "US"
        """
        return "US"

    @property
    def currency(self) -> str:
        """통화 식별자.

        Capabilities:
            - 미국 달러 "USD" 고정 반환
            - 재무제표 금액 단위 표시, 밸류에이션 통화 기준에 사용

        Requires:
            데이터: 없음 (상수)

        AIContext:
            - 재무 수치 통화 단위 명시에 사용

        Guide:
            - "이 기업 통화가 뭐야?" → c.currency

        SeeAlso:
            - stockCode: ticker 식별자
            - market: 시장 식별자

        Returns:
            str — "USD".

        Example::

            c = Company("AAPL")
            c.currency  # "USD"
        """
        return "USD"

    @property
    def quant(self):
        """주가 기술적 분석 — dual access (Phase 8 A3)."""
        from dartlab.core.dualAccess import CallableAccessor

        if "_quantAccessor" not in self._cache:
            self._cache["_quantAccessor"] = CallableAccessor(self._quantImpl, name="quant")
        return self._cache["_quantAccessor"]

    def _quantImpl(self, axis=None, *, metric=None, **kwargs):
        """주가 기술적 분석 — 30축 (내부 구현)."""
        from dartlab.quant import Quant

        if axis is None and metric is not None:
            axis = metric
        q = Quant()
        if axis is None:
            return q()
        return q(axis, self.stockCode, **kwargs)

    def macro(self, axis=None, target=None, *, overrides: dict | None = None, **kwargs):
        """시장 매크로 분석 — EDGAR 회사는 US 시장 위임 (Phase 8 A2)."""
        from dartlab.macro import Macro

        return Macro()(axis, target, market="US", overrides=overrides, **kwargs)

    # ── Phase 10 H2: story 2차 가공 직접 노출 ──

    def causalWeights(self) -> list[dict]:
        """6막 인과 가중치 (Phase 9 B2)."""
        import importlib

        buildCausalWeights = importlib.import_module("dartlab.story.narrative").buildCausalWeights
        return buildCausalWeights(self, {})

    def valuationImpact(self) -> dict:
        """인과 체인 → DCF override 힌트 (Phase 9 B3)."""
        import importlib

        _narrative = importlib.import_module("dartlab.story.narrative")
        return _narrative.buildValuationImpact(_narrative.buildCausalWeights(self, {}))

    def storyTree(self, *, basePeriod: str | None = None) -> dict:
        """3 trajectory DCF (Phase 10 G2)."""
        import importlib

        buildStoryTree = importlib.import_module("dartlab.story.storyTree").buildStoryTree
        return buildStoryTree(self, basePeriod=basePeriod)

    def narrativeDiff(self, *, claims: list[str] | None = None) -> list[dict]:
        """claim 제거 시 dFV 변화 (Phase 10 G3)."""
        import importlib

        computeImpact = importlib.import_module("dartlab.story.narrativeDiff").computeImpact
        return computeImpact(self, claims=claims)

    # ── Phase 11 A1: EDGAR 상장사 검색 (DART sync) ──

    @staticmethod
    def listing(*, forceRefresh: bool = False) -> pl.DataFrame:
        """NASDAQ/NYSE 상장 기업 목록 (EDGAR universe).

        forceRefresh 는 DartCompany.listing 과 시그니처 동기 — 현재 EDGAR 는 자동 캐시.
        """
        from dartlab.core.dataLoader import loadEdgarListedUniverse

        universe = loadEdgarListedUniverse()
        return universe.select(
            [
                pl.col("ticker").alias("종목코드"),
                pl.col("title").alias("회사명"),
                pl.col("exchange").alias("시장구분"),
                pl.col("cik"),
            ]
        )

    @staticmethod
    def search(keyword: str, *, limit: int | None = None) -> pl.DataFrame:
        """ticker / 회사명 검색. 대소무시 부분 매칭.

        Args:
            keyword: ticker 또는 회사명 부분.
            limit: 최대 행 수. None 이면 무제한.

        Returns:
            종목코드/회사명/시장구분/cik 컬럼 DataFrame.

        Example:
            >>> Company.search("apple", limit=10)
        """
        from dartlab.core.dataLoader import loadEdgarListedUniverse

        kw = keyword.strip()
        if not kw:
            return (
                loadEdgarListedUniverse()
                .head(0)
                .select(
                    [
                        pl.col("ticker").alias("종목코드"),
                        pl.col("title").alias("회사명"),
                        pl.col("exchange").alias("시장구분"),
                        pl.col("cik"),
                    ]
                )
            )
        kw_upper = kw.upper()
        universe = loadEdgarListedUniverse()
        # ticker 매칭 (정확 우선)
        hit = universe.filter(pl.col("ticker") == kw_upper)
        if hit.height == 0:
            hit = universe.filter(pl.col("ticker").str.contains(kw_upper, literal=True))
        if hit.height == 0:
            # 회사명 매칭 (대소무시)
            hit = universe.filter(pl.col("title").str.to_lowercase().str.contains(kw.lower(), literal=True))
        result = hit.select(
            [
                pl.col("ticker").alias("종목코드"),
                pl.col("title").alias("회사명"),
                pl.col("exchange").alias("시장구분"),
                pl.col("cik"),
            ]
        )
        if limit is not None:
            result = result.head(limit)
        return result

    def view(self, *, port: int = 8400) -> None:
        """브라우저에서 공시 뷰어를 열어 sections/index를 시각화.

        Capabilities:
            - 로컬 서버 기동 후 브라우저에서 sections 탐색
            - topic별 텍스트/테이블, 기간 비교를 인터랙티브로 확인

        Requires:
            데이터: sections (SEC EDGAR 자동 수집)

        AIContext:
            - 시각적 탐색 도구로, CLI/노트북이 아닌 브라우저 환경 제공

        Guide:
            - "공시 내용을 브라우저에서 보고 싶어" → c.view()

        SeeAlso:
            - sections: 수평화 보드 원본 데이터
            - index: topic 메타데이터 보드
            - show: 특정 topic 데이터 조회

        Args:
            port: 로컬 서버 포트 (기본 8400).

        Returns:
            None — 브라우저가 자동으로 열림.

        Example::

            c = Company("AAPL")
            c.view()             # localhost:8400 에서 뷰어 실행
            c.view(port=9000)    # 포트 변경
        """
        from dartlab.core.viewer import launchViewer

        launchViewer(self.ticker, port=port)

    def _buildFinanceSeries(self, *, freq: str = "Q", scope: str = "consolidated"):
        """[INTERNAL] EDGAR finance series-tuple 빌더.

        사용자 진입점은 ``c.show("IS", freq=, scope=)`` 만이다 (api-contract).
        EDGAR 는 ``scope="separate"`` 미지원 (SEC 는 연결만 보고).
        ``freq="YTD"`` 도 미지원 — annual 로 fallback.

        Args:
            freq: ``"Q"`` (분기, 기본) / ``"Y"`` (연간) / ``"YTD"`` (annual fallback).
            scope: ``"consolidated"`` (기본) — separate 는 raise.

        Returns:
            ``(series, periods)`` 또는 None.
        """
        from dartlab.providers.edgar.builder.dataDispatcher import buildFinanceSeries

        return buildFinanceSeries(self, freq=freq, scope=scope)

    # c.BS / c.IS / c.CF / c.CIS property 제거 (Plan v10 P0 — api-contract).
    # 사용자는 c.show("IS") / c.show.IS() / c.show("IS", freq="Y") 사용.

    # c.SCE property 제거 (Plan v10 P1) — c.show("SCE") 사용

    @property
    def sections(self) -> pl.DataFrame | None:
        """sections — docs + finance 통합 지도 (topic x period 수평화).

        Capabilities:
            - 10-K/10-Q/20-F 문서 항목 + 재무제표를 단일 DataFrame으로 통합
            - topic별 blockType(text/table), 기간별 셀 구조

        Requires:
            데이터: 없음 (SEC EDGAR 자동 수집)

        AIContext:
            - ask()/chat()에서 기업 전체 공시 구조 파악 컨텍스트

        Guide:
            - "전체 공시 지도를 보고 싶어" → c.sections
            - "어떤 topic이 있는지 전체 구조를 보여줘" → c.sections

        SeeAlso:
            - topics: topic 목록 요약
            - index: topic 메타데이터 보드
            - show: 특정 topic 조회
            - diff: 기간간 텍스트 변화 비교

        Returns:
            pl.DataFrame — topic | blockType | blockOrder | 2024 | 2023 | ... 또는 None.

        Example::

            c = Company("AAPL")
            c.sections  # Apple 전체 sections 지도
        """
        return self._profileAccessor.sections

    def _buildRatios(self) -> pl.DataFrame | None:
        """[INTERNAL] EDGAR 재무비율 DataFrame 빌더 — show("ratios") 가 호출."""
        from dartlab.providers.edgar.builder.dataDispatcher import buildRatios

        return buildRatios(self)

    # insights는 analysis 내부 — c.analysis("financial", "종합평가")로 접근

    @property
    def story(self):
        """재무 검토 보고서 — dual access."""
        from dartlab.core.dualAccess import CallableAccessor

        if "_storyAccessor" not in self._cache:
            self._cache["_storyAccessor"] = CallableAccessor(self._storyImpl, name="story")
        return self._cache["_storyAccessor"]

    def _storyImpl(
        self,
        section: str | None = None,
        layout=None,
        helper: bool | None = None,
        *,
        type: str | None = None,
        template: str | None = None,
        detail: bool | None = None,
        basePeriod: str | None = None,
        hypothesis: str | None = None,
        preset: str | None = None,  # deprecated
        perspective: str | None = None,  # deprecated
    ):
        """재무제표 구조화 보고서 — 기업이야기꾼의 대본.

        Capabilities:
            - 14개 섹션 전체 보고서 (수익구조~재무정합성)
            - 단일 섹션 지정 가능
            - 4개 출력 형식 (rich, html, markdown, json)
            - 프리셋 지원 (executive/audit/credit/growth/valuation)

        Requires:
            데이터: 없음 (SEC EDGAR 자동 수집)

        AIContext:
            - ask() (dartlab.ask) 가 이 결과를 tool 로 소비해 AI 해석 생성
            - ask()에서 재무분석 컨텍스트로 활용

        Guide:
            - "Story the financials" → c.story()
            - "Revenue structure" → c.story("수익구조")
            - "Audit story" → c.story(preset="audit")

        SeeAlso:
            - analysis: 14축 개별 분석 (review가 내부적으로 소비)
            - insights: 7영역 등급 + 이상치 요약

        Args:
            section: 섹션명 ("수익구조" 등). None이면 전체.
            layout: StoryLayout 커스텀. None이면 기본.
            helper: True면 해석 힌트 텍스트 포함.
            preset: 프리셋 이름 (executive/audit/credit/growth/valuation).
            template: 스토리 템플릿 이름.
            detail: False면 요약만 표시.
            basePeriod: 기준 기간.

        Returns:
            Story — 구조화 보고서.

        Example::

            c = Company("AAPL")
            c.story()                # 전체 검토서
            c.story("수익성")         # 특정 섹션
            c.story(preset="audit")  # 감사 검토용
        """
        import importlib

        buildStory = importlib.import_module("dartlab.story.registry").buildStory

        return buildStory(
            self,
            section=section,
            layout=layout,
            helper=helper,
            type=type,
            template=template,
            detail=detail,
            basePeriod=basePeriod,
            hypothesis=hypothesis,
            preset=preset,
            perspective=perspective,
        )

    @property
    def analysis(self):
        """분석 엔진 실행 — dual access."""
        from dartlab.core.dualAccess import CallableAccessor

        if "_analysisAccessor" not in self._cache:
            self._cache["_analysisAccessor"] = CallableAccessor(self._analysisImpl, name="analysis")
        return self._cache["_analysisAccessor"]

    def _analysisImpl(self, axis: str | None = None, sub: str | None = None, **kwargs):
        """분석 엔진 실행 — analysis()에 self를 바인딩 (내부 구현).

        Capabilities:
            - 22축 분석 (5 group)
              - financial (14): 수익구조, 자금조달, 자산구조, 현금흐름, 수익성, 성장성, 안정성, 효율성, 종합평가, 이익품질, 비용구조, 자본배분, 투자효율, 재무정합성
              - valuation (1): 가치평가
              - governance (3): 지배구조, 공시변화, 비교분석
              - forecast (2): 매출전망, 예측신호
              - macro (2): 매크로민감도, 밸류에이션밴드
            - 2-level 호출: c.analysis("financial", "수익성"), c.analysis("valuation", "가치평가")
            - axis 없이 호출하면 사용 가능한 축 목록 반환

        Requires:
            데이터: 없음 (SEC EDGAR 자동 수집)

        AIContext:
            - ask()/chat()에서 심화 분석 패키지 선택 컨텍스트

        Guide:
            - "재무 분석 해줘" → c.analysis("financial", "수익성")
            - "어떤 분석이 가능해?" → c.analysis()로 축 목록 확인
            - "가치평가 해줘" → c.analysis("valuation", "가치평가")
            - "매출전망" → c.analysis("forecast", "매출전망")
            - "지배구조" → c.analysis("governance", "지배구조")

        SeeAlso:
            - story: 분석 결과를 보고서로 조합
            - insights: 재무 인사이트 (간편 요약)
            - ask: AI 기반 해석

        Args:
            axis: 그룹 이름 ("financial", "valuation", "governance", "forecast", "macro") 또는 축 이름. None이면 가이드.
            sub: 그룹 내 하위 축 이름 ("수익성", "가치평가", "매출전망", "지배구조" 등).
            **kwargs: 축별 추가 파라미터.

        Returns:
            분석 결과 객체 또는 축 목록 dict.

        Example::

            c = Company("AAPL")
            c.analysis()                            # 사용 가능한 축 목록 (22축)
            c.analysis("financial", "수익성")        # 수익성 분석
            c.analysis("valuation", "가치평가")       # 가치평가
            c.analysis("governance", "지배구조")      # 지배구조
            c.analysis("forecast", "매출전망")        # 매출전망
        """
        import importlib

        Analysis = importlib.import_module("dartlab.analysis.financial").Analysis

        _analysis = Analysis()
        if axis is None:
            return _analysis()
        if sub is not None:
            return _analysis(axis, sub, company=self, **kwargs)
        return _analysis(axis, company=self, **kwargs)

    def validateStory(self, overrides: dict | None = None) -> dict:
        """Damodaran 스토리 검증 — Possible / Plausible / Probable.

        Returns:
            dict {precedents, plausibility, rules, overall}
        """
        import importlib

        _sv = importlib.import_module("dartlab.analysis.financial.storyValidation")
        calcPlausibilityBand = _sv.calcPlausibilityBand
        calcStoryPrecedents = _sv.calcStoryPrecedents
        calcValuationSins = _sv.calcValuationSins

        precedents = calcStoryPrecedents(self)
        plausibility = calcPlausibilityBand(self)
        rules = calcValuationSins(self)

        order = {"info": 0, "warn": 1, "critical": 2}
        overall = "info"
        rule_sev = rules.get("severity", "info") if rules else "info"
        if order.get(rule_sev, 0) > order.get(overall, 0):
            overall = rule_sev

        return {
            "precedents": precedents,
            "plausibility": plausibility,
            "rules": rules,
            "overall": overall,
        }

    @property
    def credit(self):
        """독립 신용평가 — dual access."""
        from dartlab.core.dualAccess import CallableAccessor

        if "_creditAccessor" not in self._cache:
            self._cache["_creditAccessor"] = CallableAccessor(self._creditImpl, name="credit")
        return self._cache["_creditAccessor"]

    def _creditImpl(self, axis: str | None = None, *, detail: bool = False, basePeriod: str | None = None):
        """독립 신용평가 — dCR 20단계 등급 (내부 구현)."""
        from dartlab.credit import creditCompany

        return creditCompany(self, axis=axis, detail=detail, basePeriod=basePeriod)

    def gather(self, axis: str | None = None, **kwargs):
        """외부 시장 데이터 수집 — gather()에 self.ticker를 바인딩.

        Capabilities:
            - 주가, 뉴스, 매크로 등 외부 데이터 소스 수집
            - axis 없이 호출하면 사용 가능한 축 목록 반환

        Requires:
            데이터: 인터넷 연결 (외부 API 호출)

        AIContext:
            - ask()/chat()에서 주가, 뉴스 등 외부 컨텍스트 보강

        Guide:
            - "주가 데이터가 필요해" → c.gather("price")
            - "어떤 외부 데이터를 수집할 수 있어?" → c.gather()

        SeeAlso:
            - news: 뉴스 수집 (gather("news") 바로가기)
            - analysis: 분석 영역 (수집 데이터를 소비)

        Args:
            axis: 수집 축 이름 (예: "price", "news"). None이면 축 목록.
            **kwargs: 축별 추가 파라미터.

        Returns
        -------
        pl.DataFrame | None
            axis=None (가이드):
                axis : str — 축 이름
                label : str — 한글 레이블
                description : str — 설명
                example : str — 사용 예시
            axis="price":
                date : date — 날짜
                open : float — 시가 (USD)
                high : float — 고가 (USD)
                low : float — 저가 (USD)
                close : float — 종가 (USD)
                volume : int — 거래량
            axis="news":
                title : str — 뉴스 제목
                link : str — 기사 URL
                pubDate : str — 발행일
            axis="macro":
                date : date — 날짜
                지표별 컬럼 : float — FRED 거시지표 값
            데이터 없으면 None.

        Example::

            c = Company("AAPL")
            c.gather()              # 사용 가능한 축 목록
            c.gather("price")       # Apple 주가 수집
        """
        from dartlab.core.gatherProvider import getGatherProvider

        provider = getGatherProvider()
        if provider is None:
            return None
        return provider.entry(axis, self.ticker, market="US", **kwargs)

    def calendar(self, *, horizonDays: int = 30) -> "pl.DataFrame":
        """다가오는 정기공시 catalyst 일정 — EDGAR/SEC 시장.

        현재 정기공시 cycle 추론은 KR DART 전용 (분기/반기/사업보고서 패턴 기반).
        SEC 의 10-K/10-Q 패턴은 별도 추론기 필요 — 미구현. 빈 DataFrame 반환.
        DartCompany.calendar 와 시그니처 일치 (CompanyProtocol 일관성).
        """
        from dartlab.providers.dart.ops.calendar import OUTPUT_SCHEMA

        return pl.DataFrame(schema=OUTPUT_SCHEMA)

    def filings(self) -> pl.DataFrame | None:
        """SEC 공시 문서 목록 — 10-K/10-Q 등 정기보고서 목록.

        Capabilities:
            - 사전 수집된 filing 메타데이터 조회
            - formType, filedAt, accessionNo 등 컬럼 포함

        Requires:
            데이터: 없음 (SEC EDGAR 자동 수집)

        AIContext:
            - 보유 공시 목록 확인으로 분석 범위 결정에 활용

        Guide:
            - "이 회사 공시 목록 보여줘" → c.filings()
            - "어떤 보고서가 있어?" → c.filings()로 보유 문서 확인

        SeeAlso:
            - disclosure: SEC filing 검색 (기간/유형/키워드 필터)
            - liveFilings: 실시간 최신 filing 조회
            - readFiling: filing 원문 읽기

        Returns:
            pl.DataFrame — docId | filedAt | formType | ... 또는 None.

        Example::

            c = Company("AAPL")
            c.filings()  # Apple SEC filing 목록
        """
        return self._docs.filings()

    def refreshFromApi(self) -> int:
        """[사용자 선택 경로] SEC companyfacts API로 로컬 finance parquet 갱신.

        Capabilities:
            - SEC companyfacts per-ticker API 호출
            - 로컬 ``data/edgar/finance/{cik}.parquet`` 덮어쓰기
            - 캐시 무효화 → 다음 show/analysis 호출부터 새 데이터 사용

        Policy:
            dartlab 자체 파이프라인은 **SEC 벌크** (``companyfacts.zip`` daily
            + 분기 ``financial-statement-data-sets``) 를 primary 소스로 사용한다.
            이 메서드는 **자동 파이프라인·프리빌드·HF 배포가 사용하지 않는다** —
            사용자가 공시 당일 최신 분기를 즉시 반영하고 싶을 때만 명시적으로 호출.
            상세: ``engines.edgar`` 및 ``operation.apiContract`` "EDGAR 수집 경로".

        Requires:
            인터넷 연결 (data.sec.gov). User-Agent 헤더.

        AIContext:
            - 자동 호출 금지. 사용자가 "API로 새로고침" 같은 명시적 의도일 때만.

        Guide:
            - "최신 실적 반영해줘" → c.refreshFromApi()
            - "SEC에서 직접 다시 받아줘" → c.refreshFromApi()

        SeeAlso:
            - filings: 현재 보유 공시 목록 확인

        Returns:
            저장된 parquet 행 수. 실패 시 0.

        Example::

            c = Company("AAPL")
            c.refreshFromApi()  # SEC API로 즉시 최신화
        """
        import polars as _pl

        from dartlab.providers.edgar.openapi.client import EdgarClient
        from dartlab.providers.edgar.openapi.saver import saveFinance

        cik = str(self.cik).zfill(10)
        client = EdgarClient()
        try:
            path = saveFinance(cik, client=client)
        except (OSError, ValueError, RuntimeError):
            return 0

        for key in list(self._cache.keys()):
            if key.startswith("_finance_") or key in ("_ratios", "_ratioSeries"):
                self._cache.pop(key, None)

        try:
            return _pl.read_parquet(path).height
        except (OSError, _pl.exceptions.PolarsError):
            return 0

    def disclosure(
        self,
        start: str | None = None,
        end: str | None = None,
        *,
        days: int = 365,
        type: str | None = None,
        keyword: str | None = None,
        finalOnly: bool = False,
    ) -> pl.DataFrame:
        """SEC EDGAR filing 검색 — liveFilings 위임.

        Capabilities:
            - 기간/유형/키워드 필터로 SEC filing 검색
            - DART disclosure()와 동일한 인터페이스

        Requires:
            데이터: 인터넷 연결 (SEC EDGAR API)

        AIContext:
            - 최근 공시 빈도/유형으로 기업 이벤트 감지에 활용

        Guide:
            - "최근 공시 뭐 나왔어?" → c.disclosure(days=30)
            - "10-K만 보고 싶어" → c.disclosure(type="10-K")

        SeeAlso:
            - liveFilings: 실시간 최신 filing (정규화 포맷)
            - readFiling: filing 원문 텍스트 읽기
            - filings: 사전 수집된 filing 목록

        Args:
            start: 시작일 (YYYY-MM-DD). None이면 end 기준 days일 전.
            end: 종료일 (YYYY-MM-DD). None이면 오늘.
            days: 기간 일수 (기본 365).
            type: form 유형 필터 (예: "10-K").
            keyword: 제목 키워드 필터.
            finalOnly: EDGAR에서는 미사용 (DART 호환 파라미터).

        Returns:
            pl.DataFrame — docId | filedAt | title | formType | docUrl | ...

        Example::

            c = Company("AAPL")
            c.disclosure()                        # 최근 1년 전체
            c.disclosure(type="10-K")             # 10-K만
            c.disclosure(keyword="earnings")      # 키워드 필터
        """
        return self.liveFilings(start, end, days=days, keyword=keyword, forms=[type] if type else None)

    def liveFilings(
        self,
        start: str | None = None,
        end: str | None = None,
        *,
        days: int | None = None,
        limit: int = 20,
        keyword: str | None = None,
        forms: list[str] | tuple[str, ...] | None = None,
        finalOnly: bool = False,
    ) -> pl.DataFrame:
        """SEC EDGAR 실시간 filing 목록 — OpenEdgar API 직접 조회.

        Capabilities:
            - SEC EDGAR submissions API에서 최신 filing 실시간 조회
            - form 유형, 기간, 키워드 복합 필터
            - readFiling()과 연계하여 원문 읽기 가능

        Requires:
            데이터: 인터넷 연결 (SEC EDGAR API)

        AIContext:
            - 최신 공시 모니터링으로 기업 이벤트 실시간 감지
            - readFiling()과 조합하여 최신 공시 원문 분석

        Guide:
            - "최신 공시 목록 보여줘" → c.liveFilings()
            - "10-K만 최근 5건" → c.liveFilings(forms=["10-K"], limit=5)

        SeeAlso:
            - readFiling: filing 원문 텍스트 읽기
            - disclosure: 기간/유형/키워드 검색 (liveFilings 위임)
            - filings: 사전 수집된 filing 목록

        Args:
            start: 시작일 (YYYY-MM-DD).
            end: 종료일 (YYYY-MM-DD).
            days: 기간 일수. start/end 미지정 시 사용.
            limit: 최대 반환 건수 (기본 20).
            keyword: 제목/설명 키워드 필터.
            forms: form 유형 리스트 (예: ["10-K", "10-Q"]). None이면 전체.
            finalOnly: EDGAR에서는 미사용.

        Returns:
            pl.DataFrame — docId | filedAt | title | formType | docUrl | ...

        Example::

            c = Company("AAPL")
            c.liveFilings()                           # 최근 filing 20건
            c.liveFilings(forms=["10-K"], limit=5)    # 10-K만 5건
        """
        del finalOnly  # EDGAR regular filings에는 finalOnly 개념이 없다.

        startDate, endDate = resolveDateWindow(start, end, days=days)
        normalizedForms = tuple(forms or SUPPORTED_REGULAR_FORMS)
        cacheKey = f"liveFilings:{startDate}:{endDate}:{limit}:{keyword}:{normalizedForms}"
        if cacheKey in self._cache:
            return self._cache[cacheKey]

        from dartlab.core.messaging import progress
        from dartlab.providers.edgar.openapi.edgar import OpenEdgar

        progress(
            f"{self.corpName} 최신 공시 목록 조회 중... "
            f"(SEC EDGAR, {startDate}~{endDate}, forms={','.join(normalizedForms)})"
        )
        df = OpenEdgar()(self.ticker).filings(
            forms=list(normalizedForms),
            since=startDate,
            until=endDate,
        )
        if isEmptyDf(df):
            result = pl.DataFrame(
                schema={
                    "docId": pl.Utf8,
                    "filedAt": pl.Utf8,
                    "title": pl.Utf8,
                    "formType": pl.Utf8,
                    "docUrl": pl.Utf8,
                    "indexUrl": pl.Utf8,
                    "market": pl.Utf8,
                    "ticker": pl.Utf8,
                    "cik": pl.Utf8,
                    "accessionNo": pl.Utf8,
                    "filingUrl": pl.Utf8,
                    "filingIndexUrl": pl.Utf8,
                    "primaryDocument": pl.Utf8,
                    "reportDate": pl.Utf8,
                }
            )
            self._cache[cacheKey] = result
            return result

        normalized = (
            filterFilingsByKeyword(
                df,
                keyword=keyword,
                columns=["title", "primary_doc_description", "form"],
            )
            .with_columns(
                [
                    pl.col("accession_no").cast(pl.Utf8).alias("docId"),
                    pl.col("filing_date").cast(pl.Utf8).alias("filedAt"),
                    pl.col("title").cast(pl.Utf8).alias("title"),
                    pl.col("form").cast(pl.Utf8).alias("formType"),
                    pl.col("filing_url").cast(pl.Utf8).alias("docUrl"),
                    pl.col("filing_index_url").cast(pl.Utf8).alias("indexUrl"),
                    pl.lit("US").alias("market"),
                    pl.col("ticker").cast(pl.Utf8).alias("ticker"),
                    pl.col("cik").cast(pl.Utf8).alias("cik"),
                    pl.col("accession_no").cast(pl.Utf8).alias("accessionNo"),
                    pl.col("filing_url").cast(pl.Utf8).alias("filingUrl"),
                    pl.col("filing_index_url").cast(pl.Utf8).alias("filingIndexUrl"),
                    pl.col("primary_document").cast(pl.Utf8).alias("primaryDocument"),
                    pl.col("report_date").cast(pl.Utf8).alias("reportDate"),
                ]
            )
            .select(
                [
                    "docId",
                    "filedAt",
                    "title",
                    "formType",
                    "docUrl",
                    "indexUrl",
                    "market",
                    "ticker",
                    "cik",
                    "accessionNo",
                    "filingUrl",
                    "filingIndexUrl",
                    "primaryDocument",
                    "reportDate",
                ]
            )
        )
        result = normalized.head(limit) if limit > 0 else normalized
        self._cache[cacheKey] = result
        return result

    def readFiling(
        self,
        filing: Any,
        *,
        maxChars: int | None = None,
    ) -> dict[str, Any]:
        """filing 원문 읽기 — URL/accessionNo/DataFrame row로 SEC 문서 다운로드.

        Capabilities:
            - filing URL, accessionNo 문자열, liveFilings() row 모두 지원
            - HTML 자동 텍스트 변환, maxChars 기준 truncate

        Requires:
            데이터: 인터넷 연결 (SEC EDGAR 문서 다운로드)

        AIContext:
            - ask()/chat()에서 특정 filing 원문을 읽어 심층 분석에 활용

        Guide:
            - "이 공시 원문 읽어줘" → c.readFiling(filing)
            - "최신 10-K 내용 보여줘" → liveFilings()로 조회 후 readFiling()

        SeeAlso:
            - liveFilings: 실시간 filing 목록 (readFiling 입력 소스)
            - disclosure: filing 검색
            - show: topic 기반 조회 (수평화된 데이터)

        Args:
            filing: filing URL(str), accessionNo(str), 또는 liveFilings() row.
            maxChars: 최대 문자수. None이면 전체.

        Returns:
            dict — docId, market, title, docUrl, raw, text, truncated 키 포함.

        Example::

            c = Company("AAPL")
            filings = c.liveFilings(forms=["10-K"], limit=1)
            result = c.readFiling(filings[0])
            _log.info(result["text"][:500])
        """
        record = filingRecord(filing) or {}

        if isinstance(filing, str):
            if filing.startswith("http://") or filing.startswith("https://"):
                docUrl = filing.strip()
                accessionNo = ""
            else:
                docUrl = ""
                accessionNo = filing.strip()
        else:
            docUrl = str(record.get("docUrl") or record.get("filingUrl") or "")
            accessionNo = str(record.get("accessionNo") or record.get("docId") or "")

        primaryDocument = str(record.get("primaryDocument") or "")
        if not docUrl and accessionNo and primaryDocument:
            accessionNoDash = accessionNo.replace("-", "")
            docUrl = f"https://www.sec.gov/Archives/edgar/data/{self.cik}/{accessionNoDash}/{primaryDocument}"
        if not docUrl and accessionNo:
            candidates = self.liveFilings(limit=50)
            matched = candidates.filter(pl.col("docId") == accessionNo) if not candidates.is_empty() else None
            if matched is not None and matched.height > 0:
                row = matched.row(0, named=True)
                docUrl = str(row.get("docUrl") or "")
                accessionNo = str(row.get("accessionNo") or accessionNo)
                primaryDocument = str(row.get("primaryDocument") or primaryDocument)

        if not docUrl:
            raise ValueError("EDGAR filing 읽기에는 filing URL 또는 accessionNo가 필요합니다.")

        from dartlab.core.messaging import progress
        from dartlab.providers.edgar.docs.fetch import _downloadFilingSource, _htmlToText

        progress(f"{self.corpName} 공시 원문 다운로드 중... ({accessionNo or Path(docUrl).name})")
        filingPayload = {
            "filingUrl": docUrl,
            "accessionNumber": accessionNo,
        }
        rawText = _downloadFilingSource(filingPayload)
        progress(f"{self.corpName} 공시 원문 정리 중... ({accessionNo or Path(docUrl).name})")
        normalizedText = _htmlToText(rawText) if "<" in rawText and ">" in rawText else rawText
        textPreview, truncated = truncateText(normalizedText, maxChars=maxChars)
        rawPreview, _ = truncateText(rawText, maxChars=maxChars)
        return {
            "docId": accessionNo,
            "market": "US",
            "title": record.get("title") or "",
            "docUrl": docUrl,
            "indexUrl": record.get("indexUrl") or record.get("filingIndexUrl") or "",
            "raw": rawPreview,
            "text": textPreview,
            "truncated": truncated,
        }

    @property
    def topics(self) -> pl.DataFrame:
        """topic 목록 요약 — topic/source/blocks/periods DataFrame.

        Capabilities:
            - finance(BS/IS/CF/CIS/ratios) + docs(10-K/10-Q 항목) 전체 topic 열거
            - 각 topic의 source, 블록 수, 기간 수 요약

        Requires:
            데이터: 없음 (SEC EDGAR 자동 수집)

        AIContext:
            - 사용 가능한 topic 목록으로 질문 라우팅 판단에 활용

        Guide:
            - "어떤 topic이 있어?" → c.topics
            - "분석 가능한 항목 목록" → c.topics로 확인

        SeeAlso:
            - sections: 전체 수평화 보드
            - index: topic 메타데이터 보드
            - show: 특정 topic 데이터 조회

        Returns:
            pl.DataFrame — topic | source | blocks | periods.

        Example::

            c = Company("AAPL")
            c.topics  # Apple 전체 topic 목록
        """
        cacheKey = "_topicsDataFrame"
        if cacheKey in self._cache:
            return self._cache[cacheKey]

        ordered: list[str] = []
        seen: set[str] = set()

        # 1. finance 제표 먼저
        for stmt in ("BS", "IS", "CF", "CIS"):
            if getattr(self._finance, stmt) is not None:
                ordered.append(stmt)
                seen.add(stmt)

        if self._finance.ratioSeries is not None and "ratios" not in seen:
            ordered.append("ratios")
            seen.add("ratios")

        # 2. docs topics — form별 정렬 (10-K → 10-Q → 20-F → 기타)
        sec = self._docs.sections
        if sec is not None:
            topicCol = sec["topic"].unique().to_list()
            topicCol = _sortDocTopics(topicCol)
            for topic in topicCol:
                if isinstance(topic, str) and topic not in seen:
                    ordered.append(topic)
                    seen.add(topic)

        # DataFrame으로 변환
        rows: list[dict] = []
        for topic in ordered:
            if sec is not None and topic in sec["topic"].to_list():
                topicRows = sec.filter(pl.col("topic") == topic)
                sources = sorted(topicRows["source"].unique().to_list()) if "source" in topicRows.columns else ["docs"]
                blocks = topicRows["blockOrder"].n_unique() if "blockOrder" in topicRows.columns else topicRows.height
                periodCols = [c for c in topicRows.columns if _isPeriodColumn(c)]
                periods = len(periodCols)
            else:
                sources = ["finance"]
                blocks = 1
                periods = 0
            rows.append(
                {
                    "topic": topic,
                    "source": ",".join(sources),
                    "blocks": blocks,
                    "periods": periods,
                }
            )

        result = pl.DataFrame(rows) if rows else pl.DataFrame({"topic": [], "source": [], "blocks": [], "periods": []})
        self._cache[cacheKey] = result
        return result

    @property
    def show(self):
        """topic 데이터 조회 — dual access (api-contract).

        Returns:
            ``CallableAccessor`` — call/attr form 둘 다 ``_showImpl`` 호출. ``pl.DataFrame``
            반환 (topic 부재 시 None). 상세는 ``_showImpl`` docstring.

        Example:
            >>> c = Company("AAPL")
            >>> c.show("IS")               # call form
            >>> c.show.IS()                # attr form
            >>> c.show.IS(period="2024")

        Raises:
            없음 (topic 부재 시 ``_showImpl`` 이 None 반환).
        """
        from dartlab.core.dualAccess import CallableAccessor

        if "_showAccessor" not in self._cache:
            self._cache["_showAccessor"] = CallableAccessor(self._showImpl, name="show")
        return self._cache["_showAccessor"]

    def _showImpl(
        self,
        topic: str,
        block: int | None = None,
        *,
        period: str | list[str] | None = None,
        raw: bool = False,
        asOf: str | None = None,
        **_kw: Any,
    ) -> pl.DataFrame | None:
        """topic 데이터 조회 — sections 사상의 핵심 소비 경로 (내부 구현).

        Capabilities:
            - finance topic(BS/IS/CF/CIS/ratios) + docs topic(10-K/10-Q 항목) 통합 조회
            - block=None이면 블록 목차, block=N이면 해당 블록 실제 데이터
            - period 리스트 전달 시 세로 뷰 (기간 x 항목) 변환
            - 단축 alias 지원: "risk" → "item1ARiskFactors", "mdna" → "item7Mdna"

        Requires:
            데이터: 없음 (SEC EDGAR 자동 수집)

        AIContext:
            - ask()/chat()에서 특정 topic 원문/수치 조회 컨텍스트

        Guide:
            - "재무상태표 보여줘" → c.show("BS")
            - "리스크 팩터 내용 보여줘" → c.show("risk") 또는 c.show("10-K::item1ARiskFactors")
            - "2024년 손익만 보고 싶어" → c.show("IS", period="2024")

        SeeAlso:
            - select: show() 결과에서 행/열 필터
            - trace: topic 데이터 출처 추적
            - sections: 전체 수평화 보드
            - topics: 사용 가능한 topic 목록

        Args:
            topic: topic 이름 (BS, IS, 10-K::item1Business, risk, mdna 등).
            block: blockOrder 인덱스. None이면 블록 목차.
            period: 특정 기간 필터. 리스트면 세로 뷰 (기간 x 항목).

        Returns
        -------
        pl.DataFrame | None
            finance topic (IS/BS/CF/CIS):
                account : str — 계정 식별자 (snakeId)
                2024, 2023, ... : float — 연간 값 (USD)
            ratios topic:
                account : str — 비율명
                2024, 2023, ... : float — 비율값 (%, 배)
            notes topic (inventory, borrowings 등):
                항목 : str — 세부 항목명
                연도 컬럼 : float — 금액 (USD)
            docs topic (10-K 항목):
                block 미지정: block : int, title : str — 블록 목차
                block 지정: 기간 컬럼에 텍스트 내용
            데이터 없으면 None.

        Example::

            c = Company("AAPL")
            c.show("BS")                          # 재무상태표
            c.show("10-K::item1ARiskFactors")     # Risk Factors 텍스트
            c.show("risk")                        # 위와 동일 (alias)
            c.show("IS", period="2024")           # 2024년만 필터
        """
        from dartlab.providers.edgar.builder.dataDispatcher import showImpl

        result = showImpl(self, topic, block, period=period, raw=raw, **_kw)
        if asOf is None or result is None:
            return result
        return _filterPeriodColumnsByAsOf(result, asOf)

    @staticmethod
    def _transposeToVertical(wide: pl.DataFrame, periods: list[str]) -> pl.DataFrame | None:
        from dartlab.providers.edgar.builder.dataDispatcher import transposeToVertical

        return transposeToVertical(wide, periods)

    def _buildBlockIndex(self, topicRows: pl.DataFrame) -> pl.DataFrame:
        """topic의 블록 목차 DataFrame."""
        from dartlab.providers.edgar.builder.dataDispatcher import buildBlockIndex

        return buildBlockIndex(topicRows)

    @property
    def select(self):
        """``show()`` 결과에서 행/열 필터 — dual access proxy.

        Returns:
            ``CallableAccessor`` — call/attr form 둘 다 ``_selectImpl`` 호출. ``SelectResult``
            반환. 상세는 ``_selectImpl`` docstring.

        Example:
            >>> c = Company("AAPL")
            >>> c.select("IS", ["sales"])    # call form
            >>> c.select.IS(["sales"])       # attr form

        Raises:
            없음 (해당 topic 부재 시 ``_selectImpl`` 이 None 반환).
        """
        from dartlab.core.dualAccess import CallableAccessor

        if "_selectAccessor" not in self._cache:
            self._cache["_selectAccessor"] = CallableAccessor(self._selectImpl, name="select")
        return self._cache["_selectAccessor"]

    def _selectImpl(
        self,
        topic: str,
        indList: str | list[str] | None = None,
        colList: str | list[str] | None = None,
        *,
        freq: str = "Q",
        scope: str = "consolidated",
        strict: bool = True,
    ):
        """show() 결과에서 행/열 필터 — 특정 계정 x 특정 기간 추출 (내부 구현).

        Capabilities:
            - show() 결과에서 행(항목)과 열(기간) 동시 필터
            - SelectResult 객체로 반환하여 체이닝/export 가능

        Requires:
            데이터: 없음 (SEC EDGAR 자동 수집)

        AIContext:
            - ask()/chat()에서 특정 계정 x 기간 조합을 정밀 추출

        Guide:
            - "Total Assets 2024년 값만 보여줘" → c.select("BS", "Total Assets", "2024")
            - "매출과 순이익 최근 2년" → c.select("IS", ["Revenue", "Net Income"], ["2024", "2023"])

        SeeAlso:
            - show: topic 전체 데이터 조회 (select의 입력 소스)
            - trace: topic 출처 추적

        Args:
            topic: topic 이름 (BS, IS 등).
            indList: 행 필터 — 항목 문자열 또는 리스트.
            colList: 열 필터 — 기간 문자열 또는 리스트.

        Returns
        -------
        SelectResult
            show()와 동일 컬럼 구조에서 indList/colList로 필터된 행/열.
            .chart() 체이닝으로 시각화 가능.
            내부 DataFrame 접근: result.df (pl.DataFrame).
            행 매칭 실패 시 ValueError (strict=True).

        Example::

            c = Company("AAPL")
            c.select("BS", "Total Assets", "2024")
            c.select("IS", ["Revenue", "Net Income"], ["2024", "2023"])
        """
        from dartlab.core.select import SelectResult
        from dartlab.core.show import selectFromShow

        # show() 가 ValueError 발생하면 그대로 propagate (silent None 차단)
        try:
            df = self.show(topic)
        except (ValueError, KeyError):
            if strict:
                raise
            return None
        if df is None or not isinstance(df, pl.DataFrame):
            if not strict:
                return None
            raise ValueError(
                f"'{topic}' topic 의 데이터를 가져올 수 없습니다 (EDGAR). "
                f"topic 이름을 확인하거나 c.show('{topic}') 로 직접 호출해보세요."
            )
        if isinstance(indList, str):
            indList = [indList]
        if isinstance(colList, str):
            colList = [colList]

        # 빈 indList → 명시적 안내
        if indList is not None and len(indList) == 0:
            if not strict:
                return None
            raise ValueError(
                "select 의 indList (행 필터) 가 비어 있습니다. "
                "필터링할 항목을 1개 이상 전달하세요. 예: c.select('IS', ['Revenue'])"
            )

        filtered = selectFromShow(df, indList, colList)
        if filtered is None:
            if not strict:
                return None
            # silent None 대신 명시적 ValueError
            available = []
            try:
                if df.width > 0:
                    first_col = df.columns[0]
                    available = df[first_col].drop_nulls().to_list()[:15]
            except (AttributeError, IndexError, TypeError):
                pass
            ind_str = indList if indList else colList
            hint = f"\n  사용 가능한 행 일부: {', '.join(str(a) for a in available)}" if available else ""
            raise ValueError(
                f"'{topic}' topic 에서 {ind_str} 를 찾을 수 없습니다 (EDGAR).{hint}\n"
                f"  c.show('{topic}') 로 전체 행을 확인하세요."
            )
        return SelectResult(
            filtered,
            topic,
            {
                "stockCode": getattr(self, "stockCode", self.ticker),
                "corpName": self.corpName,
                "currency": self.currency,
            },
        )

    def trace(self, topic: str, period: str | None = None) -> dict[str, Any] | None:
        """topic 데이터 출처 추적 — source provenance 확인.

        Capabilities:
            - topic 데이터가 docs/finance 중 어디서 왔는지 추적
            - 선택 근거(whySelected), 우선순위, 커버리지 정보 포함

        Requires:
            데이터: 없음 (SEC EDGAR 자동 수집)

        AIContext:
            - 데이터 신뢰성 검증에 활용 — 출처와 커버리지 확인

        Guide:
            - "이 데이터 어디서 왔어?" → c.trace("BS")
            - "docs에서 온 건지 finance에서 온 건지" → c.trace(topic)

        SeeAlso:
            - show: topic 데이터 조회
            - sections: 전체 수평화 보드
            - index: topic 메타데이터 보드

        Args:
            topic: topic 이름 (BS, IS, 10-K::item1ARiskFactors 등).
            period: 특정 기간 필터 (선택).

        Returns:
            dict — topic, primarySource, whySelected, availableSources 등. 없으면 None.

        Raises:
            없음 (데이터 부재 시 None 반환).

        Example:
            >>> c = Company("AAPL")
            >>> c.trace("BS")                          # finance 출처 확인
            >>> c.trace("10-K::item1ARiskFactors")     # docs 출처 확인
        """
        topic = _TOPIC_ALIASES.get(topic, topic)
        if topic in _FINANCE_TOPICS:
            df = getattr(self._finance, topic)
            if df is None:
                return None
            chapter, label = _topicChapterLabel(topic)
            return {
                "topic": topic,
                "period": period,
                "chapter": chapter,
                "label": label,
                "primarySource": "finance",
                "fallbackSources": [],
                "selectedPayloadRef": f"finance:{topic}",
                "availableSources": [{"source": "finance", "rows": df.height, "priority": 300}],
                "whySelected": "finance authoritative",
            }

        if topic == "ratios":
            rs = self._finance.ratioSeries
            if rs is None:
                return None
            series, years = rs
            df = _ratioSeriesToDataFrame(series, years)
            rowCount = df.height if df is not None else None
            yearCount = len(years)
            if df is not None and rowCount >= 20 and yearCount >= 5:
                coverage = "full"
            elif df is not None and rowCount > 0:
                coverage = "partial"
            else:
                coverage = "missing"
            chapter, label = _topicChapterLabel(topic)
            return {
                "topic": topic,
                "period": period,
                "chapter": chapter,
                "label": label,
                "primarySource": "finance",
                "fallbackSources": [],
                "selectedPayloadRef": "finance:RATIO",
                "availableSources": [{"source": "finance", "rows": 1, "priority": 300}],
                "whySelected": "finance authoritative",
                "rowCount": rowCount,
                "yearCount": yearCount,
                "coverage": coverage,
            }

        sec = self._docs.sections
        if sec is not None and topic in sec["topic"].to_list():
            topicRows = sec.filter(pl.col("topic") == topic)
            periodCols = [c for c in sec.columns if _isPeriodColumn(c)]
            nonNullPeriods = set()
            hasText = hasTable = False
            if "blockType" in sec.columns:
                hasText = topicRows.filter(pl.col("blockType") == "text").height > 0
                hasTable = topicRows.filter(pl.col("blockType") == "table").height > 0
            for r in topicRows.iter_rows(named=True):
                for c in periodCols:
                    if r.get(c) is not None:
                        nonNullPeriods.add(c)
            chapter, label = _topicChapterLabel(topic)
            return {
                "topic": topic,
                "period": period,
                "chapter": chapter,
                "label": label,
                "primarySource": "docs",
                "fallbackSources": [],
                "selectedPayloadRef": f"docs:{topic}",
                "availableSources": [{"source": "docs", "rows": topicRows.height, "priority": 100}],
                "whySelected": "docs authoritative",
                "periodCount": len(nonNullPeriods),
                "hasText": hasText,
                "hasTable": hasTable,
            }

        return None

    @property
    def index(self) -> pl.DataFrame:
        """topic별 메타데이터 인덱스 — chapter/label/kind/source/periods 보드.

        Capabilities:
            - 전체 topic의 chapter, label, kind(finance/docs), source, periods, shape 요약
            - sections 수평화 보드의 메타 레이어

        Requires:
            데이터: 없음 (SEC EDGAR 자동 수집)

        AIContext:
            - 전체 topic 구조를 한눈에 파악하여 분석 계획 수립에 활용

        Guide:
            - "전체 인덱스 보여줘" → c.index
            - "어떤 데이터가 있는지 요약" → c.index로 메타 정보 확인

        SeeAlso:
            - topics: topic 목록 간단 요약
            - sections: 전체 수평화 보드 원본
            - show: 특정 topic 데이터 조회
            - view: 브라우저에서 시각적 탐색

        Returns:
            pl.DataFrame — ``chapter | topic | label | kind | source | periods | shape | preview``.

        Raises:
            없음 (데이터 부재 시 빈 DataFrame).

        Example:
            >>> c = Company("AAPL")
            >>> c.index  # Apple 전체 topic 인덱스 보드
        """
        cacheKey = "_index"
        if cacheKey in self._cache:
            return self._cache[cacheKey]

        rows: list[dict[str, Any]] = []
        for topic in self.topics["topic"].to_list():
            traced = self.trace(topic)
            source = traced["primarySource"] if traced else None
            chapter, label = _topicChapterLabel(topic)

            if topic in _FINANCE_TOPICS:
                df = getattr(self._finance, topic)
                rows.append(
                    {
                        "chapter": chapter,
                        "topic": topic,
                        "label": label,
                        "kind": "finance",
                        "source": source,
                        "periods": self._periodsStr(df),
                        "shape": self._shapeStr(df),
                        "preview": self._previewFinance(df),
                    }
                )
            elif topic == "ratios":
                rs = self._finance.ratioSeries
                if rs is not None:
                    _, years = rs
                    df = _ratioSeriesToDataFrame(*rs)
                    rows.append(
                        {
                            "chapter": chapter,
                            "topic": topic,
                            "label": label,
                            "kind": "finance",
                            "source": source,
                            "periods": f"{years[0]}..{years[-1]}" if len(years) > 1 else (years[0] if years else "-"),
                            "shape": self._shapeStr(df),
                            "preview": f"{df.height} metrics" if df is not None else "-",
                        }
                    )
            else:
                sec = self._docs.sections
                if sec is not None:
                    topicRows = sec.filter(pl.col("topic") == topic)
                    periodCols = [c for c in sec.columns if _isPeriodColumn(c)]
                    if not topicRows.is_empty():
                        # 비어있지 않은 기간 수
                        nonNullPeriods = set()
                        for r in topicRows.iter_rows(named=True):
                            for c in periodCols:
                                if r.get(c) is not None:
                                    nonNullPeriods.add(c)
                        rows.append(
                            {
                                "chapter": chapter,
                                "topic": topic,
                                "label": label,
                                "kind": "docs",
                                "source": source,
                                "periods": f"{periodCols[0]}..{periodCols[-1]}"
                                if len(periodCols) > 1
                                else (periodCols[0] if periodCols else "-"),
                                "shape": f"{len(nonNullPeriods)}기간",
                                "preview": self._previewDocsCell(topicRows, periodCols),
                            }
                        )

        df = (
            pl.DataFrame(rows)
            if rows
            else pl.DataFrame(
                schema={
                    "chapter": pl.Utf8,
                    "topic": pl.Utf8,
                    "label": pl.Utf8,
                    "kind": pl.Utf8,
                    "source": pl.Utf8,
                    "periods": pl.Utf8,
                    "shape": pl.Utf8,
                    "preview": pl.Utf8,
                }
            )
        )
        self._cache[cacheKey] = df
        return df

    def _applyPeriodFilter(self, payload: Any, period: str | None) -> Any:
        from dartlab.providers.edgar.builder.dataDispatcher import applyPeriodFilter

        return applyPeriodFilter(payload, period)

    @staticmethod
    def _shapeStr(df: pl.DataFrame | None) -> str:
        from dartlab.providers.edgar.builder.dataDispatcher import shapeStr

        return shapeStr(df)

    @staticmethod
    def _periodsStr(df: pl.DataFrame | None) -> str:
        from dartlab.providers.edgar.builder.dataDispatcher import periodsStr

        return periodsStr(df)

    @staticmethod
    def _previewFinance(df: pl.DataFrame | None) -> str:
        from dartlab.providers.edgar.builder.dataDispatcher import previewFinance

        return previewFinance(df)

    @staticmethod
    def _previewDocsCell(topicRows: pl.DataFrame, periodCols: list[str]) -> str:
        from dartlab.providers.edgar.builder.dataDispatcher import previewDocsCell

        return previewDocsCell(topicRows, periodCols)

    def diff(
        self,
        topic: str | None = None,
        fromPeriod: str | None = None,
        toPeriod: str | None = None,
    ) -> pl.DataFrame | None:
        """기간간 텍스트 변경 비교 — 공시 서술형 diff.

        Capabilities:
            - 전체 topic 변경 요약 (topic 없이 호출)
            - 특정 topic의 기간별 변경 이력
            - 두 기간 지정 시 줄 단위 diff (추가/삭제/변경)

        Requires:
            데이터: 없음 (SEC EDGAR 자동 수집)

        AIContext:
            - ask()/chat()에서 공시 변경 포인트 감지 및 해석에 활용

        Guide:
            - "전체적으로 뭐가 바뀌었어?" → c.diff()
            - "리스크 팩터 변경 내역" → c.diff("10-K::item1ARiskFactors")
            - "2023→2024 MD&A 비교" → c.diff("10-K::item7Mdna", "2023", "2024")

        SeeAlso:
            - watch: 변화 중요도 스코어링 (diff보다 요약)
            - keywordTrend: 키워드 빈도 추이
            - show: topic 데이터 조회

        Args:
            topic: topic 이름. None이면 전체 변경 요약.
            fromPeriod: 비교 시작 기간 (예: "2023").
            toPeriod: 비교 종료 기간 (예: "2024").

        Returns:
            pl.DataFrame — 변경 요약/이력/줄단위 diff. 없으면 None.

        Example::

            c = Company("AAPL")
            c.diff()                                          # 전체 변경 요약
            c.diff("10-K::item1ARiskFactors")                 # Risk Factors 변경 이력
            c.diff("10-K::item7Mdna", "2023", "2024")         # MD&A 줄 단위 diff
        """
        from dartlab.core.docs.diff import (
            diffSummaryDataFrame,
            lineDiffDataFrame,
            sectionsDiff,
            topicHistoryDataFrame,
        )

        docsSections = self._docs.sections
        if docsSections is None:
            return None
        if topic is not None and fromPeriod is not None and toPeriod is not None:
            return lineDiffDataFrame(docsSections, topic, fromPeriod, toPeriod)
        diffResult = sectionsDiff(docsSections)
        if topic is not None:
            return topicHistoryDataFrame(diffResult, topic)
        return diffSummaryDataFrame(diffResult)

    def keywordTrend(
        self,
        keyword: str | None = None,
        keywords: list[str] | None = None,
    ) -> pl.DataFrame | None:
        """공시 텍스트 키워드 빈도 추이 — topic x period x keyword 히트맵.

        Capabilities:
            - 10-K/10-Q 서술형 텍스트에서 키워드 등장 빈도 추적
            - 단일 키워드 또는 복수 키워드 동시 추적
            - 키워드 미지정 시 내장 기본 키워드(AI, risk 등) 전체 분석

        Requires:
            데이터: 없음 (SEC EDGAR 자동 수집)

        AIContext:
            - 공시 텍스트 내 특정 주제의 강조도 변화를 추적

        Guide:
            - "AI라는 단어가 공시에서 얼마나 자주 나와?" → c.keywordTrend("AI")
            - "여러 키워드 추이를 한번에" → c.keywordTrend(keywords=["AI", "supply chain"])

        SeeAlso:
            - diff: 기간간 텍스트 변경 비교
            - watch: 변화 중요도 스코어링
            - show: topic 원문 조회

        Args:
            keyword: 단일 키워드 문자열.
            keywords: 복수 키워드 리스트. keyword와 동시 지정 시 keyword 우선.

        Returns:
            pl.DataFrame — topic | period | keyword | count. 없으면 None.

        Example::

            c = Company("AAPL")
            c.keywordTrend("AI")                              # AI 키워드 추이
            c.keywordTrend(keywords=["AI", "supply chain"])   # 복수 키워드
            c.keywordTrend()                                  # 내장 키워드 전체
        """
        from dartlab.core.docs.diff import keywordFrequency

        docsSections = self._docs.sections
        if docsSections is None:
            return None
        kws = None
        if keyword:
            kws = [keyword]
        elif keywords:
            kws = keywords
        return keywordFrequency(docsSections, keywords=kws)

    def news(self, *, days: int = 30) -> pl.DataFrame:
        """최근 뉴스 수집 — 종목 관련 뉴스 DataFrame.

        Capabilities:
            - 종목명/ticker 기반 최근 뉴스 수집
            - 기간 조절 가능 (기본 30일)

        Requires:
            데이터: 인터넷 연결 (뉴스 API)

        AIContext:
            - ask()/chat()에서 최근 이벤트 맥락 파악에 활용

        Guide:
            - "최근 뉴스 뭐 있어?" → c.news()
            - "지난 1주일 뉴스만" → c.news(days=7)

        SeeAlso:
            - gather: 외부 데이터 수집 (뉴스 포함)
            - watch: 공시 변화 감지
            - disclosure: SEC filing 검색

        Args:
            days: 수집 기간 일수 (기본 30).

        Returns:
            pl.DataFrame — 뉴스 제목, 날짜, URL 등 포함.

        Example::

            c = Company("AAPL")
            c.news()           # 최근 30일 뉴스
            c.news(days=7)     # 최근 7일
        """
        from dartlab.core.gatherProvider import getGatherProvider

        provider = getGatherProvider()
        return provider.news(self.ticker, market="US", days=days) if provider else None

    def watch(
        self,
        topic: str | None = None,
    ) -> pl.DataFrame | None:
        """공시 변화 감지 — 중요도 스코어링 기반 변화 요약.

        Capabilities:
            - 기간간 공시 텍스트 변화를 중요도 점수로 자동 스코어링
            - topic 미지정 시 전체 topic 중요도 순 정렬
            - 특정 topic 지정 시 해당 topic 상세 변화 분석

        Requires:
            데이터: 없음 (SEC EDGAR 자동 수집)

        AIContext:
            - ask()/chat()에서 주목할 공시 변화 포인트 자동 감지에 활용

        Guide:
            - "뭐가 중요하게 바뀌었어?" → c.watch()
            - "리스크 팩터 변화 상세" → c.watch("10-K::item1ARiskFactors")

        SeeAlso:
            - diff: 기간간 텍스트 변경 비교 (줄 단위)
            - keywordTrend: 키워드 빈도 추이
            - show: topic 데이터 조회

        Args:
            topic: topic 이름. None이면 전체 topic 요약.

        Returns:
            pl.DataFrame — topic | score | summary 등. 없으면 None.

        Example::

            c = Company("AAPL")
            c.watch()                              # 전체 topic 중요도 순 요약
            c.watch("10-K::item1ARiskFactors")     # Risk Factors 상세
        """
        import importlib

        scanner = importlib.import_module("dartlab.scan.watch.scanner")
        result = scanner.scanCompany(self, topic=topic)
        if result is None:
            return None
        return result.toDataframe()

    # ── AI 분석 ──

    def ask(
        self,
        question: str,
        *,
        provider: str | None = None,
        model: str | None = None,
        stream: bool = False,
        reflect: bool = False,
        **kwargs,
    ) -> str:
        """LLM에게 이 기업에 대해 질문 — 엔진 계산 결과 기반 AI 해석.

        Capabilities:
            - 질문 분류 → 분석 패키지 선택 → 엔진 계산 → LLM 해석
            - include/exclude로 컨텍스트 범위 조절
            - 복수 LLM provider 지원 (openai, ollama 등)

        Requires:
            데이터: LLM API 키 설정 (dartlab ai 또는 환경변수)

        AIContext:
            AI가 분석 전 과정을 주도. dartlab 엔진을 도구로 호출하여 분석 수행.

        Guide:
            - "이 기업 리스크가 뭐야?" → c.ask("What are the key risks?")
            - "매출 추세 분석해줘" → c.ask("Revenue trend analysis")

        SeeAlso:
            - chat: agent mode (tool calling으로 심화 분석)
            - analysis: 분석 엔진 (ask의 컨텍스트 소스)
            - insights: 재무 인사이트 (ask의 컨텍스트 소스)

        Args:
            question: 자연어 질문.
            include: 포함할 컨텍스트 키 리스트.
            exclude: 제외할 컨텍스트 키 리스트.
            provider: LLM provider 이름 (예: "openai", "ollama").
            model: 모델명. None이면 provider 최신 기본값.
            stream: 스트리밍 출력 여부.
            reflect: 자기 반성 모드 (답변 품질 자가 검증).

        Returns:
            str — LLM 응답 텍스트. ``stream=True`` 면 ``Generator[str]``.

        Raises:
            ValueError: provider/model 미설정 + 환경변수 키 부재.
            RuntimeError: LLM API 호출 실패.

        Example:
            >>> c = Company("AAPL")
            >>> c.ask("What are the key risks?")
            >>> c.ask("Revenue trend analysis", provider="openai")
        """
        import importlib

        _ask = importlib.import_module("dartlab.ai.kernel").ask
        return _ask(
            question,
            stockCode=self.stockCode,
            provider=provider,
            model=model,
            stream=stream,
            reflect=reflect,
            **kwargs,
        )

    @property
    def _report(self):
        """[INTERNAL] EDGAR report 백엔드 — XBRL 기반. 사용자 API: c.show(...)."""
        if self._reportAccessor is None:
            from dartlab.providers.edgar.accessor.reportAccessor import _ReportAccessor

            self._reportAccessor = _ReportAccessor(self)
        return self._reportAccessor

    # ── DartCompany 동기화 메소드 (test_protocol 방어막) ──
    # 아래 메소드는 DartCompany와 인터페이스를 맞추기 위해 존재한다.
    # DART report 전용 데이터가 필요한 경우 None/빈값을 반환한다.

    # ── Properties (데이터 위임) ──

    @property
    def contextSlices(self) -> pl.DataFrame | None:
        """contextSlices — TODO 한국어 동작 설명."""
        return self._docs.contextSlices if hasattr(self._docs, "contextSlices") else None

    @property
    def retrievalBlocks(self) -> pl.DataFrame | None:
        """retrievalBlocks — TODO 한국어 동작 설명."""
        return self._docs.retrievalBlocks if hasattr(self._docs, "retrievalBlocks") else None

    @property
    def notes(self):
        """주석 접근자 — EDGAR docs.notes를 래핑하여 DART Notes와 동일 인터페이스 제공."""
        from dartlab.core.memory import _CACHE_MISSING

        val = self._cache.get("_notes_wrapper", _CACHE_MISSING)
        if val is _CACHE_MISSING:
            val = _EdgarNotesWrapper(self)
            self._cache["_notes_wrapper"] = val
        return val

    @property
    def facts(self) -> pl.DataFrame | None:
        """topic × period 형태의 통합 facts 테이블."""
        return getattr(self._profileAccessor, "facts", None)

    # c.ratioSeries property 제거 (Plan v10 P1) — show("ratios") 사용
    # sector, sectorParams, sceMatrix — EXEMPT (test_protocol.py)

    @property
    def rank(self):
        """rank — TODO 한국어 동작 설명."""
        return None  # US 피어 랭킹 미지원 (향후 구현 예정)

    @property
    def sources(self) -> pl.DataFrame:
        """데이터 소스 현황 — EDGAR는 docs + finance 2개 소스."""
        rows = []
        for src, accessor in [("docs", self._docs), ("finance", self._finance)]:
            available = accessor is not None
            rows.append({"source": src, "available": available, "rows": 0, "cols": 0, "shape": ""})
        return pl.DataFrame(rows)

    # ── Methods ──

    def table(
        self, topic: str, subtopic: str | None = None, *, numeric: bool = False, period: str | None = None
    ) -> Any:
        """topic 데이터를 테이블 형태로 반환."""
        df = self.show(topic, period=period)
        if df is None:
            return None
        return df

    def audit(self) -> list | None:
        """감사/내부통제 분석 — EDGAR item9A + item14 기반.

        10-K Item 9A(Controls and Procedures) 텍스트에서 material weakness,
        going concern 등 핵심 키워드를 탐지한다.

        Returns
        -------
        list[dict] | None
            각 dict 키:
                type : str — 발견 유형 (material_weakness/going_concern/
                    ineffective_controls/clean/audit_fees)
                period : str — 해당 기간 (예: "2024")
                severity : str — 심각도 (critical/warning/ok)
                amount : str — 감사 수수료 금액 (audit_fees 유형만)
            발견 없으면 None.
        """
        import re

        findings: list[dict] = []
        # Item 9A: 내부통제
        item9a = self.show("10-K::item9AControlsAndProcedures", block=0)
        if item9a is not None:
            from dartlab.core.show import isPeriodColumn

            pcols = [c for c in item9a.columns if isPeriodColumn(c)]
            if pcols:
                latest = pcols[0]
                text = " ".join(str(v) for v in item9a[latest].to_list() if v)
                text_lower = text.lower()
                if "material weakness" in text_lower:
                    findings.append({"type": "material_weakness", "period": latest, "severity": "critical"})
                if "going concern" in text_lower:
                    findings.append({"type": "going_concern", "period": latest, "severity": "critical"})
                if "not effective" in text_lower or "ineffective" in text_lower:
                    findings.append({"type": "ineffective_controls", "period": latest, "severity": "warning"})
                if not findings:
                    findings.append({"type": "clean", "period": latest, "severity": "ok"})
        # Item 14: 감사 수수료
        item14 = self.show("10-K::item14PrincipalAccountantFees", block=0)
        if item14 is not None:
            from dartlab.core.show import isPeriodColumn

            pcols = [c for c in item14.columns if isPeriodColumn(c)]
            if pcols:
                latest = pcols[0]
                text = " ".join(str(v) for v in item14[latest].to_list() if v)
                fee_matches = re.findall(r"\$([\d,.]+)\s*(?:million|billion)", text, re.IGNORECASE)
                if fee_matches:
                    findings.append({"type": "audit_fees", "period": latest, "amount": fee_matches[0]})
        return findings or None

    def governance(self, view: str | None = None) -> pl.DataFrame | None:
        """지배구조 분석 — EDGAR item10/item12 기반.

        10-K Part III에서 이사회 구성, 소유 구조 텍스트를 제공한다.
        DART와 달리 구조화된 수치가 아닌 텍스트 데이터이다.

        Returns
        -------
        pl.DataFrame | None
            항목 : str — 분석 영역 (directors/ownership/compensation)
            기간 : str — 데이터 기간 (예: "2024")
            내용 : str — 10-K 텍스트 요약 (최대 500자)
            view="all"/"market"이면 None (EDGAR 미지원).
            데이터 없으면 None.
        """
        if view in ("all", "market"):
            return None
        rows: list[dict] = []
        for topic_key, label in [
            ("10-K::item10DirectorsAndCorporateGovernance", "directors"),
            ("10-K::item12SecurityOwnership", "ownership"),
            ("10-K::item11ExecutiveCompensation", "compensation"),
        ]:
            df = self.show(topic_key, block=0)
            if df is not None:
                from dartlab.core.show import isPeriodColumn

                pcols = [c for c in df.columns if isPeriodColumn(c)]
                if pcols:
                    latest = pcols[0]
                    text = " ".join(str(v) for v in df[latest].to_list() if v)
                    rows.append({"항목": label, "기간": latest, "내용": text[:500] if text else ""})
        if not rows:
            return None
        return pl.DataFrame(rows)

    def workforce(self, view: str | None = None) -> pl.DataFrame | None:
        """인력 분석 — EDGAR item1 + IS 기반.

        10-K Item 1(Business)에서 직원 수를 추출하고, IS 매출 대비
        1인당 매출을 계산한다.
        """
        import re

        if view in ("all", "market"):
            return None
        # 모든 block의 텍스트를 합쳐서 employee 패턴 검색
        employee_count: int | None = None
        period: str | None = None
        item1_idx = self.show("10-K::item1Business")
        if item1_idx is None:
            return None
        for row in item1_idx.iter_rows(named=True):
            block_id = row.get("block", 0)
            block_df = self.show("10-K::item1Business", block=block_id)
            if block_df is None:
                continue
            from dartlab.core.show import isPeriodColumn

            pcols = [c for c in block_df.columns if isPeriodColumn(c)]
            if not pcols:
                continue
            # 이 block에 있는 기간 중 첫 번째 사용
            block_period = pcols[0]
            if period is None:
                period = block_period
            if block_period not in block_df.columns:
                continue
            text = " ".join(str(v) for v in block_df[block_period].to_list() if v)
            # 다양한 패턴: "approximately N employees", "N full-time employees", "had N employees"
            patterns = [
                r"(?:approximately|about|over|nearly|had)\s+([\d,]+)\s+(?:full.?time\s+)?employee",
                r"([\d,]+)\s+full.?time\s+employee",
                r"([\d,]+)\s+employee",
                r"employee(?:s)?\s+(?:was|were|of)\s+(?:approximately\s+)?([\d,]+)",
                r"headcount\s+(?:of\s+)?(?:approximately\s+)?([\d,]+)",
                r"workforce\s+(?:of\s+)?(?:approximately\s+)?([\d,]+)",
            ]
            for pat in patterns:
                matches = re.findall(pat, text, re.IGNORECASE)
                for m in matches:
                    cleaned = (m if isinstance(m, str) else m[-1]).replace(",", "").strip()
                    if cleaned and cleaned.isdigit() and int(cleaned) > 100:
                        employee_count = int(cleaned)
                        break
                if employee_count:
                    break
            if employee_count:
                break
        if employee_count is None:
            return None
        # 1인당 매출 계산
        rev_per_employee = None
        isDf = self.show("IS")
        if isDf is not None:
            from dartlab.core.show import isPeriodColumn, selectFromShow

            rev_row = selectFromShow(isDf, ["sales"])
            if rev_row is not None:
                pcols = [c for c in rev_row.columns if isPeriodColumn(c)]
                if pcols:
                    rev = rev_row[pcols[0]][0]
                    if rev:
                        rev_per_employee = rev / employee_count
        return pl.DataFrame(
            [
                {
                    "종목코드": self.ticker,
                    "회사명": self.corpName,
                    "직원수": employee_count,
                    "기간": period,
                    "1인당매출": rev_per_employee,
                }
            ]
        )

    def capital(self, view: str | None = None) -> pl.DataFrame | None:
        """주주환원/자본구조 — EDGAR BS/CF 기반 단일 회사 분석.

        DART와 달리 전종목 횡단비교(view="all")는 미지원.

        Returns
        -------
        pl.DataFrame | None
            종목코드 : str — ticker
            회사명 : str — 회사명
            total_stockholders_equity : float — 자기자본 (USD)
            retained_earnings : float — 이익잉여금 (USD)
            dividends_paid : float — 배당금 지급액 (USD, 있을 때만)
            view="all"/"market"이면 None.
        """
        if view in ("all", "market"):
            return None  # 전종목 횡단비교 미지원
        bs = self.show("BS")
        cf = self.show("CF")
        if bs is None:
            return None
        from dartlab.core.show import selectFromShow

        equity = selectFromShow(bs, ["total_stockholders_equity", "retained_earnings"])
        divs = selectFromShow(cf, ["dividends_paid"]) if cf is not None else None
        if equity is None:
            return None
        rows: list[dict] = [{"종목코드": self.ticker, "회사명": self.corpName}]
        from dartlab.core.show import isPeriodColumn

        pcols = [c for c in equity.columns if isPeriodColumn(c)]
        if pcols:
            latest = pcols[0]
            for row in equity.iter_rows(named=True):
                rows[0][row["snakeId"]] = row.get(latest)
            if divs is not None:
                for row in divs.iter_rows(named=True):
                    rows[0][row["snakeId"]] = row.get(latest)
        return pl.DataFrame(rows)

    def debt(self, view: str | None = None) -> pl.DataFrame | None:
        """부채구조 분석 — EDGAR BS 기반 단일 회사 분석.

        DART와 달리 전종목 횡단비교(view="all")는 미지원.

        Returns
        -------
        pl.DataFrame | None
            종목코드 : str — ticker
            회사명 : str — 회사명
            total_liabilities : float — 부채총계 (USD)
            shortterm_borrowings : float — 단기차입금 (USD)
            longterm_borrowings : float — 장기차입금 (USD)
            current_liabilities : float — 유동부채 (USD)
            noncurrent_liabilities : float — 비유동부채 (USD)
            view="all"/"market"이면 None.
        """
        if view in ("all", "market"):
            return None
        bs = self.show("BS")
        if bs is None:
            return None
        from dartlab.core.show import selectFromShow

        debt_accts = selectFromShow(
            bs,
            [
                "total_liabilities",
                "shortterm_borrowings",
                "longterm_borrowings",
                "debentures",
                "current_liabilities",
                "noncurrent_liabilities",
            ],
        )
        if debt_accts is None:
            return None
        rows: list[dict] = [{"종목코드": self.ticker, "회사명": self.corpName}]
        from dartlab.core.show import isPeriodColumn

        pcols = [c for c in debt_accts.columns if isPeriodColumn(c)]
        if pcols:
            latest = pcols[0]
            for row in debt_accts.iter_rows(named=True):
                rows[0][row["snakeId"]] = row.get(latest)
        return pl.DataFrame(rows)
