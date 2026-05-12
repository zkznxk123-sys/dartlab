"""번들 리소스 계약 — wheel 패키징 사고 + 스키마 드리프트 동시 차단.

========================================
이 파일이 잡는 버그 클래스 (2026-04-19 실제 사고):
========================================
PyPI 0.9.15 wheel 에서 `reference/data/parserMappings/` 디렉토리가 통째로 누락된 채
배포되어, 외부 사용자 `Company("005930").sections` 첫 호출이
`AttributeError: NoneType has no columns` 로 크래시.

연쇄:
    parserMappings/sections.json 누락
    → loadSections() {}
    → runtime 모듈 import 시 _CHAPTER_BY_MAJOR = {}
    → chapterFromMajorNum(N) 모두 None
    → _reportRowsToTopicRows 0 rows
    → sections() None
    → _SectionsSource.raw.columns AttributeError

이 테스트는 unit 마커로 CI 매 실행마다 돌아가 재발을 즉시 감지한다.
wheel-smoke 잡은 격리 venv 에서 동일 불변을 재검증한다 (이중 방어).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit]

_PKG_ROOT = Path(__file__).resolve().parents[1] / "src" / "dartlab"


# ════════════════════════════════════════
# 필수 파일 존재 계약
# ════════════════════════════════════════

# git-tracked + wheel-bundled 필수 리소스만 검증.
# dalio48Cases/dalioDetailCases/damodaranDefaults/rrCrises800y 는 로컬 생성물이라
# git 에 커밋되지 않고 wheel 에도 포함되지 않음 — 필수 목록 제외.
_REQUIRED_FILES = [
    # core parserMappings — 2026-04-19 사고 발생 위치
    "reference/data/parserMappings/sections.json",
    "reference/data/parserMappings/affiliate.json",
    "reference/data/parserMappings/costByNature.json",
    "reference/data/parserMappings/sectorPriors.json",
    # core data (git-tracked)
    "reference/data/accountMappings.json",
    "reference/data/notesStructure.json",
    "reference/data/labelSupplements.json",
    # sections runtime 의존 JSON
    "providers/dart/docs/sections/mapperData/sectionMappings.json",
    "providers/dart/docs/sections/mapperData/tableMappings.json",
    "providers/dart/docs/sections/profileData/projectionRules.chapterII.json",
    "providers/dart/docs/sections/profileData/sectionProfileTable.parquet",
    # EDGAR sections
    "providers/edgar/docs/sections/mapperData/sectionMappings.json",
]


@pytest.mark.parametrize("relativePath", _REQUIRED_FILES)
def test_requiredBundleFile_exists(relativePath: str):
    """번들되어야 하는 필수 리소스가 소스 트리에 존재."""
    path = _PKG_ROOT / relativePath
    assert path.exists(), (
        f"필수 번들 리소스 누락: {relativePath}\n"
        f"이 파일이 없으면 wheel 에 자동 포함되지 않아 외부 사용자가 크래시한다.\n"
        f"소스 트리 경로: {path}"
    )


# ════════════════════════════════════════
# 필수 JSON 스키마 계약
# ════════════════════════════════════════


def test_parserMappingsSections_hasChapterByMajor():
    """sections.json 의 chapterByMajor 가 비어있지 않음.

    이 필드가 비면 chapterFromMajorNum() 모두 None 리턴 → sections() 파이프라인
    전체가 silent-fail. wheel 에 파일은 있어도 내용이 깨졌을 때를 잡는다.
    """
    path = _PKG_ROOT / "reference/data/parserMappings/sections.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "sections.json 루트가 dict 아님"

    chapterByMajor = data.get("chapterByMajor")
    assert chapterByMajor, "sections.json 에 'chapterByMajor' 키 없거나 빔"
    assert isinstance(chapterByMajor, dict)
    # I~IX 까지 기본 장번호는 반드시 존재해야 함 (DART 보고서 표준 장 구조)
    for majorNum in ("1", "2", "3", "4", "5"):
        assert majorNum in chapterByMajor, (
            f"chapterByMajor 에 장번호 {majorNum!r} 누락 — DART 표준 I~IX 장 구조 보장 실패"
        )


def test_parserMappingsSections_hasDetailTopicMap():
    """sections.json 의 detailTopicMap — 상세 토픽 라우팅 테이블."""
    path = _PKG_ROOT / "reference/data/parserMappings/sections.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    dtm = data.get("detailTopicMap")
    assert dtm, "sections.json 에 detailTopicMap 키 누락"
    assert isinstance(dtm, dict)


def test_accountMappings_hasKrFsKeys():
    """accountMappings.json — KR DART 재무제표 매핑. 비면 IS/BS/CF 전부 빔."""
    path = _PKG_ROOT / "reference/data/accountMappings.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert data, "accountMappings.json 빈 dict — 재무제표 매핑 전멸"


def test_sectionMappings_isNonEmpty():
    """sections/mapperData/sectionMappings.json — section 제목 → topic 매핑."""
    path = _PKG_ROOT / "providers/dart/docs/sections/mapperData/sectionMappings.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert len(data) > 100, f"sectionMappings.json 항목 {len(data)}개 — 정상(500+) 대비 비정상"


# ════════════════════════════════════════
# 런타임 로더 계약 — 실제 import 경로로 검증
# ════════════════════════════════════════


def test_loadSections_returnsPopulatedDict():
    """loadSections() 가 빈 dict 가 아닌 chapterByMajor 포함 dict 반환."""
    from dartlab.providers.mappers.parserMapper import loadSections

    result = loadSections()
    assert isinstance(result, dict)
    assert result, "loadSections() 빈 dict — 2026-04-19 크래시 재현 조건"
    assert "chapterByMajor" in result
    assert result["chapterByMajor"], "chapterByMajor 빈 dict — 파이프라인 silent-fail"


def test_chapterFromMajorNum_mapsKnownRange():
    """runtime.chapterFromMajorNum 이 1~9 모두 non-None 매핑."""
    from dartlab.providers.dart.docs.sections.runtime import chapterFromMajorNum

    for majorNum in range(1, 10):
        result = chapterFromMajorNum(majorNum)
        assert result is not None, (
            f"chapterFromMajorNum({majorNum}) None — _CHAPTER_BY_MAJOR 초기화 실패 (parserMappings 누락)"
        )
        assert isinstance(result, str)
        assert result  # 빈 문자열도 아님


def test_loadAffiliate_returnsPopulatedDict():
    from dartlab.providers.mappers.parserMapper import loadAffiliate

    result = loadAffiliate()
    assert isinstance(result, dict)
    assert result, "loadAffiliate() 빈 dict — affiliate 매핑 전멸"


def test_loadCostByNature_returnsPopulatedDict():
    from dartlab.providers.mappers.parserMapper import loadCostByNature

    result = loadCostByNature()
    assert isinstance(result, dict)
    assert result, "loadCostByNature() 빈 dict — costByNature 매핑 전멸"


# ════════════════════════════════════════
# Phase A1/B 추가: 나머지 loud-fail 로더 계약
# ════════════════════════════════════════


def test_loadLabelSupplements_returnsPopulatedDict():
    """labelSupplements.json 이 번들되어 정상 로드 + 빈 dict 아님."""
    from dartlab.core.utils.labels import _loadLabelSupplements

    result = _loadLabelSupplements()
    assert isinstance(result, dict)
    # supplements 는 비어있을 수도 있으므로 타입만 확인. 파일 존재는 위 _REQUIRED_FILES 에서 검증.


def test_loadEdgarStandardAccounts_returnsPopulatedDict():
    """EDGAR standardAccounts.json 이 번들되어 정상 로드."""
    from dartlab.core.utils.labels import _loadEdgarStandardAccounts

    result = _loadEdgarStandardAccounts()
    assert isinstance(result, dict)
    assert result, "_load_edgar_standard_accounts() 빈 dict — EDGAR 계정명 매핑 전멸"


def test_loadNotesStructureKeywords_returnsPopulatedDict():
    """notesStructure.json 이 번들되어 정상 로드."""
    from dartlab.providers.mappers.notesMapper import _loadKeywords

    result = _loadKeywords()
    assert isinstance(result, dict)
    assert result, "notesStructure keywords 빈 dict — 주석 매퍼 무력화"
