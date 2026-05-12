"""ParserMapper — 파서 매핑 데이터 통합 매퍼.

affiliate/costByNature/sections 파서의 인라인 매핑을
JSON 파일로 추출한 후 통합 인터페이스로 제공.

각 파서는 코드에 매핑 데이터 0줄 — JSON 로드만.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from dartlab.reference.mappers.engine import BaseMapper, MapperStats

_DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "parserMappings"


def _loadRequired(filename: str) -> dict:
    """필수 파서 매핑 JSON 로드. 누락 = 빌드/패키징 사고이므로 즉시 예외.

    과거 사고 (2026-04-19): PyPI wheel 0.9.15 에서 `reference/data/parserMappings/`
    디렉토리가 통째로 누락된 채 배포됨. loadSections() 가 빈 dict 를 리턴했고,
    sections runtime 의 `_CHAPTER_BY_MAJOR` 가 빈 상태로 초기화되어 모든
    `chapterFromMajorNum(N)` 이 None → _reportRowsToTopicRows 빈 리스트 →
    sections() None → c.sections `.raw.columns` AttributeError 로 외부 사용자
    첫 호출이 크래시.

    silent `{}` 리턴은 위 사고의 근본 원인. 파일이 없다는 것은 wheel 패키징
    누락 또는 설치 손상이므로 사용자에게 명확히 알려야 한다.
    """
    path = _DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"필수 매핑 파일 누락: {path}\n"
            f"  원인 후보:\n"
            f"    1) 설치된 dartlab wheel 에 data/parserMappings/ 가 빠짐 (패키징 사고)\n"
            f"       → pip install -U --force-reinstall dartlab\n"
            f"    2) 편집가능 설치 (editable) 중 파일이 외부 프로세스에 의해 삭제됨\n"
            f"       → git status / git restore 로 복구\n"
            f"  재현 방지: 릴리즈 전 bash scripts/build/testWheelSmoke.sh 필수"
        )
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def loadAffiliate() -> dict:
    """affiliate 파서 매핑 로드."""
    return _loadRequired("affiliate.json")


@lru_cache(maxsize=1)
def loadCostByNature() -> dict:
    """costByNature 파서 매핑 로드."""
    return _loadRequired("costByNature.json")


@lru_cache(maxsize=1)
def loadSections() -> dict:
    """sections 파서 매핑 로드."""
    return _loadRequired("sections.json")


class ParserMapper(BaseMapper):
    """파서 매핑 통합 매퍼 — affiliate/costByNature/sections."""

    @property
    def name(self) -> str:
        """name — TODO 한국어 동작 설명."""
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
        """stats — TODO 한국어 동작 설명."""
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
        """allKeys — TODO 한국어 동작 설명."""
        keys: list[str] = []
        aff = loadAffiliate()
        keys.extend(aff.get("movement", {}).keys())
        keys.extend(aff.get("profile", {}).keys())
        cost = loadCostByNature()
        keys.extend(c[0] for c in cost.get("normalize", []))
        sec = loadSections()
        keys.extend(sec.get("detailTopicMap", {}).keys())
        return keys
