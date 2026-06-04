"""DART Company 의 show dispatch core.

Company.show / _showImpl / _showFinanceStatement / _showSectionsTopic 진입점은
topic alias 해석 후 5 사례 분기 (list period / segments / finance / notes / sections)
로 dispatch. Company facade 가 본 모듈의 함수에 thin delegate.

Module-level functions:
    showImpl              — 사용자 c.show(topic, ...) 진입점 (facade._showImpl)
    showFinanceStatement  — finance topic (BS/IS/CF/CIS/SCE/ratios/ratioSeries/sceMatrix)
    showSectionsTopic     — docs/report sections 기반 topic
    showFinanceTopic      — finance source 실제 데이터
    traceFinanceTopic     — finance authoritative provenance
    showReportTopic       — report source 실제 데이터
    showSegmentsSub       — segments 하위 (region/product/composition)
    showDirectTopic       — sections 외 경로 fallback
    showSectionBlock      — sections topicFrame 의 blockOrder 별 text/table
    horizontalizeTableBlock — table 블록 기간 간 수평화
    reportFrame           — report apiType DataFrame
    reportFrameInner      — report apiType 정제 DataFrame
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import polars as pl

from dartlab.providers.dart.checks import _isPeriodColumn

if TYPE_CHECKING:
    from dartlab.providers.dart.company import Company


SHOW_FINANCE_TOPICS = frozenset({"BS", "IS", "CF", "CIS", "SCE", "ratios", "ratioSeries", "sceMatrix"})
FINANCE_CLEAN_TOPICS = frozenset({"IS", "BS", "CIS", "CF", "SCE"})


# ── finance source ─────────────────────────────────────────────────


def showFinanceTopic(
    company: Company,
    topic: str,
    *,
    period: str | None = None,
    freq: str = "Q",
    scope: str = "consolidated",
) -> pl.DataFrame | None:
    """finance source topic 의 실제 데이터 반환 (show 진입점).

    ``c.show("IS", freq="Y", scope="separate")`` 같은 사용자 호출이 여기로 들어와서
    freq/scope 에 따라 빌드.

    Args:
        company: Company 인스턴스.
        topic: BS/IS/CF/CIS/SCE/ratios/ratioSeries/sceMatrix 중 하나.
        period: 단일 기간 필터.
        freq: ``"Q"``/``"Y"``/``"YTD"``.
        scope: ``"consolidated"``/``"separate"``.

    Returns:
        wide DataFrame 또는 None.

    Raises:
        없음.

    Example:
        >>> showFinanceTopic(c, "IS", freq="Y")
    """
    if topic == "ratios":
        return company._applyPeriodFilter(company._buildRatios(), period)
    if topic == "ratioSeries":
        # dict 구조 — DataFrame 으로 변환 어려움. None 반환 + 사용자 안내.
        # 사용자는 c.show("ratios") DataFrame 사용 권장.
        return None
    if topic in {"BS", "IS", "CF", "CIS"}:
        df = company._financeOrDocsStatement(topic, freq=freq, scope=scope)
        return company._applyPeriodFilter(df, period) if df is not None else None
    if topic == "SCE":
        return company._applyPeriodFilter(company._sce(), period)
    if topic == "sceMatrix":
        # 3차원 dict — DataFrame 변환 X. 사용자는 SCE topic.
        return None
    return None


def traceFinanceTopic(company: Company, topic: str, *, period: str | None = None) -> dict[str, Any] | None:
    """finance authoritative topic provenance 를 facts 빌드 없이 직접 계산.

    Args:
        company: Company 인스턴스.
        topic: BS/IS/CF/CIS/SCE 중 하나.
        period: 특정 기간 필터.

    Returns:
        ``{topic, period, primarySource, fallbackSources, ...}`` dict 또는 None.

    Raises:
        없음.

    Example:
        >>> traceFinanceTopic(c, "BS", period="2024")
    """
    from dartlab.providers.dart.docs.sections import rawPeriod

    requestedPeriod = rawPeriod(period) if isinstance(period, str) else period
    rows: list[tuple[str, str]] = []

    def collect(series: dict[str, list[Any]] | None, years: list[Any], payloadTopic: str) -> None:
        """series → rows in-place 축적 — period 필터 적용.

        Args:
            series: ``{item: [value...], ...}`` dict 또는 None.
            years: period 리스트.
            payloadTopic: payloadRef prefix.

        Returns:
            None (in-place ``rows`` mutation).

        Raises:
            없음.

        Example:
            >>> collect({"sales": [1000]}, [2024], "IS")  # nested function example
        - ``SectionsAnalyzer`` — sections 파생표.
        """
        if not series:
            return
        for item, values in series.items():
            for idx, year in enumerate(years):
                if requestedPeriod is not None and str(year) != requestedPeriod:
                    continue
                value = values[idx] if idx < len(values) else None
                if value is None:
                    continue
                rows.append((f"finance:{payloadTopic}:{item}", f"{item}={value}"))

    if topic in {"BS", "IS", "CF"}:
        annual = company._buildFinanceSeries(freq="Y")
        if annual is None:
            return None
        series, years = annual
        collect(series.get(topic), years, topic)
    elif topic == "CIS":
        annual = company._financeCisAnnual()
        if annual is None:
            return None
        series, years = annual
        collect(series.get("CIS"), years, "CIS")
    elif topic == "SCE":
        annual = company._sceSeriesAnnual()
        if annual is None:
            return None
        series, years = annual
        collect(series.get("SCE"), years, "SCE")
    else:
        return None

    if not rows:
        return None

    payloadRef, summary = rows[0]
    return {
        "topic": topic,
        "period": requestedPeriod,
        "primarySource": "finance",
        "fallbackSources": [],
        "selectedPayloadRef": payloadRef,
        "availableSources": [
            {
                "source": "finance",
                "rows": len(rows),
                "payloadRef": payloadRef,
                "summary": summary,
                "priority": 300,
            }
        ],
        "whySelected": "finance authoritative priority",
    }


# ── report source ──────────────────────────────────────────────────


def showReportTopic(
    company: Company, topic: str, *, period: str | None = None, raw: bool = False
) -> pl.DataFrame | None:
    """report source topic 의 실제 데이터 반환.

    Args:
        company: Company 인스턴스.
        topic: report topic 이름 (예: ``"dividend"``).
        period: 기간 필터.
        raw: True 면 영문 컬럼 그대로, False 면 한글 매핑.

    Returns:
        DataFrame 또는 None.

    Raises:
        없음.

    Example:
        >>> showReportTopic(c, "dividend", period="2024")
    """
    return company._applyPeriodFilter(reportFrame(company, topic, raw=raw), period)


def reportFrame(company: Company, topic: str, *, raw: bool = False) -> pl.DataFrame | None:
    """report apiType DataFrame — topic → apiType 변환 + 정제.

    Args:
        company: Company 인스턴스.
        topic: report topic 이름.
        raw: True 면 영문 컬럼 그대로.

    Returns:
        정제 DataFrame 또는 None (apiType 미존재 / report 부재).

    Raises:
        없음 (Polars exception 모두 None 반환).

    Example:
        >>> reportFrame(c, "dividend")
    """
    if company._report is None:
        return None
    from dartlab.providers.dart.company import _apiTypeForTopic

    apiType = _apiTypeForTopic(topic)
    try:
        if apiType not in company._report.apiTypes:
            return None
        return reportFrameInner(company, apiType, topic, raw=raw)
    except (
        pl.exceptions.ColumnNotFoundError,
        pl.exceptions.InvalidOperationError,
        pl.exceptions.SchemaError,
        RuntimeError,
    ):
        return None


def reportFrameInner(company: Company, apiType: str, topic: str, *, raw: bool = False) -> pl.DataFrame | None:
    """report apiType 의 정제된 DataFrame 반환 (``reportAccessor`` 위임).

    Args:
        company: Company 인스턴스 (stockCode 추출용).
        apiType: OpenDART apiType 키.
        topic: topic 이름 (호환용).
        raw: True 면 영문 컬럼.

    Returns:
        정제 DataFrame 또는 None.

    Raises:
        없음.

    Example:
        >>> reportFrameInner(c, "dividend", "dividend")
    """
    from dartlab.providers.dart.accessor.reportAccessor import reportFrameInner as _reportFrameInner

    return _reportFrameInner(company.stockCode, apiType, topic, raw=raw)


# ── segments sub-topic ─────────────────────────────────────────────


def showSegmentsSub(company: Company, sub: str) -> pl.DataFrame | None:
    """segments 하위 topic → DataFrame (region/product/composition).

    Args:
        company: Company 인스턴스.
        sub: ``"region"``/``"product"``/``"composition"`` 중 하나.

    Returns:
        DataFrame 또는 None.

    Raises:
        없음.

    Example:
        >>> showSegmentsSub(c, "region")
    """
    segResult = company._callModule("segments")
    if segResult is None:
        return None
    typeMap = {"region": "region", "product": "product", "composition": "segment"}
    tableType = typeMap.get(sub)
    if tableType is None:
        return None
    table = segResult.latestTable(tableType)
    if table is None:
        return None
    return table.toDataFrame()


# ── direct fallback (sections 외 경로) ─────────────────────────────


def showDirectTopic(
    company: Company, topic: str, *, period: str | None = None, raw: bool = False
) -> pl.DataFrame | None:
    """sections 외 경로에서 직접 회수 가능한 topic fallback.

    우선순위: report (apiType 일치) → notes (key 일치) → primary (safe call).

    Args:
        company: Company 인스턴스.
        topic: topic 이름.
        period: 기간 필터.
        raw: True 면 영문 컬럼.

    Returns:
        DataFrame 또는 None.

    Raises:
        없음 (모든 예외 흡수).

    Example:
        >>> showDirectTopic(c, "dividend")
    """
    if company._hasReport:
        try:
            report_api_types = set(getattr(company._report, "apiTypes", []) or [])
        except (AttributeError, TypeError, ValueError):
            report_api_types = set()
        if topic in report_api_types:
            result = showReportTopic(company, topic, period=period, raw=raw)
            if isinstance(result, pl.DataFrame):
                return result

    notes = company._notesAccessor
    if notes is not None and hasattr(notes, "keys"):
        try:
            note_keys = set(notes.keys())
        except (AttributeError, TypeError, ValueError):
            note_keys = set()
        if topic in note_keys:
            try:
                result = getattr(notes, topic)
            except (AttributeError, KeyError, RuntimeError, TypeError, ValueError):
                result = None
            if isinstance(result, pl.DataFrame):
                return company._applyPeriodFilter(result, period)

    primary = company._safePrimary(topic)
    if isinstance(primary, pl.DataFrame):
        return company._applyPeriodFilter(primary, period)
    return None


# ── sections block ─────────────────────────────────────────────────


def showSectionBlock(
    company: Company,
    topicFrame: pl.DataFrame,
    *,
    block: int | None = None,
    period: str | None = None,
) -> pl.DataFrame | None:
    """sections topicFrame 에서 blockOrder 별 text/table 반환.

    - ``block=None`` → topic 전체 (blockOrder 순서, text 는 원문, table 은 수평화).
    - ``block=N`` → 해당 blockOrder 의 블록만 반환.

    Args:
        company: Company 인스턴스.
        topicFrame: topic 으로 필터된 sections DataFrame.
        block: blockOrder (None 이면 전체).
        period: 기간 필터.

    Returns:
        DataFrame 또는 None.

    Raises:
        없음.

    Example:
        >>> showSectionBlock(c, topic_df, block=0)
    """
    if "blockType" not in topicFrame.columns or "blockOrder" not in topicFrame.columns:
        return company._applyPeriodFilter(topicFrame, period)

    periodCols = [c for c in topicFrame.columns if _isPeriodColumn(c)]

    if block is not None:
        # 특정 blockOrder만
        boRows = topicFrame.filter(pl.col("blockOrder") == block)
        if boRows.is_empty():
            return None
        bt = boRows["blockType"][0]
        if bt == "text":
            keepCols = [c for c in periodCols if c in boRows.columns]
            nonNullCols = [c for c in keepCols if boRows[c].null_count() < boRows.height]
            if not nonNullCols:
                return None
            return company._applyPeriodFilter(boRows.select(nonNullCols), period)
        elif bt == "table":
            result = horizontalizeTableBlock(company, topicFrame, block, periodCols, period)
            if result is not None:
                return result
            # 수평화 실패(이력형/목록형 등) → 원본 텍스트 fallback
            keepCols = [c for c in periodCols if c in boRows.columns]
            nonNullCols = [c for c in keepCols if boRows[c].null_count() < boRows.height]
            if nonNullCols:
                return company._applyPeriodFilter(boRows.select(nonNullCols), period)
        return None

    # block=None → 전체 topic (text 원문 + table 수평화, blockOrder 순서)
    return company._applyPeriodFilter(topicFrame, period)


def horizontalizeTableBlock(
    company: Company,
    topicFrame: pl.DataFrame,
    blockOrder: int,
    periodCols: list[str],
    period: str | None = None,
) -> pl.DataFrame | None:
    """table 블록을 기간 간 수평화 — 항목 × 기간 매트릭스.

    Args:
        company: Company 인스턴스.
        topicFrame: topic 으로 필터된 sections DataFrame.
        blockOrder: blockOrder 번호.
        periodCols: 수평화 대상 period 컬럼 리스트.
        period: 기간 필터 (선택).

    Returns:
        수평화 DataFrame 또는 None (수평화 실패).

    Raises:
        없음.

    Example:
        >>> horizontalizeTableBlock(c, topic_df, 0, ["2024", "2023"])
    """
    from dartlab.providers.dart.parse.tableHorizontalizer import (
        horizontalizeTableBlock as _horizontalize,
    )

    df = _horizontalize(topicFrame, blockOrder, periodCols, period)
    if df is None:
        return None
    return company._applyPeriodFilter(df, period)


# ── show 진입점 ────────────────────────────────────────────────────


def showImpl(
    company: Company,
    topic: str,
    block: int | None = None,
    *,
    period: str | list[str] | None = None,
    freq: str = "Q",
    scope: str = "consolidated",
    raw: bool = False,
) -> pl.DataFrame | None:
    """topic 의 데이터를 반환 — 사용자 ``c.show`` 의 내부 구현.

    Q1.5 dispatcher: alias 해석 → 5 사례 분기 (list period / segments / finance /
    notes / sections).

    Args:
        company: Company 인스턴스.
        topic: topic 이름 또는 alias.
        block: blockOrder (None 이면 전체).
        period: 단일 기간 또는 기간 리스트 (vertical 변환).
        freq: ``"Q"``/``"Y"``/``"YTD"``.
        scope: ``"consolidated"``/``"separate"``.
        raw: True 면 영문 컬럼.

    Returns:
        DataFrame 또는 None.

    Raises:
        없음.

    Example:
        >>> showImpl(c, "IS", freq="Y", scope="separate")
    """
    from dartlab.providers.dart.builder.dataShapeUtils import transposeToVertical
    from dartlab.providers.dart.company import _resolveTopic
    from dartlab.providers.dart.notes import _NOTES_DISPATCH

    # Q1.5 dispatcher: alias 해석 → 5 사례 분기 (list period / segments / finance / notes / sections).
    topic = _resolveTopic(topic)

    if isinstance(period, list):
        wide = company.show(topic, block, freq=freq, scope=scope, raw=raw)
        if wide is None or not isinstance(wide, pl.DataFrame):
            return None
        return transposeToVertical(wide, period)

    if topic.startswith("segments:"):
        return showSegmentsSub(company, topic.split(":", 1)[1])

    if topic in SHOW_FINANCE_TOPICS:
        return showFinanceStatement(company, topic, block, period=period, freq=freq, scope=scope)

    if topic in _NOTES_DISPATCH and company._notesAccessor is not None:
        return company._notesAccessor._get(topic)

    return showSectionsTopic(company, topic, block, period=period, raw=raw, freq=freq, scope=scope)


def showFinanceStatement(
    company: Company,
    topic: str,
    block: int | None,
    *,
    period: str | None,
    freq: str,
    scope: str,
) -> pl.DataFrame | None:
    """finance topic (BS/IS/CF/CIS/SCE/ratios/ratioSeries/sceMatrix) 조회.

    ``block`` 이 지정되면 (not None and not 0) None. BS/IS/CIS/CF/SCE 는 clean 적용.

    Args:
        company: Company 인스턴스.
        topic: finance topic.
        block: blockOrder (None / 0 이외는 None 반환).
        period: 기간 필터.
        freq: ``"Q"``/``"Y"``/``"YTD"``.
        scope: ``"consolidated"``/``"separate"``.

    Returns:
        wide DataFrame 또는 None.

    Raises:
        없음.

    Example:
        >>> showFinanceStatement(c, "IS", None, period="2024Q4", freq="Q", scope="consolidated")
    """
    from dartlab.providers.dart.builder.dataShapeUtils import cleanFinanceDataFrame

    if block not in (None, 0):
        return None
    result = showFinanceTopic(company, topic, period=period, freq=freq, scope=scope)
    if topic in FINANCE_CLEAN_TOPICS and isinstance(result, pl.DataFrame) and result.width > 0:
        result = cleanFinanceDataFrame(result, topic)
    return result if isinstance(result, pl.DataFrame) else None


def _showFromSectionsArtifact(
    company: Company,
    topic: str,
    *,
    period: str | None,
    stripTags: bool,
) -> pl.DataFrame | None:
    """c.sections (신규 수평화 artifact) 직접 필터 — docs 본문 topic 경량 경로.

    사용자 철학 (plan snazzy-wibbling-origami): sections 가 확립(빠름·경량·수평화)되면
    show 는 c.sections 직접 필터로 따라온다. 무거운 merged board (docsProfileBuilder) +
    SectionsAnalyzer 경유 없이 c.sections 의 sectionLeaf 를 mapSectionTitle 로 분류 →
    topic 필터. report/finance 소스 전용 topic 은 매칭 0 → None 반환 (호출자가 옛 보드
    fallback). mapper 는 591줄 파이프라인이 아니라 ~240 행 분류기로만 사용.

    Returns:
        topic 매칭 c.sections 행 (label cols + period cols) 또는 None (매칭 0 / artifact 부재).
    """
    cacheKey = "_sectionsTagged"
    if cacheKey in company._cache:
        tagged = company._cache[cacheKey]
    else:
        base = company.sections
        if base is None or "sectionLeaf" not in base.columns:
            company._cache[cacheKey] = None
            return None
        from dartlab.providers.dart.sectionTopic import mapSectionTitle

        tagged = base.with_columns(
            pl.col("sectionLeaf").fill_null("").map_elements(mapSectionTitle, return_dtype=pl.Utf8).alias("_mtopic")
        )
        company._cache[cacheKey] = tagged
    if tagged is None:
        return None
    rows = tagged.filter(pl.col("_mtopic") == topic).drop("_mtopic")
    if rows.is_empty():
        return None
    labelCols = [c for c in ("chapter", "sectionLeaf", "section_title", "topic", "section_order") if c in rows.columns]
    periodCols = [c for c in rows.columns if _isPeriodColumn(c)]
    if period and isinstance(period, str) and period in periodCols:
        periodCols = [period]
    rows = rows.select(labelCols + periodCols)
    if stripTags:
        from dartlab.providers.dart.docs.sections.xmlAdapter import stripTagsFromSectionsDf

        rows = stripTagsFromSectionsDf(rows)
    return rows


def showSectionsTopic(
    company: Company,
    topic: str,
    block: int | None,
    *,
    period: str | None,
    raw: bool,
    freq: str,
    scope: str,
    stripTags: bool = True,
) -> pl.DataFrame | None:
    """docs/report sections 기반 topic 조회.

    sections 캐시 → topic 필터 → block dispatch (finance / report / docs). 미등록
    topic 은 warning + None. registered-but-empty 는 silent None.

    Args:
        company: Company 인스턴스.
        topic: topic 이름.
        block: blockOrder (None 이면 block index, N 이면 해당 block).
        period: 기간 필터.
        raw: True 면 영문 컬럼.
        freq: ``"Q"``/``"Y"``/``"YTD"``.
        scope: ``"consolidated"``/``"separate"``.
        stripTags: True (기본) — period column cell value 의 HTML/XML 태그 모두 제거
            (show/agent/analysis 호환 plain text 양식). False — mixed 양식 보존
            (HTML ``<table rowspan>`` + ``## `` heading marker, viewer 양식).

    Returns:
        DataFrame 또는 None.

    Raises:
        없음 (미등록 topic 은 UserWarning 만 발생).

    Example:
        >>> showSectionsTopic(c, "executive", None, period="2024", raw=False, freq="Q", scope="consolidated")
    """
    from dartlab.providers.dart.builder.dataShapeUtils import cleanFinanceDataFrame, warnUnknownTopic
    from dartlab.providers.dart.company import _getModuleIndex

    # 정본(v0.10.3) 블록 단위 docs show 복구 — sections-artifact 직접 필터 short-circuit 제거.
    # docs 본문 topic 은 아래 _docs.sections 블록 경로(blockOrder/blockType/textPath/sourceTopic +
    # period)로 회수한다. section-level(chapter/sectionLeaf) 뭉태기 회귀를 막는다.
    # (_showFromSectionsArtifact 는 sections 재설계 전까지 미사용 — 재설계 세션이 정리.)

    if "_sections" in company._cache:
        sec = company._cache["_sections"]
    else:
        docsSections = company._docs.sections
        if docsSections is not None:
            partialDocs = docsSections.forTopics({topic})
            if partialDocs is not None and "source" not in partialDocs.columns:
                partialDocs = partialDocs.with_columns(pl.lit("docs").alias("source"))
            sec = partialDocs
        else:
            sec = None

    if sec is None:
        if block in (None, 0):
            direct = showDirectTopic(company, topic, period=period, raw=raw)
            if direct is not None:
                return direct
        # registry 에 등록된 topic 은 "데이터 없음" 으로 간주해 silent None.
        # 미등록 topic 만 warning. registered-but-empty vs unknown-topic 구분.
        if topic not in _getModuleIndex():
            import warnings

            warnings.warn(
                f"'{topic}' topic 을 찾을 수 없습니다. 전체 목록은 c.topics 또는 c.index 로 확인하세요.",
                stacklevel=2,
            )
        return None

    topicRows = sec.filter(pl.col("topic") == topic)
    if topicRows.is_empty():
        if block in (None, 0):
            direct = showDirectTopic(company, topic, period=period, raw=raw)
            if isinstance(direct, pl.DataFrame):
                return direct
        warnUnknownTopic(topic, sec)
        return None

    if block is None:
        blockIndex = company._buildBlockIndex(topicRows)
        if blockIndex.height == 1:
            return company.show(topic, blockIndex["block"][0], period=period, raw=raw)
        # multi-block topic — sections frame slice (wide 시계열) 그대로 반환.
        # 이전 회귀 (block index 만 출력) 되돌림. block index 가 필요하면
        # ``company._buildBlockIndex(topicRows)`` 또는 ``c.show(topic, block=N)`` 명시 호출.
        period_cols = [c for c in topicRows.columns if _isPeriodColumn(c)]
        keep_meta = [c for c in ("blockOrder", "blockType", "textPath", "sourceTopic") if c in topicRows.columns]
        if keep_meta or period_cols:
            cleaned = topicRows.select(keep_meta + period_cols)
            if period and isinstance(period, str) and period in cleaned.columns:
                cleaned = cleaned.select(keep_meta + [period])
            if stripTags:
                from dartlab.providers.dart.docs.sections.xmlAdapter import stripTagsFromSectionsDf

                cleaned = stripTagsFromSectionsDf(cleaned)
            return cleaned
        if stripTags:
            from dartlab.providers.dart.docs.sections.xmlAdapter import stripTagsFromSectionsDf

            topicRows = stripTagsFromSectionsDf(topicRows)
        return topicRows

    boRows = topicRows.filter(pl.col("blockOrder") == block)
    if boRows.is_empty():
        return None

    source = boRows["source"][0] if "source" in boRows.columns else "docs"

    if source == "finance":
        result = showFinanceTopic(company, topic, period=period, freq=freq, scope=scope)
    elif source == "report":
        result = showReportTopic(company, topic, period=period, raw=raw)
    else:
        result = showSectionBlock(
            company,
            sec.filter(pl.col("topic") == topic),
            block=block,
            period=period,
        )

    if topic in FINANCE_CLEAN_TOPICS and isinstance(result, pl.DataFrame) and "항목" in result.columns:
        result = cleanFinanceDataFrame(result, topic)

    # stripTags 후처리 — show / agent / CLI 양식 (plain text). viewer 는 stripTags=False
    # 명시. 옛 호출자 영향 — sections cell 의 HTML 태그가 plain text 화 됨 (CLI 콘솔
    # 렌더 정상화).
    if stripTags and isinstance(result, pl.DataFrame):
        from dartlab.providers.dart.docs.sections.xmlAdapter import stripTagsFromSectionsDf

        result = stripTagsFromSectionsDf(result)

    return result if isinstance(result, pl.DataFrame) else None


def isStrongTopic(topic: str) -> bool:
    """topic 이 finance/notes/report 강한 소스인지 — c.panel facade 주입 라우팅 SSOT.

    panel facade(``c.panel``)가 ``c.panel("IS")`` 같은 호출을 raw 공시(panel) vs 강한 소스
    (finance/report — XBRL 정규화 숫자·정형 공시)로 가른다. 본 함수가 그 단일 판정 — show 와
    동일 분류 기준(``SHOW_FINANCE_TOPICS`` · ``_NOTES_DISPATCH`` · registry apiType)을 재사용해
    panel·show 가 한 SSOT 를 공유한다(분류 중복 0).

    Args:
        topic: 토픽 이름 (BS/IS/CF/ratios/inventory/dividend/canonicalKey/한글 섹션명 등).

    Returns:
        True 면 강한 소스(finance/notes/report — c.show 위임 대상), False 면 raw 공시(panel 행).

    Raises:
        없음 — registry 조회 실패는 False.

    Example:
        >>> isStrongTopic("IS")  # doctest: +SKIP
        True
        >>> isStrongTopic("NT_D826380")  # doctest: +SKIP  (canonicalKey → raw panel)
        False

    SeeAlso:
        - ``showImpl`` — 강한 소스의 실제 dispatch (finance/notes/report).
        - ``providers.dart.panel.Panel.__call__`` — 본 판정을 facade 주입으로 받아 라우팅.

    Requires:
        - dartlab. registry (report 판정).

    Capabilities:
        - panel·show 분류 SSOT — finance(BS/IS/…) · notes(inventory/…) · report(dividend/…) 식별.

    Guide:
        - facade(Company.panel)가 ``_strongFn`` 으로 주입. panel.py 는 직접 import 안 함(주입만).

    AIContext:
        - 순수 판정 — finance set ∪ notes dispatch ∪ (apiType 매핑되는) report.

    LLM Specifications:
        AntiPatterns:
            - panel.py 에서 직접 import 금지 — facade 가 _strongFn 으로 주입(panel 은 finance 모름).
            - 분류 중복 정의 금지 — SHOW_FINANCE_TOPICS·_NOTES_DISPATCH SSOT 재사용.
        OutputSchema:
            - ``bool``.
        Prerequisites:
            - registry (report apiType 판정).
        Freshness:
            - registry 변경 시 반영.
        Dataflow:
            - _resolveTopic → finance set / notes dispatch / apiType 매핑 → bool.
        TargetMarkets:
            - KR (DART). US 후속.
    """
    from dartlab.core.registry import getModuleEntries
    from dartlab.providers.dart.company import _resolveTopic
    from dartlab.providers.dart.notes import _NOTES_DISPATCH

    t = _resolveTopic(topic)
    if t in SHOW_FINANCE_TOPICS or t in _NOTES_DISPATCH:
        return True
    # report/notes/finance category = 정규화된 강한 소스 (dividend 등 정형 공시). disclosure(서술
    # docs)·canonicalKey·한글 섹션명은 raw 공시(panel 본분) → False.
    strongCats = {"finance", "report", "notes"}
    return any(e.name == t and getattr(e, "category", None) in strongCats for e in getModuleEntries())
