"""EDGAR Company 의 show dispatch + finance/ratio builders + period helpers.

Company facade 의 show 본체와 finance 빌더, period filter, preview helper 를
같이 옮긴다. Company facade 는 thin delegate.

Module-level functions:
    showImpl              — c.show(topic, ...) 사용자 진입점 본체
    buildFinanceSeries    — finance series-tuple 빌더 (Q/Y/YTD)
    buildRatios           — 재무비율 DataFrame
    applyPeriodFilter     — period 필터 (Q4 fallback 포함)
    transposeToVertical   — wide → long (period 리스트)
    buildBlockIndex       — topic blockOrder 목차
    shapeStr / periodsStr / previewFinance / previewDocsCell — preview helpers
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import polars as pl

from dartlab.core.polarsUtil import isEmptyDf

if TYPE_CHECKING:
    from dartlab.providers.edgar.company import Company

import re

_PERIOD_COLUMN_RE = re.compile(r"^\d{4}(Q[1-4])?$")


def _isPeriodColumn(col: str) -> bool:
    return bool(_PERIOD_COLUMN_RE.fullmatch(col))


# ── finance builders ───────────────────────────────────────────────


def buildFinanceSeries(company: Company, *, freq: str = "Q", scope: str = "consolidated"):
    """[INTERNAL] EDGAR finance series-tuple 빌더.

    사용자 진입점은 ``c.show("IS", freq=, scope=)`` 만이다 (api-contract).
    EDGAR 는 ``scope="separate"`` 미지원 (SEC 는 연결만 보고).
    ``freq="YTD"`` 도 미지원 — annual 로 fallback.
    """
    if freq not in ("Q", "Y", "YTD"):
        raise ValueError(f"freq 는 'Q' / 'Y' / 'YTD' 중 하나 (받음: {freq!r})")
    if scope == "separate":
        raise ValueError("EDGAR 는 scope='separate' 미지원 — SEC 는 연결만 보고")
    if scope != "consolidated":
        raise ValueError(f"scope 는 'consolidated' / 'separate' 중 하나 (받음: {scope!r})")
    # EDGAR _FinanceAccessor 는 freq 옵션 직접 지원
    if freq == "Q":
        if "_ts" not in company._cache:
            from dartlab.providers.edgar.finance.pivot import buildTimeseries

            company._cache["_ts"] = buildTimeseries(company.cik)
        return company._cache.get("_ts")
    # Y / YTD → annual
    if "_annual" not in company._cache:
        from dartlab.providers.edgar.finance.pivot import buildAnnual

        company._cache["_annual"] = buildAnnual(company.cik)
    return company._cache["_annual"]


def buildRatios(company: Company) -> pl.DataFrame | None:
    """[INTERNAL] EDGAR 재무비율 DataFrame 빌더 — show("ratios") 가 호출."""
    from dartlab.providers.edgar.company import _ratioSeriesToDataFrame

    rs = company._finance.ratioSeries
    if rs is None:
        return None
    series, years = rs
    df = _ratioSeriesToDataFrame(series, years)
    if df is not None:
        metaCols = [c for c in df.columns if not _isPeriodColumn(c)]
        periodCols = [c for c in df.columns if _isPeriodColumn(c)]
        periodCols.sort(reverse=True)
        df = df.select(metaCols + periodCols)
    return df


# ── period filter / transpose / block index ────────────────────────


def applyPeriodFilter(payload: Any, period: str | None) -> Any:
    if period is None or not isinstance(payload, pl.DataFrame) or payload.is_empty():
        return payload
    requestedPeriod = str(period)
    q4Fallback = f"{requestedPeriod}Q4" if "Q" not in requestedPeriod else None
    exactPeriod = (
        requestedPeriod
        if requestedPeriod in payload.columns
        else (q4Fallback if q4Fallback and q4Fallback in payload.columns else None)
    )
    if exactPeriod is not None:
        keepCols = [c for c in payload.columns if not _isPeriodColumn(c)]
        keepCols.append(exactPeriod)
        result = payload.select(keepCols)
        if exactPeriod != requestedPeriod:
            result = result.rename({exactPeriod: requestedPeriod})
        return result
    return payload


def transposeToVertical(wide: pl.DataFrame, periods: list[str]) -> pl.DataFrame | None:
    from dartlab.core.show import transposeToVertical as _coreTranspose

    return _coreTranspose(wide, periods)


def buildBlockIndex(topicRows: pl.DataFrame) -> pl.DataFrame:
    """topic의 블록 목차 DataFrame."""
    from dartlab.core.show import buildBlockIndex as _coreBuildBlockIndex

    return _coreBuildBlockIndex(topicRows)


# ── preview helpers ────────────────────────────────────────────────


def shapeStr(df: pl.DataFrame | None) -> str:
    if df is None:
        return "-"
    return f"{df.height}x{df.width}"


def periodsStr(df: pl.DataFrame | None) -> str:
    if df is None:
        return "-"
    periodCols = [c for c in df.columns if _PERIOD_COLUMN_RE.fullmatch(c)]
    if not periodCols:
        return "-"
    return f"{periodCols[0]}..{periodCols[-1]}" if len(periodCols) > 1 else periodCols[0]


def previewFinance(df: pl.DataFrame | None) -> str:
    if isEmptyDf(df):
        return "-"
    return f"{df.height} accounts"


def previewDocsCell(topicRows: pl.DataFrame, periodCols: list[str]) -> str:
    for row in topicRows.iter_rows(named=True):
        for col in periodCols:
            val = row.get(col)
            if val is not None:
                text = str(val).strip().replace("\n", " ")
                return f"{col}: {text[:100]}" if len(text) > 100 else f"{col}: {text[:80]}"
    return "-"


# ── show 진입점 ────────────────────────────────────────────────────


_SHOW_FINANCE_TOPICS = frozenset({"IS", "BS", "CF", "CIS", "SCE", "ratios"})


def showImpl(
    company: Company,
    topic: str,
    block: int | None = None,
    *,
    period: str | list[str] | None = None,
    raw: bool = False,
    **_kw: Any,
) -> pl.DataFrame | None:
    """topic 데이터 조회 — c.show 의 내부 구현 본체."""
    from dartlab.providers.edgar.company import _TOPIC_ALIASES

    # alias 해석 (riskFactors → item1ARiskFactors 등)
    topic = _TOPIC_ALIASES.get(topic, topic)

    # period가 리스트면 세로 뷰
    if isinstance(period, list):
        wide = company.show(topic, block)
        if wide is None or not isinstance(wide, pl.DataFrame):
            return None
        return transposeToVertical(wide, period)

    # Finance topic(IS/BS/CF/CIS/SCE/ratios) — sections 거치지 않고 직접
    if topic in _SHOW_FINANCE_TOPICS:
        freq = _kw.get("freq", "Q")
        if topic == "ratios":
            df = buildRatios(company)
        elif topic == "SCE":
            df = company._finance.SCE
        else:
            df = company._finance._stmtDf(topic, freq=freq)
        return applyPeriodFilter(df, period) if df is not None else None

    # Notes 12 항목 — DART show("inventory") 와 동일 패턴 (XBRL 수치 태그 기반)
    try:
        from dartlab.providers.edgar.docs.notesParsers import availableCategories

        if topic in availableCategories():
            return company._docs.notesByCategory(topic)
    except (ImportError, AttributeError):
        pass

    sec = company.sections
    if sec is None:
        # silent None 대신 명시적 ValueError 로 안내
        raise ValueError(
            f"sections 데이터를 가져올 수 없습니다 (ticker={getattr(company, 'ticker', '?')}). "
            f"네트워크 또는 SEC EDGAR API 상태를 확인하세요."
        )

    topicRows = sec.filter(pl.col("topic") == topic)
    if topicRows.is_empty():
        # 가용 topic 일부 안내 (silent None 차단)
        try:
            available = sec["topic"].unique().to_list()[:20]
        except (AttributeError, KeyError):
            available = []
        hint = f"\n  사용 가능한 topic 일부: {', '.join(available)}" if available else ""
        raise ValueError(
            f"'{topic}' topic 을 찾을 수 없습니다 (EDGAR).{hint}\n  전체 목록: c.topics 또는 c.index 로 확인하세요."
        )

    if block is None:
        blockIndex = buildBlockIndex(topicRows)
        if blockIndex.height == 1:
            return company.show(topic, blockIndex["block"][0], period=period)
        return blockIndex

    # 특정 block의 실제 데이터
    source = "docs"
    if "source" in topicRows.columns:
        srcRows = topicRows.filter(pl.col("blockOrder") == block) if "blockOrder" in topicRows.columns else topicRows
        if not srcRows.is_empty():
            source = srcRows["source"][0]

    if source == "finance":
        freq = _kw.get("freq", "Q")
        if topic == "ratios":
            df = buildRatios(company)
            return applyPeriodFilter(df, period) if df is not None else None
        if topic == "SCE":
            df = company._finance.SCE
            return applyPeriodFilter(df, period) if df is not None else None
        df = company._finance._stmtDf(topic, freq=freq)
        return applyPeriodFilter(df, period) if df is not None else None

    # docs — blockType에 따라 text/table 반환
    periodCols = [c for c in topicRows.columns if _isPeriodColumn(c)]
    if "blockType" in topicRows.columns:
        # blockOrder로 필터 (None이면 blockType으로 대체)
        bt = "text"
        if "blockOrder" in topicRows.columns:
            boFiltered = topicRows.filter(pl.col("blockOrder") == block)
            if not boFiltered.is_empty():
                bt = boFiltered["blockType"][0]
            else:
                # blockOrder가 None인 경우 — 인덱스로 접근
                btList = topicRows["blockType"].to_list()
                bt = btList[block] if block < len(btList) else "text"

        if bt == "text":
            textRows = topicRows.filter(pl.col("blockType") == "text")
            if textRows.is_empty():
                return None
            nonNullCols = [c for c in periodCols if textRows[c].null_count() < textRows.height]
            if not nonNullCols:
                return None
            return applyPeriodFilter(textRows.select(nonNullCols), period)
        else:
            tableRows = topicRows.filter(pl.col("blockType") == "table")
            if tableRows.is_empty():
                return None
            nonNullCols = [c for c in periodCols if tableRows[c].null_count() < tableRows.height]
            if not nonNullCols:
                return None
            return applyPeriodFilter(tableRows.select(nonNullCols), period)

    return applyPeriodFilter(topicRows, period)
