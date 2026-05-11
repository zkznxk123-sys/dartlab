"""DART 엔진 내부 Company 본체.

사용법::

    from dartlab.providers.dart.company import Company

    c = Company("005930")         # 한국 (DART)
    c = Company("삼성전자")        # 한국 (회사명)
    c.show("BS")                  # 재무상태표 DataFrame (분기 연결 기본)
    c.show("IS", freq="Y")        # 손익계산서 (연간 합산)
    c.show("ratios")              # 재무비율
    c.insights                    # 인사이트 등급
"""

from __future__ import annotations

import re
from typing import Any

import polars as pl

pl.Config.set_fmt_str_lengths(80)
pl.Config.set_tbl_width_chars(200)

from dartlab.core.dataLoader import (
    buildIndex,
    extractCorpName,
    loadData,
)
from dartlab.core.logger import getLogger
from dartlab.core.polarsUtil import isEmptyDf

_log = getLogger(__name__)

# ── 모듈 레지스트리 (core/registry.py에서 자동 생성) ──
# (모듈 import 경로, 함수명, 한글 라벨, primary DataFrame 추출)
# fsSummary/statements는 내부 디스패치 전용 (BS/IS/CF property가 statements를 호출)
from dartlab.core.registry import getModuleEntries as _getModuleEntries


# listing 함수는 ListingResolver registry 경유 (정공법 B — DIP).
# providers/dart 가 gather/listing 직접 import 0 (cycle 회피).
def _listingResolver():
    """ListingResolver lazy resolver — auto-discovery 가 gather/listing register."""
    from dartlab.core.listingResolver import getListingResolver

    resolver = getListingResolver()
    if resolver is None:
        raise RuntimeError("ListingResolver 미등록 — dartlab.gather.listing 모듈 로드 실패")
    return resolver


def codeToName(stockCode):
    """ListingResolver 경유 stockCode → 회사명."""
    return _listingResolver().codeToName(stockCode)


def nameToCode(corpName):
    """ListingResolver 경유 회사명 → stockCode."""
    return _listingResolver().nameToCode(corpName)


def getKindList(*, forceRefresh: bool = False):
    """ListingResolver 경유 KIND 상장법인 목록."""
    return _listingResolver().kindList(forceRefresh=forceRefresh)


def searchName(keyword):
    """ListingResolver 경유 회사명 검색."""
    return _listingResolver().search(keyword)


from dartlab.providers.dart.checks import (
    _checkDartDocsFreshness,
    _ensureAllData,
    _importAndCall,
    _shapeString,
)
from dartlab.providers.dart.docs.notes import Notes
from dartlab.providers.dart.docsAccessor import _DocsAccessor
from dartlab.providers.dart.financeAccessor import _FinanceAccessor
from dartlab.providers.dart.financeMappers import (
    _RATIO_TEMPLATE_FIELDS,
    _ratioArchetypeOverrideForIndustryGroup,
    _ratioResultHasHeadlineSignal,
    _ratioSeriesToDataFrame,
    _ratioTemplateKeyForIndustryGroup,
    _shouldFallbackToAnnualRatios,
)
from dartlab.providers.dart.profileAccessor import _ProfileAccessor
from dartlab.providers.dart.reportAccessor import _ReportAccessor

# 플러그인 등록 후 재구축 가능하도록 lazy 초기화
_MODULE_REGISTRY: list[tuple[str, str, str, Any]] | None = None
_MODULE_INDEX: dict[str, int] | None = None
_ALL_PROPERTIES: list[tuple[str, str]] | None = None


def _getModuleRegistry() -> list[tuple[str, str, str, Any]]:
    """lazy 모듈 레지스트리 — 최초 접근 시 구축."""
    global _MODULE_REGISTRY, _MODULE_INDEX
    if _MODULE_REGISTRY is None:
        _MODULE_REGISTRY = [
            ("dartlab.providers.dart.docs.finance.summary", "fsSummary", "요약재무정보", None),
            ("dartlab.providers.dart.docs.finance.statements", "statements", "재무제표", None),
        ] + [(e.modulePath, e.funcName, e.label, e.extractor) for e in _getModuleEntries()]
        _MODULE_INDEX = {entry[1]: i for i, entry in enumerate(_MODULE_REGISTRY)}
    return _MODULE_REGISTRY


def _getModuleIndex() -> dict[str, int]:
    """lazy 모듈 인덱스 — 최초 접근 시 구축."""
    global _MODULE_INDEX
    if _MODULE_INDEX is None:
        _getModuleRegistry()
    return _MODULE_INDEX  # type: ignore[return-value]


def _getAllProperties() -> list[tuple[str, str]]:
    """lazy all() 순서 목록 — 최초 접근 시 구축."""
    global _ALL_PROPERTIES
    if _ALL_PROPERTIES is None:
        _ALL_PROPERTIES = [
            ("BS", "재무상태표"),
            ("IS", "손익계산서"),
            ("CF", "현금흐름표"),
        ]
        for entry in _getModuleRegistry():
            name = entry[1]
            if name in ("fsSummary", "statements", "companyOverview"):
                continue
            _ALL_PROPERTIES.append((name, entry[2]))
    return _ALL_PROPERTIES


def rebuildModuleRegistry() -> None:
    """플러그인 등록 후 호출 — 모듈 레지스트리 캐시 무효화."""
    global _MODULE_REGISTRY, _MODULE_INDEX, _ALL_PROPERTIES
    _MODULE_REGISTRY = None
    _MODULE_INDEX = None
    _ALL_PROPERTIES = None


_CHAPTER_TITLES: dict[str, str] = {
    "I": "I. 회사의 개요",
    "II": "II. 사업의 내용",
    "III": "III. 재무에 관한 사항",
    "IV": "IV. 이사의 경영진단 및 분석의견",
    "V": "V. 감사인의 감사의견등",
    "VI": "VI. 이사회등회사의기관및계열회사에관한사항",
    "VII": "VII. 주주에 관한 사항",
    "VIII": "VIII. 임원 및 직원 등에 관한 사항",
    "IX": "IX. 이해관계자와의 거래내용",
    "X": "X. 그 밖에 투자자 보호를 위하여 필요한 사항",
    "XI": "XI. 재무제표등",
    "XII": "XII. 상세표 및 부속명세서",
}

_CHAPTER_ORDER: dict[str, int] = {chapter: idx for idx, chapter in enumerate(_CHAPTER_TITLES, start=1)}


# Q1.1 (2026-04-21): `_REPORT_TOPIC_TO_API_TYPE` / `_API_TYPE_TO_TOPIC` 하드코딩
# dict 제거. registry DataEntry.apiType 필드로 단일 출처화.
# topic ↔ DART API apiType 변환은 아래 두 헬퍼 하나로.


def _apiTypeForTopic(topic: str) -> str:
    """topic → DART API apiType. registry entry 의 apiType 이 있으면 그걸, 없으면 topic 그대로."""
    from dartlab.core.registry import getEntry

    entry = getEntry(topic)
    if entry is not None and entry.apiType:
        return entry.apiType
    return topic


def _topicForApiType(apiType: str) -> str:
    """DART API apiType → user-facing topic. registry 에서 역탐색.

    registry 에서 apiType 필드가 매치되는 entry 찾아 name 리턴. 없으면 apiType 그대로.
    """
    from dartlab.core.registry import getModuleEntries

    for e in getModuleEntries():
        if e.apiType and e.apiType == apiType:
            return e.name
    return apiType


# ── 재무제표 약칭 (AI-친화 layer) ──────────────────────────────────
# AI 가 흔히 시도하는 영문 lower-case / 복수형 / 합성어 → canonical 재무제표 topic.
# Business alias (board/pay/tangible 등 → 해당 topic) 는 registry.resolveAlias() 로
# 이관 (2026-04-21 Q1.4). 여기는 핵심 4 재무제표의 case-insensitive 변형만 유지.
_AI_CASE_ALIAS: dict[str, str] = {
    "cashflow": "CF",
    "cashflows": "CF",
    "cf": "CF",
    "incomestatement": "IS",
    "is": "IS",
    "pl": "IS",
    "profitloss": "IS",
    "balancesheet": "BS",
    "bs": "BS",
    "comprehensiveincome": "CIS",
    "cis": "CIS",
    "equitychanges": "SCE",
    "sce": "SCE",
}


def _resolveTopic(topic: str) -> str:
    """topic 또는 alias → canonical topic name.

    순서: (1) AI-친화 lowercase 변형, (2) registry business alias, (3) 그대로.
    """
    if topic in _AI_CASE_ALIAS:
        return _AI_CASE_ALIAS[topic]
    from dartlab.core.registry import resolveAlias

    return resolveAlias(topic)


_TOPIC_LABELS: dict[str, str] = {
    "businessOverview": "사업의 개요",
    "businessStatus": "사업현황",
    "consolidatedNotes": "연결재무제표 주석",
    "consolidatedStatements": "연결재무제표",
    "financialNotes": "재무제표 주석",
    "financialStatements": "재무제표",
    "financialSoundnessOtherReference": "재무건전성 기타참고",
    "governanceOverview": "지배구조 개요",
    "majorContractsAndRnd": "주요계약 및 R&D",
    "mdna": "경영진단 및 분석의견",
    "segmentFinancialSummary": "부문별 재무요약",
    "investmentInOtherDetail": "타법인출자 상세",
    "stockAdministration": "주식사무",
    "stockPriceTrend": "주가 추이",
    "appendixSchedule": "상세표",
    "investorProtection": "투자자보호",
    "disclosureChanges": "공시내용 변경",
    "subsequentEvents": "후발사건",
    "expertConfirmation": "전문가확인",
    "subsidiaryDetail": "종속회사 상세",
    "affiliateGroupDetail": "계열회사 상세",
    "rndDetail": "연구개발 상세",
    "otherReference": "기타참고사항",
    "otherReferences": "기타참고사항",
    "operatingFacilities": "생산설비",
    # subtopic에 등장하는 내부 topic명 한글화
    "marketRisk": "시장위험",
    "liquidityRisk": "유동성위험",
    "capitalRisk": "자본위험",
    "creditRisk": "신용위험",
    "derivativeExposure": "파생상품 노출",
    "fxRisk": "환율위험",
    "fairValueRisk": "공정가치위험",
    "interestRateRisk": "이자율위험",
    "priceRisk": "가격위험",
    "segmentIct": "ICT 부문",
    "segmentOther": "기타 부문",
    "segmentDigitalMedia": "디지털미디어 부문",
    "salesOrder": "매출 및 수주",
    "rawMaterial": "원재료 및 설비",
    "riskDerivative": "위험관리 및 파생상품",
    "costByNature": "비용의 성격별 분류",
    "segments": "부문정보",
}


def _filterPeriodColumnsByAsOf(df: "pl.DataFrame", asOf: str) -> "pl.DataFrame":
    """asOf 이후 fiscal period 컬럼/행 drop — look-ahead bias 방지.

    DART 재무제표 finance topic 의 horizontal view 는 컬럼명이 fiscal period
    (예: "2025Q4", "2024", "2023Q3"). 사용자가 시점 X 분석 재현 시 X 이후
    컬럼은 미래 정보 누설.

    asOf 형식: "YYYY-MM-DD" / "YYYYQn" / "YYYY". 컬럼 헤더가 fiscal period
    pattern 이면 비교, 아니면 그대로 유지 (snakeId / 항목 같은 metadata 컬럼).
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
    import re as _re

    raw = str(value or "").strip()
    if not raw:
        return None, None
    m = _re.match(r"^(\d{4})[Qq]([1-4])$", raw)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = _re.match(r"^(\d{4})-(\d{1,2})-\d{1,2}$", raw)
    if m:
        month = int(m.group(2))
        return int(m.group(1)), (month - 1) // 3 + 1
    m = _re.match(r"^(\d{4})$", raw)
    if m:
        return int(m.group(1)), None
    return None, None


def listExportModules() -> list[tuple[str, str]]:
    """Excel/export용 DART 공개 모듈 목록.

    Returns
    -------
    list[tuple[str, str]]
        (prop : str, label : str) 튜플 리스트 — Excel export 시 컬럼 이름
        생성용. prop 은 Company 속성명 (예: "businessOverview"), label 은
        사용자 표시용 한글 라벨.
    """
    return list(_getAllProperties())


class Company:
    """DART 기반 한국 상장기업 분석.

    기본 사용 모델은 index / show / trace다.

    - ``index``: sections 뼈대 위에 finance/report가 채워진 수평화 보드
    - ``show(topic)``: 특정 topic의 실제 payload(DataFrame)
    - ``trace(topic, period)``: 선택 source와 provenance

    3개 데이터 소스를 강점 기반으로 선별하여 제공:

    - **finance** (XBRL 정규화): BS/IS/CIS/CF/SCE, timeseries, annual, ratios
    - **report** (DART API 정형): 28개 apiType 체계, 현재 가용 항목 중심 structured disclosure
    - **docs** (HTML 파싱): 서술형(business, mdna), K-IFRS 주석(notes), 거버넌스, 리스크 등

    소스 우선순위:
    - docs sections 수평화가 구조의 spine
    - finance가 숫자 재무 authoritative source
    - report가 정형 공시 authoritative source
    - Company는 이 세 source를 merged board로 제공한다

    Example::

        c = Company("005930")           # 삼성전자
        c.index                          # 전체 수평화 보드
        c.show("BS")                     # 재무상태표
        c.show("salesOrder")             # sections 기반 subtopic DataFrame
        c.show("costByNature")           # sections/detailTopic 우선 + legacy fallback
        c.trace("dividend")              # source provenance
        c.show("CIS")                    # 포괄손익계산서
        c.show("SCE")                    # 자본변동표
        c.show("treasuryStock")          # 정형 공시
        c.show("sections")              # docs source view

    Notes
    -----
    **첫 호출 시간** — Company(stockCode) 최초 호출은 해당 종목의 docs /
    finance / report parquet 를 HuggingFace 에서 자동 다운로드한다 (총
    ~수MB ~ 수십MB). 네트워크 속도에 따라 **30~60초** 소요. 2회째부터는
    로컬 캐시 사용 — 즉시 반환.

    Company 편의성 3원칙 (CLAUDE.md) 중 "속도 — 첫 호출 5초 이내" 는 캐시
    적중 기준. cold start (캐시 없음) 는 다운로드 시간 포함이며 진행 상황
    은 기본 INFO 레벨 logger 로 출력 (silence: ``logging.getLogger("dartlab").setLevel(WARNING)``).
    """

    @staticmethod
    def canHandle(code: str) -> bool:
        """DART 종목코드(6자) 또는 한글 회사명이면 처리 가능.

        Parameters
        ----------
        code : str
            종목코드 또는 회사명 후보.

        Returns
        -------
        bool
            True 면 DART provider 로 처리. 6자리 alphanumeric (KR 종목코드)
            또는 한글 포함 문자열이면 True.
        """
        if re.match(r"^[0-9A-Za-z]{6}$", code):
            return True
        if any("\uac00" <= ch <= "\ud7a3" for ch in code):
            return True
        return False

    @staticmethod
    def priority() -> int:
        """낮을수록 먼저 시도. DART=10 (기본 provider).

        Returns
        -------
        int
            provider 우선순위. DART 는 10 — EDGAR (20) 보다 먼저 시도.
        """
        return 10

    def __init__(self, stockCode: str):
        import time as _time

        _initStart = _time.perf_counter()

        normalized = stockCode.strip()
        if re.match(r"^[0-9A-Za-z]{6}$", normalized):
            self.stockCode = normalized.upper()
        else:
            code = nameToCode(normalized)
            if code is None:
                raise ValueError(f"'{normalized}'에 해당하는 종목을 찾을 수 없음")
            self.stockCode = code
        from dartlab.core.memory import BoundedCache

        self._cache: BoundedCache = BoundedCache(maxEntries=30)

        _dataStatus = _ensureAllData(self.stockCode)
        self._hasDocs = _dataStatus.get("docs", False)
        self._freshnessResult = None
        if self._hasDocs:
            self._freshnessResult = _checkDartDocsFreshness(self.stockCode, "docs")
        self._hasFinanceParquet = _dataStatus.get("finance", False)
        self._hasReport = _dataStatus.get("report", False)

        import sys

        corpName = None if sys.platform == "emscripten" else codeToName(self.stockCode)
        if corpName:
            self.corpName = corpName
        elif sys.platform == "emscripten":
            # pyodide: docs 선행 fetch 회피 — 사용자가 요청한 카테고리만 lazy fetch.
            # 진짜 corpName 이 필요하면 show/select 가 나중에 docs 를 가져옴.
            self.corpName = self.stockCode
        elif self._hasDocs:
            df = loadData(self.stockCode, category="docs", columns=["corp_name"])
            self.corpName = extractCorpName(df)
        else:
            self.corpName = self.stockCode

        # finance는 lazy — 첫 접근 시 _ensureFinanceLoaded()에서 검증
        self._financeChecked = False

        if not self._hasDocs and not self._hasFinanceParquet and not self._hasReport:
            from dartlab.core.messaging import emit

            emit("error:no_data", stockCode=self.stockCode, raiseAs=ValueError)

        self._hintedKeys: set[str] = set()  # 동일 안내 반복 방지

        self._notesAccessor = Notes(self) if self._hasDocs else None
        # public namespace 모두 제거 (P3a/b/c/d)
        self._profileAccessor = _ProfileAccessor(self)
        # private 백엔드 — 내부 compute 전용 (story/credit/valuation 등)
        self._docs = _DocsAccessor(self)
        self._finance = _FinanceAccessor(self)
        self._report = _ReportAccessor(self)

        # 초기화 wall-clock — 2초 이상이면 사용자에게 총 시간 보고 (cold start
        # 시 HF 다운로드 포함. Company 편의성 3원칙 "첫 호출 5초 이내" 감시).
        _initElapsed = _time.perf_counter() - _initStart
        if _initElapsed >= 2.0:
            _log.info("Company('%s') 준비 완료 (%.1fs)", self.stockCode, _initElapsed)

    def __repr__(self):
        from dartlab.core.htmlRenderer import getHtmlRenderer

        renderer = getHtmlRenderer()
        if renderer is not None:
            text = renderer.renderCompany(self)
            if text is not None:
                return text
        return f"Company({self.stockCode}, {self.corpName})"

    def _hintOnce(self, key: str, prop: str, category: str = "docs") -> None:
        """동일 안내를 세션 내 1회만 출력."""
        if key in self._hintedKeys:
            return
        self._hintedKeys.add(key)
        from dartlab.core.messaging import emit

        emit(f"hint:no_{category}", stockCode=self.stockCode, prop=prop)

    def _financeProperty(self, name: str):
        """finance accessor 위임 + hint."""
        result = getattr(self._finance, name)
        if result is None:
            self._hintOnce(name, name, "finance")
        return result

    def topicSummaries(self) -> dict[str, str]:
        """토픽별 요약 dict — AI가 경로 탐색에 사용.

        각 docs topic의 최신 기간 첫 텍스트에서 200자 요약을 추출한다.
        finance topic은 고정 설명을 반환한다.

        Returns
        -------
        dict[str, str]
            키 = topic 이름 (예: "BS", "IS", "dividend", "companyOverview")
            값 = 200자 요약 텍스트
        """
        cacheKey = "_topicSummaries"
        if cacheKey in self._cache:
            return self._cache[cacheKey]

        summaries: dict[str, str] = {}

        # finance 고정 설명
        _FINANCE_SUMMARIES = {
            "BS": "재무상태표 — 자산, 부채, 자본 잔액",
            "IS": "손익계산서 — 매출, 영업이익, 당기순이익",
            "CIS": "포괄손익계산서 — 기타포괄손익 포함",
            "CF": "현금흐름표 — 영업/투자/재무 활동 현금",
            "SCE": "자본변동표 — 자본 구성요소별 변동",
            "ratios": "재무비율 — 수익성/안정성/성장성/효율성/밸류에이션",
        }
        summaries.update(_FINANCE_SUMMARIES)

        # docs topic 요약 — 최신 기간 첫 텍스트 200자
        if self._hasDocs:
            raw = loadData(
                self.stockCode,
                category="docs",
                sinceYear=2016,
                columns=["year", "report_type", "section_order", "section_title", "section_content"],
            )
            if raw is not None and not raw.is_empty() and "section_content" in raw.columns:
                from dartlab.core.reportSelector import selectReport
                from dartlab.providers.dart.docs.sections.mapper import mapSectionTitle

                # 최신 연도의 사업보고서에서 추출
                years = sorted(
                    {str(y) for y in raw["year"].drop_nulls().to_list()},
                    reverse=True,
                )
                for year in years:
                    report = selectReport(raw, year, reportKind="annual")
                    if isEmptyDf(report):
                        continue
                    scoped = report.filter(pl.col("section_content").is_not_null()).sort("section_order")
                    seen: set[str] = set()
                    for row in scoped.iter_rows(named=True):
                        rawTitle = str(row.get("section_title") or "").strip()
                        topic = mapSectionTitle(rawTitle)
                        if not topic or topic in seen or topic in summaries:
                            continue
                        seen.add(topic)
                        content = str(row.get("section_content") or "").strip()
                        if not content:
                            continue
                        # 첫 200자 (줄바꿈 → 공백)
                        preview = content.replace("\n", " ").replace("  ", " ")[:200].strip()
                        if preview:
                            summaries[topic] = preview
                    break  # 최신 연도만

        self._cache[cacheKey] = summaries
        return summaries

    @property
    def _analyzer(self):
        """sections 구조 분석기 (lazy)."""
        cacheKey = "_sectionsAnalyzer"
        if cacheKey not in self._cache:
            from dartlab.providers.dart.docsSectionsAnalyzer import SectionsAnalyzer

            self._cache[cacheKey] = SectionsAnalyzer(self)
        return self._cache[cacheKey]

    @property
    def _hasFinance(self) -> bool:
        """finance 사용 가능 여부 — lazy check 포함."""
        self._ensureFinanceLoaded()
        return self._hasFinanceParquet

    # ── 내부 호출 ──

    def _callModule(self, name: str, **kwargs) -> Any:
        """모듈 호출 + 캐싱. Notes에서도 사용."""
        if not self._hasDocs:
            return None
        cacheKey = f"{name}:{sorted(kwargs.items())}" if kwargs else name
        if cacheKey in self._cache:
            return self._cache[cacheKey]
        idx = _getModuleIndex()[name]
        entry = _getModuleRegistry()[idx]
        result = _importAndCall(entry[0], entry[1], self.stockCode, **kwargs)
        self._cache[cacheKey] = result
        return result

    def _callNotesDetail(self, keyword: str, period: str = "y") -> Any:
        """notesDetail 호출 (키워드 + 기간별 캐싱).

        Args:
            keyword: 주석 키워드 (예: "재고자산", "매출채권").
            period: "y" (연간, 기본), "q" (분기 포함), "h" (반기 포함).
        """
        if not self._hasDocs:
            return None
        cacheKey = f"notesDetail:{keyword}:{period}"
        if cacheKey in self._cache:
            return self._cache[cacheKey]
        result = _importAndCall(
            "dartlab.providers.dart.docs.finance.notesDetail",
            "notesDetail",
            self.stockCode,
            keyword=keyword,
            period=period,
        )
        self._cache[cacheKey] = result
        return result

    def _getPrimary(self, name: str, **kwargs) -> Any:
        """모듈 호출 후 primary DataFrame 추출."""
        from dartlab import config

        cacheKey = f"{name}:{sorted(kwargs.items())}" if kwargs else name
        idx = _getModuleIndex()[name]
        entry = _getModuleRegistry()[idx]
        label = entry[2]

        if config.verbose and cacheKey not in self._cache and name != "sections":
            _log.info("  ▶ %s · %s", self.corpName, label)

        result = self._callModule(name, **kwargs)
        extractor = entry[3]
        if result is None:
            return None
        if extractor is None:
            return result
        return extractor(result)

    # ── 인덱스·메타 ──

    @staticmethod
    def listing(*, forceRefresh: bool = False) -> pl.DataFrame:
        """KRX 전체 상장법인 목록 (KIND 기준).

        Capabilities:
            - KOSPI + KOSDAQ 전체 상장법인
            - 종목코드, 종목명, 시장구분, 업종

        Args:
            forceRefresh: True면 캐시 무시, KIND에서 재다운로드.

        Returns:
            pl.DataFrame — code, name, market, sector 등.

        Requires:
            데이터: listing (자동 다운로드)
        """
        return getKindList(forceRefresh=forceRefresh)

    @staticmethod
    def search(keyword: str) -> pl.DataFrame:
        """회사명 부분 검색 (KIND 목록 기준).

        Args:
            keyword: 검색어 (부분 일치).

        Returns:
            pl.DataFrame — 매칭 종목 목록.
        """
        return searchName(keyword)

    @staticmethod
    def resolve(stockCode: str) -> str | None:
        """종목코드 또는 회사명 → 종목코드 변환.

        Args:
            stockCode: 종목코드 ("005930") 또는 종목명 ("삼성전자").

        Returns:
            str | None — 6자리 종목코드. 못 찾으면 None.
        """
        normalized = stockCode.strip()
        if re.match(r"^[0-9A-Za-z]{6}$", normalized):
            return normalized.upper()
        return nameToCode(normalized)

    @staticmethod
    def codeName(stockCode: str) -> str | None:
        """종목코드 → 회사명 변환.

        Args:
            stockCode: 6자리 종목코드.

        Returns:
            str | None — 회사명. 못 찾으면 None.
        """
        return codeToName(stockCode)

    @staticmethod
    def status() -> pl.DataFrame:
        """로컬에 보유한 전체 종목 인덱스.

        Capabilities:
            - 로컬 데이터 현황 (종목별 docs/finance/report 보유 여부)
            - 최종 업데이트 일시

        Returns:
            pl.DataFrame — 종목코드, 회사명, docs/finance/report 유무, 최종일시.
        """
        return buildIndex()

    def filings(self) -> pl.DataFrame | None:
        """공시 문서 목록 + DART 뷰어 링크.

        Capabilities:
            - 로컬에 보유한 공시 문서 목록
            - 기간별, 문서유형별 정리
            - DART 뷰어 링크 포함

        Returns:
            pl.DataFrame | None — year, rceptDate, rceptNo, reportNm, viewerUrl 등.

        AIContext:
            - 어떤 공시가 보유돼 있는지 확인하여 분석 범위 결정에 활용

        Guide:
            - "이 회사 공시 목록 보여줘" → c.filings()
            - "어떤 보고서가 있어?" → c.filings()로 보유 문서 확인

        SeeAlso:
            - disclosure: OpenDART API 기반 실시간 공시 목록 (로컬 보유가 아닌 전체)
            - liveFilings: 최신 공시 실시간 조회
            - update: 누락 공시 증분 수집

        Requires:
            데이터: docs (자동 다운로드)

        LLM Specifications:
            AntiPatterns:
                - 실시간 공시 확인용으로 사용 (filings 는 local cache — 실시간은 disclosure/liveFilings)
                - readFiling 호출 전 filings 결과의 컬럼명 추측 (rceptNo 사용)
            OutputSchema:
                - rceptNo : str — 공시 접수번호 (readFiling 입력용)
                - filedAt : str — 공시 일자
                - title : str — 공시 제목
                - viewerUrl : str — DART 뷰어 링크
            Freshness:
                local cache 기반. c.update() 호출 시점이 기준.
        """
        from dartlab.providers.dart.filingsCatalog import buildFilings

        return buildFilings(self)

    def update(self, *, categories: list[str] | None = None) -> dict[str, int]:
        """누락된 최신 공시를 증분 수집.

        Capabilities:
            - DART API로 최신 공시 확인 후 누락분만 수집
            - 카테고리별 선택 수집

        Args:
            categories: ["finance", "docs", "report"]. None이면 전체.

        Returns:
            dict — {카테고리: 수집 건수}.

        AIContext:
            - 데이터 최신성 유지에 활용 — 분석 전 자동 갱신 트리거 가능

        Guide:
            - "최신 공시 반영해줘" → c.update()
            - "데이터 업데이트" → c.update()로 증분 수집

        SeeAlso:
            - filings: 현재 보유 공시 목록 확인
            - disclosure: OpenDART 전체 공시 조회

        Requires:
            API 키: DART_API_KEY

        LLM Specifications:
            AntiPatterns:
                - 분석 전 무조건 update() 호출 (이미 최신이면 불필요한 비용)
                - categories 에 "all" 같은 값 (None 또는 list[str] 만)
            OutputSchema:
                - finance : int — 추가 수집된 finance 건수
                - docs : int — 추가 수집된 docs 건수
                - report : int — 추가 수집된 report 건수
            Freshness:
                호출 시점에 DART API 와 비교해 누락만 수집. 매 호출 시점 = 최신 기준.
        """
        from dartlab.providers.dart.filingsCatalog import buildUpdate

        return buildUpdate(self, categories=categories)

    def _docsTopicManifest(self) -> pl.DataFrame:
        """→ SectionsAnalyzer.topicManifest()."""
        return self._analyzer.topicManifest()

    def _docsSectionTopics(self) -> list[str]:
        """→ SectionsAnalyzer.sectionTopics()."""
        return self._analyzer.sectionTopics()

    def _docsTopicOutline(self, topic: str | None = None) -> pl.DataFrame:
        """→ SectionsAnalyzer.topicOutline()."""
        return self._analyzer.topicOutline(topic=topic)

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
        """**[단일 종목 전용]** OpenDART 공시 목록 조회. **stockCode 필수**.

        ⚠ AI 사용 분기 — 절대 헷갈리지 마라:
            - "**삼성전자** 최근 공시" → ``c.disclosure(stockCode="005930")`` ✅
            - "**최근 자사주 매입 공시 낸 회사**" → ``dartlab.search("자사주 취득")`` (전종목 검색)
            - "**전종목 정기공시 5건**" → ``dartlab.search("사업보고서")`` (전종목 검색)
            - 전종목 검색에 disclosure 호출 금지. stockCode 없이는 실패한다.

        Capabilities:
            - 전체 공시유형 조회 (정기, 주요사항, 발행, 지분, 외부감사 등)
            - 기간, 유형, 키워드 필터링
            - 최종보고서만 필터 (정정 이전 제외)

        Args:
            start: 조회 시작일 (YYYYMMDD 또는 YYYY-MM-DD). None이면 최근 days일.
            end: 조회 종료일. None이면 오늘.
            days: start/end 없을 때 최근 일수. 기본 365.
            type: 공시유형 필터 (A=정기, B=주요사항, C=발행, D=지분, E=기타, F=외부감사). None이면 전체.
            keyword: 제목/회사명 키워드 필터.
            finalOnly: True면 최종보고서만 (정정 이전 제외).

        Returns:
            pl.DataFrame -- docId, filedAt, title, formType 등 공시 목록 (이 종목 한정).

        Requires:
            API 키: DART_API_KEY

        Example::

            c = Company("005930")
            c.disclosure()                  # 최근 1년 전체 공시
            c.disclosure(days=30)           # 최근 30일
            c.disclosure(type="A")          # 정기공시만
            c.disclosure(keyword="사업보고서")

        AIContext:
            - 특정 종목의 공시 빈도/유형 패턴 → 이벤트 감지
            - 단일 종목 분석 시 최근 공시 컨텍스트 보강용

        Guide:
            - 단일 종목: "삼성전자 최근 공시 뭐 나왔어?" → c.disclosure(days=30)
            - 전종목: "최근 어떤 회사들이 자사주 매입했어?" → dartlab.search("자기주식 취득")

        SeeAlso:
            - dartlab.search: **전종목 공시 검색 — 키워드 기반 (이 함수 대안)**
            - liveFilings: 실시간 최신 공시 (정규화된 포맷, 단일 종목)
            - readFiling: 공시 원문 텍스트 읽기
            - filings: 로컬 보유 공시 목록 (단일 종목)

        LLM Specifications:
            AntiPatterns:
                - 전종목 disclosure() (단일 종목 전용 — 전종목은 dartlab.search())
                - days 와 start/end 동시 (start/end 우선)
            OutputSchema:
                - rceptNo : str — 공시 접수번호 (readFiling 입력용)
                - filedAt : str — 공시 일자 (YYYY-MM-DD)
                - title : str — 공시 제목
                - formType : str — 공시 유형 (정기/주요사항/지분 등)
            Freshness:
                DART API 실시간 (분 단위). filings() 와 다름 (filings 는 local cache).
        """
        from dartlab.providers.dart.filingsCatalog import buildDisclosure

        return buildDisclosure(self, start, end, days=days, type=type, keyword=keyword, finalOnly=finalOnly)

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
        """OpenDART 기준 실시간 공시 목록 조회.

        Capabilities:
            - OpenDART API 실시간 공시 조회
            - 기간, 건수, 키워드 필터링
            - 정규화된 컬럼 (docId, filedAt, title, formType 등)

        Args:
            start: 조회 시작일 (YYYYMMDD 또는 YYYY-MM-DD). None이면 최근 days일.
            end: 조회 종료일. None이면 오늘.
            days: start/end 없을 때 최근 일수. None이면 기본값 적용.
            limit: 최대 반환 건수. 기본 20.
            keyword: 제목/회사명 키워드 필터.
            forms: 미사용 (DART는 forms 개념 없음).
            finalOnly: True면 최종보고서만 (정정 이전 제외).

        Returns:
            pl.DataFrame -- docId, filedAt, title, formType, docUrl, viewerUrl 등 정규화된 공시 목록.

        Requires:
            API 키: DART_API_KEY

        Example::

            c = Company("005930")
            c.liveFilings()                 # 최근 공시 20건
            c.liveFilings(days=7)           # 최근 7일
            c.liveFilings(keyword="배당")   # 키워드 필터

        AIContext:
            - 최신 공시 모니터링으로 기업 이벤트(배당, 유증, 합병 등) 실시간 감지
            - readFiling()과 조합하여 최신 공시 원문 분석

        Guide:
            - "최근 공시 확인해줘" → c.liveFilings()
            - "이번 주 공시 있어?" → c.liveFilings(days=7)
            - "배당 관련 공시" → c.liveFilings(keyword="배당")

        SeeAlso:
            - disclosure: 과거 전체 공시 이력 조회
            - readFiling: 공시 원문 텍스트 읽기
            - watch: 공시 변화 중요도 스코어링

        LLM Specifications:
            AntiPatterns:
                - 종목코드 외 ticker 전달 (KR DART 전용)
                - keyword 정규식 입력 (단순 substring 만 지원)
            OutputSchema:
                - rceptNo : str — 공시 접수번호 (readFiling 입력용)
                - filedAt : str — 공시 일자
                - title : str — 공시 제목
                - importance : float — 중요도 점수
            Freshness:
                DART API 실시간 (분 단위).
            TargetMarkets:
                - KR
        """
        from dartlab.providers.dart.filingsCatalog import buildLiveFilings

        return buildLiveFilings(
            self,
            start,
            end,
            days=days,
            limit=limit,
            keyword=keyword,
            forms=forms,
            finalOnly=finalOnly,
        )

    def readFiling(
        self,
        filing: Any,
        *,
        maxChars: int | None = None,
        sections: bool = False,
    ) -> dict[str, Any]:
        """접수번호 또는 liveFilings row로 공시 원문을 읽는다.

        Capabilities:
            - 접수번호(str) 직접 지정 또는 DataFrame row 자동 파싱
            - 전문 텍스트 또는 ZIP 기반 구조화 섹션 반환
            - 텍스트 길이 제한 (truncation) 지원

        Args:
            filing: 접수번호(str) 또는 disclosure()/liveFilings() row.
            maxChars: 텍스트 최대 길이 (sections=False일 때만 적용).
            sections: True면 ZIP 기반 구조화된 섹션 목록 반환.

        Returns:
            dict -- rceptNo, viewerUrl, text/sections 등 원문 정보.

        Requires:
            API 키: DART_API_KEY

        Example::

            c = Company("005930")
            result = c.readFiling("20240315000123")
            result = c.readFiling("20240315000123", sections=True)

        AIContext:
            - 공시 원문 텍스트를 LLM 컨텍스트에 주입하여 심층 분석 수행
            - sections=True로 구조화하면 특정 섹션만 선택적 분석 가능

        Guide:
            - "이 공시 내용 보여줘" → c.readFiling(접수번호)
            - "공시 원문 분석해줘" → c.readFiling()으로 원문 확보 후 ask()로 분석

        SeeAlso:
            - liveFilings: 최신 공시 목록에서 접수번호 확인
            - disclosure: 과거 공시 목록에서 접수번호 확인

        LLM Specifications:
            AntiPatterns:
                - 종목 이름 (str) 을 filing 인자로 전달 (rceptNo 또는 row 만)
                - sections=True + maxChars 동시 (sections 일 때 maxChars 무시)
            OutputSchema:
                - rceptNo : str — 공시 접수번호
                - viewerUrl : str — DART 뷰어 링크
                - text : str — 공시 본문 (sections=False)
                - sections : list[dict] — 섹션 목록 (sections=True)
            Freshness:
                DART API 실시간. 단 본문 캐시 없음 — 매 호출 = 새 download.
        """
        from dartlab.providers.dart.filingsCatalog import buildReadFiling

        return buildReadFiling(self, filing, maxChars=maxChars, sections=sections)

    # ── 원본 데이터 (property) ──

    @property
    def rawDocs(self) -> pl.DataFrame | None:
        """공시 문서 원본 parquet 전체 (가공 전).

        Capabilities:
            - HuggingFace docs 카테고리 원본 데이터 직접 접근
            - 가공/정규화 이전 상태 그대로 반환

        Returns:
            pl.DataFrame | None -- 원본 docs parquet. 데이터 없으면 None.

        Requires:
            데이터: HuggingFace docs parquet (자동 다운로드)

        Example::

            c = Company("005930")
            c.rawDocs              # 삼성전자 공시 문서 원본
            c.rawDocs.columns      # 컬럼 목록 확인

        AIContext:
            - 원본 데이터 구조 파악 — 파싱 전 상태로 디버깅/검증에 활용

        Guide:
            - "원본 공시 데이터 보여줘" → c.rawDocs
            - "가공 전 데이터 확인" → c.rawDocs

        SeeAlso:
            - sections: docs 가공 후 topic x period 통합 지도
            - rawFinance: 재무제표 원본 데이터
            - rawReport: 정기보고서 원본 데이터

        LLM Specifications:
            AntiPatterns:
                - 분석 답변에 raw parquet 직접 인용 (sections / show 가공본 우선)
                - 메모리 부담 큼 — 매 호출마다 호출 X (캐시)
            OutputSchema:
                - HuggingFace docs parquet 원본 — 컬럼 구조는 dataset 별로 다름
            Freshness:
                HuggingFace parquet 다운로드 시점.
        """
        if not self._hasDocs:
            self._hintOnce("rawDocs", "rawDocs", "docs")
            return None
        cacheKey = "_rawDocs"
        if cacheKey in self._cache:
            return self._cache[cacheKey]
        df = loadData(self.stockCode, category="docs")
        self._cache[cacheKey] = df
        return df

    @property
    def rawFinance(self) -> pl.DataFrame | None:
        """재무제표 원본 parquet 전체 (가공 전).

        Capabilities:
            - HuggingFace finance 카테고리 원본 데이터 직접 접근
            - XBRL 정규화 이전 상태 그대로 반환

        Returns:
            pl.DataFrame | None -- 원본 finance parquet. 데이터 없으면 None.

        Requires:
            데이터: HuggingFace finance parquet (자동 다운로드)

        Example::

            c = Company("005930")
            c.rawFinance           # 삼성전자 재무제표 원본
            c.rawFinance.columns   # 컬럼 목록 확인

        AIContext:
            - XBRL 정규화 전 원본 구조 파악 — 매핑 검증에 활용

        Guide:
            - "원본 재무 데이터 보여줘" → c.rawFinance
            - "XBRL 원본 확인" → c.rawFinance

        SeeAlso:
            - BS: 가공된 재무상태표
            - IS: 가공된 손익계산서
            - rawDocs: 공시 문서 원본

        LLM Specifications:
            AntiPatterns:
                - 분석 답변에 raw parquet 직접 인용 (show("BS") 등 가공본 우선)
                - 매 호출 reload (캐시 — 1 회면 충분)
            OutputSchema:
                - XBRL 정규화 전 원본 — bsns_year / sj_div / account_id / amount 등
            Freshness:
                HuggingFace finance parquet 다운로드 시점.
        """
        if not self._hasFinanceParquet:
            self._hintOnce("rawFinance", "rawFinance", "finance")
            return None
        cacheKey = "_rawFinance"
        if cacheKey in self._cache:
            return self._cache[cacheKey]
        df = loadData(self.stockCode, category="finance")
        self._cache[cacheKey] = df
        return df

    @property
    def rawReport(self) -> pl.DataFrame | None:
        """정기보고서 원본 parquet 전체 (가공 전).

        Capabilities:
            - HuggingFace report 카테고리 원본 데이터 직접 접근
            - 정기보고서 API 데이터 가공 이전 상태 반환

        Returns:
            pl.DataFrame | None -- 원본 report parquet. 데이터 없으면 None.

        Requires:
            데이터: HuggingFace report parquet (자동 다운로드)

        Example::

            c = Company("005930")
            c.rawReport            # 삼성전자 정기보고서 원본
            c.rawReport.columns    # 컬럼 목록 확인

        AIContext:
            - 정기보고서 API 원본 확인 — report topic 매핑 검증에 활용

        Guide:
            - "원본 보고서 데이터 보여줘" → c.rawReport
            - "정기보고서 원본 확인" → c.rawReport

        SeeAlso:
            - rawDocs: 공시 문서 원본
            - rawFinance: 재무제표 원본
            - show: 가공된 topic 데이터 조회

        LLM Specifications:
            AntiPatterns:
                - report 원본을 본문 답변에 직접 인용 (show / story 가공본 우선)
                - 매 호출 reload (캐시 — 1 회면 충분)
            OutputSchema:
                - 정기보고서 API 원본 — 컬럼은 보고서 form 별로 다름
            Freshness:
                HuggingFace report parquet 다운로드 시점.
        """
        if not self._hasReport:
            self._hintOnce("rawReport", "rawReport", "report")
            return None
        cacheKey = "_rawReport"
        if cacheKey in self._cache:
            return self._cache[cacheKey]
        df = loadData(self.stockCode, category="report")
        self._cache[cacheKey] = df
        return df

    # c.notes property 제거 (Plan v10 P2) — 12 sub-property 모두 c.show("inventory") 등으로 통합.
    # Notes 클래스는 _notesAccessor (private) 로 유지, show() topic dispatch 가 호출.

    def _docsSectionsFreq(self, freqScope: str, *, includeMixed: bool = True) -> pl.DataFrame | None:
        """→ SectionsAnalyzer.sectionsFreq()."""
        return self._analyzer.sectionsFreq(freqScope, includeMixed=includeMixed)

    def _docsSectionsOrdered(self, *, recentFirst: bool = True, annualAsQ4: bool = True) -> pl.DataFrame | None:
        """→ SectionsAnalyzer.sectionsOrdered()."""
        return self._analyzer.sectionsOrdered(recentFirst=recentFirst, annualAsQ4=annualAsQ4)

    def _docsSectionsCoverage(
        self, *, topic: str | None = None, recentFirst: bool = True, annualAsQ4: bool = True
    ) -> pl.DataFrame | None:
        """→ SectionsAnalyzer.sectionsCoverage()."""
        return self._analyzer.sectionsCoverage(topic=topic, recentFirst=recentFirst, annualAsQ4=annualAsQ4)

    def _docsSectionsSemanticRegistry(
        self,
        *,
        topic: str | None = None,
        freqScope: str = "all",
        includeMixed: bool = True,
        collisionsOnly: bool = False,
    ) -> pl.DataFrame | None:
        """→ SectionsAnalyzer.sectionsSemanticRegistry()."""
        return self._analyzer.sectionsSemanticRegistry(
            topic=topic, freqScope=freqScope, includeMixed=includeMixed, collisionsOnly=collisionsOnly
        )

    def _docsSectionsStructureRegistry(
        self,
        *,
        topic: str | None = None,
        freqScope: str = "all",
        includeMixed: bool = True,
        collisionsOnly: bool = False,
        nodeType: str | None = None,
    ) -> pl.DataFrame | None:
        """→ SectionsAnalyzer.sectionsStructureRegistry()."""
        return self._analyzer.sectionsStructureRegistry(
            topic=topic,
            freqScope=freqScope,
            includeMixed=includeMixed,
            collisionsOnly=collisionsOnly,
            nodeType=nodeType,
        )

    def _docsSectionsStructureEvents(
        self,
        *,
        topic: str | None = None,
        freqScope: str = "all",
        includeMixed: bool = True,
        changedOnly: bool = True,
        nodeType: str | None = None,
    ) -> pl.DataFrame | None:
        """→ SectionsAnalyzer.sectionsStructureEvents()."""
        return self._analyzer.sectionsStructureEvents(
            topic=topic,
            freqScope=freqScope,
            includeMixed=includeMixed,
            changedOnly=changedOnly,
            nodeType=nodeType,
        )

    def _docsSectionsStructureSummary(
        self,
        *,
        topic: str | None = None,
        freqScope: str = "all",
        includeMixed: bool = True,
        nodeType: str | None = None,
    ) -> pl.DataFrame | None:
        """→ SectionsAnalyzer.sectionsStructureSummary()."""
        return self._analyzer.sectionsStructureSummary(
            topic=topic, freqScope=freqScope, includeMixed=includeMixed, nodeType=nodeType
        )

    def _docsSectionsStructureChanges(
        self,
        *,
        topic: str | None = None,
        freqScope: str = "all",
        includeMixed: bool = True,
        nodeType: str | None = None,
        latestOnly: bool = True,
        changedOnly: bool = True,
    ) -> pl.DataFrame | None:
        """→ SectionsAnalyzer.sectionsStructureChanges()."""
        return self._analyzer.sectionsStructureChanges(
            topic=topic,
            freqScope=freqScope,
            includeMixed=includeMixed,
            nodeType=nodeType,
            latestOnly=latestOnly,
            changedOnly=changedOnly,
        )

    def _retrievalBlocks(self) -> pl.DataFrame | None:
        if not self._hasDocs:
            return None
        cacheKey = "retrievalBlocks"
        if cacheKey in self._cache:
            return self._cache[cacheKey]
        from dartlab.providers.dart.docs.sections import retrievalBlocks

        result = retrievalBlocks(self.stockCode)
        self._cache[cacheKey] = result
        return result

    def _contextSlices(self) -> pl.DataFrame | None:
        if not self._hasDocs:
            return None
        cacheKey = "contextSlices"
        if cacheKey in self._cache:
            return self._cache[cacheKey]
        from dartlab.providers.dart.docs.sections import contextSlices

        result = contextSlices(self.stockCode)
        self._cache[cacheKey] = result
        return result

    def _topicSubtables(self, topic: str):
        """→ SectionsAnalyzer.topicSubtables()."""
        return self._analyzer.topicSubtables(topic)

    def _sectionsSubtopicWide(self, topic: str) -> pl.DataFrame | None:
        """→ SectionsAnalyzer.subtopicWide()."""
        return self._analyzer.subtopicWide(topic)

    def _sectionsSubtopicLong(self, topic: str) -> pl.DataFrame | None:
        """→ SectionsAnalyzer.subtopicLong()."""
        return self._analyzer.subtopicLong(topic)

    def _safePrimary(self, name: str) -> pl.DataFrame | None:
        try:
            payload = self._getPrimary(name)
        except (KeyError, ValueError, TypeError, FileNotFoundError, AttributeError):
            import logging

            logging.getLogger(__name__).debug("_safePrimary(%s) failed", name, exc_info=True)
            return None
        return payload if isinstance(payload, pl.DataFrame) else None

    def _sceMatrix(self):
        from dartlab.providers.dart.financeStatementBuilder import sceMatrix

        return sceMatrix(self)

    def _sceSeriesAnnual(self):
        from dartlab.providers.dart.financeStatementBuilder import sceSeriesAnnual

        return sceSeriesAnnual(self)

    def _sce(self) -> pl.DataFrame | None:
        from dartlab.providers.dart.financeStatementBuilder import sce

        return sce(self)

    def _financeCisAnnual(self):
        from dartlab.providers.dart.financeStatementBuilder import financeCisAnnual

        return financeCisAnnual(self)

    def _financeCisQuarterly(self):
        from dartlab.providers.dart.financeStatementBuilder import financeCisQuarterly

        return financeCisQuarterly(self)

    def _ratioSeries(self):
        from dartlab.providers.dart.financeStatementBuilder import ratioSeries

        return ratioSeries(self)

    def _financeOrDocsStatement(
        self, sjDiv: str, *, freq: str = "Q", scope: str = "consolidated"
    ) -> pl.DataFrame | None:
        from dartlab.providers.dart.financeStatementBuilder import financeOrDocsStatement

        return financeOrDocsStatement(self, sjDiv, freq=freq, scope=scope)

    # ── 재무제표 (property) ──
    # finance(XBRL) 우선 → docs fallback

    @staticmethod
    def _aggregateCisAnnual(qDf: pl.DataFrame) -> pl.DataFrame | None:
        from dartlab.providers.dart.financeStatementBuilder import aggregateCisAnnual

        return aggregateCisAnnual(qDf)

    def _financeStmt(self, sjDiv: str, *, freq: str = "Q", scope: str = "consolidated") -> pl.DataFrame | None:
        from dartlab.providers.dart.financeStatementBuilder import financeStmt

        return financeStmt(self, sjDiv, freq=freq, scope=scope)

    # c.BS / c.IS / c.CF / c.CIS property 제거 (Plan v10 P0 — api-contract).
    # 사용자는 c.show("IS") / c.show.IS() / c.show("IS", freq="Y", scope="separate") 사용.

    @property
    def sections(self) -> pl.DataFrame | None:
        """sections — docs + finance + report 통합 지도.

        ⚠️ 전체 docs + finance + report를 통합 로드한다. 메모리 소비가 크다.
        특정 topic만 필요하면 show(topic)을 사용하라 (부분 빌드, 빠름).

        docs 수평화 위에 finance/report를 같은 topic 안에 끼워넣는다.
        - docs에 있는 topic (dividend 등) → docs 블록 뒤에 report 행 append
        - docs에 없는 topic (BS, auditContract 등) → 해당 chapter에 독립 삽입

        Capabilities:
            - topic × period 수평화 통합 DataFrame
            - docs/finance/report 3-source 병합
            - show(topic)/trace(topic)/diff() 의 근간 데이터

        AIContext:
            - 전체 지도가 필요할 때만 사용. 개별 topic은 show(topic) 추천
            - 메모리 부하가 크므로 AI 코드에서 직접 접근 지양

        Guide:
            - "이 회사 전체 데이터 지도" → c.sections
            - "어떤 topic이 있어?" → c.topics (경량)

        SeeAlso:
            - topics: sections 기반 topic 요약 (더 간결)
            - show: 특정 topic 데이터 조회
            - index: 전체 구조 메타데이터 목차

        Returns:
            pl.DataFrame — chapter | topic | period | source | ... 또는 None.

        Requires:
            데이터: docs (필수), finance/report (선택, 자동 다운로드)

        Example::

            c = Company("005930")
            c.sections  # 전체 sections 지도

        LLM Specifications:
            AntiPatterns:
                - 단일 topic 만 필요한데 sections 호출 (메모리 폭주 — show(topic) 사용)
                - sections 결과를 캐시 안 하고 반복 호출 (re-build 비용 큼)
            OutputSchema:
                - chapter : str — 장 이름
                - topic : str — topic 식별자
                - period : str — 기간
                - source : str — docs / finance / report
            Freshness:
                docs/finance/report 3 source 각각의 최신 시점. c.update() 시점.
        """
        from dartlab.providers.dart.docsProfileBuilder import buildSections

        return buildSections(self)

    def _profileTable(self) -> pl.DataFrame | None:
        from dartlab.providers.dart.docsProfileBuilder import profileTable

        return profileTable(self)

    def _chapterMap(self) -> dict[str, str]:
        from dartlab.providers.dart.docsProfileBuilder import chapterMap

        return chapterMap(self)

    def _chapterForTopic(self, topic: str) -> str:
        from dartlab.providers.dart.docsProfileBuilder import chapterForTopic

        return chapterForTopic(self, topic)

    def _topicLabel(self, topic: str) -> str:
        from dartlab.providers.dart.docsProfileBuilder import topicLabel

        return topicLabel(self, topic)

    def _buildBlockIndex(self, topicRows: pl.DataFrame) -> pl.DataFrame:
        """topic의 블록 목차 DataFrame."""
        from dartlab.core.show import buildBlockIndex

        return buildBlockIndex(topicRows)

    def _showFinanceTopic(
        self,
        topic: str,
        *,
        period: str | None = None,
        freq: str = "Q",
        scope: str = "consolidated",
    ) -> pl.DataFrame | None:
        from dartlab.providers.dart.dataDispatcher import showFinanceTopic

        return showFinanceTopic(self, topic, period=period, freq=freq, scope=scope)

    def _traceFinanceTopic(self, topic: str, *, period: str | None = None) -> dict[str, Any] | None:
        from dartlab.providers.dart.dataDispatcher import traceFinanceTopic

        return traceFinanceTopic(self, topic, period=period)

    def _showReportTopic(self, topic: str, *, period: str | None = None, raw: bool = False) -> pl.DataFrame | None:
        from dartlab.providers.dart.dataDispatcher import showReportTopic

        return showReportTopic(self, topic, period=period, raw=raw)

    def _showSegmentsSub(self, sub: str) -> pl.DataFrame | None:
        from dartlab.providers.dart.dataDispatcher import showSegmentsSub

        return showSegmentsSub(self, sub)

    def _showDirectTopic(self, topic: str, *, period: str | None = None, raw: bool = False) -> pl.DataFrame | None:
        from dartlab.providers.dart.dataDispatcher import showDirectTopic

        return showDirectTopic(self, topic, period=period, raw=raw)

    def _showSectionBlock(
        self,
        topicFrame: pl.DataFrame,
        *,
        block: int | None = None,
        period: str | None = None,
    ) -> pl.DataFrame | None:
        from dartlab.providers.dart.dataDispatcher import showSectionBlock

        return showSectionBlock(self, topicFrame, block=block, period=period)

    def _horizontalizeTableBlock(
        self,
        topicFrame: pl.DataFrame,
        blockOrder: int,
        periodCols: list[str],
        period: str | None = None,
    ) -> pl.DataFrame | None:
        from dartlab.providers.dart.dataDispatcher import horizontalizeTableBlock

        return horizontalizeTableBlock(self, topicFrame, blockOrder, periodCols, period)

    def _reportFrame(self, topic: str, *, raw: bool = False) -> pl.DataFrame | None:
        from dartlab.providers.dart.dataDispatcher import reportFrame

        return reportFrame(self, topic, raw=raw)

    def _reportFrameInner(self, apiType: str, topic: str, *, raw: bool = False) -> pl.DataFrame | None:
        from dartlab.providers.dart.dataDispatcher import reportFrameInner

        return reportFrameInner(self, apiType, topic, raw=raw)

    def _applyPeriodFilter(self, payload: Any, period: str | None) -> Any:
        from dartlab.providers.dart.dataShapeUtils import applyPeriodFilter

        return applyPeriodFilter(payload, period)

    @property
    def show(self):
        """원본 데이터 단일 진입점 — 재무제표(BS/IS/CF/CIS)/주석/공시 DataFrame. analysis 결과 검증용.

        Guide:
            - "손익계산서" → c.show("IS")
            - "재무상태" → c.show("BS")
            - "현금흐름" → c.show("CF")
            - "사업 개요" → c.show("businessOverview")
            - "주요 제품" → c.show("mainProduct")
            - "주요주주/최대주주" → c.show("majorHolder")  # majorShareholder 아님
            - "차입금" → c.show("borrowings")

        Returns
        -------
        CallableAccessor
            dual-access proxy. ``c.show("BS")`` call-form 또는 ``c.show.BS()``
            attr-form 호출 시 ``_showImpl`` 이 실행되어 ``pl.DataFrame`` 반환.
            반환 구조 상세는 ``_showImpl`` docstring 참조.
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
        freq: str = "Q",
        scope: str = "consolidated",
        raw: bool = False,
        asOf: str | None = None,
    ) -> pl.DataFrame | None:
        """topic 의 데이터를 반환 — 내부 구현 (사용자는 ``c.show`` 호출).

        ``operation.apiContract`` 의 "단일 진입점 + 파라미터 계약" 규칙에 따라
        모든 topic 접근은 ``c.show(topic, ...)`` 로 통합한다.
        ``c.show("BS")``, ``c.show("ratios")``, ``c.show("dividend")`` 등.

        Capabilities:
            - 120+ topic 접근 (재무제표, 사업내용, 지배구조, 임원현황 등)
            - 기간 / 주기 / 범위 / 블록 / 세로뷰 모두 파라미터 토글
            - docs / finance / report 3 source 자동 통합

        Args:
            topic: topic 이름. ``"BS"`` ``"IS"`` ``"CF"`` ``"CIS"`` ``"SCE"`` ``"ratios"``
                같은 finance topic 또는 ``"dividend"`` ``"companyOverview"`` 같은 docs/report
                topic. 주요주주/최대주주 topic은 ``"majorHolder"`` 이며
                ``"majorShareholder"`` 가 아니다. 전체 목록은 ``c.topics``.
            block: 블록 인덱스. None 이면 블록 목차 (1개면 바로 데이터).
            period: 단일 기간 필터 (``"2023"``, ``"2024Q2"``) 또는 리스트 (세로 비교 뷰).
            freq: 시계열 주기 — ``"Q"`` (분기, 기본) / ``"Y"`` (연간 strict 합) /
                ``"YTD"`` (year-to-date 누적). pandas 관용 코드. **finance topic 한정**.
            scope: 재무제표 범위 — ``"consolidated"`` (연결, 기본) / ``"separate"`` (별도).
                **finance topic 한정**.
            raw: True 면 원본 그대로 (정제 없이).

        Returns
        -------
        pl.DataFrame | None
            finance topic (IS/BS/CF/CIS/SCE):
                snakeId : str — 계정 식별자 (영문 snake_case)
                항목 : str — 계정명 (한글)
                2025Q4, 2025Q3, ... : float — 분기별 값 (원 단위, freq="Q" 기본)
                2025, 2024, ... : float — 연간 합산 값 (원 단위, freq="Y")
            ratios topic:
                항목 : str — 비율명
                2025Q4, 2025Q3, ... : float — 비율값 (%, 배)
            notes topic (inventory, borrowings 등):
                항목 : str — 세부 항목명
                당기, 전기 또는 연도 컬럼 : float — 금액 (원 단위)
            docs/report topic (dividend, employee 등):
                topic별 컬럼 구조 — c.show(topic) 실행으로 확인
            블록 미지정 + 멀티블록 topic:
                block : int — 블록 번호
                title : str — 블록 제목
            데이터 없으면 None.

        Requires:
            데이터: docs (자동 다운로드). finance topic 은 finance parquet 도 필요.

        AIContext:
            - 120+ topic 단일 접근점 — LLM 이 데이터 조회 핵심 도구
            - finance topic 은 freq/scope 토글로 분기/연간/연결/별도 자유 전환

        Guide:
            - "분기 손익" → ``c.show("IS")``
            - "연간 손익" → ``c.show("IS", freq="Y")``
            - "별도 재무상태표" → ``c.show("BS", scope="separate")``
            - "2023년 손익" → ``c.show("IS", period="2023")``
            - "배당 정보" → ``c.show("dividend")``
            - "주요주주/최대주주" → ``c.show("majorHolder")``

        SeeAlso:
            - select: show() 결과에서 행/열 필터 + 차트
            - trace: 데이터 출처 추적
            - topics: 사용 가능한 topic 전체 목록

        Example::

            c = dartlab.Company("005930")
            c.show("IS")                              # 분기 연결 (기본)
            c.show("IS", freq="Y")                    # 연간 연결
            c.show("IS", scope="separate")            # 분기 별도
            c.show("IS", freq="Y", scope="separate")  # 연간 별도
            c.show("IS", period="2023")               # 2023년 필터
            c.show("dividend")                        # 배당
            c.show("majorHolder")                     # 주요주주/최대주주

        LLM Specifications:
            AntiPatterns:
                - 분기 컬럼명을 "Q4_2025" 로 추측 (실제는 "2025Q4")
                - freq="M" 같은 미지원 값 (Q/Y/YTD 만)
                - finance topic 에 raw=True 후 비율 계산 (정제 단계 누락)
            OutputSchema:
                - snakeId : str — 영문 snake_case 계정 식별자 (finance 한정)
                - 항목 : str — 한글 계정명
                - 2025Q4, 2025Q3, ... : float — 분기 값 (원 단위, freq="Q" 기본)
                - 2025, 2024, ... : float — 연간 합산 (원 단위, freq="Y")
            Freshness:
                분기 마감 후 45일 (DART 공시 마감일). c.update() 로 증분 갱신.
        """
        from dartlab.providers.dart.dataDispatcher import showImpl

        result = showImpl(self, topic, block, period=period, freq=freq, scope=scope, raw=raw)
        if asOf is None or result is None:
            return result
        return _filterPeriodColumnsByAsOf(result, asOf)

    def _showFinanceStatement(
        self,
        topic: str,
        block: int | None,
        *,
        period: str | None,
        freq: str,
        scope: str,
    ) -> pl.DataFrame | None:
        from dartlab.providers.dart.dataDispatcher import showFinanceStatement

        return showFinanceStatement(self, topic, block, period=period, freq=freq, scope=scope)

    def _showSectionsTopic(
        self,
        topic: str,
        block: int | None,
        *,
        period: str | None,
        raw: bool,
        freq: str,
        scope: str,
    ) -> pl.DataFrame | None:
        from dartlab.providers.dart.dataDispatcher import showSectionsTopic

        return showSectionsTopic(self, topic, block, period=period, raw=raw, freq=freq, scope=scope)

    @staticmethod
    def _warnUnknownTopic(topic: str, sec: pl.DataFrame) -> None:
        from dartlab.providers.dart.dataShapeUtils import warnUnknownTopic

        warnUnknownTopic(topic, sec)

    @staticmethod
    def _transposeToVertical(wide: pl.DataFrame, periods: list[str]) -> pl.DataFrame | None:
        from dartlab.providers.dart.dataShapeUtils import transposeToVertical

        return transposeToVertical(wide, periods)

    @staticmethod
    def _cleanFinanceDataFrame(df: pl.DataFrame, sjDiv: str) -> pl.DataFrame:
        from dartlab.providers.dart.dataShapeUtils import cleanFinanceDataFrame

        return cleanFinanceDataFrame(df, sjDiv)

    _FINANCE_TOPICS = frozenset({"BS", "IS", "CF", "CIS", "SCE"})

    # ── docs multi-block select 지원 ──────────────────────────

    def _buildDocsItemIndex(self, topic: str) -> dict[str, list[tuple[int, pl.DataFrame]]]:
        from dartlab.providers.dart.docsSelectMatcher import buildDocsItemIndex

        return buildDocsItemIndex(self, topic)

    def _selectFromDocsTopic(
        self,
        topic: str,
        indList: list[str],
        colList: list[str] | None,
    ) -> pl.DataFrame | None:
        from dartlab.providers.dart.docsSelectMatcher import selectFromDocsTopic

        return selectFromDocsTopic(self, topic, indList, colList)

    def _selectFromDocsTopicAll(
        self,
        topic: str,
        indList: list[str] | None,
        colList: list[str] | None,
    ) -> pl.DataFrame | None:
        from dartlab.providers.dart.docsSelectMatcher import selectFromDocsTopicAll

        return selectFromDocsTopicAll(self, topic, indList, colList)

    @property
    def select(self):
        """show() 결과에서 행/열 필터 — dual access.

            c.select("IS", ["매출액"])           # call form
            c.select.IS(["매출액"])              # attr form
            c.select.IS(["매출액"], freq="Y")    # attr + kwargs

        실제 동작은 ``_selectImpl`` 참조.

        Returns
        -------
        CallableAccessor
            dual-access proxy. call/attr form 둘 다 ``_selectImpl`` 호출
            — ``SelectResult`` 반환 (filtered DataFrame + meta). 상세는
            ``_selectImpl`` docstring.
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
        """show() 결과에서 행(indList) + 열(colList) 필터 — 내부 구현.

        ``c.show()`` 와 동일한 freq/scope 파라미터를 받는다 (api-contract).

        Args:
            topic: IS, BS, CF, CIS, SCE 또는 docs topic.
            indList: 행 필터. 한글 항목/snakeId/항목명. 단일 str 도 가능.
            colList: 열(기간) 필터. 단일 str 도 가능.
            freq: 시계열 주기 — ``"Q"`` (분기, 기본) / ``"Y"`` (연간) / ``"YTD"`` (누적).
            scope: 재무제표 범위 — ``"consolidated"`` (연결, 기본) / ``"separate"`` (별도).

        Returns
        -------
        SelectResult
            show()와 동일 컬럼 구조에서 indList/colList로 필터된 행/열.
            .chart() 체이닝으로 시각화 가능.
            내부 DataFrame 접근: result.df (pl.DataFrame).
            finance topic 예시 (c.select("IS", ["매출액"])):
                snakeId : str — 계정 식별자
                항목 : str — 계정명
                2025Q4, 2025Q3, ... : float — 분기별 값 (원 단위)
            행 매칭 실패 시 ValueError.

        Example::

            c.select("IS", ["매출액", "영업이익"])
            c.select("IS", ["매출액"], freq="Y")              # 연간 매출
            c.select("BS", ["자본총계"], scope="separate")    # 별도 자본
            c.select("IS", ["매출액"]).chart()
        """
        from dartlab.core.select import SelectResult
        from dartlab.core.show import selectFromShow

        # show() 가 ValueError 발생하면 그대로 propagate (silent None X)
        try:
            df = self.show(topic, freq=freq, scope=scope)
        except (ValueError, KeyError):
            if strict:
                raise
            return None
        if df is None or not isinstance(df, pl.DataFrame):
            if not strict:
                return None
            # show 가 정상 None 반환한 경우 (raw 모드 등) — ValueError 대신 명확한 안내
            raise ValueError(
                f"'{topic}' topic 의 데이터를 가져올 수 없습니다. "
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
                "필터링할 항목을 1개 이상 전달하세요. 예: c.select('IS', ['매출액'])"
            )

        # multi-block docs topic 감지 → 역인덱스 경로
        isBlockIndex = (
            isinstance(df, pl.DataFrame)
            and "block" in df.columns
            and "type" in df.columns
            and "preview" in df.columns
            and topic not in self._FINANCE_TOPICS
        )
        if isBlockIndex and (indList is not None or colList is not None):
            filtered = self._selectFromDocsTopicAll(topic, indList, colList)
        else:
            filtered = selectFromShow(df, indList, colList)
        if filtered is None:
            if not strict:
                return None
            # indList 가 dataframe 에 매치 안 되면 silent None 대신 명시적 에러
            available = []
            try:
                # 첫 컬럼이 보통 항목
                if df.width > 0:
                    first_col = df.columns[0]
                    available = df[first_col].drop_nulls().to_list()[:15]
            except (AttributeError, IndexError, TypeError):
                pass
            ind_str = indList if indList else colList
            hint = f"\n  사용 가능한 행 일부: {', '.join(str(a) for a in available)}" if available else ""
            raise ValueError(
                f"'{topic}' topic 에서 {ind_str} 를 찾을 수 없습니다.{hint}\n"
                f"  c.show('{topic}') 로 전체 행을 확인하세요."
            )
        return SelectResult(
            filtered,
            topic,
            {
                "stockCode": self.stockCode,
                "corpName": self.corpName,
                "currency": self.currency,
            },
        )

    def trace(self, topic: str, period: str | None = None) -> dict[str, Any] | None:
        """topic 데이터의 출처(docs/finance/report)와 선택 근거 추적.

        Capabilities:
            - topic별 데이터 출처 확인 (docs, finance, report)
            - 출처 선택 이유 (우선순위, fallback 경로)
            - 각 출처별 데이터 행 수, 기간 수, 커버리지

        Args:
            topic: topic 이름.
            period: 특정 기간. None이면 전체.

        Returns:
            dict — primarySource, fallbackSources, whySelected, availableSources 등.

        Requires:
            데이터: docs + finance + report (보유한 것만 추적)

        Example::

            c.trace("BS")           # 재무상태표 출처
            c.trace("dividend")     # 배당 데이터 출처

        AIContext:
            - 데이터 출처 신뢰도 판단 — finance > report > docs 우선순위 확인
            - 분석 결과의 근거 투명성 확보

        Guide:
            - "이 데이터 어디서 온 거야?" → c.trace("BS")
            - "데이터 출처 확인" → c.trace(topic)

        SeeAlso:
            - show: topic 데이터 조회 (trace로 출처 확인 후 열람)
            - sources: 3개 source 전체 가용 현황
        """
        topic = _resolveTopic(topic)
        if topic == "docsStatus" and not self._hasDocs:
            return {
                "topic": topic,
                "period": period,
                "primarySource": "docs",
                "fallbackSources": [],
                "selectedPayloadRef": None,
                "availableSources": [],
                "whySelected": "docs unavailable",
            }
        if topic == "ratios":
            ratioSeries = self._ratioSeries()
            templateKey = _ratioTemplateKeyForIndustryGroup(getattr(self.sector, "industryGroup", None))
            rowCount = None
            yearCount = None
            coverage = "missing"
            if ratioSeries is not None:
                series, years = ratioSeries
                fieldNames = _RATIO_TEMPLATE_FIELDS.get(templateKey)
                ratioFrame = _ratioSeriesToDataFrame(series, years, fieldNames=fieldNames)
                rowCount = None if ratioFrame is None else ratioFrame.height
                yearCount = len(years)
                if ratioFrame is not None and rowCount >= 30 and yearCount >= 5:
                    coverage = "full"
                elif ratioFrame is not None and rowCount > 0:
                    coverage = "partial"
            return {
                "topic": topic,
                "period": period,
                "primarySource": "finance",
                "fallbackSources": [],
                "selectedPayloadRef": "finance:RATIO",
                "availableSources": []
                if ratioSeries is None
                else [
                    {
                        "source": "finance",
                        "rows": 1,
                        "payloadRef": "finance:RATIO",
                        "summary": "annual ratio series"
                        if templateKey is None
                        else f"annual ratio series ({templateKey} template)",
                        "priority": 300,
                    }
                ],
                "whySelected": "finance authoritative priority"
                if templateKey is None
                else f"finance authoritative priority with {templateKey} industry template",
                "template": templateKey or "general",
                "rowCount": rowCount,
                "yearCount": yearCount,
                "coverage": coverage,
            }
        if topic in {"BS", "IS", "CF", "CIS", "SCE"}:
            result = self._traceFinanceTopic(topic, period=period)
            if result is not None:
                return result
        return self._profileAccessor.trace(topic, period=period)

    def diff(
        self,
        topic: str | None = None,
        fromPeriod: str | None = None,
        toPeriod: str | None = None,
    ) -> pl.DataFrame | None:
        """기간간 텍스트 변경 비교.

        Capabilities:
            - 전체 topic 변경 요약 (변경량 스코어링)
            - 특정 topic 기간별 변경 이력
            - 두 기간 줄 단위 diff (추가/삭제/변경)

        Args:
            topic: topic 이름. None이면 전체 변경 요약.
            fromPeriod: 비교 시작 기간 ("2023").
            toPeriod: 비교 끝 기간 ("2024").

        Returns:
            pl.DataFrame | None — 변경 요약, 히스토리, 또는 줄 단위 diff.

        Requires:
            데이터: docs (2개 이상 기간 필요)

        Example::

            c.diff()                                    # 전체 변경 요약
            c.diff("businessOverview")                  # 사업개요 변경 이력
            c.diff("businessOverview", "2023", "2024")  # 줄 단위 diff

        AIContext:
            - 기간간 공시 변경 감지 — 사업 방향 전환, 리스크 요인 변화 탐지
            - watch()보다 세밀한 줄 단위 변경 추적

        Guide:
            - "공시에서 뭐가 바뀌었어?" → c.diff()
            - "사업개요 변경 이력" → c.diff("businessOverview")
            - "2023 vs 2024 차이" → c.diff("businessOverview", "2023", "2024")

        SeeAlso:
            - watch: 변화 중요도 스코어링 (diff보다 요약적)
            - keywordTrend: 키워드 빈도 추이 (텍스트 변화의 다른 관점)
            - show: 특정 기간 원문 조회
        """
        if topic is not None:
            topic = _resolveTopic(topic)
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
        """공시 텍스트 키워드 빈도 추이 (topic x period x keyword).

        Capabilities:
            - 공시 텍스트에서 키워드 빈도 추이 분석
            - 54개 내장 키워드 세트 (AI, ESG, 탄소중립 등)
            - topic별 x 기간별 빈도 매트릭스
            - 복수 키워드 동시 검색

        Args:
            keyword: 단일 키워드. None이면 내장 키워드 전체.
            keywords: 복수 키워드 리스트.

        Returns:
            pl.DataFrame | None — topic x period x keyword 빈도.

        Requires:
            데이터: docs (자동 다운로드)

        Example::

            c.keywordTrend("AI")
            c.keywordTrend(keywords=["AI", "ESG"])
            c.keywordTrend()                  # 54개 내장 키워드 전체

        AIContext:
            - 공시 텍스트의 키워드 빈도 변화로 전략 방향 전환 감지
            - AI, ESG, 탄소중립 등 트렌드 키워드 모니터링

        Guide:
            - "AI 언급 추이" → c.keywordTrend("AI")
            - "ESG 관련 변화" → c.keywordTrend("ESG")
            - "전체 키워드 트렌드" → c.keywordTrend()

        SeeAlso:
            - diff: 텍스트 줄 단위 변경 비교 (키워드가 아닌 전체 변경)
            - watch: 변화 중요도 스코어링
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
        """최근 뉴스 수집.

        Capabilities:
            - Google News RSS 기반 뉴스 수집
            - 제목, 날짜, 소스, 링크
            - 기간 조절 가능

        Args:
            days: 최근 N일. 기본 30.

        Returns:
            pl.DataFrame — title, date, source, link.

        Requires:
            없음 (공개 RSS)

        Example::

            c.news()           # 최근 30일
            c.news(days=7)     # 최근 7일

        AIContext:
            - 최근 뉴스로 시장 반응, 이슈, 이벤트 파악
            - ask()/chat()에서 정성적 시장 맥락 보충

        Guide:
            - "최근 뉴스 보여줘" → c.news()
            - "이번 주 뉴스" → c.news(days=7)

        SeeAlso:
            - liveFilings: 최신 공시 (뉴스가 아닌 공식 공시)
            - gather: 뉴스 포함 4축 외부 데이터 수집
        """
        from dartlab.core.gatherProvider import getGatherProvider

        provider = getGatherProvider()
        return provider.news(self.corpName, market="KR", days=days) if provider else None

    def watch(
        self,
        topic: str | None = None,
    ) -> pl.DataFrame | None:
        """공시 변화 감지 — 중요도 스코어링 기반 변화 요약.

        Capabilities:
            - 전체 topic 변화 중요도 스코어링
            - 텍스트 변화량 + 재무 영향 통합 평가
            - 특정 topic 상세 변화 내역

        Args:
            topic: topic 이름. None이면 전체 중요도 순 요약.

        Returns:
            pl.DataFrame | None — topic, score, changeType, details 등.

        Requires:
            데이터: docs (자동 다운로드)

        Example::

            c.watch()                    # 전체 중요도 순
            c.watch("riskManagement")    # 특정 topic

        AIContext:
            - 공시 변화 중요도 자동 평가 — 분석 우선순위 결정에 활용
            - 텍스트 변화량 + 재무 영향 통합 스코어

        Guide:
            - "뭐가 크게 바뀌었어?" → c.watch()
            - "리스크 관련 변화" → c.watch("riskManagement")

        SeeAlso:
            - diff: 줄 단위 상세 변경 비교 (watch보다 세밀)
            - keywordTrend: 키워드 빈도 추이
        """
        import importlib

        scanner = importlib.import_module("dartlab.scan.watch.scanner")
        result = scanner.scanCompany(self, topic=topic)
        if result is None:
            return None
        return result.toDataframe()

    @property
    def story(self):
        """5엔진 결과 조립 보고서 — 11 reportType × 7 template. 느림(60~80초). dual access.

        Guide:
            - "보고서" → c.story()
            - "신용 보고서" → c.story(type="credit")
            - "수익성 블록만" → c.story("수익성")
            - "사이클 관점" → c.story(type="full", template="사이클")

        실제 동작은 ``_storyImpl`` 참조.

        Returns
        -------
        CallableAccessor
            dual-access proxy. 호출 시 ``_storyImpl`` 이 ``Story`` 객체 반환
            (blocks / toMarkdown() / toHtml()). 상세는 ``_storyImpl`` docstring.
        """
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
        """재무제표 구조화 보고서 — 기업이야기꾼의 대본 (내부 구현).

        Capabilities:
            - 14개 섹션 전체 보고서 (수익구조~재무정합성)
            - 단일 섹션 지정 가능
            - 4개 출력 형식 (rich, html, markdown, json)
            - 섹션간 순환 서사 자동 감지
            - 프리셋 지원 (executive/audit/credit/growth/valuation)
            - 스토리 템플릿 (사이클/프랜차이즈/턴어라운드/성장/자본집약/지주/현금부자)
            - detail=False로 요약만 표시
            - 레이아웃 커스텀

        AIContext:
            - ask() (dartlab.ask) 가 이 결과를 tool 로 소비해 AI 해석 생성
            - ask()에서 재무분석 컨텍스트로 활용

        Args:
            section: 섹션명 ("수익구조" 등). None이면 전체.
            layout: StoryLayout 커스텀. None이면 기본.
            helper: True면 해석 힌트 텍스트 포함. None이면 자동.
            preset: 프리셋명 ("executive"/"audit"/"credit"/"growth"/"valuation"). None이면 전체.
            template: 스토리 템플릿 ("성장"/"자본집약"/"지주" 등). "auto"면 자동 판별.
            detail: True면 전체 블록, False면 섹션 요약만. None이면 preset 기본값 또는 True.

        Returns:
            Story — 구조화 보고서.

        Requires:
            데이터: finance + report (자동 다운로드)

        Example::

            c.story()                        # 전체 검토서
            c.story("수익구조")                # 특정 섹션
            c.story(preset="audit")          # 감사/회계 검토용
            c.story(template="auto")         # 스토리 자동 판별
            c.story(template="성장")          # 성장 템플릿 적용
            c.story(detail=False)            # 전 섹션 요약만

        Guide:
            When: 구조화된 보고서가 필요할 때. 사용자가 "보고서" 명시 시에만.
            How: 무인자 = 전체 보고서. section 으로 개별 섹션. type 으로 보고서 타입.
            - "재무 검토서 만들어줘" -> c.story()
            - "수익구조 분석" -> c.story("수익구조")
            - "감사용 리뷰" -> c.story(preset="audit")
            - "이 회사 스토리는?" -> c.story(template="auto")
            - "요약만 보여줘" -> c.story(detail=False)
            - "AI 가 해석한 보고서" -> dartlab.ask("005930 보고서 작성해줘") (AI 가 story tool 호출)
            Verified:
                - credit 타입 → 신용 종합 보고서 (observed via credit ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)
                - audit 타입 → 분식회계 가능성 판정 보고서 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)
                - governance 타입 → 지배구조 점검 보고서 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)
                - dividend 타입 → 배당 매력 종합 보고서 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)

        SeeAlso:
            - dartlab.ask: AI 자율 분석 (분석 질문은 여기로)
            - analysis: 14축 개별 분석 (story가 내부적으로 소비)
            - insights: 7영역 등급 + 이상치 요약

        LLM Specifications:
            AntiPatterns:
                - story() 무인자 호출 후 결과 dict 전체를 답변 본문에 dump (사용자 부담)
                - section 추측 (정확한 한글 섹션명 — c.topics 또는 가이드 확인 후)
                - preset / template 잘못 매핑 (executive/audit/credit/growth/valuation 만)
            OutputSchema:
                - Story 객체 — 14 섹션 dict + 메타 (basePeriod, prefset, template)
                - section 지정 시: 단일 섹션 dict
                - .toMarkdown() 메서드로 markdown 문자열 변환
            Prerequisites:
                - finance + report 데이터 (자동 다운로드, 첫 호출 시간 소요)
            Freshness:
                finance/report 데이터의 c.update() 시점.
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
        """재무제표 완전 분석 — 22축 (5 group), 6막 인과 구조. dual access (api-contract).

        Guide:
            - "분석해줘" → c.analysis() (가이드 반환)
            - "수익성" → c.analysis("financial", "수익성")
            - "가치평가" → c.analysis("valuation", "가치평가")
            - "override 재계산" → c.analysis("가치평가", overrides={"wacc": 9.0})

        실제 동작은 ``_analysisImpl`` 참조.

        Returns
        -------
        CallableAccessor
            dual-access proxy. 호출 시 ``_analysisImpl`` 이
            ``pl.DataFrame | dict`` 반환 (axis=None → 가이드 DataFrame, axis
            지정 → 축별 dict). 상세는 ``_analysisImpl`` docstring.
        """
        from dartlab.core.dualAccess import CallableAccessor

        if "_analysisAccessor" not in self._cache:
            self._cache["_analysisAccessor"] = CallableAccessor(self._analysisImpl, name="analysis")
        return self._cache["_analysisAccessor"]

    def _analysisImpl(self, axis: str | None = None, sub: str | None = None, **kwargs):
        """재무제표 완전 분석 — 22축, 단일 종목 심층 (내부 구현).

        Capabilities:
            - 22축 분석 (5 group)
              - financial (14): 수익구조, 자금조달, 자산구조, 현금흐름, 수익성, 성장성, 안정성, 효율성, 종합평가, 이익품질, 비용구조, 자본배분, 투자효율, 재무정합성
              - valuation (1): 가치평가
              - governance (3): 지배구조, 공시변화, 비교분석
              - forecast (2): 매출전망, 예측신호
              - macro (2): 매크로민감도, 밸류에이션밴드
            - 축 없이 호출 시 22축 가이드 반환
            - 개별 축 분석 시 Company 바인딩 (self 자동 전달)
            - 2-level 호출: c.analysis("financial", "수익성"), c.analysis("valuation", "가치평가")

        AIContext:
            - ask()/chat()에서 분석 결과를 컨텍스트로 주입
            - story가 내부적으로 analysis 결과를 소비

        Args:
            axis: 그룹 이름 ("financial", "valuation", "governance", "forecast", "macro") 또는 축 이름. None이면 가이드 반환.
            sub: 그룹 내 하위 축 이름 ("수익성", "가치평가", "매출전망", "지배구조", "매크로민감도" 등).
            **kwargs: 축별 추가 옵션.

        Returns:
            pl.DataFrame | dict — axis=None이면 가이드 DataFrame (axis/label/description/example/group/items).
            axis 지정 시 dict:
                {calcName} : dict — 축별 계산 결과
                    history : list[dict] — 시계열 ({period, ...지표})
                    displayHints : dict — core 컬럼 목록
                    turningPoints : list — 전환점 (있으면)
                {calcName}Flags : list[str] — 경고 플래그
                dataAsOf : dict — latestPeriod, retrievedAt
            _summary (autoEnrich 자동 주입) — 핵심 지표 요약 + [엔진가정] 블록.
            assumptions — 엔진 가정 (overrides 재호출용).

        Requires:
            데이터: finance (자동 다운로드)

        Example::

            c = Company("005930")
            c.analysis()                            # 전체 가이드 (22축)
            c.analysis("financial", "수익구조")       # 수익구조 분석
            c.analysis("valuation", "가치평가")       # 가치평가
            c.analysis("governance", "지배구조")      # 지배구조
            c.analysis("forecast", "매출전망")        # 매출전망
            c.analysis("macro", "매크로민감도")        # 매크로 민감도

        Guide:
            AI 역할: AI는 analysis를 단일 기업 재무·가치·리스크 해석 엔진으로 보고 axis/subaxis와 필요한 재무 evidence를 선택한다.
            When: 특정 종목의 재무 심층 분석이 필요할 때.
            How: axis 로 분석 영역, sub 로 세부 축 지정.
            - "22축 분석 뭐가 있어?" → c.analysis() (가이드 반환)
            - "수익구조 분석해줘" → c.analysis("financial", "수익구조")
            - "안정성 분석" → c.analysis("financial", "안정성")
            - "가치평가 해줘" → c.analysis("valuation", "가치평가")
            - "매출전망" → c.analysis("forecast", "매출전망")
            Verified:
                - 수익성 단독 → 마진 시계열 + 전환점 + 반도체 사이클 인과 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)
                - 이익품질 + 재무정합성 → 분식회계 가능성 판정 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)
                - 가치평가 → 적정주가 범위 + 현재가 대비 판정 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)
                - 자본배분 + 현금흐름 → 배당 매력 종합 판단 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)
                - 지배구조 → 이사회 독립성 + 지배력 집중 점검 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)

        SeeAlso:
            - story: 22축 분석을 섹션별 보고서로 조합
            - insights: 7영역 등급 요약 (analysis보다 요약적)
            - ratios: 재무비율 시계열 (analysis의 입력 데이터)

        LLM Specifications:
            AntiPatterns:
                - axis 만 주고 sub 없이 호출 (그룹 가이드만 반환, 실제 분석 X)
                - 그룹명 ("financial") 을 axis 로, 축명 ("수익성") 을 sub 로 — 순서 헷갈림
                - sub 에 영문 ("profitability") 사용 (실제는 한글)
            OutputSchema:
                - history : list[dict] — 시계열 (period + 지표들)
                - displayHints : dict — core 컬럼 목록
                - turningPoints : list — 전환점
                - dataAsOf : dict — latestPeriod, retrievedAt
                - assumptions : dict — 엔진 가정 (overrides 재호출용)
            Freshness:
                finance 데이터 기준 — 분기 마감 후 45일.
        """
        from dartlab.analysis.financial import Analysis

        _analysis = Analysis()
        if axis is None:
            return _analysis()
        if sub is not None:
            return _analysis(axis, sub, company=self, **kwargs)
        return _analysis(axis, company=self, **kwargs)

    def validateStory(self, overrides: dict | None = None) -> dict:
        """Damodaran 스토리 검증 — Possible / Plausible / Probable 3 테스트 통합.

        *Narrative and Numbers* (2017) 의 핵심: 밸류에이션의 타당성은
        (1) 과거 유사 사례, (2) 피어 분포 내 위치, (3) 수학·경제 첫 원칙
        3 층의 검증을 통과해야 한다.

        Capabilities:
            - calcStoryPrecedents (scan peer + KnowledgeDB insights)
            - calcPlausibilityBand (섹터 피어 분포 percentile)
            - calcValuationSins (정합성 규칙 위반)
            - overrides 로 AI 개입 (lifeCyclePhase, terminalGrowth 등)

        Args:
            overrides: 검증 기준 조율 (VALUATION_KEYS).

        Returns:
            dict
                precedents : dict — Possible Test 결과
                plausibility : dict — Plausible Test 결과
                rules : dict — Probable Test 결과
                overall : str — "info" | "warn" | "critical"

        Example::

            c = Company("005930")
            r = c.validateStory()
            for f in r["rules"]["flags"]:
                print(f['severity'], f['reason'])
        """
        from dartlab.analysis.financial.storyValidation import (
            calcPlausibilityBand,
            calcStoryPrecedents,
            calcValuationSins,
        )

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
        """dartlab 독립 신용평가 (dCR-AAA~D). 7축 — 채무상환/자본구조/유동성/현금흐름/사업안정성/재무신뢰성/공시리스크.

        Guide:
            - "신용등급" → c.credit("등급")
            - "채무 감당되나" → c.credit("채무상환")
            - "전체 평가" → c.credit(detail=True)
            - "속성 접근" → c.credit.유동성()

        실제 동작은 ``_creditImpl`` 참조.

        Returns
        -------
        CallableAccessor
            dual-access proxy. 호출 시 ``_creditImpl`` 이 dict 반환 (grade,
            score (점), healthScore (점), axes, outlook). 상세는 ``_creditImpl``.
        """
        from dartlab.core.dualAccess import CallableAccessor

        if "_creditAccessor" not in self._cache:
            self._cache["_creditAccessor"] = CallableAccessor(self._creditImpl, name="credit")
        return self._cache["_creditAccessor"]

    def _creditImpl(
        self,
        axis: str | None = None,
        *,
        detail: bool = False,
        basePeriod: str | None = None,
        overrides: dict | None = None,
    ):
        """독립 신용평가 — dCR 20단계 등급 (내부 구현).

        dartlab 독립 신용평가 엔진(credit/)이 산출하는 dCR 등급.
        7축 정량 스코어링 + 업종별 차등 + 시계열 안정화.

        Args:
            axis: 축 이름 ("채무상환", "자본구조" 등). None이면 등급 종합.
            detail: True이면 7축 상세 + 지표 시계열 포함.
            basePeriod: 분석 기준 기간. None이면 최신.
            overrides: AI/사용자가 엔진 계산 가정을 직접 교체하는 dict.
                키: debtRatio, interestCoverage, currentRatio, quickRatio, ocfToDebt,
                fcfToDebt, scenarioStress. 상세: core/overrides.py.

        Returns:
            dict | None: 등급 결과. axis 지정 시 해당 축만.

        Example::

            c.credit()              # → {"grade": "dCR-AA", "score": 6.6, ...}
            c.credit("채무상환")     # → {"axis": "채무상환능력", "score": 2.7, ...}
            c.credit(detail=True)   # → 7축 상세 + metricsHistory
            c.credit(overrides={"debtRatio": 150, "interestCoverage": 2.5})  # 스트레스 시나리오

        Guide:
            When: 부도 위험·신용등급·채무상환능력 판단이 필요할 때.
            How: 무인자 호출로 종합 등급, axis 로 개별 축, detail=True 로 시계열.
            Verified:
                - credit 단독 → dCR 등급 + 7축 위험점수 분해 + PD 추정 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)
                - credit + analysis(안정성,현금흐름) → 부도 위험 종합 진단 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)

        SeeAlso:
            - story("신용평가"): 보고서 형식으로 렌더링
            - analysis("financial", "신용평가"): analysis 축으로 접근

        LLM Specifications:
            AntiPatterns:
                - axis 와 detail=True 동시 (개별 축에 detail 효과 없음)
                - overrides 키 추측 (validateOverrides 가 검증, 미지원 키는 차단)
            OutputSchema:
                - grade : str — dCR 등급 (예: dCR-AA, dCR-BBB)
                - score : float — 종합 점수 (0~10)
                - healthScore : float — 재무 건전성 점수
                - axes : dict — 7축 위험 점수 (axis 미지정 시)
                - outlook : str — 등급 전망
            Freshness:
                finance 데이터 기준 — 분기 마감 후 45일.
        """
        from dartlab.core.overrides import validateOverrides
        from dartlab.credit import creditCompany

        clean = validateOverrides(overrides, engine="credit")
        kwargs: dict = {}
        if clean:
            kwargs["overrides"] = clean
        return creditCompany(self, axis=axis, detail=detail, basePeriod=basePeriod, **kwargs)

    def gather(self, axis: str | None = None, target: str | None = None, **kwargs):
        """외부 시장 데이터 수집 — 4축 (price/flow/macro/news).

        Args:
            axis: 데이터 축. price/flow/macro/news/sector/insider/peers/ownership.
            target: 축별 부가 인자.
                - axis='news' 일 때: 검색어 (예: '한국 경제', '반도체 수출 동향').
                  시장 레벨 뉴스 조회. 비우면 종목 기반 fallback.
                - axis='macro' 일 때: 시리즈 이름 또는 시나리오.
                - axis='sector'/'peers' 일 때: 비교 대상 sector/종목.
            **kwargs: market, days, start, end 등 축별 옵션.

        Capabilities:
            - price: OHLCV 주가 시계열 (KR Naver / US Yahoo)
            - flow: 외국인/기관 수급 동향 (KR 전용)
            - macro: ECOS(KR) / FRED(US) 거시지표 시계열 (기본 HF 벌크)
            - news: Google News RSS 뉴스 수집
            - 자동 fallback 체인, circuit breaker, TTL 캐시

        AIContext:
            - ask()/chat()에서 주가/수급/거시 데이터를 컨텍스트로 주입
            - 기업 분석 시 시장 데이터 보충 자료로 활용

        Args:
            axis: 축 이름 ("price", "flow", "macro", "news"). None이면 가이드 반환.
            **kwargs: market, start, end, days 등 축별 옵션.

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
                open : float — 시가 (원)
                high : float — 고가 (원)
                low : float — 저가 (원)
                close : float — 종가 (원)
                volume : int — 거래량
            axis="flow":
                date : date — 날짜
                외국인순매수 : int — 외국인 순매수량
                기관순매수 : int — 기관 순매수량
                (KR 전용. EDGAR ticker는 None 반환)
            axis="macro":
                date : date — 날짜
                지표별 컬럼 : float — ECOS/FRED 거시지표 값
            axis="news":
                title : str — 뉴스 제목
                link : str — 기사 URL
                pubDate : str — 발행일
            데이터 없으면 None.

        Requires:
            price/flow/news: 없음 (공개 API)
            macro: 불필요 -- apiKey 명시 시 ECOS/FRED 직접 API 호출

        Example::

            c = Company("005930")
            c.gather()                 # 4축 가이드
            c.gather("price")          # 주가 시계열
            c.gather("news")           # 뉴스

        Guide:
            When: 주가·수급·거시지표·뉴스 원본 데이터가 필요할 때.
            How: axis 로 데이터 종류 지정. 무인자 = 가이드.
            - "주가 데이터" → c.gather("price")
            - "외국인/기관 수급" → c.gather("flow")
            - "거시경제 지표" → c.gather("macro")
            - "뉴스 수집" → c.gather("news") 또는 c.news()
            Verified:
                - gather("news") → 뉴스 목록 + 헤드라인 해석 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)

        SeeAlso:
            - news: 뉴스 전용 단축 메서드
            - ask: gather 데이터를 컨텍스트로 활용한 AI 분석

        LLM Specifications:
            AntiPatterns:
                - axis="all" 같은 미지원 값 (price/flow/macro/news/sector/insider/peers/ownership 만)
                - flow 를 EDGAR ticker (US) 에 호출 (KR 전용)
                - news 의 target 비워두고 종목 무관 결과 기대 (종목 fallback 발생)
            OutputSchema:
                - price: date / open / high / low / close / volume (원, 정수)
                - flow: date / 외국인순매수 / 기관순매수 (KR 전용, 정수)
                - macro: date / 지표별 컬럼 (float)
                - news: title / link / pubDate (string)
            Freshness:
                price/flow: T+1 (전일 종가). macro: ECOS/FRED 갱신 주기. news: 실시간 RSS.
        """
        from dartlab.core.gatherProvider import getGatherProvider

        provider = getGatherProvider()
        if provider is None:
            return None
        return provider.entry(axis, self.stockCode, **kwargs)

    def table(
        self,
        topic: str,
        subtopic: str | None = None,
        *,
        numeric: bool = False,
        period: str | None = None,
    ) -> Any:
        """subtopic wide 셀의 markdown table을 구조화 DataFrame으로 파싱.

        Capabilities:
            - docs 원문의 markdown table을 Polars DataFrame으로 변환
            - subtopic 지정으로 특정 표만 추출
            - numeric 모드로 금액 문자열을 float 변환
            - period 필터로 특정 기간 컬럼만 선택

        Args:
            topic: docs topic 이름
            subtopic: 파싱할 subtopic 이름 (None이면 첫 번째 subtopic)
            numeric: True이면 금액 문자열을 float로 변환
            period: 기간 필터 (예: "2024")

        Returns:
            ParsedSubtopicTable (df, subtopic, columns) 또는 파싱 불가 시 None

        Requires:
            데이터: docs (자동 다운로드)

        Example::

            c.table("employee")                    # 첫 번째 subtopic
            c.table("employee", "직원현황")         # 특정 subtopic
            c.table("employee", numeric=True)       # 숫자 변환

        AIContext:
            - docs 원문 테이블을 구조화하여 정량 분석에 활용
            - numeric=True로 금액 문자열을 수치화하면 계산 가능

        Guide:
            - "직원 현황 테이블" → c.table("employee")
            - "표 데이터를 숫자로" → c.table(topic, numeric=True)

        SeeAlso:
            - show: topic 전체 데이터 (table은 subtopic 단위 파싱)
            - select: show() 결과에서 행/열 필터
        """
        result = self._topicSubtables(topic)
        if result is None:
            return None
        from dartlab.providers.dart.docs.sections import parseSubtopicTable

        parsed = parseSubtopicTable(result, subtopic, numeric=numeric)
        if parsed is None:
            return None
        if period is not None and parsed.df is not None:
            labelCol = (
                "항목"
                if "항목" in parsed.df.columns
                else "항목"
                if "항목" in parsed.df.columns
                else parsed.df.columns[0]
            )
            periodCols = [c for c in parsed.df.columns if c != labelCol]
            matchedCols = [c for c in periodCols if period in c]
            if matchedCols:
                from dataclasses import replace

                filteredDf = parsed.df.select([labelCol, *matchedCols])
                return replace(parsed, df=filteredDf)
        return parsed

    @property
    def topics(self) -> pl.DataFrame:
        """topic별 요약 DataFrame -- 전체 데이터 지도.

        Capabilities:
            - docs/finance/report 모든 source의 topic을 하나의 DataFrame으로 통합
            - chapter 순서대로 정렬, 각 topic의 블록 수/기간 수/최신 기간 표시
            - 어떤 데이터가 있는지 한눈에 파악

        AIContext:
            - LLM이 가용 topic 목록을 파악하는 데 사용
            - 분석 범위 결정 시 참조

        Guide:
            - "어떤 데이터가 있어?" → c.topics
            - "topic 목록" → c.topics

        SeeAlso:
            - show: 특정 topic 데이터 조회
            - sections: topic x period 전체 지도 (topics보다 상세)
            - index: 전체 구조 메타데이터 목차

        Returns:
            pl.DataFrame -- 컬럼: order, chapter, topic, source, blocks, periods, latestPeriod

        Requires:
            데이터: docs/finance/report 중 하나 이상 (자동 다운로드)

        Example::

            c = Company("005930")
            c.topics                   # 전체 topic 요약
            c.topics.filter(pl.col("source") == "finance")  # finance만

        LLM Specifications:
            AntiPatterns:
                - 매 호출마다 c.topics 재호출 (캐시 — 1 회면 충분)
                - topics 결과로 추측한 토픽명을 show() 에 잘못 매핑 (정확한 topic 문자열 필요)
            OutputSchema:
                - order : int — chapter 순서
                - chapter : str — 장 이름
                - topic : str — topic 식별자 (show 호출 키)
                - source : str — docs / finance / report
                - blocks : int — 블록 수
                - periods : int — 기간 수
                - latestPeriod : str — 최신 기간
            Freshness:
                docs/finance/report 각각의 c.update() 시점.
        """
        cacheKey = "_topicsDataFrame"
        if cacheKey in self._cache:
            return self._cache[cacheKey]

        docsManifest = self._docsTopicManifest()
        rows = docsManifest.to_dicts() if not docsManifest.is_empty() else []
        seen = {str(row["topic"]) for row in rows if isinstance(row.get("topic"), str)}

        financeRows: list[dict[str, Any]] = []
        if self._hasFinanceParquet:
            raw = loadData(self.stockCode, category="finance", columns=["bsns_year"])
            years = (
                sorted({str(year) for year in raw["bsns_year"].drop_nulls().to_list() if str(year) != "2015"})
                if raw is not None and not raw.is_empty() and "bsns_year" in raw.columns
                else []
            )
            latestPeriod = years[-1] if years else None
            for idx, topic in enumerate(("BS", "IS", "CIS", "CF", "SCE", "ratios")):
                if topic in seen:
                    continue
                financeRows.append(
                    {
                        "order": 3000 + idx,
                        "chapter": "III",
                        "topic": topic,
                        "source": "finance",
                        "blocks": 1,
                        "periods": len(years),
                        "latestPeriod": latestPeriod,
                    }
                )

        combined = rows + financeRows
        if not combined:
            from dartlab.providers.dart.docsSectionsAnalyzer import _emptyTopicManifest

            result = _emptyTopicManifest()
        else:
            result = (
                pl.DataFrame(combined, strict=False)
                .with_columns(pl.col("chapter").replace(_CHAPTER_ORDER).cast(pl.Int64).alias("_chapterOrder"))
                .sort(["_chapterOrder", "order", "topic"])
                .drop("_chapterOrder")
            )
        self._cache[cacheKey] = result
        return result

    @property
    def sources(self) -> pl.DataFrame:
        """docs/finance/report 3개 source의 가용 현황 요약.

        Capabilities:
            - 3개 데이터 source(docs, finance, report) 존재 여부/규모 한눈에 확인
            - 각 source의 row/col 수와 shape 문자열 제공
            - 데이터 로드 전 가용성 사전 점검

        Returns:
            pl.DataFrame -- 컬럼: source, available, rows, cols, shape

        Requires:
            없음 (메타데이터만 조회, 데이터 파싱 불필요)

        Example::

            c = Company("005930")
            c.sources                  # 3행 DataFrame

        AIContext:
            - 데이터 가용성 사전 점검 — 분석 가능 범위 판단의 기초

        Guide:
            - "데이터 뭐가 있어?" → c.sources
            - "docs/finance/report 상태" → c.sources

        SeeAlso:
            - topics: topic 단위 상세 데이터 지도
            - trace: 특정 topic의 출처 추적

        LLM Specifications:
            AntiPatterns:
                - 매 분석마다 c.sources 호출 (캐시 — 1 회면 충분)
                - sources 결과로 분석 결정 (가용성만 확인, 실제 분석은 show)
            OutputSchema:
                - source : str — docs / finance / report
                - available : bool — 데이터 보유 여부
                - rows : int | None — 행 수
                - cols : int | None — 컬럼 수
                - shape : str — "rows × cols" 표기
            Freshness:
                rawDocs / rawFinance / rawReport 의 다운로드 시점 기준.
        """
        rows = []
        for source, raw in (
            ("docs", self.rawDocs),
            ("finance", self.rawFinance),
            ("report", self.rawReport),
        ):
            rows.append(
                {
                    "source": source,
                    "available": raw is not None,
                    "rows": raw.height if raw is not None else None,
                    "cols": raw.width if raw is not None else None,
                    "shape": _shapeString(raw),
                }
            )
        return pl.DataFrame(rows)

    @property
    def index(self) -> pl.DataFrame:
        """현재 공개 Company 구조 인덱스 DataFrame -- 전체 데이터 목차.

        Capabilities:
            - docs sections + finance + report 전체를 하나의 목차로 통합
            - 각 항목의 chapter, topic, label, kind, source, periods, shape, preview 제공
            - sections 메타데이터 + 존재 확인만으로 구성 (파서 미호출, lazy)
            - viewer/렌더러가 소비하는 메타데이터 원천

        AIContext:
            - LLM이 Company 전체 구조를 파악하는 핵심 진입점
            - ask()에서 어떤 데이터를 참조할지 결정하는 기초 정보

        Guide:
            - "전체 목차 보여줘" → c.index
            - "어떤 데이터가 있는지 구조적으로" → c.index

        SeeAlso:
            - topics: topic 단위 요약 (index보다 간결)
            - sections: 전체 sections 지도 (index의 원본)
            - profile: 통합 프로필 접근자

        Returns:
            pl.DataFrame -- 컬럼: chapter, topic, label, kind, source, periods, shape, preview

        Requires:
            데이터: docs/finance/report 중 하나 이상 (자동 다운로드)

        Example::

            c = Company("005930")
            c.index                    # 전체 구조 목차
            c.index.filter(pl.col("source") == "docs")  # docs 항목만

        LLM Specifications:
            AntiPatterns:
                - index 결과 전체를 답변 본문에 dump (50+ 행)
                - chapter / kind 추측 (docs / finance / report 중 source 컬럼 확인 후)
            OutputSchema:
                - chapter : str — I / II / III ... (보고서 장)
                - topic : str — topic 식별자 (show 호출 키)
                - label : str — 사람용 라벨
                - kind : str — table / text / notice
                - source : str — docs / finance / report
                - periods : str — 보유 기간 표기
                - shape : str — "rows × cols"
                - preview : str — 첫 줄 미리보기
            Freshness:
                docs / finance / report 다운로드 시점.
        """
        cacheKey = "_lazyIndex"
        if cacheKey in self._cache:
            return self._cache[cacheKey]

        rows: list[dict[str, Any]] = []

        if not self._hasDocs:
            rows.append(
                {
                    "chapter": "안내",
                    "topic": "docsStatus",
                    "label": "사업보고서",
                    "kind": "notice",
                    "source": "docs",
                    "periods": "-",
                    "shape": "missing",
                    "preview": "현재 사업보고서 부재",
                    "_sortKey": (0, 0),
                }
            )

        rows.extend(self._indexFinanceRows())
        rows.extend(self._indexDocsRows())
        rows.extend(self._indexReportRows(existingTopics={r["topic"] for r in rows}))

        rows.sort(key=lambda r: r.get("_sortKey", (99, 999)))
        for r in rows:
            r.pop("_sortKey", None)

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

    def _indexFinanceRows(self) -> list[dict[str, Any]]:
        from dartlab.providers.dart.docsIndexBuilder import indexFinanceRows

        return indexFinanceRows(self)

    def _indexDocsRows(self) -> list[dict[str, Any]]:
        from dartlab.providers.dart.docsIndexBuilder import indexDocsRows

        return indexDocsRows(self)

    def _indexReportRows(self, *, existingTopics: set[str] | None = None) -> list[dict[str, Any]]:
        from dartlab.providers.dart.docsIndexBuilder import indexReportRows

        return indexReportRows(self, existingTopics=existingTopics)

    @property
    def facts(self) -> pl.DataFrame | None:
        """topic × period 형태의 통합 facts 테이블 (sections + finance + report merge).

        Returns
        -------
        pl.DataFrame | None
            topic : str — 데이터 소스 topic
            period : str — 기간 (예: "2025Q4")
            value : str — 해당 topic/period 의 텍스트 또는 숫자 요약
            데이터 없으면 None.

        LLM Specifications:
            AntiPatterns:
                - facts 결과를 그대로 답변 본문에 dump (수백 행)
                - value 가 텍스트일 때 숫자 계산 시도 (numeric 파싱 별도)
            OutputSchema:
                - topic : str — topic 식별자
                - period : str — 기간 (2025Q4 형식)
                - value : str — 텍스트 또는 숫자 요약
            Freshness:
                sections / finance / report 의 c.update() 시점.
        """
        return self._profileAccessor.facts

    @property
    def retrievalBlocks(self) -> pl.DataFrame | None:
        """원문 markdown 보존 retrieval block DataFrame.

        Capabilities:
            - docs 원문을 markdown 형태 그대로 보존한 검색용 블록
            - 각 블록은 topic/subtopic/period 단위로 분할
            - RAG, 벡터 검색, 원문 참조에 최적화된 포맷

        AIContext:
            - ask()/chat()에서 원문 기반 답변 생성 시 소스로 사용
            - retrieval 기반 컨텍스트 주입의 원천 데이터

        Guide:
            - "원문 검색용 블록" → c.retrievalBlocks
            - "RAG용 데이터" → c.retrievalBlocks

        SeeAlso:
            - contextSlices: retrievalBlocks를 LLM 윈도우에 맞게 슬라이싱한 결과
            - sections: 구조화된 데이터 지도 (retrievalBlocks의 원본)

        Returns:
            pl.DataFrame | None -- 컬럼: topic, subtopic, period, content 등. docs 없으면 None.

        Requires:
            데이터: docs (자동 다운로드)

        Example::

            c = Company("005930")
            c.retrievalBlocks          # 전체 retrieval 블록
        """
        return self._docs.retrievalBlocks

    @property
    def contextSlices(self) -> pl.DataFrame | None:
        """LLM 투입용 context slice DataFrame.

        Capabilities:
            - retrievalBlocks를 LLM 컨텍스트 윈도우에 맞게 슬라이싱
            - 토큰 예산 내에서 최대한 많은 관련 정보를 담는 압축 포맷
            - topic/period 기준 우선순위 정렬

        AIContext:
            - ask()/chat()의 시스템 프롬프트에 직접 주입되는 데이터
            - LLM이 소비하는 최종 형태의 컨텍스트

        Guide:
            - "LLM에 들어가는 컨텍스트" → c.contextSlices
            - "AI가 보는 데이터" → c.contextSlices

        SeeAlso:
            - retrievalBlocks: 슬라이싱 전 전체 retrieval 블록
            - ask: contextSlices를 내부적으로 소비하는 AI 질문 인터페이스

        Returns:
            pl.DataFrame | None -- 슬라이싱된 context 블록. docs 없으면 None.

        Requires:
            데이터: docs (자동 다운로드)

        Example::

            c = Company("005930")
            c.contextSlices            # LLM용 context 슬라이스
        """
        return self._docs.contextSlices

    # ── financeEngine (숫자 재무 데이터) ──

    def _ensureFinanceLoaded(self) -> None:
        """lazy finance: 첫 접근 시 buildTimeseries 실행."""
        if self._financeChecked:
            return
        self._financeChecked = True
        if not self._hasFinanceParquet:
            return
        from dartlab.providers.dart.finance.pivot import buildTimeseries

        try:
            ts = buildTimeseries(self.stockCode)
        except Exception as e:
            # finance parquet 로딩/파싱 실패 → 이유 노출 후 docs fallback 허용.
            # silent 실패 시 show("IS") 가 docs 기반으로 잘못된 결과 반환하는 사례 방지.
            import warnings

            warnings.warn(
                f"finance parquet 로딩 실패 ({self.stockCode}): {type(e).__name__}: {e}. "
                f"docs fallback 으로 전환됩니다 — 수치 정합성이 떨어질 수 있습니다.",
                stacklevel=2,
            )
            ts = None
        if ts is not None:
            self._cache["_finance_q_CFS"] = ts
        else:
            self._hasFinanceParquet = False

    def _getFinanceBuild(self, period: str = "q", fsDivPref: str = "CFS"):
        """finance parquet 시계열 빌드 (캐싱).

        Args:
            period: "q" (분기별 standalone), "y" (연도별), "cum" (분기별 누적).
            fsDivPref: "CFS" (연결) 또는 "OFS" (별도).
        """
        cacheKey = f"_finance_{period}_{fsDivPref}"
        if cacheKey in self._cache:
            return self._cache[cacheKey]

        from dartlab.providers.dart.finance.pivot import (
            _aggregateAnnual,
            _aggregateCumulative,
            buildTimeseries,
        )

        if period == "q":
            result = buildTimeseries(self.stockCode, fsDivPref=fsDivPref)
        else:
            qResult = self._getFinanceBuild("q", fsDivPref=fsDivPref)
            if qResult is None:
                result = None
            else:
                series, periods = qResult
                if period == "y":
                    result = _aggregateAnnual(series, periods)
                elif period == "cum":
                    result = _aggregateCumulative(series, periods)
                else:
                    result = qResult
        self._cache[cacheKey] = result
        return result

    def _getRatiosInternal(self, fsDivPref: str = "CFS"):
        """내부용 재무비율 계산 (deprecation 없음)."""
        cacheKey = f"_ratios_{fsDivPref}"
        if cacheKey in self._cache:
            return self._cache[cacheKey]
        from dartlab.analysis.financial.ratios import calcRatios

        archetypeOverride = _ratioArchetypeOverrideForIndustryGroup(getattr(self.sector, "industryGroup", None))
        ts = self._getFinanceBuild("q", fsDivPref)
        result = None
        if ts is not None:
            series, _ = ts
            result = calcRatios(series, archetypeOverride=archetypeOverride)

        if _shouldFallbackToAnnualRatios(result, archetypeOverride):
            annual = self._getFinanceBuild("y", fsDivPref)
            if annual is not None:
                annualSeries, _ = annual
                annualResult = calcRatios(annualSeries, annual=True, archetypeOverride=archetypeOverride)
                if _ratioResultHasHeadlineSignal(annualResult):
                    result = annualResult

        self._cache[cacheKey] = result
        return result

    def _buildRatios(self) -> pl.DataFrame | None:
        """[INTERNAL] 재무비율 DataFrame 빌더.

        사용자는 ``c.show("ratios")`` 호출. show() 가 finance topic dispatch 에서
        이 빌더를 호출.
        """
        from dartlab.providers.dart.financeStatementBuilder import buildRatios

        return buildRatios(self)

    def _buildFinanceSeries(self, *, freq: str = "Q", scope: str = "consolidated"):
        """[INTERNAL] finance series-tuple 빌더.

        사용자는 직접 호출하지 않는다. 사용자 진입점은 ``c.show("IS", freq=, scope=)``
        / ``c.select("IS", [...], freq=, scope=)`` 만이다 (api-contract).

        analysis / forecast / valuation / credit / story 등 calc 모듈이
        ``(series, periods)`` 튜플 형태가 필요할 때만 호출한다.

        Args:
            freq: ``"Q"`` (분기, 기본) / ``"Y"`` (연간) / ``"YTD"`` (누적).
            scope: ``"consolidated"`` (연결, 기본) / ``"separate"`` (별도).

        Returns:
            ``(series, periods)`` 또는 None.
        """
        from dartlab.providers.dart.financeStatementBuilder import buildFinanceSeries

        return buildFinanceSeries(self, freq=freq, scope=scope)

    # c.SCE / c.sceMatrix / c.ratios / c.ratioSeries property 제거 (Plan v10 P1).
    # 사용자는 c.show("SCE") / c.show("sceMatrix") / c.show("ratios") /
    # c.show("ratioSeries") 사용. ratioSeries 는 dict 구조라 show 에서 dict topic 으로 처리.

    # ── 섹터 분류 ──

    @property
    def sector(self):
        """WICS 투자 섹터 분류 (KIND 업종 + 키워드 기반).

        Capabilities:
            - WICS 11대 섹터 + 하위 산업그룹 자동 분류
            - KIND 업종명 + 주요제품 키워드 기반 매칭
            - override 테이블 우선 → 키워드 → 업종명 순 fallback

        Returns:
            SectorInfo (sector, industryGroup, confidence, source).

        Requires:
            데이터: KIND 상장사 목록 (자동 로드)

        Example::

            c = Company("005930")
            c.sector              # SectorInfo(IT/반도체와반도체장비, conf=1.00, src=override)
            c.sector.sector       # Sector.IT
            c.sector.industryGroup  # IndustryGroup.SEMICONDUCTOR

        AIContext:
            - 섹터 분류 결과로 동종업계 비교, 섹터 파라미터 자동 선택
            - analysis/valuation에서 섹터별 벤치마크 기준으로 활용

        Guide:
            - "이 회사 어떤 섹터야?" → c.sector
            - "업종 분류" → c.sector

        SeeAlso:
            - sectorParams: 섹터별 밸류에이션 파라미터 (할인율, PER 등)
            - rank: 섹터 내 규모 순위
            - insights: 섹터 기준 등급 평가

        LLM Specifications:
            AntiPatterns:
                - sector 결과를 sector 컬럼 (str) 만 인용 (industryGroup 도 함께)
                - confidence 무시하고 단정 (1.0 = override, 0.5~0.9 = 키워드 매칭)
            OutputSchema:
                - sector : Sector enum — IT / Materials / Industrials / ...
                - industryGroup : IndustryGroup enum — SEMICONDUCTOR / AUTOMOBILE / ...
                - confidence : float — 0.0~1.0 (1.0 = override, 0.5+ = 키워드 매칭)
                - source : str — override / keyword / industry
            Freshness:
                KIND 상장사 목록 시점.
            TargetMarkets:
                - KR
        """
        cacheKey = "_sector"
        if cacheKey in self._cache:
            return self._cache[cacheKey]
        from dartlab.industry import classify

        kindDf = getKindList()
        row = kindDf.filter(pl.col("종목코드") == self.stockCode)
        kindIndustry = row["업종"][0] if row.height > 0 and "업종" in kindDf.columns else None
        mainProducts = row["주요제품"][0] if row.height > 0 and "주요제품" in kindDf.columns else None
        result = classify(self.corpName or "", kindIndustry, mainProducts)
        self._cache[cacheKey] = result
        return result

    @property
    def sectorParams(self):
        """현재 종목의 섹터별 밸류에이션 파라미터.

        Capabilities:
            - 섹터별 할인율, 성장률, PER 멀티플 제공
            - 섹터 분류 결과에 연동된 파라미터 자동 선택

        Returns:
            SectorParams (discountRate, growthRate, perMultiple, ...).

        Requires:
            데이터: sector 분류 결과 (자동 연산)

        Example::

            c = Company("005930")
            c.sectorParams.perMultiple   # 15
            c.sectorParams.discountRate  # 13.0

        AIContext:
            - valuation()에서 DCF 할인율, 성장률 자동 적용
            - 섹터 특성 반영된 밸류에이션 파라미터

        Guide:
            - "이 섹터 할인율은?" → c.sectorParams.discountRate
            - "PER 멀티플" → c.sectorParams.perMultiple

        SeeAlso:
            - sector: 섹터 분류 정보 (sectorParams의 기반)
            - valuation: 밸류에이션 (sectorParams를 내부적으로 소비)
        """
        cacheKey = "_sectorParams"
        if cacheKey in self._cache:
            return self._cache[cacheKey]
        from dartlab.industry import getParams

        result = getParams(self.sector)
        self._cache[cacheKey] = result
        return result

    # ── 규모 랭크 ──

    @property
    def rank(self):
        """전체 시장 + 섹터 내 규모 순위 (매출/자산/성장률).

        스냅샷이 없으면 None 반환. buildSnapshot()으로 사전 빌드 필요.

        Capabilities:
            - 전체 시장 내 매출/자산 순위
            - 섹터 내 상대 순위
            - 매출 성장률 기반 규모 분류 (large/mid/small)

        Returns:
            RankInfo 또는 스냅샷 미빌드 시 None.

        Requires:
            데이터: buildSnapshot() 사전 실행 필요

        Example::

            from dartlab.analysis.financial.insight import buildSnapshot
            buildSnapshot()

            c = Company("005930")
            c.rank                    # RankInfo(삼성전자, 매출 2/2192, 섹터 2/467, large)
            c.rank.revenueRank        # 2
            c.rank.revenueRankInSector # 2
            c.rank.sizeClass          # "large"

        AIContext:
            - 시장/섹터 내 상대 위치 파악 — 피어 비교 분석의 기초
            - sizeClass로 대형/중형/소형주 분류

        Guide:
            - "이 회사 순위는?" → c.rank
            - "시장에서 몇 등이야?" → c.rank.revenueRank
            - "대형주야?" → c.rank.sizeClass

        SeeAlso:
            - sector: 섹터 분류 (rank의 기준 그룹)
            - insights: 종합 등급 평가

        LLM Specifications:
            AntiPatterns:
                - rank 단독 노출 (sizeClass + sector 함께)
                - rank 결과를 절대 평가로 인용 (시장 전체 / 섹터 내 모두 표시)
            OutputSchema:
                - revenueRank : int — 매출 기준 시장 순위
                - revenueRankInSector : int — 매출 기준 섹터 순위
                - sizeClass : str — large / mid / small
                - sectorTotal : int — 섹터 종목 수
            Freshness:
                scan 데이터 기준 — 분기 마감 후 갱신.
            TargetMarkets:
                - KR
        """
        cacheKey = "_rank"
        if cacheKey in self._cache:
            return self._cache[cacheKey]
        import importlib

        getRank = importlib.import_module("dartlab.scan.screen.rank").getRank
        result = getRank(self.stockCode)
        self._cache[cacheKey] = result
        return result

    # insights는 analysis 내부 — c.analysis("financial", "종합평가")로 접근

    def audit(self):
        """감사 리스크 종합 분석.

        Capabilities:
            - 감사의견 추이 (적정/한정/부적정/의견거절)
            - 감사인 변경 이력 + 사유
            - 계속기업 불확실성 플래그
            - 핵심감사사항 (KAM) 추출
            - 내부회계관리제도 검토의견

        Args:
            없음 (self 바인딩).

        Returns
        -------
        dict
            opinion : str — 감사의견 ("적정", "한정", "부적정", "의견거절")
            auditorChanges : list[dict] — 감사인 변경 이력 (year, from, to, reason)
            goingConcern : bool — 계속기업 불확실성 존재 여부
            kam : list[str] — 핵심감사사항 목록
            internalControl : str — 내부회계관리제도 검토의견

        Requires:
            데이터: docs + report (자동 다운로드)

        Example::

            c = Company("005930")
            c.audit()

        AIContext:
            - 감사 리스크 종합 평가 — 투자 의사결정의 핵심 안전장치
            - 감사의견 변경, 계속기업 불확실성은 최고 경고 수준

        Guide:
            - "감사의견 확인" → c.audit()
            - "감사인 바뀌었어?" → c.audit()["auditorChanges"]
            - "계속기업 의문은?" → c.audit()["goingConcern"]

        SeeAlso:
            - governance: 지배구조 분석 (감사위원회 구성 포함)
            - insights: 종합 등급 (감사 리스크도 반영)
            - story: 재무정합성 섹션에서 감사 결과 활용

        LLM Specifications:
            AntiPatterns:
                - "한정/부적정" 같은 무거운 결과를 답변 본문에 단정 노출 (출처 + 연도 함께)
                - audit() 결과를 매 분석마다 호출 (캐시 — 1 회면 충분)
            OutputSchema:
                - opinion : str — 감사의견 (적정 / 한정 / 부적정 / 의견거절)
                - auditorChanges : list[dict] — 감사인 변경 이력 (year, from, to, reason)
                - goingConcern : bool — 계속기업 불확실성 존재 여부
                - kam : list[str] — 핵심감사사항
                - internalControl : str — 내부회계관리제도 검토의견
            Freshness:
                report 데이터 기준 — 정기보고서 마감 후 30~45 일.
        """
        from dartlab.analysis.financial.insight.pipeline import analyzeAudit

        return analyzeAudit(self)

    @property
    def market(self) -> str:
        """시장 코드 (DART 제공자는 항상 KR).

        SeeAlso:
            - currency: 통화 코드

        Returns:
            str — "KR".

        Example::

            c = Company("005930")
            c.market  # "KR"
        """
        return "KR"

    @property
    def fiscalYearEnd(self) -> str:
        """회계연도 종료 월-일 (한국 종목은 12-31 표준).

        EDGAR 와의 fiscal year-end 비교를 위한 metadata.
        한국 회계 관습 상 거의 모든 상장사가 12월말 결산 — 상수 반환.

        Returns:
            "12-31".
        """
        return "12-31"

    @property
    def currency(self) -> str:
        """통화 코드 (DART 제공자는 항상 KRW).

        SeeAlso:
            - market: 시장 코드

        Returns:
            str — "KRW".

        Example::

            c = Company("005930")
            c.currency  # "KRW"
        """
        return "KRW"

    # ── network (관계 지도) ──────────────────────────────────

    # ── scan-related 5 진입점 (network/governance/workforce/capital/debt) ──
    # 구현은 dartlab.providers.dart.scanAggregator 모듈에 위임. facade 는
    # docstring + thin delegate 만 유지.

    def network(self, view: str | None = None, *, hops: int = 1):
        """관계 네트워크 (지분출자 + 그룹 계열사 지도).

        Capabilities:
            - 그룹 계열사 목록 (members)
            - 출자/피출자 연결 + 지분율 (edges)
            - 순환출자 경로 탐지 (cycles)
            - ego 서브그래프 (peers)
            - 인터랙티브 네트워크 시각화 (브라우저)

        Args:
            view: None이면 시각화(NetworkView), "members"/"edges"/"cycles"/"peers"이면 DataFrame.
            hops: peers/시각화 뷰에서 홉 수.

        Returns:
            NetworkView (view=None) 또는 DataFrame (view 지정 시). 데이터 없으면 None.

        Requires:
            데이터: DART 대량보유/임원 공시 (자동 수집)

        Example::

            c = Company("005930")
            c.network()              # → NetworkView (.show()로 브라우저)
            c.network().show()       # 브라우저 오픈
            c.network("members")     # 같은 그룹 계열사 DataFrame
            c.network("edges")       # 출자/지분 연결 DataFrame
            c.network("cycles")      # 순환출자 경로 DataFrame
            c.network("peers")       # 이 회사 중심 서브그래프 DataFrame

        AIContext:
            - 그룹 계열사/출자 구조 파악 — 지배구조 분석의 기초 데이터
            - 순환출자 탐지로 거버넌스 리스크 감지

        Guide:
            - "계열사 관계도" → c.network() 또는 c.network().show()
            - "같은 그룹 계열사" → c.network("members")
            - "출자/지분 구조" → c.network("edges")
            - "순환출자 있어?" → c.network("cycles")

        SeeAlso:
            - governance: 이사회/감사위원/최대주주 분석
            - capital: 주주환원 분석

        LLM Specifications:
            AntiPatterns:
                - view 미지정 시 NetworkView 객체 — 답변 본문에 dump X (.show() 로 별도)
                - hops > 2 (네트워크 폭주, 메모리 부담)
                - "순환출자 = 분식" 단정 X (한국 그룹 일반)
            OutputSchema:
                - view="members": 종목코드 / 종목명 / 그룹 / 지분율
                - view="edges": from / to / 지분율 / 출자유형
                - view="cycles": cycle 경로 (list[stockCode])
                - view="peers": ego 서브그래프 노드
            Freshness:
                대량보유/임원 공시 기준.
        """
        from dartlab.providers.dart.scanAggregator import buildScanNetwork

        return buildScanNetwork(self, view, hops=hops)

    def governance(self, view: str | None = None) -> pl.DataFrame | None:
        """지배구조 분석 (이사회, 감사위원, 최대주주).

        Capabilities:
            - 사외이사 비율 + 감사위원회 구성
            - 최대주주 지분율 + 특수관계인
            - 시장 전체 거버넌스 횡단 비교

        Args:
            view: None → 이 회사 행, "all" → 전체, "market" → 시장별 요약.

        Returns
        -------
        pl.DataFrame | None
            종목코드 : str — 6자리 종목코드
            종목명 : str — 회사명
            최대주주지분율 : float — 최대주주 + 특수관계인 지분율 (%)
            사외이사비율 : float — 사외이사 비율 (%)
            감사위원회 : str — 감사위원회 설치 여부
            종합점수 : float — 거버넌스 종합 점수 (100점 만점)
            등급 : str — A/B/C/D/E 등급
            데이터 없으면 None.

        Requires:
            데이터: DART 정기보고서 (자동 수집)

        Example::

            c = Company("005930")
            c.governance()           # 삼성전자 거버넌스
            c.governance("all")      # 전체 상장사

        AIContext:
            - 지배구조 리스크 평가 — 사외이사/감사위원/최대주주 정량 데이터
            - 시장 횡단 비교로 상대적 거버넌스 수준 판단

        Guide:
            - "지배구조 분석" → c.governance()
            - "사외이사 비율은?" → c.governance()
            - "전체 상장사 거버넌스 비교" → c.governance("all")

        SeeAlso:
            - network: 출자/계열사 관계 (거버넌스의 다른 관점)
            - audit: 감사 리스크 (감사위원회와 연관)

        LLM Specifications:
            AntiPatterns:
                - view="all" 호출 후 전체 결과를 답변 본문에 dump (수천 행)
                - 종합점수 단독 노출 (사외이사 비율 + 최대주주 지분율 함께)
            OutputSchema:
                - 종목코드 : str — 6 자리
                - 종목명 : str
                - 최대주주지분율 : float — % (특수관계인 포함)
                - 사외이사비율 : float — %
                - 감사위원회 : str — 설치 여부
                - 종합점수 : float — 100 점 만점
                - 등급 : str — A/B/C/D/E
            Freshness:
                정기보고서 마감 후 30~45 일.
            TargetMarkets:
                - KR (DART)
        """
        from dartlab.providers.dart.scanAggregator import buildScanGovernance

        return buildScanGovernance(self, view)

    def workforce(self, view: str | None = None) -> pl.DataFrame | None:
        """인력/급여 분석 (직원수, 평균급여, 근속연수).

        Capabilities:
            - 직원수 + 정규직/비정규직 비율
            - 평균 급여 + 1인당 매출
            - 평균 근속연수
            - 시장 전체 인력 횡단 비교

        Args:
            view: None → 이 회사 행, "all" → 전체, "market" → 시장별 요약.

        Returns:
            DataFrame 또는 데이터 없으면 None.

        Requires:
            데이터: DART 정기보고서 (자동 수집)

        Example::

            c = Company("005930")
            c.workforce()            # 삼성전자 인력 현황
            c.workforce("all")       # 전체 상장사

        AIContext:
            - 인력 효율성/근무환경 정량 평가 — 1인당 매출, 급여 수준 비교
            - 시장 횡단 비교로 인적자원 경쟁력 판단

        Guide:
            - "직원 현황" → c.workforce()
            - "평균 급여는?" → c.workforce()
            - "전체 상장사 인력 비교" → c.workforce("all")

        SeeAlso:
            - governance: 이사회/감사위원 구성 (인력의 다른 관점)
            - show: c.show("employee")로 docs 기반 직원 상세

        LLM Specifications:
            AntiPatterns:
                - 평균 급여 단독 노출 (1 인당 매출 + 평균 근속 함께)
                - "고임금 = 위험" 단정 X (생산성 함께)
            OutputSchema:
                - 종목코드 : str
                - 직원수 : int — 정규/비정규 합계
                - 평균근속 : float — 년
                - 1인당매출 : float — 억원
            Freshness:
                정기보고서 마감 후 30~45 일.
            TargetMarkets:
                - KR
        """
        from dartlab.providers.dart.scanAggregator import buildScanWorkforce

        return buildScanWorkforce(self, view)

    def capital(self, view: str | None = None) -> pl.DataFrame | None:
        """주주환원 분석 (배당, 자사주, 총환원율).

        Capabilities:
            - 배당수익률 + 배당성향 추이
            - 자사주 매입/소각 이력
            - 총주주환원율 (배당 + 자사주)
            - 시장 전체 주주환원 횡단 비교

        Args:
            view: None → 이 회사 행, "all" → 전체, "market" → 시장별 요약.

        Returns
        -------
        pl.DataFrame | None
            종목코드 : str — 6자리 종목코드
            종목명 : str — 회사명
            배당수익률 : float — 배당수익률 (%)
            배당성향 : float — 배당성향 (%)
            자사주매입 : int — 자사주 매입 주수 (주)
            총환원율 : float — (배당 + 자사주) / 시가총액 (%)
            분류 : str — 환원형/중립/희석형
            데이터 없으면 None.

        Requires:
            데이터: DART 정기보고서 (자동 수집)

        Example::

            c = Company("005930")
            c.capital()              # 삼성전자 주주환원
            c.capital("all")         # 전체 상장사

        AIContext:
            - 주주환원 정책 평가 — 배당수익률/성향/자사주 정량 데이터
            - 시장 횡단 비교로 상대적 환원 수준 판단

        Guide:
            - "배당 정보" → c.capital() 또는 c.show("dividend")
            - "주주환원율은?" → c.capital()
            - "전체 상장사 배당 비교" → c.capital("all")

        SeeAlso:
            - show: c.show("dividend")로 docs 기반 배당 상세
            - sceMatrix: 자본변동표 (배당/자사주가 자본에 미치는 영향)
            - debt: 부채 구조 (자본 정책의 다른 면)

        LLM Specifications:
            AntiPatterns:
                - 배당수익률 단독 노출 (배당성향 + 자사주 함께)
                - "환원형" 단정 X (총환원율 + 분류 + 시계열 함께)
            OutputSchema:
                - 종목코드 : str
                - 배당수익률 : float — %
                - 배당성향 : float — %
                - 자사주매입 : int — 주
                - 총환원율 : float — % ((배당 + 자사주) / 시가총액)
                - 분류 : str — 환원형 / 중립 / 희석형
            Freshness:
                정기보고서 마감 후 30~45 일.
            TargetMarkets:
                - KR
        """
        from dartlab.providers.dart.scanAggregator import buildScanCapital

        return buildScanCapital(self, view)

    def debt(self, view: str | None = None) -> pl.DataFrame | None:
        """부채 구조 분석 (차입금, 부채비율, 만기 구조).

        Capabilities:
            - 총차입금 + 순차입금 규모
            - 부채비율 + 차입금의존도
            - 단기/장기 차입금 비율
            - 시장 전체 부채 구조 횡단 비교

        Args:
            view: None → 이 회사 행, "all" → 전체, "market" → 시장별 요약.

        Returns
        -------
        pl.DataFrame | None
            종목코드 : str — 6자리 종목코드
            종목명 : str — 회사명
            부채비율 : float — 부채비율 (%)
            차입금의존도 : float — 차입금의존도 (%)
            ICR : float — 이자보상배율 (배)
            위험등급 : str — 안전/주의/경고/위험
            데이터 없으면 None.

        Requires:
            데이터: DART 정기보고서 (자동 수집)

        Example::

            c = Company("005930")
            c.debt()                 # 삼성전자 부채 구조
            c.debt("all")            # 전체 상장사

        AIContext:
            - 부채 구조/건전성 정량 평가 — 차입금 의존도, 만기 구조
            - 시장 횡단 비교로 상대적 재무 안정성 판단

        Guide:
            - "부채 구조 분석" → c.debt()
            - "부채비율은?" → c.debt() 또는 c.show("ratios")
            - "전체 상장사 부채 비교" → c.debt("all")

        SeeAlso:
            - BS: 재무상태표 (부채 원본 데이터)
            - ratios: 재무비율 (부채비율 포함)
            - capital: 주주환원 (자본 정책의 다른 면)

        LLM Specifications:
            AntiPatterns:
                - 부채비율 단독 노출 (ICR + 의존도 함께)
                - "위험" 단정 X (위험등급 + 절대값 + peer median 함께)
            OutputSchema:
                - 종목코드 : str
                - 부채비율 : float — %
                - 차입금의존도 : float — %
                - ICR : float — 배 (이자보상배율)
                - 위험등급 : str — 안전 / 주의 / 경고 / 위험
            Freshness:
                정기보고서 마감 후 30~45 일.
            TargetMarkets:
                - KR
        """
        from dartlab.providers.dart.scanAggregator import buildScanDebt

        return buildScanDebt(self, view)

    @property
    def quant(self):
        """주가 기술적 분석 (31축). 기술지표/벤치마크/팩터/감성/최적화. dual access.

        Guide:
            - "차트 판단" → c.quant("판단")
            - "모멘텀" → c.quant("모멘텀")
            - "지표 DF" → c.quant("지표")
            - "베타" → c.quant("베타")
            - "섹터 베타" → c.quant("베타", benchmarkMode="sector")

        실제 동작은 ``_quantImpl`` 참조.

        Returns
        -------
        CallableAccessor
            dual-access proxy. 호출 시 ``_quantImpl`` 이 axis 따라
            ``pl.DataFrame`` (지표 시계열) 또는 dict (판단/팩터 등) 반환.
            상세는 ``_quantImpl`` docstring.
        """
        from dartlab.core.dualAccess import CallableAccessor

        if "_quantAccessor" not in self._cache:
            self._cache["_quantAccessor"] = CallableAccessor(self._quantImpl, name="quant")
        return self._cache["_quantAccessor"]

    def _quantImpl(self, axis=None, *, overrides: dict | None = None, metric=None, **kwargs):
        """주가 기술적 분석 — 30축 (내부 구현).

        Args:
            axis: 축 이름. None이면 30축 가이드 DataFrame.
                  (Phase 8 A1: 기존 `metric=` 은 호환 alias)
            overrides: 기술 분석 파라미터 교체. 키: window/threshold/period/benchmark.
            **kwargs: 축별 추가 파라미터.

        Returns:
            axis=None → DataFrame (30축 가이드)
            axis="종합" → dict (verdict, RSI, ADX, SMA 등)
            axis="지표" → DataFrame (45개 지표)

        Guide:
            When: 주가 기반 기술적 판단이 필요할 때.
            How: axis 로 분석 영역 지정. 무인자 = 가이드.
            Verified:
                - quant("판단") → RSI/ADX/MACD/볼린저/상대강도 + 종합 판정 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)

        LLM Specifications:
            AntiPatterns:
                - 영문 axis ("momentum") 사용 (실제는 한글 "모멘텀")
                - metric= 인자 사용 (Phase 8 deprecated alias — axis= 사용)
                - overrides 키 추측 (window/threshold/period/benchmark 만)
            OutputSchema:
                - axis="판단": dict — verdict (str) + RSI/ADX/SMA/MACD 등 핵심 지표
                - axis="지표": DataFrame — 45 개 기술 지표 컬럼
                - axis="베타": dict — beta 값 + benchmark + window
            Freshness:
                price 데이터 기준 — T+1 (전일 종가).
        """
        from dartlab.core.overrides import validateOverrides
        from dartlab.quant import Quant

        if axis is None and metric is not None:
            axis = metric
        clean = validateOverrides(overrides, engine="quant")
        merged = {**clean, **kwargs}
        q = Quant()
        if axis is None:
            return q()
        result = q(axis, self.stockCode, **merged)
        if isinstance(result, dict):
            from dartlab.core.overrides import buildAssumptions

            enriched = {
                **result,
                **{k: v for k, v in merged.items() if k in ("window", "threshold", "period", "benchmark")},
            }
            assumptions = buildAssumptions(enriched, engine="quant", overrides=clean)
            if assumptions:
                result.setdefault("assumptions", assumptions)
        return result

    def macro(self, axis=None, target=None, *, overrides: dict | None = None, **kwargs):
        """시장 매크로 (6막 인과 — 사이클/재고/기업/정책/유동성/심리/시나리오). KR 자동 위임.

        Returns
        -------
        pl.DataFrame | dict
            axis=None: 가이드 DataFrame (axis/label/description/example/group).
            axis 지정: dict — 축별 매크로 분석 결과 (indicators, narrative 포함).

        Guide:
            When: 거시경제 환경·사이클 판단이 필요할 때.
            How: axis 로 분석 영역 지정. 무인자 = 가이드.
            - "매크로" → c.macro()
            - "경기 사이클" → c.macro("사이클")
            - "위기 진단" → c.macro("위기")
            - "2008 시나리오" → c.macro("시나리오", "2008 금융위기")
            Verified:
                - macro("사이클") → CLI + 사분면 + 금리 + 유동성 + 심리 6축 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)
                - macro + analysis → 경제 고려한 종목 분석 (observed via thesis ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)

        LLM Specifications:
            AntiPatterns:
                - axis 추측 (한글 — 사이클 / 위기 / 시나리오 / 유동성 / 심리)
                - 종목 매크로 = 시장 매크로 혼동 (이건 c.macro = 시장 KR 자동)
            OutputSchema:
                - axis="사이클": dict — quadrant + indicators + narrative
                - axis="시나리오": dict — historical analogue + projection
                - axis 미지정: 가이드 DataFrame
            Freshness:
                ECOS / FRED 갱신 주기 (월 / 분기).
        """
        from dartlab.macro import Macro

        return Macro()(axis, target, market="KR", overrides=overrides, **kwargs)

    # ── Phase 10 H2: story 2차 가공 직접 노출 (AI tool 자동 수집 대상) ──

    def causalWeights(self) -> list[dict]:
        """6막 인과 가중치 — 수익구조→수익성→현금흐름→자금조달→자산배치→가치평가 amplify/dampen/neutral.

        Guide:
            - "인과 체인" → c.causalWeights()
            - "어느 막이 약해" → 결과의 direction='dampen' 필터

        Returns:
            list[dict] — from_act/to_act/metric_from/metric_to/delta_from/delta_to/weight/direction

        LLM Specifications:
            AntiPatterns:
                - direction 단독 인용 (weight + metric 함께)
                - 6 막 인과는 종목 분석 한정 — 매크로 / 산업 분석에는 부적합
            OutputSchema:
                - from_act : str — 출발 막
                - to_act : str — 도착 막
                - metric_from : str — 출발 지표
                - metric_to : str — 도착 지표
                - delta_from / delta_to : float — 변화율
                - weight : float — 영향 강도
                - direction : str — amplify / dampen / neutral
            Freshness:
                finance 시계열 시점.
        """
        import importlib

        buildCausalWeights = importlib.import_module("dartlab.story.narrative").buildCausalWeights

        return buildCausalWeights(self, {})

    def valuationImpact(self) -> dict:
        """인과 체인에서 DCF override 힌트 — narrative → 숫자 피드백.

        Guide:
            - "WACC 조정 어떻게" → c.valuationImpact()['waccAdj']
            - "override 근거" → c.valuationImpact()['narrative']

        Returns:
            dict — terminalGrowthAdj/waccAdj/narrative/overrides

        LLM Specifications:
            AntiPatterns:
                - waccAdj 단독 노출 (narrative 근거 함께)
                - DCF 직접 override 적용 X (overrides 는 힌트, 사용자 판단 후 적용)
            OutputSchema:
                - terminalGrowthAdj : float — terminal growth 가산 (% 포인트)
                - waccAdj : float — WACC 가산 (% 포인트)
                - narrative : str — 조정 근거 (인과 체인)
                - overrides : dict — analysis(valuation, overrides=...) 호출용
            Freshness:
                story 인과 체인 기준 — finance 데이터 시점.
        """
        import importlib

        _narrative = importlib.import_module("dartlab.story.narrative")
        buildCausalWeights = _narrative.buildCausalWeights
        buildValuationImpact = _narrative.buildValuationImpact

        chains = buildCausalWeights(self, {})
        return buildValuationImpact(chains)

    def storyTree(self, *, basePeriod: str | None = None) -> dict:
        """Damodaran 3P — possible(낙관)/plausible(중도)/probable(보수) 3 DCF + 민감도.

        Guide:
            - "3 시나리오 가치" → c.storyTree()
            - "서사 민감도" → c.storyTree()['summary']['spreadPct']

        Returns:
            dict — possible/plausible/probable + summary {min/max/spread/spreadPct/mean}

        LLM Specifications:
            AntiPatterns:
                - 단일 시나리오 (예: probable) 만 인용 (3 시나리오 + 분포 함께)
                - spreadPct 가 작으면 "확실" 단정 X (가정 강도와 함께)
            OutputSchema:
                - possible : dict — 낙관 시나리오 DCF 결과
                - plausible : dict — 중도 시나리오
                - probable : dict — 보수 시나리오
                - summary : dict — min / max / spread / spreadPct / mean
            Freshness:
                finance 시계열 시점.
        """
        import importlib

        buildStoryTree = importlib.import_module("dartlab.story.storyTree").buildStoryTree

        return buildStoryTree(self, basePeriod=basePeriod)

    def narrativeDiff(self, *, claims: list[str] | None = None) -> list[dict]:
        """각 claim 제거 시 dFV 변화 — Thought Anchors 기반 정량 기여도.

        Guide:
            - "가치 기여도" → c.narrativeDiff()
            - "낮은WACC 기여 몇%" → 결과 필터 claim='낮은WACC'

        Returns:
            list[dict] — claim/dFV_neutral/delta_abs/delta_pct/contribution

        LLM Specifications:
            AntiPatterns:
                - contribution 단독 인용 (delta_abs + delta_pct 함께)
                - claim 추측 (default 또는 명시 list 만)
            OutputSchema:
                - claim : str — narrative claim 식별자
                - dFV_neutral : float — 중립 시나리오 가치
                - delta_abs : float — claim 제거 시 절대 변화
                - delta_pct : float — % 변화
                - contribution : float — 기여도 (정규화)
            Freshness:
                story 인과 체인 시점.
        """
        import importlib

        computeImpact = importlib.import_module("dartlab.story.narrativeDiff").computeImpact

        return computeImpact(self, claims=claims)

    def industry(self) -> dict | None:
        """이 회사의 밸류체인 산업 내 위치를 분석한다.

        Returns:
            dict | None: 산업 내 위치 정보.
                chainId, chainName, stage, stageLabel, confidence, matches, products, peers.
                매칭 실패 시 None.

        Example::

            c = Company("005930")
            pos = c.industry()
            # {'chainId': 'semiconductor', 'stage': 'fab', 'stageLabel': '전공정(FAB)', ...}

        LLM Specifications:
            AntiPatterns:
                - sector 와 industry 혼동 (sector = 11 대 분류, industry = 가치 사슬 위치)
                - peers 추측 (industry().peers 가 실제 매칭된 종목)
                - confidence 무시하고 단정 (낮으면 매칭 신뢰도 낮음)
            OutputSchema:
                - chainId : str — 산업 체인 ID (semiconductor / automobile / ...)
                - chainName : str — 한글 산업명
                - stage : str — upstream / midstream / downstream / fab / equipment / ...
                - stageLabel : str — 한글 단계 레이블
                - confidence : float — 0.0~1.0 매칭 신뢰도
                - peers : list[str] — 같은 stage 종목코드
            Freshness:
                산업 지도 정의 시점 — 운영자 수동 업데이트.
        """
        from dartlab.industry.calcs.companyCalcs import calcChainPosition

        return calcChainPosition(self)

    def view(self, *, port: int = 8400) -> None:
        """브라우저에서 공시 뷰어를 엽니다.

        Capabilities:
            - 로컬 서버 기반 공시 뷰어 실행
            - 브라우저에서 sections/index 탐색

        Args:
            port: 로컬 서버 포트. 기본 8400.

        Returns:
            None

        Requires:
            데이터: HuggingFace docs parquet (자동 다운로드)

        Example::

            c = Company("005930")
            c.view()

        AIContext:
            - 시각적 탐색 인터페이스 — 사용자가 브라우저에서 직접 데이터 탐색

        Guide:
            - "공시 뷰어 열어줘" → c.view()
            - "브라우저에서 보기" → c.view()

        SeeAlso:
            - index: 뷰어가 소비하는 메타데이터 (프로그래밍 접근)
            - sections: 뷰어의 원본 데이터
        """
        from dartlab.core.viewer import launchViewer

        launchViewer(self.stockCode, port=port)

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
        """LLM에게 이 기업에 대해 질문.

        Capabilities:
            - 엔진 계산 결과를 컨텍스트로 조립하여 LLM에 전달
            - 질문 분류 기반 분석 패키지 자동 선택 (financial, valuation, risk 등)
            - 멀티 provider 지원 (openai, ollama, codex 등)
            - 스트리밍 응답 지원

        AIContext:
            AI가 분석 전 과정을 주도. dartlab 엔진(analysis, scan, gather 등)을
            도구로 호출하여 데이터 수집, 계산, 판단, 해석을 수행.

        Args:
            question: 질문 텍스트.
            include: 포함할 분석 패키지 목록. None이면 자동 선택.
            exclude: 제외할 분석 패키지 목록.
            provider: LLM provider 이름 (openai, ollama, codex 등). None이면 기본값.
            model: 모델명. None이면 provider 기본값.
            stream: True면 스트리밍 제너레이터 반환.
            reflect: True면 답변 후 자기 평가 수행.
            **kwargs: provider별 추가 옵션.

        Returns:
            str -- LLM 응답 텍스트. stream=True면 Generator[str].

        Requires:
            API 키: LLM provider API 키 (OPENAI_API_KEY 등)

        Example::

            c = Company("005930")
            c.ask("영업이익률 추세는?")
            c.ask("핵심 리스크 3가지", provider="codex")

            # 스트리밍
            for chunk in c.ask("배당 분석해줘", stream=True):
                print(chunk, end="")

        Guide:
            - "영업이익률 분석해줘" → c.ask("영업이익률 추세는?")
            - "AI한테 질문하고 싶어" → c.ask("질문")
            - "스트리밍으로 답변받기" → c.ask("질문", stream=True)

        SeeAlso:
            - chat: 에이전트 모드 (tool calling 기반 심화 분석)
            - ask: AI 종합 분석 (자연어 대화)
            - story: AI 없는 데이터 검토서
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

    def calendar(self, *, horizonDays: int = 30) -> "pl.DataFrame":
        """다가오는 정기공시 catalyst 일정 추론 (Korea 시장).

        본 회사 disclosure history 를 수집해 providers/dart/calendar 에 위임.
        intra-package import 라 cycle 0 (gather 의존 X).
        """
        from dartlab.providers.dart.calendar import OUTPUT_SCHEMA, predictCalendar

        history = self.disclosure(days=400, type="A")
        if history is None or history.is_empty():
            return pl.DataFrame(schema=OUTPUT_SCHEMA)
        return predictCalendar({self.stockCode: history}, horizonDays=horizonDays)


# ── DisclosureFetcher 구현 + register (정공법 B — DIP) ─────────────


class _DartDisclosureFetcher:
    """gather/Calendar 가 사용할 DART 공시 수집 어댑터."""

    def fetch(self, stockCode, *, days=400, type="A"):
        """단일 종목 공시 history 반환. 실패 시 None."""
        try:
            return Company(stockCode).disclosure(days=days, type=type)
        except (OSError, ValueError, RuntimeError):
            return None


def _registerDartDisclosureFetcher() -> None:
    """import 시점 등록."""
    from dartlab.core.disclosureFetcher import registerDisclosureFetcher

    registerDisclosureFetcher(_DartDisclosureFetcher())


_registerDartDisclosureFetcher()
