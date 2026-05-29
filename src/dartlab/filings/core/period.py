"""period (YYYYQn) 정규화 공통 — 시장 무관.

sections artifact·finance 모두 period 를 ``YYYYQn`` (예: 2025Q4) 단일 양식으로
emit → 문자열 정렬이 곧 시간 정렬 (2025Q4 > 2025Q3 > 2024Q4 …). annual 보고서는
``YYYYQ4``.

LLM Specifications:
    AntiPatterns:
        - period 를 (year, quarter) 튜플로 분해 후 정렬 금지 — YYYYQn 문자열 정렬로 충분.
        - period 컬럼 판별 시 길이/위치 가정 금지 — regex 단일 SSOT.
    OutputSchema:
        - ``isPeriodColumn(str)->bool`` / ``periodColumns(df)->list[str]`` /
          ``sortPeriods(list)->list[str]``.
    Prerequisites:
        - polars.
    TargetMarkets:
        - KR + US + JP 공통.
"""

from __future__ import annotations

import re

import polars as pl

# YYYY 또는 YYYYQn (Q1~Q4). 분기 미상 annual 은 YYYYQ4 로 emit 됨.
PERIOD_RE = re.compile(r"^\d{4}(Q[1-4])?$")


def isPeriodColumn(name: str) -> bool:
    """컬럼명이 period (YYYYQn) 양식인지."""
    return bool(PERIOD_RE.match(name))


def periodColumns(df: pl.DataFrame, *, descending: bool = True) -> list[str]:
    """DataFrame 의 period 컬럼만 추출 (기본 최근 우선)."""
    return sorted((c for c in df.columns if isPeriodColumn(c)), reverse=descending)


def sortPeriods(periods, *, descending: bool = True) -> list[str]:
    """period 리스트 정렬 (YYYYQn 문자열 정렬 = 시간 정렬)."""
    return sorted((p for p in periods if isPeriodColumn(p)), reverse=descending)
