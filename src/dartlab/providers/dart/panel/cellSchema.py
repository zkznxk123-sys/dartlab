"""panel read-time 셀 schema — 재무 5표 native XBRL 셀 계약 SSOT (L0, 14-col).

메인 panel(14-col blob 격자)의 5표 row ``contentRaw`` 를 read-time 으로 분해한 in-memory
schema 다. 정부 `<TE ACODE ACONTEXT>` native 태그를 재무 5표(BS/IS/CIS/CF/SCE)에 대해 셀 단위로
분해한 결과 — 한 행 = 한 개념의 한 (기간, 축) 값. 별도 panelCell parquet 는 없다.

저장 원칙(불변 원본 + 순수 규칙 산물만 굽기): ACONTEXT 분해(ctxYear/ctxFlow/ctxQuarter/ctxMode)·
axisPath·acode 는 정부 truth 위 결정론적 순수 규칙이라 read-time 분해 결과에 담는다. freq(분기/연도)
선택은 표현이라 read 계산(``cell.readCellWide``). ``valueRaw`` 는 콤마·괄호 그대로 무손실 — 숫자화는 read.

ACONTEXT 기간 토큰 문법(전수 실측): ``[C|P|BP]FY{year}[d|e]{marker}`` —
    marker = FY(연간) / FQ?(1분기) / HY?(반기·2분기) / TQ?(3분기), 접미 A(누적)·Q(단독)·∅(시점).
    예: dFY(연간흐름)·eFY(연말잔액)·dFQA(1분기누적=Q1)·dFQQ(1분기단독)·dHYA(반기누적6M)·
    dHYQ(2분기단독)·dTQA(3분기누적9M)·dTQQ(3분기단독)·eFQA(당기말잔액)·eFQ(전기말잔액).

LLM Specifications:
    AntiPatterns:
        - valueRaw 를 build 에서 숫자(콤마/괄호 제거)로 굽기 금지 — 불변 원본 훼손, 파싱은 read.
        - 메인 PANEL_SCHEMA 14-col 에 셀 컬럼 섞기 금지 — read-time in-memory view (wide 정체성).
        - freq 별 미리 펼친 컬럼 굽기 금지 — 토큰(ctxQuarter/ctxMode)만 굽고 freq 선택은 read.
    OutputSchema:
        - ``CELL_SCHEMA: dict[str, pl.DataType]`` 14 col.
        - ``CELL_PIVOT_INDEX: list[str]`` — acode×period pivot 행 정체성.
    Prerequisites:
        - polars.
    Freshness:
        - ACONTEXT 양식 변경 시 build/cell.decodeAcontext + 본 schema 동시 정합.
    Dataflow:
        - panel.parquet contentRaw → build.cell.cellsFromContent(read-time) → 본 schema → cell.readCellWide.
    TargetMarkets:
        - KR (DART). ACONTEXT 는 2025-03 사업보고서부터 (그 이전 셀 없음).
"""

from __future__ import annotations

import polars as pl

# 14-col read-time 셀 schema (재무 5표 native XBRL 셀).
CELL_SCHEMA: dict[str, pl.DataType] = {
    "corp": pl.Utf8,  # 종목코드
    "rceptNo": pl.Utf8,  # 접수번호 provenance
    "filingPeriod": pl.Utf8,  # 보고서 period (YYYYQn, 메인 panel 과 동일 라벨)
    "statement": pl.Utf8,  # canonicalKey(ACLASS) — BS/IS2/IS3/CF/EF
    "scope": pl.Utf8,  # consolidated / standalone (ACLASS _S 파생, read.scopeExpr 규칙)
    "acode": pl.Utf8,  # ifrs-full_Revenue / dart_* (언어무관 개념 정체성)
    "label": pl.Utf8,  # 같은 TR 첫 ACODE-없는 TE 한글 라벨 ("매출액 (주30)")
    "ctxYear": pl.Int32,  # ACONTEXT 토큰의 실연도 (당기/전기/전전기 직접)
    "ctxFlow": pl.Utf8,  # d(흐름/duration) / e(시점/instant)
    "ctxQuarter": pl.Int32,  # 1/2/3/4 (FQ=1분기·HY=반기/2분기·TQ=3분기·FY=연간/4분기)
    "ctxMode": pl.Utf8,  # Y(연간full) / A(누적YTD) / Q(분기단독) / P(시점bare)
    "axisPath": pl.Utf8,  # 멤버만 | join ("ConsolidatedMember|RetainedEarningsMember")
    "valueRaw": pl.Utf8,  # "333,605,938" / "(1,234)" 불변 원본 (숫자화는 read)
    "cellOrder": pl.UInt32,  # 표 내 TE 등장 순서 (정렬·라운드트립)
}

# acode×period pivot 시 행 정체성 (평탄화: acode@axisPath, 같은 acode 다축 충돌 회피).
# label 은 제외 — 주석번호가 연도마다 변동("매출액 (주30)"→"(주27)")해 같은 개념이 쪼개지므로
# 정체성 아님. read 가 최신 filing label 을 대표로 별도 부착.
CELL_PIVOT_INDEX: list[str] = ["statement", "acode", "axisPath", "scope"]
