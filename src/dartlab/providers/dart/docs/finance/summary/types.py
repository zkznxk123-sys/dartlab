from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl


@dataclass
class YearAccounts:
    """단일 period 의 표준 계정 시계열 — accounts dict + 원본 등장 순서."""

    year: str  # "2024" 또는 "2024Q1"
    accounts: dict[str, list[float | None]]
    order: list[str]


@dataclass
class BridgeResult:
    """두 period 사이 계정 매칭 결과 — 동일 계정 비율 + pair 매핑."""

    curYear: str  # period key
    prevYear: str
    rate: float
    matched: int
    total: int
    yearGap: int  # annual: 연도차, quarterly: 분기차
    pairs: dict[str, str]


@dataclass
class Segment:
    """계정 구조가 일관 유지되는 연속 period 구간 — bridge 매칭률 한 임계 이상."""

    startYear: str  # period key
    endYear: str
    nYears: int  # period 수
    matched: int
    total: int
    rate: float | None


@dataclass
class AnalysisResult:
    """summary 파이프라인 최종 결과 — 전체/연속 매칭률 + segment 분할 + 재무제표 DF."""

    corpName: str | None
    nYears: int  # period 수
    nPairs: int
    nBreakpoints: int
    nSegments: int
    allRate: float | None
    allMatched: int
    allTotal: int
    contRate: float | None
    contMatched: int
    contTotal: int
    segments: list[Segment]
    breakpoints: list[BridgeResult]
    pairResults: list[BridgeResult]
    yearAccounts: dict[str, YearAccounts]
    period: str = "y"  # "y" | "q" | "h"
    FS: pl.DataFrame | None = None  # 전체 재무제표 (BS + IS)
    BS: pl.DataFrame | None = None  # 재무상태표
    IS: pl.DataFrame | None = None  # 손익계산서
