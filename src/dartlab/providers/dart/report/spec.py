"""dart/report 엔진 스펙 — 코드에서 자동 추출."""

from __future__ import annotations


def buildSpec() -> dict:
    """dart/report 엔진 스펙 반환.

    Args:
        (인자 자동 생성).

    Raises:
        없음.

    Example:
        >>> buildSpec(...)

    Returns:
        <TODO: return desc> (dict)

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - <TODO: external requires>
    """
    from dartlab.providers.dart.report.types import API_TYPE_LABELS, API_TYPES

    return {
        "name": "dart.report",
        "description": "DART 정기보고서 API 데이터 (배당, 직원, 임원 등)",
        "summary": {
            "apiTypes": len(API_TYPES),
            "keyModules": ["dividend", "employee", "majorHolder", "executive", "auditOpinion"],
        },
        "detail": {
            "apiTypes": {t: API_TYPE_LABELS.get(t, t) for t in API_TYPES},
        },
    }
