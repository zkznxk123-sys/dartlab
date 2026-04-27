"""DART Company 의 finance 빌더 helpers.

Company 의 finance topic (BS/IS/CF/CIS/SCE/ratios) 빌드 로직을 facade 에서 분리.
Company facade 는 본 모듈의 함수에 thin delegate.

show("ratios") / show("BS") / show("CIS") 같은 finance topic 호출 → _showDispatch 가
이 모듈의 함수들로 dispatch (상위 facade method 경유).

Module-level functions:
    sceMatrix             — SCE 3차원 매트릭스 (캐시)
    sceSeriesAnnual       — SCE 연간 시계열 (캐시)
    sce                   — SCE DataFrame (분기/연도 정렬)
    financeCisAnnual      — CIS 연간 series (캐시)
    financeCisQuarterly   — CIS 분기 series (캐시)
    ratioSeries           — 비율 분기 series + 연간 fallback
    financeOrDocsStatement — finance 우선, docs fallback dispatch
    aggregateCisAnnual    — CIS 분기 → 연간 (4 분기 합)
    financeStmt           — sjDiv DataFrame (캐싱)
    buildRatios           — 비율 DataFrame 정렬
    buildFinanceSeries    — series-tuple 빌더 (Q/Y/YTD × CFS/OFS)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import polars as pl

from dartlab.providers.dart._finance_helpers import (
    _financeCisAnnual,
    _financeCisQuarterly,
    _financeToDataFrame,
    _ratioArchetypeOverrideForIndustryGroup,
    _ratioSeriesToDataFrame,
    _sceToDataFrame,
)
from dartlab.providers.dart._utils import _isPeriodColumn

if TYPE_CHECKING:
    from dartlab.providers.dart.company import Company


import re

_QUARTER_COL_RE = re.compile(r"^(\d{4})Q[1-4]$")


# ── SCE ──────────────────────────────────────────────────────────


def sceMatrix(company: Company):
    if not company._hasFinance:
        return None
    cacheKey = "_sceMatrix_CFS"
    if cacheKey in company._cache:
        return company._cache[cacheKey]
    from dartlab.providers.dart.finance.pivot import buildSceMatrix

    result = buildSceMatrix(company.stockCode)
    company._cache[cacheKey] = result
    return result


def sceSeriesAnnual(company: Company):
    if not company._hasFinance:
        return None
    cacheKey = "_sceAnnual_CFS"
    if cacheKey in company._cache:
        return company._cache[cacheKey]
    from dartlab.providers.dart.finance.pivot import buildSceAnnual

    result = buildSceAnnual(company.stockCode)
    company._cache[cacheKey] = result
    return result


def sce(company: Company) -> pl.DataFrame | None:
    cacheKey = "_sceDataFrame_CFS"
    if cacheKey in company._cache:
        return company._cache[cacheKey]
    result = sceSeriesAnnual(company)
    if result is None:
        company._cache[cacheKey] = None
        return None
    series, years = result
    df = _sceToDataFrame(series, years)
    if df is not None:
        # 컬럼 정렬: 메타 컬럼 + 연도 역순 (최신 → 과거) — IS/BS/CF 와 일관성
        metaCols = [c for c in df.columns if not (c.isdigit() and len(c) == 4)]
        yearCols = sorted([c for c in df.columns if c.isdigit() and len(c) == 4], reverse=True)
        df = df.select(metaCols + yearCols)
    company._cache[cacheKey] = df
    return df


# ── CIS ──────────────────────────────────────────────────────────


def financeCisAnnual(company: Company):
    if not company._hasFinance:
        return None
    cacheKey = "_financeCISAnnual_CFS"
    if cacheKey in company._cache:
        return company._cache[cacheKey]
    result = _financeCisAnnual(company.stockCode, "CFS")
    company._cache[cacheKey] = result
    return result


def financeCisQuarterly(company: Company):
    """CIS 분기별 시계열 (연간 합산 없이)."""
    if not company._hasFinance:
        return None
    cacheKey = "_financeCISQuarterly_CFS"
    if cacheKey in company._cache:
        return company._cache[cacheKey]
    result = _financeCisQuarterly(company.stockCode, "CFS")
    company._cache[cacheKey] = result
    return result


def aggregateCisAnnual(qDf: pl.DataFrame) -> pl.DataFrame | None:
    """CIS 분기 DataFrame → 연간 (4분기 합)."""
    yearGroups: dict[str, list[str]] = {}
    for col in qDf.columns:
        m = _QUARTER_COL_RE.match(col)
        if m:
            yearGroups.setdefault(m.group(1), []).append(col)
    if not yearGroups:
        return None
    # 4분기 모두 있는 연도만 합산 (strict)
    years = sorted([y for y, qs in yearGroups.items() if len(qs) == 4], reverse=True)
    if not years:
        return None
    metaCols = [c for c in qDf.columns if not _QUARTER_COL_RE.match(c)]
    exprs = [pl.col(c) for c in metaCols]
    for year in years:
        qs = sorted(yearGroups[year])
        exprs.append(pl.sum_horizontal([pl.col(q) for q in qs]).alias(year))
    return qDf.select(exprs)


# ── Ratios ───────────────────────────────────────────────────────


def ratioSeries(company: Company):
    if not company._hasFinance:
        return None
    cacheKey = "_ratioSeries_Q_CFS"
    if cacheKey in company._cache:
        return company._cache[cacheKey]
    qResult = buildFinanceSeries(company, freq="Q")
    if qResult is None:
        return None
    qSeries, periods = qResult
    # 2016-Q1 → 2016Q1 포맷 통일
    normalizedPeriods = [p.replace("-", "") for p in periods]
    from dartlab.analysis.financial.ratios import calcRatioSeries, toSeriesDict

    archetypeOverride = _ratioArchetypeOverrideForIndustryGroup(getattr(company.sector, "industryGroup", None))
    rs = calcRatioSeries(qSeries, normalizedPeriods, archetypeOverride=archetypeOverride, yoyLag=4)
    result = toSeriesDict(rs)
    company._cache[cacheKey] = result
    return result


def buildRatios(company: Company) -> pl.DataFrame | None:
    """[INTERNAL] 재무비율 DataFrame 빌더.

    사용자는 ``c.show("ratios")`` 호출. show() 가 finance topic dispatch 에서
    이 빌더를 호출.
    """
    rs = ratioSeries(company)
    if rs is None:
        return None
    series, periods = rs
    df = _ratioSeriesToDataFrame(series, periods)
    if df is not None:
        metaCols = [c for c in df.columns if not _isPeriodColumn(c)]
        periodCols = [c for c in df.columns if _isPeriodColumn(c)]
        periodCols.sort(key=lambda p: (int(p[:4]), int(p[-1])), reverse=True)
        df = df.select(metaCols + periodCols)
    return df


# ── Statement (BS/IS/CF/CIS) build/dispatch ──────────────────────


def financeStmt(company: Company, sjDiv: str, *, freq: str = "Q", scope: str = "consolidated") -> pl.DataFrame | None:
    """finance 시계열에서 sjDiv DataFrame 생성 (캐싱).

    Internal helper. show("IS", freq=, scope=) 진입점이 호출.
    """
    cacheKey = f"_financeStmt_{sjDiv}_{freq}_{scope}"
    if cacheKey in company._cache:
        return company._cache[cacheKey]
    qResult = buildFinanceSeries(company, freq=freq, scope=scope)
    if qResult is None:
        return None
    series, periods = qResult
    # 2016-Q1 → 2016Q1 포맷 통일
    normalizedPeriods = [str(p).replace("-", "") for p in periods]
    df = _financeToDataFrame(series, normalizedPeriods, sjDiv)
    company._cache[cacheKey] = df
    return df


def financeOrDocsStatement(
    company: Company, sjDiv: str, *, freq: str = "Q", scope: str = "consolidated"
) -> pl.DataFrame | None:
    # CIS 는 별도 quarterly 캐시 — annual 은 4분기 합산 합성
    if sjDiv == "CIS" and scope == "consolidated":
        cisQ = financeCisQuarterly(company) if company._hasFinance else None
        if cisQ is not None:
            series, periods = cisQ
            normalizedPeriods = [p.replace("-", "") for p in periods]
            df = _financeToDataFrame(series, normalizedPeriods, "CIS")
            if df is not None and freq == "Y":
                df = aggregateCisAnnual(df)
            if df is not None:
                return df
    df = financeStmt(company, sjDiv, freq=freq, scope=scope) if company._hasFinance else None
    if df is not None:
        return df
    # docs fallback 은 분기 연결만 지원
    if freq == "Q" and scope == "consolidated":
        r = company._call_module("statements")
        return getattr(r, sjDiv, None) if r else None
    return None


def buildFinanceSeries(company: Company, *, freq: str = "Q", scope: str = "consolidated"):
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
    if freq not in ("Q", "Y", "YTD"):
        raise ValueError(f"freq 는 'Q' / 'Y' / 'YTD' 중 하나여야 합니다 (받음: {freq!r})")
    if scope not in ("consolidated", "separate"):
        raise ValueError(f"scope 는 'consolidated' / 'separate' 중 하나여야 합니다 (받음: {scope!r})")
    if not company._hasFinance:
        return None
    _periodMap = {"Q": "q", "Y": "y", "YTD": "cum"}
    _scopeMap = {"consolidated": "CFS", "separate": "OFS"}
    return company._getFinanceBuild(_periodMap[freq], _scopeMap[scope])
