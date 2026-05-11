"""DART Company 의 show/select 보조 utility.

Company.show / select 가 호출하는 stateless utility 헬퍼 — facade 의 책임 분산
1차 (show/select 본체 분리는 Stage 2-4b 이후 단계).

Module-level helpers:
    cleanFinanceDataFrame  — BS/IS/CF/CIS/SCE 후처리 (all-null 행 제거, 중복 병합)
    transposeToVertical    — wide → long 변환 (delegate to dartlab.core.show)
    warnUnknownTopic       — 미등록 topic 경고 (유사 topic 제안)
    applyPeriodFilter      — period 컬럼 필터링 (exact / Q4 fallback / period column)
"""

from __future__ import annotations

from typing import Any

import polars as pl

from dartlab.providers.dart.checks import _isPeriodColumn


def cleanFinanceDataFrame(df: pl.DataFrame, sjDiv: str) -> pl.DataFrame:
    """재무제표 DataFrame 후처리: all-null 행 제거, CF 고유 정리, 중복행 병합."""
    periodCols = [c for c in df.columns if _isPeriodColumn(c)]
    if not periodCols:
        return df
    labelCol = "항목"
    # CF 고유: 당기순이익 제거 (standalone 차분 오류), 영문 항목 제거
    if sjDiv == "CF":
        df = df.filter(~pl.col(labelCol).is_in(["당기순이익", "법인세비용차감전순이익"]))
        df = df.filter(~pl.col(labelCol).str.contains(r"^[a-z_]+$"))
    # 공통: all-null 행 제거 (모든 기간이 null 인 행)
    notAllNull = pl.any_horizontal([pl.col(c).is_not_null() for c in periodCols])
    df = df.filter(notAllNull)
    # 공통: 같은 항목 중복행 병합 — mapper 의 한국어 → 여러 snakeId (1:N) 충돌 해결.
    if df[labelCol].n_unique() < df.height:
        hasSnakeId = "snakeId" in df.columns
        aggCols = list(periodCols)
        extraAgg = [pl.col("snakeId").first().alias("snakeId")] if hasSnakeId else []
        merged = df.group_by(labelCol, maintain_order=True).agg(
            extraAgg + [pl.col(c).drop_nulls().first().alias(c) for c in aggCols]
        )
        df = merged.select([c for c in df.columns if c in merged.columns])
    return df


def transposeToVertical(wide: pl.DataFrame, periods: list[str]) -> pl.DataFrame | None:
    """wide → long 변환. dartlab.core.show 의 transposeToVertical 위임."""
    from dartlab.core.show import transposeToVertical as _coreTransposeToVertical

    return _coreTransposeToVertical(wide, periods)


def warnUnknownTopic(topic: str, sec: pl.DataFrame) -> None:
    """미등록 topic 경고 — 유사 topic 제안 + c.topics 안내."""
    import difflib
    import warnings

    all_topics = sec["topic"].unique().sort().to_list() if "topic" in sec.columns else []
    similar = difflib.get_close_matches(topic, all_topics, n=3, cutoff=0.4)
    if similar:
        warnings.warn(
            f"'{topic}' topic을 찾을 수 없습니다. "
            f"유사한 topic: {', '.join(similar)}. "
            f"전체 목록은 c.topics로 확인하세요.",
            stacklevel=3,
        )
    else:
        warnings.warn(
            f"'{topic}' topic을 찾을 수 없습니다. 전체 목록은 c.topics 또는 c.index로 확인하세요.",
            stacklevel=3,
        )


def applyPeriodFilter(payload: Any, period: str | None) -> Any:
    """period 컬럼 필터링 — exact / Q4 fallback / period 컬럼 매칭."""
    if period is None or not isinstance(payload, pl.DataFrame) or payload.is_empty():
        return payload
    from dartlab.providers.dart.docs.sections import rawPeriod

    requestedPeriod = str(period)
    normalizedPeriod = rawPeriod(period)

    # exact match first, then normalized (Q4 → annual alias), then Q4 expansion
    q4Fallback = f"{requestedPeriod}Q4" if "Q" not in requestedPeriod else None
    exactPeriod = (
        normalizedPeriod
        if normalizedPeriod in payload.columns
        else (
            requestedPeriod
            if requestedPeriod in payload.columns
            else (q4Fallback if q4Fallback and q4Fallback in payload.columns else None)
        )
    )
    if exactPeriod is not None:
        keepCols = [c for c in payload.columns if not _isPeriodColumn(c)]
        keepCols.append(exactPeriod)
        result = payload.select(keepCols)
        if exactPeriod != requestedPeriod:
            result = result.rename({exactPeriod: requestedPeriod})
        return result

    if "period" in payload.columns:
        return payload.filter(pl.col("period") == normalizedPeriod)
    if "year" in payload.columns:
        return payload.filter(pl.col("year").cast(pl.Utf8) == normalizedPeriod)
    return payload
