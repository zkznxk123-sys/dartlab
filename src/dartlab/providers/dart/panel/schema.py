"""panel artifact schema — cross-market 계약 SSOT (L0, 14-col 동결).

모든 시장(dart/edgar/edinet)의 BUILD 가 **동일한 14-col schema** 를 산출한다.
panel reader(`providers/dart/panel`)·facade 는 이 schema 만 안다 → EDGAR build 가
us-gaap 에서 같은 14-col 을 내면 reader/facade 무변경 동작 (다시장 깨끗함의 토대).

수평화 2-레벨을 담는 그릇:
    - L1 (수평화 축) = ``xbrlClass``(ACLASS raw) / ``disclosureKey``(bridge canonical).
    - L2 (하부) = ``sectionLeaf``(heading) + ``contentRaw``(body, 태그 무손실).
    - 행 = (disclosureKey, scope) 단일 앵커 × 열 = period.

LLM Specifications:
    AntiPatterns:
        - 시장별로 컬럼 추가/이름 다르게 금지 — 14-col 동결, 시장차이는 값으로.
        - content_plain/mixed/stripped 류 사전 파생 컬럼 추가 금지 (태그 무손실 단일).
        - ``scope`` 를 저장 컬럼으로 추가 금지 — read 시점 xbrlClass 파생 (anchor.scopeExpr).
    OutputSchema:
        - ``PANEL_SCHEMA: dict[str, pl.DataType]`` 14 col.
        - ``PIVOT_INDEX: list[str]`` — 회사내 다기간 + 회사간 정렬 키.
    Prerequisites:
        - polars.
    Freshness:
        - schema 변경 시 build·reader·전 시장 동시 정합 필요 (계약 SSOT).
    Dataflow:
        - gather build(write) → 14-col parquet → providers reader(read) 가 본 schema 만 의존.
    TargetMarkets:
        - KR + US + JP 공통 계약.
"""

from __future__ import annotations

import polars as pl

# 14-col panel artifact schema (cross-market 동결).
PANEL_SCHEMA: dict[str, pl.DataType] = {
    "chapter": pl.Utf8,  # SECTION-1 대분류 (I~XII; EDGAR Part/Item)
    "sectionLeaf": pl.Utf8,  # 절 이름 (SECTION-N TITLE 원본 보존)
    "blockLeaf": pl.Utf8,  # 블록 소제목 (TABLE-GROUP TITLE)
    "xbrlClass": pl.Utf8,  # ACLASS 직접 (BS_C/IS_C2/CF_C/EF_C/NT_C_D######, +_S 별도)
    "xbrlMatched": pl.Boolean,  # ACLASS exact(True) vs fuzzy(False)
    "xbrlMatchScore": pl.Float32,
    "atocId": pl.Utf8,  # provenance
    "aassocnote": pl.Utf8,  # provenance
    "blockOrder": pl.UInt32,  # 문서 순서
    "contentRaw": pl.Utf8,  # 태그 무손실 raw XML (etree.tostring 그대로) — 단일 본문 컬럼
    "period": pl.Utf8,  # YYYYQn (결산월 무관 calendar quarter)
    "corp": pl.Utf8,  # 종목코드
    "rceptNo": pl.Utf8,  # 접수번호 provenance
    "disclosureKey": pl.Utf8,  # bridge canonical (xbrlClass→snakeId, cross-company/market)
}

# canonical pivot index (회사 내 다기간 + 회사 간 정렬 키).
# 최신기준 수평화(요구 #7): keyed 행은 (disclosureKey, scope) 단일 앵커 — era 마다
# 흔들리는 xbrlClass 대신 scope(연결/별도, xbrlClass 파생)로 대체해 BS↔BS_C drift 흡수.
# chapter/sectionLeaf/blockLeaf 는 anchorLatest 가 최신값으로 통일 → 표시 라벨 겸 정렬 안정.
# scope = anchor.scopeExpr(xbrlClass) 런타임 파생 (저장 14-col 불변).
PIVOT_INDEX: list[str] = ["chapter", "sectionLeaf", "blockLeaf", "disclosureKey", "scope"]
