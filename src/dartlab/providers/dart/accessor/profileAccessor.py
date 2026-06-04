"""docs spine + finance/report authoritative merge accessor.

company.py에서 분리된 accessor 클래스.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import polars as pl

from dartlab.core.polarsUtil import isEmptyDf
from dartlab.providers.dart.checks import _isPeriodColumn

if TYPE_CHECKING:
    from dartlab.providers.dart.company import Company


class _ProfileAccessor:
    """docs spine + finance/report authoritative merge."""

    _CANONICAL_TOPIC_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

    _PREFERRED_TOPIC_ORDER = [
        "BS",
        "IS",
        "CIS",
        "CF",
        "SCE",
        "ratios",
        "dividend",
        "employee",
        "majorHolder",
        "executive",
        "audit",
        "capitalChange",
        "treasuryStock",
        "stockTotal",
        "investedCompany",
        "majorHolderChange",
        "minorityHolder",
        "outsideDirector",
        "publicOfferingUsage",
        "privateOfferingUsage",
        "corporateBond",
        "shortTermBond",
        "auditContract",
        "nonAuditContract",
    ]

    _REPORT_AUTHORITATIVE_TOPICS = {
        "dividend",
        "employee",
        "majorHolder",
        "executive",
        "audit",
        "capitalChange",
        "treasuryStock",
        "stockTotal",
        "investedCompany",
        "majorHolderChange",
        "minorityHolder",
        "outsideDirector",
        "publicOfferingUsage",
        "privateOfferingUsage",
        "corporateBond",
        "shortTermBond",
        "auditContract",
        "nonAuditContract",
        "executivePayAllTotal",
        "executivePayIndividual",
        "unregisteredExecutivePay",
        "topPay",
        "debtSecurities",
        "commercialPaper",
        "hybridSecurities",
        "contingentCapital",
        "executivePayTotal",
        "executivePayByType",
    }

    def __init__(self, company: "Company"):
        self._company = company

    @classmethod
    def _isProfileTopic(cls, topic: Any) -> bool:
        if not isinstance(topic, str) or not topic:
            return False
        return bool(cls._CANONICAL_TOPIC_RE.fullmatch(topic))

    @property
    def facts(self) -> pl.DataFrame | None:
        """기업 facts 통합 long-format — finance + CIS + SCE + report + docs 4 source merge.

        Capabilities:
            - finance series (BS/IS/CF) annual → "finance" source, priority 300.
            - financeCisAnnual (CIS) → "finance" source, priority 300.
            - sceSeriesAnnual (SCE) → "finance" source, priority 300.
            - report 28 apiType → "report" source, priority 200.
            - docs retrievalBlocks → "docs" source, priority 100, semanticTopic/detailTopic 자동 coalesce.
            - cacheKey = ``"_profileFacts"`` — 한 번 빌드 후 재사용.

        Returns:
            pl.DataFrame | None — long format. 컬럼 ``topic`` (str) / ``period`` (str) /
            ``source`` (finance/report/docs) / ``valueType`` (number/field/text/table 등) /
            ``valueKey`` (str) / ``value`` (Union) / ``payloadRef`` (str) / ``priority`` (Int) /
            ``summary`` (str). 모든 source 부재 → None.

        Example:
            >>> # facts = c._profileAccessor.facts
            >>> # facts.filter(pl.col("topic") == "BS").head()

        Guide:
            - "이 회사의 모든 facts 한 테이블" → ``c._profileAccessor.facts``.
            - "특정 topic 다 출처 모음" → ``facts.filter(pl.col("topic")==X)``.
            - "최우선 source 만" → priority 내림차순 정렬 + topic groupby first.
            - "summary 만 LLM 입력" → ``facts.select("summary")`` head.

        SeeAlso:
            - ``sections`` — docs spine 캐노니컬 sections (본 함수와 보완).
            - ``availableTopics`` — facts + sections topic 합집합.
            - ``trace`` — 단일 topic 의 출처 우선순위 분석.
            - ``Company._buildFinanceSeries`` / ``_financeCisAnnual`` / ``_sceSeriesAnnual`` —
              finance source.

        Requires:
            - polars — DataFrame.
            - dartlab.core.polarsUtil.isEmptyDf.

        AIContext:
            Workbench "이 회사 무슨 데이터 있냐" / "모든 출처 보여줘" 질문 entry. priority 컬럼
            으로 finance > report > docs 자동 ranking. AI 가 summary 컬럼만 추려 토큰 절약.
            None 시 회사 데이터 미수집.

        LLM Specifications:
            AntiPatterns:
                - 모든 source 부재 → None (silent). caller 는 None 시 "데이터 없음" fallback.
                - cache hit → 신규 데이터 미반영. fresh 보장 필요 시 cache invalidate.
                - vertical_relaxed concat → 컬럼 형식 다양 (value 가 Float / str 혼재).
            OutputSchema:
                - 9 컬럼 long format.
                - row count: source 별 facts 합. 회사 1 개 당 수백~수천.
            Prerequisites:
                - 어느 source 라도 1 개 수집되어 있음.
            Freshness:
                - source 의 freshness 의존 + cache.
            Dataflow:
                - 4 source → 본 함수 (long merge) → caller (AI / trace / availableTopics).
            TargetMarkets:
                - KR (DART) 한정.

        Raises:
            없음.
        """
        cacheKey = "_profileFacts"
        if cacheKey in self._company._cache:
            return self._company._cache[cacheKey]

        frames: list[pl.DataFrame] = []

        annual = self._company._buildFinanceSeries(freq="Y")
        if annual is not None:
            series, years = annual
            for sj in ("BS", "IS", "CF"):
                stmt = series.get(sj, {})
                if not stmt:
                    continue
                rows = []
                for item, values in stmt.items():
                    for idx, year in enumerate(years):
                        value = values[idx] if idx < len(values) else None
                        if value is None:
                            continue
                        rows.append(
                            {
                                "topic": sj,
                                "period": str(year),
                                "source": "finance",
                                "valueType": "number",
                                "valueKey": item,
                                "value": value,
                                "payloadRef": f"finance:{sj}:{item}",
                                "priority": 300,
                                "summary": f"{item}={value}",
                            }
                        )
                if rows:
                    frames.append(pl.DataFrame(rows))

        cisAnnual = self._company._financeCisAnnual()
        if cisAnnual is not None:
            cisSeries, years = cisAnnual
            rows = []
            for item, values in cisSeries.get("CIS", {}).items():
                for idx, year in enumerate(years):
                    value = values[idx] if idx < len(values) else None
                    if value is None:
                        continue
                    rows.append(
                        {
                            "topic": "CIS",
                            "period": str(year),
                            "source": "finance",
                            "valueType": "number",
                            "valueKey": item,
                            "value": value,
                            "payloadRef": f"finance:CIS:{item}",
                            "priority": 300,
                            "summary": f"{item}={value}",
                        }
                    )
            if rows:
                frames.append(pl.DataFrame(rows))

        sce = self._company._sceSeriesAnnual()
        if sce is not None:
            sceSeries, years = sce
            for item, values in sceSeries.get("SCE", {}).items():
                rows = []
                for idx, year in enumerate(years):
                    value = values[idx] if idx < len(values) else None
                    if value is None:
                        continue
                    rows.append(
                        {
                            "topic": "SCE",
                            "period": str(year),
                            "source": "finance",
                            "valueType": "number",
                            "valueKey": item,
                            "value": value,
                            "payloadRef": f"finance:SCE:{item}",
                            "priority": 300,
                            "summary": f"{item}={value}",
                        }
                    )
                if rows:
                    frames.append(pl.DataFrame(rows))

        if self._company._report is not None:
            for apiType in self._company._report.apiTypes:
                df = self._company._report.extractAnnual(apiType)
                if isEmptyDf(df):
                    continue
                rows = []
                for row in df.iter_rows(named=True):
                    year = row.get("year")
                    quarter = row.get("quarter")
                    summaryParts = []
                    for key, value in row.items():
                        if key in {"stockCode", "year", "quarter", "quarterNum", "apiType", "stlm_dt"}:
                            continue
                        if value is None:
                            continue
                        summaryParts.append(f"{key}={value}")
                        rows.append(
                            {
                                "topic": self._canonicalReportTopic(apiType),
                                "period": str(year),
                                "source": "report",
                                "valueType": "field",
                                "valueKey": key,
                                "value": str(value),
                                "payloadRef": f"report:{apiType}:{quarter}",
                                "priority": 200,
                                "summary": None,
                            }
                        )
                    if rows and summaryParts:
                        summary = "; ".join(summaryParts[:6])
                        for item in rows[-len(summaryParts) :]:
                            item["summary"] = summary
                if rows:
                    frames.append(pl.DataFrame(rows))

        docsBlocks = self._company._docs.retrievalBlocks
        if docsBlocks is not None and not docsBlocks.is_empty():
            # topic = coalesce(detailTopic, semanticTopic, topic)
            topicExpr = pl.col("topic")
            if "semanticTopic" in docsBlocks.columns:
                topicExpr = pl.coalesce(pl.col("semanticTopic"), topicExpr)
            if "detailTopic" in docsBlocks.columns:
                topicExpr = pl.coalesce(pl.col("detailTopic"), topicExpr)

            valueKeyExpr = topicExpr.cast(pl.Utf8)
            if "rawTitle" in docsBlocks.columns:
                valueKeyExpr = pl.coalesce(pl.col("rawTitle"), valueKeyExpr)
            if "blockLabel" in docsBlocks.columns:
                valueKeyExpr = pl.coalesce(pl.col("blockLabel"), valueKeyExpr)

            payloadExpr = pl.concat_str(
                [pl.lit("docs:"), topicExpr.cast(pl.Utf8), pl.lit(":"), pl.col("period").cast(pl.Utf8)]
            )
            if "cellKey" in docsBlocks.columns:
                payloadExpr = pl.coalesce(pl.col("cellKey"), payloadExpr)

            docsDf = (
                docsBlocks.filter(
                    pl.col("period").is_not_null() & pl.col("blockText").is_not_null() & (pl.col("blockText") != "")
                )
                .with_columns(topicExpr.alias("_topic"))
                .filter(pl.col("_topic").is_not_null())
                .select(
                    [
                        pl.col("_topic").cast(pl.Utf8).alias("topic"),
                        pl.col("period").cast(pl.Utf8).alias("period"),
                        pl.lit("docs").alias("source"),
                        (pl.col("blockType") if "blockType" in docsBlocks.columns else pl.lit("text")).alias(
                            "valueType"
                        ),
                        valueKeyExpr.alias("valueKey"),
                        pl.col("blockText").cast(pl.Utf8).alias("value"),
                        payloadExpr.alias("payloadRef"),
                        pl.lit(100).alias("priority"),
                        pl.col("blockText").cast(pl.Utf8).str.slice(0, 400).alias("summary"),
                    ]
                )
            )
            if docsDf.height > 0:
                frames.append(docsDf)

        result = pl.concat(frames, how="vertical_relaxed") if frames else None
        self._company._cache[cacheKey] = result
        return result

    @property
    def sections(self) -> pl.DataFrame | None:
        """merged canonical sections — docs spine + finance/report 통합 wide 보드.

        Capabilities:
            - ``Company._getPrimary("sections")`` 위임 — docs sections + finance/report merge.
            - facts 는 long, 본 함수는 wide (topic × period).
            - sections 결과의 period 컬럼은 ``_isPeriodColumn`` 매칭 (예 "2024Q1").

        Returns:
            pl.DataFrame | None — wide DataFrame. 컬럼 ``topic`` + period N + meta.
            sections 미수집 → None.

        Example:
            >>> # c._profileAccessor.sections.head()

        Guide:
            - "이 회사 topic × 시간 매트릭스" → 본 함수.
            - long format 으로 → ``facts`` 사용.

        SeeAlso:
            - ``facts`` — 본 함수의 long format 자매.
            - ``Company._getPrimary("sections")`` — 본 함수 본체.

        Requires:
            - polars — DataFrame.

        AIContext:
            Workbench "이 회사 토픽 매트릭스" 질문 처리. AI 가 wide → 각 topic row 의 period
            컬럼 lookup → 자연어 답변.

        LLM Specifications:
            AntiPatterns:
                - sections 미수집 (docs 또는 finance 모두 부재) → None.
            OutputSchema:
                - wide DataFrame — topic + period + meta.
            Prerequisites:
                - docs sections parquet 또는 finance 수집.
            Freshness:
                - source 의존.
            Dataflow:
                - docs / finance → _getPrimary → 본 함수 → AI.
            TargetMarkets:
                - KR (DART) 한정.

        Raises:
            없음.
        """
        return self._company._getPrimary("sections")

    @property
    def availableTopics(self) -> list[str]:
        """profile 에서 접근 가능한 topic 목록 — sections 컬럼 + facts topic 합집합 정렬.

        Capabilities:
            - sections 의 ``topic`` 컬럼 to_list + facts 의 ``topic`` unique to_list 합집합.
            - None 값 제외 + 알파벳 정렬.

        Returns:
            list[str] — 정렬된 topic 이름들. 데이터 부재 시 빈 list.

        Example:
            >>> # topics = c._profileAccessor.availableTopics
            >>> # "BS" in topics
            >>> # True

        Guide:
            - "이 회사 어떤 topic 분석 가능한가" → 본 함수.
            - "topic 1 개 데이터 보기" → ``c.show(topic)``.
            - "출처 우선순위" → ``trace(topic)``.

        SeeAlso:
            - ``facts`` / ``sections`` — 본 함수의 source.
            - ``trace`` — 단일 topic 출처 분석.

        Requires:
            - polars — DataFrame to_list.

        AIContext:
            Workbench "이 회사에서 분석 가능한 항목" 질문 entry. 결과 list 가 짧으면 회사 데이터
            부족, 길면 분석 가능 범위 넓음. AI 가 list 를 검토하여 다음 질문 추천.

        LLM Specifications:
            AntiPatterns:
                - sections/facts 모두 부재 → 빈 list.
                - topic 이름이 한국어/영문 혼재 가능 (apiType 가 영문, docs topic 이 한국어 변형).
            OutputSchema:
                - list[str] — 알파벳 정렬.
            Prerequisites:
                - facts 또는 sections 1 개 이상.
            Freshness:
                - source 의존.
            Dataflow:
                - facts + sections → union → 본 함수.
            TargetMarkets:
                - KR (DART) 한정.

        Raises:
            없음.
        """
        topics = set()
        if self.sections is not None and "topic" in self.sections.columns:
            topics.update(self.sections["topic"].to_list())
        facts = self.facts
        if facts is not None and "topic" in facts.columns:
            topics.update(facts["topic"].unique().to_list())
        return sorted(str(t) for t in topics if t is not None)

    def get(self, topic: str) -> Any:
        """topic 데이터 조회 — DEPRECATED alias (``c.show(topic)`` 권장).

        Capabilities:
            - DeprecationWarning 항상 발생.
            - BS/IS/CF/CIS → finance attribute lookup.
            - SCE → ``_finance.SCE``.
            - report authoritative topic → report attribute lookup.
            - 그 외 → sections row filter.

        Args:
            topic: topic 이름.

        Returns:
            pl.DataFrame | dict | None — topic 의 source 의존.

        Raises:
            없음 (warnings.warn 만 발생). 신규 코드는 ``c.show(topic)`` 사용.

        Example:
            >>> # c._profileAccessor.get("BS")  # DEPRECATED
            >>> # c.show("BS")  # 권장

        Guide:
            - 본 함수 사용 X → ``c.show(topic)`` 또는 ``c.select(topic, [...])``.
            - profile 페이지의 raw access 가 필요하면 ``facts`` / ``sections`` 직접.

        SeeAlso:
            - ``Company.show`` / ``Company.select`` — 권장 API.
            - ``facts`` / ``sections`` — long/wide raw access.

        Requires:
            - polars — DataFrame (sections 경로).
            - warnings (stdlib).

        AIContext:
            AI 가 본 함수 호출 X. 발견 시 c.show 로 migrate.

        LLM Specifications:
            AntiPatterns:
                - 본 함수 새로 호출 → DeprecationWarning 누적. show 로 마이그.
                - report topic 이 _REPORT_AUTHORITATIVE_TOPICS 외 → sections fallback.
            OutputSchema:
                - DataFrame / dict / None (topic 의 source 의존).
            Prerequisites:
                - finance / report / docs 중 1.
            Freshness:
                - source 의존.
            Dataflow:
                - 본 함수 → finance / report / sections attribute.
            TargetMarkets:
                - KR (DART) 한정.
        """
        import warnings

        warnings.warn("profile.get(topic) → show(topic) 경로 권장", DeprecationWarning, stacklevel=2)
        if topic in {"BS", "IS", "CF", "CIS"}:
            return getattr(self._company.finance, topic)
        if topic == "SCE":
            return self._company._finance.SCE
        if topic in self._REPORT_AUTHORITATIVE_TOPICS and self._company._report is not None:
            if topic == "audit":
                return self._company._report.audit
            return getattr(self._company._report, topic, None)
        sections = self.sections
        if sections is None:
            return None
        return sections.filter(pl.col("topic") == topic)

    def trace(self, topic: str, period: str | None = None) -> pl.DataFrame | dict[str, Any] | None:
        """topic 출처 추적 — 4 source 우선순위 + payloadRef + whySelected 메타.

        Capabilities:
            - facts (long) 에서 topic 별 row 추출 → source 별 group_by + priority max.
            - docs sections 의 wide row 추가 ("docs-sections:topic:period" payload).
            - period 명시 시 ``rawPeriod`` 정규화 후 filter.
            - 출처 list 를 (priority, source) 내림차순 정렬 → primary + fallback 분리.
            - 출처 1 개 이상 있으면 dict, 없으면 None.

        Args:
            topic: topic 이름.
            period: 특정 기간 또는 None (전체).

        Returns:
            dict | None — 키 ``topic`` / ``period`` / ``primarySource`` /
            ``fallbackSources`` (list) / ``selectedPayloadRef`` / ``availableSources`` (list[dict]) /
            ``whySelected``.

        Example:
            >>> # c._profileAccessor.trace("BS", period="2024")

        Guide:
            - "이 값 어디서 왔냐" 디버깅 → 본 함수.
            - "finance vs docs 값 차이" → availableSources 의 row 들 비교.
            - "여러 period 한 번에" → period=None 후 availableSources 그룹 분석.

        SeeAlso:
            - ``facts`` / ``sections`` — 본 함수의 source.
            - ``_sourcePriority`` (모듈 private) — whySelected 의 priority 로직.
            - ``dartlab.providers.dart.docs.sections.rawPeriod`` — period 정규화.

        Requires:
            - polars — DataFrame group_by + filter.
            - dartlab.providers.dart.docs.sections — rawPeriod.

        AIContext:
            AI 가 "이 값이 어디서 나온 거냐" 출처 질문 처리 시 entry. primarySource 만 사용자
            에게 노출, availableSources 는 디버깅 컨텍스트. whySelected 가 priority 규칙
            (finance > report > docs) 설명.

        LLM Specifications:
            AntiPatterns:
                - topic 존재 X → None (silent).
                - period 형식 다양 ("2024" / "2024-Q1" / "2024Q1") → rawPeriod 정규화 한계.
            OutputSchema:
                - dict — 7 키 또는 None.
            Prerequisites:
                - facts 또는 sections 중 1 개 이상.
            Freshness:
                - source 의존.
            Dataflow:
                - facts + sections → 본 함수 → AI 디버그 응답.
            TargetMarkets:
                - KR (DART) 한정.

        Raises:
            없음.
        """
        from dartlab.providers.dart.sectionPeriod import rawPeriod

        requestedPeriod = rawPeriod(period) if isinstance(period, str) else period
        facts = self.facts
        docsSections = self._company._docs.sections

        sources: list[dict[str, Any]] = []

        if facts is not None:
            traced = facts.filter(pl.col("topic") == topic)
            if requestedPeriod is not None:
                traced = traced.filter(pl.col("period") == requestedPeriod)
            if not traced.is_empty():
                grouped = traced.group_by("source").agg(
                    [
                        pl.len().alias("rows"),
                        pl.col("payloadRef").first().alias("payloadRef"),
                        pl.col("summary").first().alias("summary"),
                        pl.col("priority").max().alias("priority"),
                    ]
                )
                sources.extend(grouped.iter_rows(named=True))

        if docsSections is not None and topic in docsSections["topic"].to_list():
            row = docsSections.filter(pl.col("topic") == topic)
            if not row.is_empty():
                periodCols = [c for c in docsSections.columns if _isPeriodColumn(c)]
                if requestedPeriod is not None and requestedPeriod in periodCols:
                    value = row.item(0, requestedPeriod)
                    if value is not None:
                        sources.append(
                            {
                                "source": "docs",
                                "rows": 1,
                                "payloadRef": f"docs-sections:{topic}:{requestedPeriod}",
                                "summary": str(value)[:400],
                                "priority": 100,
                            }
                        )

        if not sources:
            return None

        sources.sort(key=lambda r: (r.get("priority", 0), r.get("source", "")), reverse=True)
        primary = sources[0]
        return {
            "topic": topic,
            "period": requestedPeriod,
            "primarySource": primary.get("source"),
            "fallbackSources": [r.get("source") for r in sources[1:]],
            "selectedPayloadRef": primary.get("payloadRef"),
            "availableSources": sources,
            "whySelected": f"{self._sourcePriority(topic)} authoritative priority",
        }

    def _canonicalReportTopic(self, apiType: str) -> str:
        if apiType == "auditOpinion":
            return "audit"
        return apiType

    @property
    def sharesOutstanding(self) -> int | None:
        """발행주식수 (유통중 보통주, 최신 ``stockTotal`` report 의 ``istc_totqy``).

        Capabilities:
            - ``stockTotal`` apiType 의 annual report 추출.
            - ``se='보통주'`` 필터.
            - ``stlm_dt`` 최신순 정렬 후 1 번째 row 의 ``istc_totqy`` 추출.
            - 모든 예외 (AttributeError/KeyError/IndexError/ValueError/TypeError) → None.
            - cacheKey = ``"_sharesOutstanding"``.

        Returns:
            int | None — 발행주식수 (정수). report 부재 / 추출 실패 → None.

        Example:
            >>> # c._profileAccessor.sharesOutstanding
            >>> # 7234500000  # 삼성전자 보통주

        Guide:
            - "삼성전자 발행주식수" → 본 함수 (보통주 한정).
            - "우선주까지" → ``c._report.extractAnnual("stockTotal")`` 직접 (se filter X).
            - 시가총액 계산 = 본 함수 × 현재 주가.

        SeeAlso:
            - ``dartlab.providers.dart.report.extract.extractAnnual`` — report 추출 backend.
            - ``stockTotal`` apiType — 발행주식수 source.

        Requires:
            - polars — DataFrame filter + sort.
            - report parquet 수집.

        AIContext:
            AI 가 "시가총액 계산" / "유통주식수" 질문 entry. None 시 "report 미수집" fallback.
            우선주 회사 (예 삼성전자 우) 의 경우 보통주 + 우선주 별도 처리 필요 — 본 함수는
            보통주만.

        LLM Specifications:
            AntiPatterns:
                - 우선주만 있는 회사 → 보통주 row 0 → None.
                - report parquet 미수집 → None.
                - istc_totqy 컬럼이 신규/이전 양식 차이로 부재 → None.
            OutputSchema:
                - 1 int 또는 None.
            Prerequisites:
                - report parquet 의 stockTotal apiType 1 회 이상 수집.
            Freshness:
                - report 수집 시점 + cache. 갱신 후 invalidate 필요.
            Dataflow:
                - report parquet (stockTotal) → extractAnnual → 본 함수 → 시가총액 계산.
            TargetMarkets:
                - KR (DART) 한정.

        Raises:
            없음.
        """
        cacheKey = "_sharesOutstanding"
        if cacheKey in self._company._cache:
            return self._company._cache[cacheKey]

        result = None
        try:
            df = self._company._report.extractAnnual("stockTotal")
            if df is not None and len(df) > 0:
                # se='보통주', 최신 날짜 기준 istc_totqy(유통중주식총수) 추출
                common = df.filter(pl.col("se") == "보통주")
                if len(common) > 0 and "istc_totqy" in common.columns:
                    # 최신순 정렬
                    if "stlm_dt" in common.columns:
                        common = common.sort("stlm_dt", descending=True)
                    val = common["istc_totqy"][0]
                    if val is not None:
                        result = int(float(val))
        except (AttributeError, KeyError, IndexError, ValueError, TypeError):
            pass

        self._company._cache[cacheKey] = result
        return result

    def _sourcePriority(self, topic: str) -> str:
        if topic in {"BS", "IS", "CIS", "CF", "SCE"}:
            return "finance"
        if topic in self._REPORT_AUTHORITATIVE_TOPICS:
            return "report"
        return "docs"
