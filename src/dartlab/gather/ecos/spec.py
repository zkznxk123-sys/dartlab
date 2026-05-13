"""ECOS 엔진 AI 스펙 메타데이터."""

from __future__ import annotations

from . import catalog as _catalog


def buildSpec() -> dict:
    """AI spec 수집기용 ECOS 엔진 스펙 메타데이터 생성.

    Capabilities: catalog 그룹 + 시리즈 list + capabilities + tools 종합 dict.
    AIContext: Skill OS auto-discover / dartlab.skills/specs build 진입.
    Guide: 정적 카탈로그 기반 — ECOS API 호출 없음.
    When: Skill OS 산출물 명시 관리 시.
    How: catalog.getGroups iterate → 각 entry meta dict 패킹.

    카탈로그 그룹·시리즈 목록을 순회하여 AI 자동 발견(autoDiscover)용
    구조화된 dict 를 반환한다.

    Returns
    -------
    dict
        name : str — 엔진 이름 ("ecos")
        label : str — 표시 레이블
        description : str — 엔진 설명
        tier : str — 안정성 단계 ("beta")
        capabilities : list[str] — 지원 기능 목록
        catalog_groups : dict — 그룹별 시리즈 메타 (count, series)
        total_catalog_series : int — 전체 카탈로그 시리즈 수 (개)
        tools : list[dict] — AI tool 정의 목록 (name, description)

    Raises
    ------
    없음
        카탈로그 비어 있어도 빈 그룹 dict 반환.

    Requires
    --------
    catalog._INDICATORS 정적 사전.

    Example
    -------
    >>> spec = buildSpec()

    See Also
    --------
    catalog.toDataframe : 카탈로그 DataFrame 형식.
    skills/specs : 본 함수 결과의 caller (Skill OS build).
    """
    groups = {}
    for name in _catalog.getGroups():
        entries = _catalog.getGroup(name)
        groups[name] = {
            "count": len(entries),
            "series": [{"id": e.id, "label": e.label} for e in entries],
        }

    return {
        "name": "ecos",
        "label": "ECOS 경제지표",
        "description": "한국은행 경제통계시스템 (GDP, 물가, 금리, 환율 등 21개 주요 지표)",
        "tier": "beta",
        "capabilities": [
            "시계열 조회 (series)",
            "복수 시리즈 비교 (compare)",
            "주요 지표 카탈로그 (10개 그룹)",
            "키워드 검색 (search)",
        ],
        "catalog_groups": groups,
        "total_catalog_series": len(_catalog.getAllIds()),
        "tools": [
            {"name": "ecos_series", "description": "ECOS 시계열 조회"},
            {"name": "ecos_compare", "description": "복수 시계열 비교"},
            {"name": "ecos_catalog", "description": "한국 경제지표 카탈로그"},
            {"name": "ecos_search", "description": "지표 키워드 검색"},
        ],
    }
