"""ParserMapper — 파서 매핑 데이터 통합 매퍼.

affiliate/costByNature/sections 파서의 인라인 매핑을
JSON 파일로 추출한 후 통합 인터페이스로 제공.

각 파서는 코드에 매핑 데이터 0줄 — JSON 로드만.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from dartlab.core.mappers.engine import BaseMapper, MapperStats

_DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "parserMappings"


@lru_cache(maxsize=1)
def loadAffiliate() -> dict:
    """affiliate 파서 매핑 로드."""
    path = _DATA_DIR / "affiliate.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def loadCostByNature() -> dict:
    """costByNature 파서 매핑 로드."""
    path = _DATA_DIR / "costByNature.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def loadSections() -> dict:
    """sections 파서 매핑 로드."""
    path = _DATA_DIR / "sections.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


class ParserMapper(BaseMapper):
    """파서 매핑 통합 매퍼 — affiliate/costByNature/sections."""

    @property
    def name(self) -> str:
        return "parser"

    # ── affiliate ──

    def affiliateMovement(self, key: str) -> str | None:
        """변동내역 열 이름 → canonical (opening/closing/acquisition/...)."""
        return loadAffiliate().get("movement", {}).get(key)

    def affiliateProfile(self, key: str) -> str | None:
        """프로파일 필드 → canonical (ownership/bookValue/location/...)."""
        return loadAffiliate().get("profile", {}).get(key)

    def affiliateTransposedMovement(self, key: str) -> str | None:
        """횡전개 변동 필드 → canonical."""
        return loadAffiliate().get("transposedMovement", {}).get(key)

    # ── costByNature ──

    def costNormalize(self, rawName: str) -> str | None:
        """비용 항목 정규화. 원재료/인건비 등 → canonical."""
        cleaned = rawName.replace(" ", "")
        for canonical, aliases in loadCostByNature().get("normalize", []):
            if any(alias in cleaned for alias in aliases):
                return canonical
        return None

    def isCostTotal(self, name: str) -> bool:
        """합계 행인지."""
        cleaned = name.replace(" ", "")
        return any(p in cleaned for p in loadCostByNature().get("totalPatterns", []))

    def isCostSkip(self, name: str) -> bool:
        """건너뛸 키워드인지."""
        cleaned = name.replace(" ", "")
        return cleaned in loadCostByNature().get("skipKeywords", set())

    # ── sections ──

    def sectionTopic(self, heading: str) -> str | None:
        """명세서 제목 → topic code."""
        cleaned = heading.replace(" ", "")
        return loadSections().get("detailTopicMap", {}).get(cleaned)

    def sectionKeywords(self, topicCode: str) -> list[str]:
        """topic code → 키워드 목록."""
        return loadSections().get("detailTopicKeywords", {}).get(topicCode, [])

    def chapterFromMajor(self, majorNum: int) -> str | None:
        """정수 장번호 → 로마숫자."""
        return loadSections().get("chapterByMajor", {}).get(str(majorNum))

    # ── BaseMapper ──

    def lookup(self, key: str) -> dict | None:
        """통합 검색 — affiliate → cost → sections 순."""
        # affiliate movement
        val = self.affiliateMovement(key)
        if val:
            return {"source": "affiliate.movement", "canonical": val}

        # affiliate profile
        val = self.affiliateProfile(key)
        if val:
            return {"source": "affiliate.profile", "canonical": val}

        # cost normalize
        val = self.costNormalize(key)
        if val:
            return {"source": "costByNature.normalize", "canonical": val}

        # section topic
        val = self.sectionTopic(key)
        if val:
            return {"source": "sections.detailTopic", "topicCode": val}

        return None

    def stats(self) -> MapperStats:
        aff = loadAffiliate()
        cost = loadCostByNature()
        sec = loadSections()
        total = (
            len(aff.get("movement", {}))
            + len(aff.get("profile", {}))
            + len(aff.get("transposedMovement", {}))
            + len(cost.get("normalize", []))
            + len(sec.get("detailTopicMap", {}))
        )
        return MapperStats(
            name=self.name,
            totalEntries=total,
            mappedEntries=total,
            coverage=1.0,
            lastUpdated="",
        )

    def allKeys(self) -> list[str]:
        keys: list[str] = []
        aff = loadAffiliate()
        keys.extend(aff.get("movement", {}).keys())
        keys.extend(aff.get("profile", {}).keys())
        cost = loadCostByNature()
        keys.extend(c[0] for c in cost.get("normalize", []))
        sec = loadSections()
        keys.extend(sec.get("detailTopicMap", {}).keys())
        return keys
