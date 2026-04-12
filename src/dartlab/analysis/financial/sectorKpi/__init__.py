"""업종별 KPI 모듈 — 범용 14축으로 안 잡히는 업종 특수 지표.

4개 업종 지원: 건설 / 반도체 / 게임·엔터 / 제약·바이오.
각 모듈은 2~4 calc 함수를 제공하며, sectorKpi(company)가 업종 자동 감지 후 dispatch.
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
    """업종명/업종코드에서 sectorKpi 모듈 키 반환."""
    industry = getattr(company, "industryName", "") or getattr(company, "industry", "") or ""
    for keyword, module in _SECTOR_MAP.items():
        if keyword in industry:
            return module
    return None


def sectorKpi(company: Any) -> dict | None:
    """업종 자동 감지 → 해당 모듈 dispatch → calc 결과 dict 반환.

    Returns
    -------
    dict | None
        sector : str — 감지된 업종 ("construction" / "semiconductor" / ...)
        kpis : dict — 업종별 KPI dict
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
