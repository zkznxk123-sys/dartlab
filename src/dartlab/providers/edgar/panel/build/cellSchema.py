"""EDGAR panel 셀 schema — DART ``panel.cellSchema`` 의 us-gaap 미러 (계약 SSOT).

필링 inline XBRL(``<ix:nonFraction us-gaap:X contextRef>`` + ``<xbrli:context>``)을 build-time 에 해소한
계정×기간 셀의 14-col 계약. DART ``CELL_SCHEMA`` 와 동형 — 컬럼명만 us-gaap 어휘(acode→concept). DART 는
ACONTEXT 가 셀에 자급이라 read-time 분해하지만, EDGAR 는 contextRef 가 문서-전역 ``<xbrli:context>`` 간접
참조라 read-time 고립 분해 불가 → build 가 해소해 별도 artifact(``data/edgar/panelCell/{ticker}.parquet``)로
저장. ``cellRead`` 가 read.

LLM Specifications:
    AntiPatterns:
        - 시장별 컬럼 추가/이름 변경 금지 — DART CELL_SCHEMA 와 동형(concept=acode 대응).
        - scale/sign 미적용 raw 텍스트 저장 금지 — valueRaw 는 해소 numeric 문자열(companyfacts val 동치).
    OutputSchema:
        - ``EDGAR_CELL_SCHEMA: dict[str, pl.DataType]`` 14 col.
        - ``CELL_PIVOT_INDEX: list[str]`` (statement, concept, axisPath, scope).
    Prerequisites:
        - polars.
    Freshness:
        - schema 변경 시 build(cell)·read(cellRead) 동시 정합.
    Dataflow:
        - build(facts×context×role 해소) → 14-col parquet → cellRead pivot.
    TargetMarkets:
        - US (EDGAR us-gaap).
"""

from __future__ import annotations

import polars as pl

# 14-col EDGAR 셀 schema (DART CELL_SCHEMA 미러 — acode→concept).
EDGAR_CELL_SCHEMA: dict[str, pl.DataType] = {
    "corp": pl.Utf8,  # ticker
    "rceptNo": pl.Utf8,  # accession
    "filingPeriod": pl.Utf8,  # YYYYQn (필링 보고 기준)
    "statement": pl.Utf8,  # BS/IS/CF/CIS/EF (presentation role → roleToStatement)
    "scope": pl.Utf8,  # consolidated (EDGAR 연결-only)
    "concept": pl.Utf8,  # us-gaap local-name (us-gaap:Revenues → Revenues) — DART acode 대응
    "label": pl.Utf8,  # preferredLabel / EX-101.LAB
    "ctxYear": pl.Int32,  # context 기간/시점 연도 (calendar)
    "ctxFlow": pl.Utf8,  # d(duration) / e(instant)
    "ctxQuarter": pl.Int32,  # 1/2/3/4 (calendarQuarterFromEnd)
    "ctxMode": pl.Utf8,  # Y(annual) / A(YTD) / Q(standalone) / P(instant point)
    "axisPath": pl.Utf8,  # context dimension members "|" join (DART axisPath 대응)
    "valueRaw": pl.Utf8,  # 해소 numeric 문자열 (scale·sign 적용; nil → "")
    "cellOrder": pl.UInt32,  # presentation arc 순서 (문서 표시순)
}

# 셀 pivot 행 identity (DART CELL_PIVOT_INDEX 동형 — acode→concept).
CELL_PIVOT_INDEX: list[str] = ["statement", "concept", "axisPath", "scope"]
