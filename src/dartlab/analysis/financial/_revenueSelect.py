"""revenue.py 의 docs/select 헬퍼 + 공유 상수.

revenue.py facade + _revenueSegment / _revenueGrowth / _revenueQuality 가 본 모듈을 import.
순환 import 방지를 위해 _revenueHelpers 는 함수 내부에서 deferred import.
"""

from __future__ import annotations

from dartlab.core.utils.helpers import (
    annualColsFromPeriods as _annualColsFromPeriods,
)
from dartlab.core.utils.helpers import (
    parseNumStr as _parseNumStr,
)

_MAX_SEGMENTS = 8
_MAX_YEARS = 8

_SKIP_KEYWORDS = {"합계", "조정", "내부", "소계", "총계", "부문계", "기타", "국내외"}


def _getRatios(company):
    """ratios 객체 (RatioResult) 를 안전하게 가져온다 — internal 사용.

    Returns
    -------
    RatioResult | None
        회사의 재무비율 객체. 데이터 없으면 None.
    """
    try:
        return company._getRatiosInternal()
    except (ValueError, KeyError, AttributeError):
        return None


def _selectDocsRevenue(
    company, *, basePeriod: str | None = None
) -> tuple[dict[str, dict[str, float]], list[str]] | None:
    """productService/salesOrder 토픽에서 부문별 매출 시계열을 추출.

    DART 전용 경로. EDGAR(US) 는 SEC companyfacts API 가 XBRL segment
    dimension(axis/member) 을 제공하지 않아 segment 분해 불가 — None 반환.
    (EDGAR segment 지원은 10-K 본문 파싱 별도 파이프라인 필요.)

    Returns
    -------
    tuple[dict[str, dict[str, float]], list[str]] | None
        ``(segData, annualCols)`` 튜플.
        segData : dict — ``{부문명: {period: 매출액(원)}}`` 매핑.
        annualCols : list[str] — 최신순 정렬된 연간 컬럼 목록.
        데이터 없으면 None.
    """
    for topic in ("productService", "salesOrder"):
        try:
            result = company.select(topic, ["매출액"])
        except (ValueError, KeyError):
            result = None
        if result is None:
            continue
        parsed = _parseDocsRevenueResult(result, basePeriod=basePeriod)
        if parsed is not None:
            return parsed

    return None


def _parseDocsRevenueResult(
    result, *, basePeriod: str | None = None
) -> tuple[dict[str, dict[str, float]], list[str]] | None:
    """docs select 결과에서 부문별 매출 시계열 파싱.

    Returns
    -------
    tuple[dict[str, dict[str, float]], list[str]] | None
        ``(segData, annualCols)`` 튜플. 파싱 실패 시 None.
    """
    df = result.df
    if df.is_empty():
        return None

    itemCol = df.columns[0]
    pCols = [c for c in df.columns if c != itemCol]
    yCols = _annualColsFromPeriods(pCols, basePeriod, _MAX_YEARS)
    if not yCols:
        return None

    segData: dict[str, dict[str, float]] = {}
    for row in df.iter_rows(named=True):
        rawItem = str(row.get(itemCol, ""))
        if any(kw in rawItem for kw in _SKIP_KEYWORDS):
            continue
        segName = rawItem.replace("_매출액", "").strip()
        if not segName:
            continue

        vals: dict[str, float] = {}
        for yc in yCols:
            v = _parseNumStr(row.get(yc))
            if v is not None and v > 0:
                vals[yc] = v
        if vals:
            segData[segName] = vals

    if not segData:
        return None
    return segData, yCols


def _selectDocsOpIncome(company, yCols: list[str]) -> dict[str, dict[str, float]] | None:
    """productService/salesOrder에서 부문별 영업이익 시계열을 추출 (있는 기업만).

    Returns
    -------
    dict[str, dict[str, float]] | None
        ``{부문명: {period: 영업이익(원)}}`` 매핑. 데이터 없으면 None.
    """
    for topic in ("productService", "salesOrder"):
        result = company.select(topic, ["영업이익", "영업손익"], strict=False)
        if result is None:
            continue
        df = result.df
        if df.is_empty():
            continue

        itemCol = df.columns[0]
        opData: dict[str, dict[str, float]] = {}
        for row in df.iter_rows(named=True):
            rawItem = str(row.get(itemCol, ""))
            if any(kw in rawItem for kw in _SKIP_KEYWORDS):
                continue
            segName = rawItem.replace("_영업이익", "").replace("_영업손익", "").strip()
            if not segName:
                continue
            vals: dict[str, float] = {}
            for yc in yCols:
                v = _parseNumStr(row.get(yc))
                if v is not None:
                    vals[yc] = v
            if vals:
                opData[segName] = vals

        if opData:
            return opData
    return None


def _selectDocsSalesOrder(company, keyword: str | None = None):
    """salesOrder에서 항목별 매출 시계열을 추출.

    Returns
    -------
    SelectResult | None
        select() 결과 객체. 데이터 없으면 None.
    """
    if keyword:
        result = company.select("salesOrder", [keyword])
    else:
        result = company.select("salesOrder", colList=None)
    if result is None:
        return None
    return result
