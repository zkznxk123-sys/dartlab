"""sections textPath / textSemanticPath 의 비교 가능 경로 정규화.

``_comparablePathInfo(topic, semanticPathKey)`` 가 sections wide 보드의 join
key 인 ``textComparablePathKey`` / ``textComparableParentPathKey`` 를 생성.
주체 중립 — 의미 보존 변환만 수행.

본 모듈은 ``pipeline.py`` 에서 분리됨 (operation.sectionsRefactor §5 부채 1).
caller API 0 변경 — pipeline.py 가 본 함수들을 re-import.
"""

from __future__ import annotations

import re

_RE_BUSINESS_UNIT_SEGMENT = re.compile(r".+(?:부문|총괄)$")
_RE_BUSINESS_UNIT_SHORT = re.compile(r"^[A-Z][A-Z0-9&/-]{1,7}$")

_BUSINESS_OVERVIEW_COMPARABLE_ROOTS: dict[str, str] = {
    "주요제품서비스등": "주요제품및서비스",
    "매출및수주상황": "매출",
    "주요계약및연구개발활동": "연구개발활동",
    "주요원재료": "원재료및생산설비",
    "주요사업장현황": "생산및설비",
    "위험관리및파생거래": "시장위험과위험관리",
}

_STRUCTURE_SLOT_ALIASES: dict[str, dict[str, str]] = {
    "businessOverview": {
        "판매경로": "판매경로및판매방법",
        "판매방법및조건": "판매경로및판매방법",
        "판매전략": "판매경로및판매방법",
        "판매조직": "판매경로및판매방법",
        "판매경로및판매방법등": "판매경로및판매방법",
        "생산능력": "생산능력생산실적가동률",
        "생산실적": "생산능력생산실적가동률",
        "가동률": "생산능력생산실적가동률",
        "생산능력및산출근거": "생산능력생산실적가동률",
        "생산능력생산실적가동률": "생산능력생산실적가동률",
        "생산능력산출근거및생산실적": "생산능력생산실적가동률",
        "사업부문별요약재무현황": "사업부문별요약재무현황",
        "산업의특성": "산업의특성",
        "시장여건": "시장여건",
        "영업현황": "영업현황",
    },
    "auditSystem": {
        "감사위원회교육실시계획및현황": "감사위원회교육",
        "감사위원회의교육실시계획": "감사위원회교육",
        "감사위원회교육실시현황": "감사위원회교육",
    },
}

_BUSINESS_UNIT_SEGMENT_LITERALS = {"Harman", "SDC"}


def _splitPathSegments(path: str | None) -> list[str]:
    if not isinstance(path, str) or not path:
        return []
    return [segment.strip() for segment in path.split(" > ") if segment.strip()]


def _joinPathSegments(segments: list[str]) -> str | None:
    cleaned = [segment for segment in segments if isinstance(segment, str) and segment]
    if not cleaned:
        return None
    return " > ".join(cleaned)


def _isBusinessUnitSegment(segment: str) -> bool:
    return (
        segment in _BUSINESS_UNIT_SEGMENT_LITERALS
        or bool(_RE_BUSINESS_UNIT_SEGMENT.fullmatch(segment))
        or bool(_RE_BUSINESS_UNIT_SHORT.fullmatch(segment))
    )


def _normalizeComparableSegment(topic: str, segment: str) -> str:
    if topic == "businessOverview":
        segment = _BUSINESS_OVERVIEW_COMPARABLE_ROOTS.get(segment, segment)
    return _STRUCTURE_SLOT_ALIASES.get(topic, {}).get(segment, segment)


def _comparablePathInfo(topic: str, semanticPathKey: str | None) -> tuple[str | None, str | None]:
    segments = _splitPathSegments(semanticPathKey)
    if not segments:
        return None, None

    normalized: list[str] = []
    unitAnchorInserted = False

    for segment in segments:
        if segment.startswith("@topic:"):
            normalized.append(segment)
            continue

        if topic == "businessOverview" and _isBusinessUnitSegment(segment):
            if not unitAnchorInserted:
                anchor = "사업부문현황"
                if not normalized or normalized[-1] != anchor:
                    normalized.append(anchor)
                unitAnchorInserted = True
            continue

        normalizedSegment = _normalizeComparableSegment(topic, segment)
        if normalized and normalized[-1] == normalizedSegment:
            continue
        normalized.append(normalizedSegment)

    pathKey = _joinPathSegments(normalized)
    parentPathKey = _joinPathSegments(normalized[:-1])
    return pathKey, parentPathKey
