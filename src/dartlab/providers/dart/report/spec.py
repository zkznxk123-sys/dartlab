"""dart/report 엔진 스펙 — 코드에서 자동 추출."""

from __future__ import annotations


def buildSpec() -> dict:
    """dart/report 엔진 자가기술 (apiType 카탈로그 + key module 인덱스).

    Capabilities:
        - report 엔진의 지원 apiType 28 종 + 한국어 라벨을 dict 로 반환.
        - 상위 요약 (summary) 와 detail 2 단 구조.
        - key module 5 (dividend/employee/majorHolder/executive/auditOpinion) 는 pivot 함수가
          준비된 코어 토픽.

    Args:
        없음.

    Returns:
        dict — ``{"name": "dart.report", "description": ..., "summary": {"apiTypes": 28,
        "keyModules": [...]}, "detail": {"apiTypes": {apiType: label, ...}}}``. 무상태.

    Example:
        >>> from dartlab.providers.dart.report.spec import buildSpec
        >>> spec = buildSpec()
        >>> spec["name"]
        'dart.report'
        >>> spec["summary"]["apiTypes"]
        28

    Guide:
        - "report 엔진이 무엇을 다루는지 사람에게 설명" → ``buildSpec()["description"]``.
        - "지원 apiType 28 종 한국어 라벨" → ``buildSpec()["detail"]["apiTypes"]``.
        - 새 apiType 추가 시 → ``types.API_TYPES`` + ``API_TYPE_LABELS`` 만 갱신, 본 함수는 무수정.

    SeeAlso:
        - ``dartlab.providers.dart.report.types.API_TYPES`` — 28 apiType SSOT.
        - ``dartlab.providers.dart.report.types.API_TYPE_LABELS`` — 한국어 라벨 매핑.
        - ``extractRaw`` / ``extractResult`` — apiType 별 실제 데이터 추출.

    Requires:
        - 외부 의존 없음 (lazy import: ``dartlab.providers.dart.report.types``).
        - DART API/parquet 무관 — 순수 메타데이터.

    AIContext:
        Workbench 가 "이 엔진이 뭘 하느냐" 메타 질문에 답할 때 호출. 새 회사 분석 진입 시
        catalogue 제시 → apiType 별 nYears 조회 (별도 extractResult 호출) 와 조합. spec 자체는
        실제 데이터 없음, "어떤 카테고리가 있냐" 만 알려준다.

    LLM Specifications:
        AntiPatterns:
            - API_TYPES 와 API_TYPE_LABELS 불일치 (LABEL 누락) → spec.detail.apiTypes[t] = t
              자체 (영문 폴백). types 갱신 시 LABELS 동시 추가 필수.
            - 본 함수 결과를 사람에게 직접 보여줄 때 keyModules 5 외 23 종은 "raw 만 지원"
              경고 동행 (pivot 미구비).
        OutputSchema:
            - row: 1 dict instance.
            - 필드: 4 종 (name/description/summary/detail).
            - keyModules: list[str], detail.apiTypes: dict[str, str].
        Prerequisites:
            - types 모듈 import 가능 (lazy — 순환 의존 회피).
        Freshness:
            - 정적 메타데이터. types 변경 시 함수 결과 변경.
        Dataflow:
            - types (API_TYPES + API_TYPE_LABELS) → 본 함수 → caller (메타 답변).
        TargetMarkets:
            - KR (DART) 한정. 동등 함수는 edgar/edinet 도 동일 패턴 (각 provider 마다 spec.py).
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
