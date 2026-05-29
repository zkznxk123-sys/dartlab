"""DART sections ref table scanner.

목적:
    DART 본문 XML 의 ``<TABLE-GROUP ACLASS="{XBRL}...">`` 를 회사 무관 canonical
    key 로 활용. 전체 102k zip 스캔 → ``sectionsXbrlRef.parquet`` 자동 추출.
    mapper.py 의 591 손수 regex 폐기 (사용자 요구 #2).

LLM Specifications:
    AntiPatterns:
        - 손수 작성 regex 추가 금지 — ref table 은 데이터 (parquet), 코드 아님.
        - corpCount < 3 entry SSOT 입성 금지 — noise 차단.
        - mapper.py / topicStandard.py 호출 금지 — 의존 0.
    OutputSchema:
        - ``sectionsXbrlRef.parquet`` 11 col: rawId / rawTitleCanonical /
          rawTitleVariants / parentRawId / taxonomyVersion / firstSeenPeriod /
          lastSeenPeriod / corpCount / periodCount / occurrenceCount / marketNs.
    Prerequisites:
        - ``data/dart/original/docs/{code}/*.zip`` 로컬.
    Freshness:
        - 분기 incremental rebuild — 신규 zip 만 스캔 후 ref table merge.
    Dataflow:
        - zip → XML → lxml TABLE-GROUP iter → ACLASS / TITLE / AASSOCNOTE 추출
          → corp/period 별 집계 → corp ≥ 3 필터.
    TargetMarkets:
        - KR (DART). EDGAR 는 별도.
"""

from __future__ import annotations

from dartlab.filings.dart.build.refScan.aclassExtractor import (
    extractAclassEntries,
    iterTableGroups,
)
from dartlab.filings.dart.build.refScan.titleNormalizer import (
    normalizeTitle,
    tokenize,
)
from dartlab.filings.dart.build.refScan.zipScanWorker import (
    scanAllZips,
    scanRefBaseline,
    scanZipFiles,
)

__all__ = [
    "extractAclassEntries",
    "iterTableGroups",
    "normalizeTitle",
    "scanAllZips",
    "scanRefBaseline",
    "scanZipFiles",
    "tokenize",
]
