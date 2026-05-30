"""sections artifact schema — cross-market 계약 SSOT.

모든 시장(dart/edgar/edinet)의 BUILD 가 **동일한 14-col schema** 를 산출한다.
core 의 reader(`sections.py`)·facade 는 이 schema 만 안다 → EDGAR build 가
us-gaap 에서 같은 14-col 을 내면 reader/facade 무변경 동작 (다시장 깨끗함의 토대).

LLM Specifications:
    AntiPatterns:
        - 시장별로 컬럼 추가/이름 다르게 금지 — 14-col 동결, 시장차이는 값으로.
        - content_plain/mixed 류 사전 파생 컬럼 추가 금지 (요구 #4 무손실 단일).
    OutputSchema:
        - ``SECTIONS_SCHEMA: dict[str, pl.DataType]`` 14 col.
    Prerequisites:
        - polars.
    TargetMarkets:
        - KR + US + JP 공통 계약.
"""

from __future__ import annotations

import polars as pl

# 14-col sections artifact schema (cross-market 동결).
SECTIONS_SCHEMA: dict[str, pl.DataType] = {
    "chapter": pl.Utf8,  # SECTION-1 대분류 (I~XII; EDGAR Part/Item)
    "sectionLeaf": pl.Utf8,  # 절 이름 (SECTION-N TITLE 원본 보존)
    "blockLeaf": pl.Utf8,  # 블록 소제목 (TABLE-GROUP TITLE)
    "xbrlClass": pl.Utf8,  # ACLASS 직접 (BS_C/IS_C2/CF_C/EF_C/NT_C_D######, +_S 연결)
    "xbrlMatched": pl.Boolean,  # ACLASS exact(True) vs fuzzy(False)
    "xbrlMatchScore": pl.Float32,
    "atocId": pl.Utf8,  # provenance
    "aassocnote": pl.Utf8,  # provenance
    "blockOrder": pl.UInt32,  # 문서 순서
    "contentRaw": pl.Utf8,  # 무손실 raw XML (etree.tostring 그대로) — 단일 본문 컬럼
    "period": pl.Utf8,  # YYYYQn
    "corp": pl.Utf8,  # 종목코드
    "rceptNo": pl.Utf8,  # 접수번호 provenance
    "disclosureKey": pl.Utf8,  # bridge canonical (xbrlClass→snakeId, cross-company/market)
}

# canonical pivot index (회사 내 다기간 + 회사 간 정렬 키).
# 최신기준 수평화(요구 #7): keyed 행은 (disclosureKey, scope) 단일 앵커 — era 마다
# 흔들리는 xbrlClass 대신 scope(연결/별도, xbrlClass 파생)로 대체해 BS↔BS_C drift 흡수.
# chapter/sectionLeaf/blockLeaf 는 anchorLatest 가 최신값으로 통일 → 표시 라벨 겸 정렬 안정.
# scope = canonical.scopeExpr(xbrlClass) 런타임 파생 (저장 14-col 불변).
PIVOT_INDEX: list[str] = ["chapter", "sectionLeaf", "blockLeaf", "disclosureKey", "scope"]
