"""재무 데이터 공통 헬퍼 — L0 순수 유틸.

SelectResult→dict 변환, 기간 컬럼 추출, 차입금 합산 등.
analysis, credit, quant 모두가 사용하는 범용 함수.
원래 analysis/financial/_helpers.py에 있던 것을 L0으로 이동.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import polars as pl

_TRIANGLE_RE = re.compile(r"[△▲\u25B3\u25B2]")


# ══════════════════════════════════════
# 문자열 파싱
# ══════════════════════════════════════


def parseNumStr(s: str | None) -> float | None:
    """문자열 숫자를 float로 변환. 콤마, △(마이너스), % 처리."""
    if s is None:
        return None
    s = str(s).strip()
    if not s or s == "-":
        return None
    negative = False
    if _TRIANGLE_RE.match(s):
        negative = True
        s = _TRIANGLE_RE.sub("", s)
    s = s.replace(",", "").replace("%", "").strip()
    if not s:
        return None
    try:
        v = float(s)
        return -v if negative else v
    except ValueError:
        return None


# ══════════════════════════════════════
# 기간 컬럼 추출
# ══════════════════════════════════════


_PERIOD_COLUMN_RE = re.compile(r"^\d{4}(Q[1-4])?$")


def periodCols(df: pl.DataFrame) -> list[str]:
    """DataFrame에서 기간 컬럼만 추출 (최신 먼저)."""
    return [c for c in df.columns if _PERIOD_COLUMN_RE.fullmatch(c)]


def annualCols(df: pl.DataFrame, maxYears: int = 8) -> list[str]:
    """연도 컬럼만 추출 (Q4 또는 연도)."""
    cols = periodCols(df)
    annual = [c for c in cols if "Q" not in c]
    if annual:
        return annual[:maxYears]
    return [c for c in cols if c.endswith("Q4")][:maxYears]


def quarterlyCols(df: pl.DataFrame, maxQuarters: int = 8) -> list[str]:
    """분기 컬럼만 추출 (최신 먼저)."""
    cols = periodCols(df)
    return [c for c in cols if "Q" in c][:maxQuarters]


# ══════════════════════════════════════
# basePeriod 인프라
# ══════════════════════════════════════

_QUARTER_RE = re.compile(r"^(\d{4})Q([1-4])$")
_YEAR_RE = re.compile(r"^(\d{4})$")


@dataclass(frozen=True)
class PeriodRange:
    """basePeriod로부터 결정된 분석 기간 범위."""

    basePeriod: str
    annualCols: list[str]
    quarterlyCols: list[str]


def _periodSortKey(p: str) -> str:
    """기간 문자열을 정렬 가능한 키로 변환."""
    if "Q" not in p:
        return p + "Q5"
    return p


def annualColsFromPeriods(
    periods: list[str],
    basePeriod: str | None = None,
    maxYears: int = 8,
) -> list[str]:
    """기간 목록에서 연간 컬럼 추출 — basePeriod 이하만.

    연도("2024") 우선, 없으면 Q4("2024Q4") fallback.
    """
    cols = sorted([c for c in periods if "Q" not in c], reverse=True)
    if not cols:
        cols = sorted([c for c in periods if c.endswith("Q4")], reverse=True)
    if basePeriod is not None:
        limit = _periodSortKey(basePeriod)
        cols = [c for c in cols if _periodSortKey(c) <= limit]
    return cols[:maxYears]


def quarterlyColsFromPeriods(
    periods: list[str],
    basePeriod: str | None = None,
    maxQuarters: int = 8,
) -> list[str]:
    """기간 목록에서 분기 컬럼 추출 — basePeriod 이하만."""
    qs = sorted([c for c in periods if "Q" in c], reverse=True)
    if not qs:
        qs = sorted([c for c in periods if c.isdigit() and len(c) == 4], reverse=True)
    if basePeriod is not None:
        limit = _periodSortKey(basePeriod)
        qs = [c for c in qs if _periodSortKey(c) <= limit]
    return qs[:maxQuarters]


# ══════════════════════════════════════
# SelectResult → dict 변환
# ══════════════════════════════════════


def toDict(selectResult, maxPeriods: int = 0) -> tuple[dict[str, dict], list[str]] | None:
    """SelectResult → ({항목: {period: val}}, periodCols).

    EDGAR DataFrame(account=snakeId)일 때 키를 한국어 라벨로 자동 변환.
    """
    if selectResult is None:
        return None

    df = selectResult.df
    periods = sorted(periodCols(df), reverse=True)
    if maxPeriods > 0:
        periods = periods[:maxPeriods]
    if not periods:
        return None

    labelCol = "항목" if "항목" in df.columns else (df.columns[0] if df.columns else None)
    if labelCol is None:
        return None

    needsBridge = labelCol not in ("항목",)
    krLabels: dict[str, str] | None = None
    if needsBridge:
        from dartlab.core.utils.labels import getKoreanLabels

        krLabels = getKoreanLabels()

    data: dict[str, dict] = {}
    for row in df.iter_rows(named=True):
        label = str(row.get(labelCol, ""))
        key = krLabels.get(label, label) if krLabels else label
        data[key] = {c: row.get(c) for c in periods}
    if not data:
        return None

    from dartlab.core.utils.flow import synthesizeAnnualFromQuarters

    periods = synthesizeAnnualFromQuarters(data, periods, getattr(selectResult, "topic", None))
    return (data, periods)


def toDictBySnakeId(selectResult, maxPeriods: int = 0) -> tuple[dict[str, dict], list[str]] | None:
    """SelectResult → ({snakeId: {period: val}}, periodCols).

    snakeId + 한국어 라벨 양쪽 키로 접근 가능.
    SNAKEID_ALIASES 자동 노출.
    """
    if selectResult is None:
        return None

    df = selectResult.df
    periods = sorted(periodCols(df), reverse=True)
    if maxPeriods > 0:
        periods = periods[:maxPeriods]
    if not periods:
        return None

    idCol = "snakeId" if "snakeId" in df.columns else None
    if idCol is None:
        return toDict(selectResult, maxPeriods)

    labelCol = "항목" if "항목" in df.columns else None

    data: dict[str, dict] = {}
    for row in df.iter_rows(named=True):
        sid = str(row.get(idCol, ""))
        rowData = {c: row.get(c) for c in periods}
        data[sid] = rowData
        if labelCol:
            label = str(row.get(labelCol, ""))
            if label and label != sid:
                data[label] = rowData

    if not data:
        return None

    from dartlab.core.utils.flow import synthesizeAnnualFromQuarters

    periods = synthesizeAnnualFromQuarters(data, periods, getattr(selectResult, "topic", None))

    from dartlab.core.utils.labels import SNAKEID_ALIASES, mergeAliasRows

    mergeAliasRows(data, metaCols=set())
    # transitive 체인 (A→B, B→C 등) 해소를 위해 fixpoint 반복.
    # 예: stockholders_equity → total_equity, total_stockholders_equity → total_equity.
    # 1패스만으론 실행 순서에 따라 total_stockholders_equity 가 미채워질 수 있음.
    for _ in range(4):
        changed = False
        for alias, canonical in SNAKEID_ALIASES.items():
            canonRow = data.get(canonical)
            aliasRow = data.get(alias)
            if canonRow is not None and aliasRow is None:
                data[alias] = canonRow
                changed = True
            elif aliasRow is not None and canonRow is None:
                data[canonical] = aliasRow
                changed = True
        if not changed:
            break

    return (data, periods)


# ══════════════════════════════════════
# 행 merge
# ══════════════════════════════════════


def mergeRows(primary: dict | None, fallback: dict | None) -> dict:
    """두 행을 merge. primary의 값이 None이면 fallback 값 사용."""
    if primary is None and fallback is None:
        return {}
    if primary is None:
        return fallback or {}
    if fallback is None:
        return primary
    merged = dict(primary)
    for k, v in fallback.items():
        if merged.get(k) is None and v is not None:
            merged[k] = v
    return merged


# ══════════════════════════════════════
# 차입금 합산
# ══════════════════════════════════════

MAX_RATIO_YEARS = 8
