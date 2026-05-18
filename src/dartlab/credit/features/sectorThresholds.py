"""업종별 신용등급 기준표 — facade. 본체는 `_sectorThresholdsA` / `_sectorThresholdsB`.

KIS/KR/NICE + Moody's/S&P 공개 방법론을 종합하여
업종 대분류별 핵심 재무지표의 등급 구간을 정의한다.

등급 구간은 Moody's 선형 보간 방식(linear interpolation)으로
연속적 점수(0-100)를 산출한다. 값이 클수록 위험(100=D, 0=AAA).

각 지표별 방향:
- lower_is_better=True: 값이 낮을수록 좋다 (예: Debt/EBITDA)
- lower_is_better=False: 값이 높을수록 좋다 (예: ICR, 유동비율)
"""

from __future__ import annotations

from dartlab.credit.features._sectorThresholdsA import (
    _SECTOR_THRESHOLDS,
    _constructionThresholds,
    _defaultThresholds,
    _energyThresholds,
    _financialsThresholds,
    _itThresholds,
    _utilitiesThresholds,
)
from dartlab.credit.features._sectorThresholdsB import (
    _INDUSTRY_THRESHOLDS,
    _airlineThresholds,
    _autoThresholds,
    _holdingThresholds,
    _metalsThresholds,
    _semiconductorThresholds,
    _shipbuildingThresholds,
    _telecomThresholds,
    financialTrackBThresholds,
)
from dartlab.frame.sector import IndustryGroup, Sector


def getThresholds(sector: Sector | None, industryGroup: IndustryGroup | None = None) -> dict:
    """업종별 기준표 반환.

    Capabilities:
        IndustryGroup override (반도체/조선/은행 등 13 개) 가 있으면 우선, 없으면 Sector 대분류
        기본값. 둘 다 None 이면 ``_defaultThresholds`` 폴백. credit 7 축 metric 의 임계값 dict
        단일 진입점.

    IndustryGroup override가 있으면 우선, 없으면 Sector 대분류 사용.

    Args:
        sector: 대분류 Sector enum (없으면 _defaultThresholds).
        industryGroup: 세부 IndustryGroup enum (없으면 sector 사용).

    Returns:
        업종별 metric → breakpoints dict.

    Raises:
        없음.

    Example:
        >>> from dartlab.credit.features.sectorThresholds import getThresholds
        >>> th = getThresholds(None, IndustryGroup.SEMICONDUCTOR)
        >>> th["debt_to_ebitda"]["lower_is_better"]
        True

    Guide:
        Track A 7 축 metric 점수 산정 시 본 기준표의 breakpoints 를 piecewise linear 로 적용.

    When:
        ``credit.engine.evaluateCompany`` 가 ``_getSectorInfo`` 후 본 함수 호출.

    How:
        industryGroup override 우선 → sector 매핑 → 둘 다 부재 시 default.

    Requires:
        - 외부 의존 없음 (정적 dict 룩업).

    See Also:
        - ``dartlab.credit.features.sectorThresholds.getSectorLabel`` : 한국어 라벨

    AIContext:
        AI 답변 시 업종 임계값을 "반도체 업종 기준 D/EBITDA < 3 양호" 식으로 명시.
    """
    if industryGroup is not None and industryGroup in _INDUSTRY_THRESHOLDS:
        return _INDUSTRY_THRESHOLDS[industryGroup]
    if sector is None:
        return _defaultThresholds()
    return _SECTOR_THRESHOLDS.get(sector, _defaultThresholds())


def getSectorLabel(sector: Sector | None) -> str:
    """업종 라벨 반환.

    Raises:
        없음.

    Example:
        >>> from dartlab.credit.features.sectorThresholds import getSectorLabel
        >>> getSectorLabel(None)
        '일반'

    Requires:
        - 외부 의존 없음.
    """
    if sector is None:
        return "일반"
    return sector.value


__all__ = [
    "_INDUSTRY_THRESHOLDS",
    "_SECTOR_THRESHOLDS",
    "_airlineThresholds",
    "_autoThresholds",
    "_constructionThresholds",
    "_defaultThresholds",
    "_energyThresholds",
    "_financialsThresholds",
    "_holdingThresholds",
    "_itThresholds",
    "_metalsThresholds",
    "_semiconductorThresholds",
    "_shipbuildingThresholds",
    "_telecomThresholds",
    "_utilitiesThresholds",
    "financialTrackBThresholds",
    "getSectorLabel",
    "getThresholds",
]
