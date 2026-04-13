"""core/sector 호환 인터페이스 — 완전 자립.

core/sector의 classify(), getParams(), getThresholds()와 동일한 시그니처.
sectorParams.json + thresholds.json에서 데이터를 읽는다.
core/sector에 대한 의존 0.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).parent


# ── Enum ──


class Sector(str, Enum):
    ENERGY = "에너지"
    MATERIALS = "소재"
    INDUSTRIALS = "산업재"
    CONSUMER_DISC = "경기관련소비재"
    CONSUMER_STAPLES = "필수소비재"
    HEALTHCARE = "건강관리"
    FINANCIALS = "금융"
    IT = "IT"
    COMMUNICATION = "커뮤니케이션서비스"
    UTILITIES = "유틸리티"
    REAL_ESTATE = "부동산"
    UNKNOWN = "기타"


class IndustryGroup(str, Enum):
    """WICS 중분류 — core/sector/types.py 원본과 동일한 멤버명."""

    # 에너지
    ENERGY_EQUIP = "에너지장비및서비스"
    OIL_GAS = "석유와가스"
    # 소재
    CHEMICAL = "화학"
    CONSTRUCTION_MATERIALS = "건설자재"
    CONTAINERS = "용기와포장"
    METALS = "금속과광물"
    PAPER = "종이와목재"
    # 산업재
    CAPITAL_GOODS = "자본재"
    COMMERCIAL_SERVICE = "상업서비스와공급품"
    TRANSPORTATION = "운송"
    AEROSPACE_DEFENSE = "항공우주와국방"
    CONSTRUCTION = "건설"
    MACHINERY = "기계"
    SHIPBUILDING = "조선"
    # 경기관련소비재
    AUTO = "자동차와부품"
    CONSUMER_DURABLES = "내구소비재와의류"
    CONSUMER_SERVICE = "소비자서비스"
    MEDIA_ENTERTAINMENT = "미디어와엔터테인먼트"
    RETAIL = "소매(유통)"
    HOTEL_LEISURE = "호텔,레스토랑,레저"
    # 필수소비재
    FOOD_STAPLES = "식품과기본식료품소매"
    FOOD_BEV_TOBACCO = "식품,음료,담배"
    HOUSEHOLD = "가정용품과개인용품"
    # 건강관리
    HEALTHCARE_EQUIP = "건강관리장비와서비스"
    PHARMA_BIO = "제약과바이오"
    # 금융
    BANK = "은행"
    DIVERSIFIED_FINANCIALS = "다각화된금융"
    INSURANCE = "보험"
    # IT
    SOFTWARE = "소프트웨어와서비스"
    TECH_HARDWARE = "기술하드웨어와장비"
    SEMICONDUCTOR = "반도체와반도체장비"
    IT_SERVICE = "IT서비스"
    DISPLAY = "디스플레이"
    # 커뮤니케이션서비스
    TELECOM = "전기통신서비스"
    MEDIA = "미디어"
    INTERNET = "인터넷과카탈로그소매"
    GAME = "게임엔터테인먼트"
    # 유틸리티
    UTILITIES = "유틸리티"
    ELECTRIC = "전력"
    GAS_UTILITY = "가스"
    # 부동산
    REAL_ESTATE = "부동산"
    REIT = "리츠"
    # 기타
    UNKNOWN = "기타"


@dataclass
class SectorInfo:
    sector: Sector
    industryGroup: IndustryGroup
    confidence: float
    source: str


@dataclass
class SectorParams:
    discountRate: float = 10.0
    growthRate: float = 3.0
    perMultiple: float = 15
    pbrMultiple: float = 1.2
    evEbitdaMultiple: float = 8
    beta: float = 1.0
    exitMultiple: float = 8.0
    label: str = ""


# ── 데이터 로드 ──


@lru_cache(maxsize=1)
def _loadSectorData() -> dict:
    return json.loads((_DATA_DIR / "sectorParams.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _loadThresholds() -> dict:
    return json.loads((_DATA_DIR / "thresholds.json").read_text(encoding="utf-8"))


def _byValue(cls: type, val: str, default: Any = None) -> Any:
    for m in cls:
        if m.value == val:
            return m
    return default


# ── classify ──


def classify(
    companyName: str,
    kindIndustry: str | None = None,
    mainProducts: str | None = None,
) -> SectorInfo:
    """회사명/업종/주요제품으로 섹터 분류. core/sector 의존 0."""
    data = _loadSectorData()

    # 1. 수동 override
    overrides = data.get("manualOverrides", {})
    if companyName in overrides:
        ov = overrides[companyName]
        return SectorInfo(
            sector=_byValue(Sector, ov["sector"], Sector.UNKNOWN),
            industryGroup=_byValue(IndustryGroup, ov["industryGroup"], IndustryGroup.UNKNOWN),
            confidence=1.0,
            source="override",
        )

    # 1.5 부분명 매칭
    for name, ov in overrides.items():
        if name in companyName or companyName in name:
            return SectorInfo(
                sector=_byValue(Sector, ov["sector"], Sector.UNKNOWN),
                industryGroup=_byValue(IndustryGroup, ov["industryGroup"], IndustryGroup.UNKNOWN),
                confidence=0.95,
                source="override",
            )

    # 2. 주요제품 키워드 매칭 (KSIC보다 우선 — 더 구체적)
    if mainProducts:
        result = _matchProductKeywords(mainProducts, data.get("productKeywords", {}))
        if result:
            sector, ig, score = result
            return SectorInfo(
                sector=_byValue(Sector, sector, Sector.UNKNOWN),
                industryGroup=_byValue(IndustryGroup, ig, IndustryGroup.UNKNOWN),
                confidence=min(0.9, 0.6 + score * 0.1),
                source="keyword",
            )

    # 3. KSIC 매핑
    if kindIndustry:
        ksicMap = data.get("ksicMapping", {})
        for ksic, mapping in ksicMap.items():
            if ksic in kindIndustry or kindIndustry in ksic:
                return SectorInfo(
                    sector=_byValue(Sector, mapping["sector"], Sector.UNKNOWN),
                    industryGroup=_byValue(IndustryGroup, mapping["industryGroup"], IndustryGroup.UNKNOWN),
                    confidence=0.7,
                    source="ksic",
                )

    return SectorInfo(sector=Sector.UNKNOWN, industryGroup=IndustryGroup.UNKNOWN, confidence=0.0, source="unknown")


def _matchProductKeywords(
    products: str,
    keywordMap: dict[str, list[str]],
) -> tuple[str, str, int] | None:
    """주요제품 텍스트에서 키워드 매칭. sector|ig 키 → 점수."""
    if not products:
        return None

    productsLower = products.lower()
    best: tuple[str, str, int] | None = None
    bestScore = 0

    for key, keywords in keywordMap.items():
        parts = key.split("|")
        if len(parts) != 2:
            continue
        sector, ig = parts
        score = sum(1 for kw in keywords if kw.lower() in productsLower)
        if score > bestScore:
            bestScore = score
            best = (sector, ig, score)

    return best if best and bestScore > 0 else None


# ── getParams ──


def getParams(sectorInfo: SectorInfo | None = None) -> SectorParams:
    """섹터별 밸류에이션 파라미터. IndustryGroup 우선, Sector fallback."""
    data = _loadSectorData()
    sp = data.get("sectorParams", {})
    igp = data.get("industryGroupParams", {})

    if sectorInfo is None:
        return SectorParams()

    igVal = sectorInfo.industryGroup.value if sectorInfo.industryGroup else ""
    if igVal in igp:
        p = igp[igVal]
        return SectorParams(
            discountRate=p["discountRate"],
            growthRate=p["growthRate"],
            perMultiple=p["perMultiple"],
            pbrMultiple=p["pbrMultiple"],
            evEbitdaMultiple=p["evEbitdaMultiple"],
            beta=p["beta"],
            exitMultiple=p["exitMultiple"],
            label=p.get("label", ""),
        )

    sVal = sectorInfo.sector.value if sectorInfo.sector else ""
    if sVal in sp:
        p = sp[sVal]
        return SectorParams(
            discountRate=p["discountRate"],
            growthRate=p["growthRate"],
            perMultiple=p["perMultiple"],
            pbrMultiple=p["pbrMultiple"],
            evEbitdaMultiple=p["evEbitdaMultiple"],
            beta=p["beta"],
            exitMultiple=p["exitMultiple"],
            label=p.get("label", ""),
        )

    return SectorParams()


@dataclass(frozen=True)
class MarketParams:
    """국가별 시장 파라미터 — core/sector/types.py 호환."""

    riskFreeRate: float
    equityRiskPremium: float
    countryRiskPremium: float
    defaultTaxRate: float
    gdpGrowth: float

    @property
    def totalErp(self) -> float:
        return self.equityRiskPremium + self.countryRiskPremium

    def ke(self, beta: float = 1.0) -> float:
        return self.riskFreeRate + beta * self.totalErp


MARKET_KR = MarketParams(riskFreeRate=3.5, equityRiskPremium=5.5, countryRiskPremium=0.9, defaultTaxRate=22.0, gdpGrowth=4.0)
MARKET_US = MarketParams(riskFreeRate=4.2, equityRiskPremium=5.5, countryRiskPremium=0.0, defaultTaxRate=21.0, gdpGrowth=4.5)
MARKET_PARAMS: dict[str, MarketParams] = {"KRW": MARKET_KR, "USD": MARKET_US}


def getMarketParams(currency: str = "KRW") -> MarketParams:
    """통화 기반 시장 파라미터."""
    return MARKET_PARAMS.get(currency, MARKET_KR)


# ── getThresholds ──


def getThresholds(
    sector: Sector | str | None = None,
    industryGroup: IndustryGroup | str | None = None,
) -> dict:
    """섹터별 신용등급 기준표. IndustryGroup 우선, Sector fallback, default."""
    all_t = _loadThresholds()

    # IndustryGroup 우선
    if industryGroup:
        igVal = industryGroup.value if isinstance(industryGroup, IndustryGroup) else str(industryGroup)
        key = f"ig:{igVal}"
        if key in all_t:
            return all_t[key]

    # Sector
    if sector:
        sVal = sector.value if isinstance(sector, Sector) else str(sector)
        key = f"sector:{sVal}"
        if key in all_t:
            return all_t[key]

    return all_t.get("_default", {})
