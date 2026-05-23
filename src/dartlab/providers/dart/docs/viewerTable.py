"""viewer 테이블 블록 빌더 — viewer.py 분할 (규칙 3 LoC).

structured / raw_markdown 테이블 블록 빌더 + 헬퍼.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import polars as pl

from dartlab.core.polarsUtil import isEmptyDf
from dartlab.providers.dart.docs.viewer import (
    BlockMeta,
    ViewerBlock,
    _periodCols,
)

if TYPE_CHECKING:
    from dartlab.providers.dart.company import Company


def _buildTableBlock(
    company: Company,
    topic: str,
    topicFrame: pl.DataFrame,
    bo: int,
    periodCols: list[str],
) -> ViewerBlock | None:
    """table 블록 — 수평화 시도 후 structured / raw_markdown 분류."""
    from dartlab.providers.dart.parse.tableHorizontalizer import horizontalizeTableBlock

    result = horizontalizeTableBlock(topicFrame, bo, periodCols, None)

    if result is not None and isinstance(result, pl.DataFrame):
        resPeriods = _periodCols(result)
        firstCol = result.columns[0] if result.columns else ""

        if resPeriods and firstCol and not firstCol.startswith("20"):
            sampleVal = str(result[resPeriods[0]][0]) if result.height > 0 else ""
            if _isRawMarkdown(sampleVal):
                return _buildRawMarkdownBlock(result, bo, resPeriods, firstCol)

            # 파이프 합침 값 감지 → raw_markdown으로 재분류
            if _hasPipeCells(result, resPeriods):
                return _buildRawMarkdownBlock(result, bo, resPeriods, firstCol)

            result = _cleanStructuredTable(result, resPeriods, firstCol)
            resPeriods = _periodCols(result)
            scale, divisor = _detectScale(result, resPeriods)
            return ViewerBlock(
                block=bo,
                kind="structured",
                source="docs",
                data=result,
                meta=BlockMeta(
                    scale=scale,
                    scaleDivisor=divisor,
                    periods=resPeriods,
                    rowCount=result.height,
                    colCount=len(result.columns),
                ),
            )

    # 수평화 실패 — 원본 마크다운
    boRows = topicFrame.filter(pl.col("blockOrder") == bo)
    keepCols = [c for c in periodCols if c in boRows.columns]
    nonNullCols = [c for c in keepCols if boRows[c].null_count() < boRows.height]

    if not nonNullCols:
        return None

    rawMd: dict[str, str] = {}
    row = boRows.row(0, named=True)
    for p in nonNullCols:
        val = row.get(p)
        if val is not None and str(val).strip():
            rawMd[p] = str(val)

    if not rawMd:
        return None

    return ViewerBlock(
        block=bo,
        kind="raw_markdown",
        source="docs",
        data=None,
        meta=BlockMeta(
            periods=list(rawMd.keys()),
            rowCount=1,
            colCount=len(rawMd),
        ),
        rawMarkdown=rawMd,
    )


def _buildRawMarkdownBlock(result: pl.DataFrame, bo: int, resPeriods: list[str], firstCol: str) -> ViewerBlock:
    """수평화 결과가 마크다운 문자열인 경우 raw_markdown으로 분류."""
    rawMd: dict[str, str] = {}
    for p in resPeriods:
        vals = result[p].to_list()
        combined = "\n".join(str(v) for v in vals if v is not None and str(v).strip())
        if combined:
            rawMd[p] = combined

    return ViewerBlock(
        block=bo,
        kind="raw_markdown",
        source="docs",
        data=None,
        meta=BlockMeta(
            periods=list(rawMd.keys()),
            rowCount=1,
            colCount=len(rawMd),
        ),
        rawMarkdown=rawMd,
    )


# ── Structured 테이블 정리 ──


def _periodSortKey(p: str) -> tuple[int, int]:
    """기간 컬럼 정렬키: 2021Q1→(2021,1), 2021→(2021,5), 2021Q4→(2021,4)."""
    m = re.fullmatch(r"(\d{4})(Q([1-4]))?", p)
    if not m:
        return (9999, 0)
    year = int(m.group(1))
    q = int(m.group(3)) if m.group(3) else 5  # 연간은 Q4 뒤
    return (year, q)


def _cleanStructuredTable(df: pl.DataFrame, periodCols: list[str], firstCol: str) -> pl.DataFrame:
    """structured 테이블 정리: 기간 정렬 + 전체 null 컬럼 제거."""
    # 1. 전체 null인 기간 컬럼 제거
    keepPeriods = []
    for p in periodCols:
        if p in df.columns and df[p].null_count() < df.height:
            keepPeriods.append(p)

    # 2. 기간 정렬
    keepPeriods.sort(key=_periodSortKey, reverse=True)

    # 3. 항목 컬럼 + 정렬된 기간 컬럼으로 재구성
    nonPeriodCols = [c for c in df.columns if c not in periodCols]
    orderedCols = nonPeriodCols + keepPeriods

    # 존재하는 컬럼만
    orderedCols = [c for c in orderedCols if c in df.columns]
    return df.select(orderedCols)


# ── 유틸리티 ──


def _isRawMarkdown(text: str) -> bool:
    """셀 값이 마크다운 테이블 원본인지 판별."""
    if not text or len(text) < 5:
        return False
    lines = text.strip().split("\n")
    mdLines = sum(1 for l in lines[:5] if l.strip().startswith("|"))
    return mdLines >= 2


def _hasPipeCells(df: pl.DataFrame, periodCols: list[str]) -> bool:
    """structured 테이블의 셀에 파이프 합침 값이 있는지 감지.

    horizontalizeTableBlock에서 헤더/데이터 컬럼 수 불일치 시
    `" | ".join(vals)` 형태로 합쳐진 셀을 감지한다.
    첫 5행 중 하나라도 " | " 패턴이 있으면 True.
    """
    for col in periodCols[:2]:
        if col not in df.columns:
            continue
        for val in df[col].head(5).to_list():
            if val is not None and " | " in str(val):
                return True
    return False


def _detectScale(df: pl.DataFrame, periodCols: list[str]) -> tuple[str | None, float]:
    """DataFrame 숫자 크기로 추천 스케일 판별."""
    maxAbs = 0.0
    for col in periodCols:
        if col not in df.columns:
            continue
        series = df[col]
        if series.dtype in (pl.Float64, pl.Float32, pl.Int64, pl.Int32):
            absMax = series.drop_nulls().cast(pl.Float64).abs().max()
            if absMax is not None and absMax > maxAbs:
                maxAbs = absMax
        else:
            for val in series.to_list()[:10]:
                if val is None:
                    continue
                s = str(val).strip().replace(",", "")
                try:
                    v = abs(float(s))
                    if v > maxAbs:
                        maxAbs = v
                except ValueError:
                    pass

    if maxAbs >= 1e12:
        return ("억원", 1e8)
    if maxAbs >= 1e8:
        return ("백만원", 1e6)
    return (None, 1.0)


# ── 직렬화 ──
