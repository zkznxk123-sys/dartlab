"""DataEntry — disclosure 카테고리 진입점 (Cut 8 분할).

단일 진실의 원천은 list 자체. 로직은 ``core/registry.py``.
"""

from __future__ import annotations

from dartlab.core.dataEntry import ColumnMeta, DataEntry  # noqa: F401

_DISCLOSURE_ENTRIES: list[DataEntry] = [
    # disclosure — 서술형 공시
    # ═══════════════════════════════════════════════════════
    DataEntry(
        name="business",
        label="사업의내용",
        category="disclosure",
        dataType="text",
        description="사업보고서 '사업의 내용' 서술. 사업 구조와 현황 파악.",
        modulePath="dartlab.providers.dart.docs.disclosure.business",
        funcName="business",
        extractor=lambda r: r.sections,
        requires="docs",
        analysisHints=(
            "핵심 사업모델과 경쟁력 파악",
            "산업 리스크 요인 확인",
        ),
        maxRows=5,
        aiKeywords=("사업",),
    ),
    DataEntry(
        name="companyOverview",
        label="회사개요정량",
        category="disclosure",
        dataType="dict",
        description="공시 기반 회사 정량 개요 데이터.",
        modulePath="dartlab.providers.dart.docs.disclosure.companyOverview",
        funcName="companyOverview",
        extractor=None,
        requires="docs",
        aiKeywords=("개요", "신용등급"),
    ),
    DataEntry(
        name="mdna",
        label="MD&A",
        category="disclosure",
        dataType="text",
        description="이사의 경영진단 및 분석의견. 경영진 시각의 실적 평가와 전망.",
        modulePath="dartlab.providers.dart.docs.disclosure.mdna",
        funcName="mdna",
        extractor=lambda r: r.overview,
        requires="docs",
        analysisHints=(
            "경영진의 실적 자기평가와 전망",
            "언급된 리스크 요인",
        ),
        aiKeywords=("MD&A", "경영진단"),
    ),
    DataEntry(
        name="rawMaterial",
        label="원재료설비",
        category="disclosure",
        dataType="dict",
        description="원재료 매입, 유형자산 현황, 시설투자 데이터.",
        modulePath="dartlab.providers.dart.docs.disclosure.rawMaterial",
        funcName="rawMaterial",
        extractor=None,
        requires="docs",
        analysisHints=("원재료 조달 집중도", "시설투자 규모 추이"),
        relatedModules=("costByNature", "tangibleAsset"),
        aiQuestionTypes=("사업", "리스크"),
        aiKeywords=("원재료", "설비"),
    ),
    DataEntry(
        name="sections",
        label="사업보고서섹션",
        category="disclosure",
        dataType="dataframe",
        description="사업보고서 전체 섹션 텍스트를 topic(행) × period(열) DataFrame으로 구조화. "
        "leaf title 기준 수평 비교 가능. 연간+분기+반기 전 기간 포함.",
        modulePath="dartlab.providers.dart.docs.sectionsLegacy",
        funcName="sections",
        extractor=None,
        requires="docs",
        columns=(ColumnMeta("topic", "섹션 주제명 (leaf title)"),),
        analysisHints=(
            "사업 리스크, 소송, 제재, 후발사건 등 서술형 정보 탐색",
            "연도별 텍스트 변화 비교 (같은 topic의 기간별 텍스트 대조)",
            "경영진 전망, 이사회 활동, 위험관리 정책 등 정성 분석",
        ),
    ),
    # ═══════════════════════════════════════════════════════
]
