"""sections artifact → 옛 docs.parquet schema 호환 변환 SSOT.

plan snazzy-wibbling-origami v4 — docs.parquet 폐기 보류 (사용자 명시) 상태에서
*분석 path 만* sections artifact 우선 채택. 옛 docs.parquet 호출자 (sentiment /
risk / changes / disclosureDiff / docsIndex / scan changes builder 등) 가 0 변경
으로 sections artifact 를 소비하도록 호환 schema 노출.

호환 schema (옛 docs.parquet 의 long row 양식):
    year           Int32   period 첫 4 자리.
    report_kind    Utf8    period 의 quarter suffix ("" = annual / "Q1" / "Q2" / "Q3" / "Q4").
    section_title  Utf8    sections artifact 의 topic (16 토픽 namespace).
    section_content Utf8   sub-section content_raw join + runtime stripTags.
    rcept_no       Utf8    그대로.
    period         Utf8    sections artifact 그대로.

sub-section row 처리:
    sections artifact 는 sub-section 단위 row (1500+ row / period 005930). 옛 docs
    는 section_title 단위 1 row. 호환 위해 (period, topic) group_by aggregate —
    content_raw 들을 space-join 후 stripTags. 새 sub-section 기반 정밀 변화 감지
    가 필요하면 ``loadSectionsLong`` 직접 사용 (textSemanticPathKey 단위 shift).

LLM Specifications:
    AntiPatterns:
        - content_plain 컬럼 pre-compute 금지 (memory/feedback_no_content_plain_precompute.md).
          runtime stripTagsExpr (polars SIMD ~50ms) 만.
        - sub-section row 를 직접 노출하면 옛 docs 단어 검색 호출자가 같은 단어 반복
          카운트. group_by aggregate 필수.
    OutputSchema:
        - year/section_title/section_content/rcept_no/period/report_kind 6 컬럼.
    Prerequisites:
        - data/dart/sections/{code}/*.parquet 1 개 이상.
    Freshness:
        - sections artifact 빌드 직후 호출 가능 (변환 stateless).
    Dataflow:
        - loadSectionsLong → group_by(period, topic) → str.concat → stripTagsExpr.
    TargetMarkets:
        - KR (DART).
"""

from __future__ import annotations

import logging

import polars as pl

from dartlab.providers.dart.docs.sectionsLegacy.sectionsStorage import (
    hasSectionsArtifact,
    loadSectionsLong,
    stripTagsExpr,
)

_log = logging.getLogger(__name__)


def loadDocsCompat(stockCode: str) -> pl.DataFrame | None:
    """sections artifact → 옛 docs.parquet long schema 호환 DataFrame.

    sections artifact (sub-section row 양식) 를 (period, topic) group_by 후
    옛 docs schema (year/section_title/section_content/...) 로 노출. docs.parquet
    호출자 0 변경으로 sections artifact 채택.

    Args:
        stockCode: 종목코드.

    Returns:
        호환 DataFrame (year/section_title/section_content/rcept_no/period/report_kind)
        또는 None (sections artifact 부재).

    Capabilities:
        - sub-section row 를 옛 section_title 단위 1 row 로 aggregate.
        - content_raw join 후 runtime stripTagsExpr — 옛 plain text 호출자 호환.

    AIContext:
        sentiment/risk/disclosureDiff 같은 옛 docs schema 의존 모듈이 sections
        artifact 만으로 동작하게 만드는 진입점.

    Guide:
        새 sub-section 정밀 변화 감지가 필요하면 직접 ``loadSectionsLong`` 사용.
        본 helper 는 옛 호환 전용.

    When:
        docs.parquet 폐기 보류 상태에서 sections artifact 우선 path 가 필요한
        모든 분석 모듈 진입점.

    How:
        loadSectionsLong → group_by([period, topic]) → str.concat → stripTagsExpr.

    Requires:
        ``data/dart/sections/{code}/*.parquet`` 1 개 이상.

    Raises:
        없음 — artifact 부재 / 변환 실패 시 None.

    Example:
        >>> df = loadDocsCompat("005930")
        >>> sorted(df.columns)[:3]
        ['period', 'rcept_no', 'report_kind']
    """
    if not hasSectionsArtifact(stockCode):
        return None
    long = loadSectionsLong(stockCode)
    if long is None or long.is_empty():
        return None
    needed = {"period", "topic", "content_raw"}
    if not needed.issubset(set(long.columns)):
        return None
    try:
        # rcept_no 는 (period, topic) 단위로 first — 같은 period 내 같은 rcept_no 다중 row.
        grouped = long.group_by(["period", "topic"]).agg(
            pl.col("content_raw").str.concat(" ").alias("_content_raw_joined"),
            pl.col("rcept_no").first().alias("rcept_no")
            if "rcept_no" in long.columns
            else pl.lit("").alias("rcept_no"),
        )
        return grouped.with_columns(
            pl.col("period").str.slice(0, 4).cast(pl.Int32, strict=False).alias("year"),
            pl.col("period").str.slice(4).alias("report_kind"),
            pl.col("topic").alias("section_title"),
            stripTagsExpr("_content_raw_joined").alias("section_content"),
        ).drop("_content_raw_joined")
    except (pl.exceptions.ComputeError, pl.exceptions.SchemaError) as exc:
        _log.warning("docs compat 변환 실패 (%s): %s", stockCode, exc)
        return None


__all__ = ["loadDocsCompat"]
