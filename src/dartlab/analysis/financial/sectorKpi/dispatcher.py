"""sectorKpi dispatcher — 업종 자동 감지 + 모듈 dispatch.

업종명/업종코드에서 sectorKpi 모듈 키를 매핑하고, 해당 모듈의 calc 함수를
호출해 dict 결과를 반환한다.
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

_SECTOR_MAP: dict[str, str] = {
    "건설업": "construction",
    "종합건설": "construction",
    "토목건설": "construction",
    "반도체": "semiconductor",
    "반도체와반도체장비": "semiconductor",
    "디스플레이": "semiconductor",
    "게임": "gaming",
    "인터넷": "gaming",
    "디지털콘텐츠": "gaming",
    "엔터테인먼트": "gaming",
    "제약": "pharma",
    "바이오": "pharma",
    "의약품": "pharma",
    "생물공학": "pharma",
}


def detectSector(company: Any) -> str | None:
    """업종명/업종코드에서 sectorKpi 모듈 키 반환.

    Capabilities:
        - industry 문자열 키워드 매칭 → sectorKpi 모듈명 (construction/semiconductor/gaming/pharma).

    Guide:
        company.industryName 또는 company.industry 에 _SECTOR_MAP 키 substring 검사.

    When:
        sectorKpi() 진입 직전 dispatch 키 확인.

    How:
        _SECTOR_MAP 순회 substring 매칭. 첫 히트 반환.

    Requires:
        company 가 industryName 또는 industry 속성을 가져야.

    Raises:
        없음. getattr 기본값 "" 처리.

    Returns:
        str | None — 모듈 키 ("construction" 등) 또는 미매칭 시 None.

    Example:
        >>> detectSector(company)
        "construction"

    See Also:
        - sectorKpi : 본 dispatch 키를 받아 실제 calc 호출.

    AIContext:
        섹터별 특화 KPI 라우팅 결정 근거.
    """
    industry = getattr(company, "industryName", "") or getattr(company, "industry", "") or ""
    for keyword, module in _SECTOR_MAP.items():
        if keyword in industry:
            return module
    return None


def sectorKpi(company: Any) -> dict | None:
    """업종 자동 감지 → 해당 모듈 dispatch → calc 결과 dict 반환.

    Capabilities:
        - detectSector → 4 모듈 (construction/semiconductor/gaming/pharma) 중 1 선택 호출.

    Guide:
        detectSector() 키로 lazy import 후 calc{Sector}Kpis 호출.

    When:
        업종 특화 분석 시 (일반 ratio 외에 도메인 KPI 필요).

    How:
        sector key switch → lazy import → calc 결과 wrap.

    Requires:
        company 가 sector 모듈 calc 함수 입력 계약 만족.

    Raises:
        없음. ImportError/AttributeError/ValueError/TypeError try 흡수 후 None.

    Returns:
        dict | None
            sector : str — 감지된 업종 ("construction" / "semiconductor" / ...)
            kpis : dict — 업종별 KPI dict

    Example:
        >>> sectorKpi(현대건설)
        {"sector": "construction", "kpis": {...}}

    See Also:
        - detectSector : 업종 키 매핑.

    AIContext:
        섹터 한정 deep-dive KPI 진입점.
    """
    sector = detectSector(company)
    if not sector:
        return None

    try:
        if sector == "construction":
            from dartlab.analysis.financial.sectorKpi.construction import calcConstructionKpis

            kpis = calcConstructionKpis(company)
        elif sector == "semiconductor":
            from dartlab.analysis.financial.sectorKpi.semiconductor import calcSemiconductorKpis

            kpis = calcSemiconductorKpis(company)
        elif sector == "gaming":
            from dartlab.analysis.financial.sectorKpi.gaming import calcGamingKpis

            kpis = calcGamingKpis(company)
        elif sector == "pharma":
            from dartlab.analysis.financial.sectorKpi.pharma import calcPharmaKpis

            kpis = calcPharmaKpis(company)
        else:
            return None
    except (ImportError, AttributeError, ValueError, TypeError) as e:
        log.debug("sectorKpi %s 실행 실패: %s", sector, e)
        return None

    if not kpis:
        return None
    return {"sector": sector, "kpis": kpis}
