"""sections artifact builder v5 — TABLE-GROUP 단위 row emit.

신개념 (마스터 플랜 v5):
    raw XML 의 ``<TABLE-GROUP ACLASS="{XBRL}...">`` 가 회사 무관 universal
    canonical key. 각 leaf TABLE-GROUP = 1 row. content_raw = element 의
    ``etree.tostring`` 그대로 (P/SPAN/USERMARK/TABLE/ALIGN 100% 보존).

옛 양식 (~2023Q3, ATOCID 없음):
    - top-level ACLASS (BS_C/IS_C/CF_C/EF_C) 존재
    - 개별 주석 단위 NT_C_D###### 없음
    - matchToRef 로 ref table fuzzy lookup → xbrlClass 부여

신 양식 (2023Q4+, ATOCID 박힘):
    - top + nested ACLASS 풍부 (NT_C_D###### 등)
    - ACLASS 직접 사용

LLM Specifications:
    AntiPatterns:
        - 옛 lossy chain (xmlChunkToMixed / _splitContentBlocks 등) 호출 0
        - mapper.py / topicStandard.py import 금지
        - content_plain 사전 계산 금지 — raw XML 단일.
    OutputSchema:
        - ``buildSections(corpCode) -> dict[period, rowCount]``
        - period sharded parquet 저장.
    Prerequisites:
        - ref table (data/dart/sectionsXbrlRef.parquet) 또는 5 baseline scan
          결과 DataFrame.
        - data/dart/original/docs/{code}/*.zip 로컬.
    Freshness:
        - ref table 갱신 후 옛 양식 매핑 재빌드 가능.
    Dataflow:
        - zip → XML → walker.walkSections → row list → polars write_parquet.
    TargetMarkets:
        - KR (DART). EDGAR 별도.

마스터 플랜: v5 §2.4 + §5.4.
"""

from __future__ import annotations

from dartlab.providers.dart.docs.sectionsNew.v5Builder import (
    buildSections,
    buildSectionsAll,
    buildSectionsBaseline,
)
from dartlab.providers.dart.docs.sectionsNew.walker import (
    detectSchemaEra,
    walkSections,
)

__all__ = [
    "buildSections",
    "buildSectionsAll",
    "buildSectionsBaseline",
    "detectSchemaEra",
    "walkSections",
]
