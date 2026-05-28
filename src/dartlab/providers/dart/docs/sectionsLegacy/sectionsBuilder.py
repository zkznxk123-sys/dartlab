"""sections artifact 빌더 — SSOT 단순 schema (raw XML + 메타 통합).

plan snazzy-wibbling-origami 사용자 비전 100%:
    - cell = raw XML 그대로 (모든 DART 태그 P/SPAN/TABLE/TD ALIGN/AUNIT/ADENO/CLASS/USERMARK 보존)
    - 메타 컬럼 통합 (rcept_no, rcept_date, section_url, corp_name, atocid, assocnote)
    - 추가 파일 0 (_index, _raw 같은 부수 파일 폐기)
    - 추가 컬럼 0 (content_plain, content_table_struct 같은 derive 컬럼 폐기)
    - docs.parquet 완전 폐기 가능 — sections artifact 가 모든 정보 보유

저장 양식:
    ``data/dart/sections/{code}/{period}.parquet`` (period sharded long format)
    schema: chapter / topic / section_order / section_title /
            section_content (raw XML) /
            rcept_no / rcept_date / section_url / corp_name / atocid / assocnote / period

호출:
    - ``c.sectionsRaw()`` — wide pivot, cell = raw XML 그대로 (viewer / parser 룰 변경)
    - ``c.sections`` — wide pivot + polars native regex strip (분석 / show / agent)
    - ``c.sectionsLong()`` — period sharded long read (메모리 절약)

block 단위 분리 (text/table/heading) 는 호출자 (viewer / show) 가 runtime parsing.
빌더는 section 단위만 carry — 단순 SSOT.
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager

import polars as pl

from dartlab.providers.dart.docs.sectionsLegacy.sectionsStorage import (
    sectionsDir,
    sectionsPath,
)

_log = logging.getLogger(__name__)


@contextmanager
def _builderMode():
    """빌더 mode env set — dataLoader 가 docs.parquet 합성 path 우회 (무한 루프 차단)."""
    KEY = "DARTLAB_BUILDER_MODE"
    prev = os.environ.get(KEY)
    os.environ[KEY] = "1"
    try:
        yield
    finally:
        if prev is None:
            os.environ.pop(KEY, None)
        else:
            os.environ[KEY] = prev


_META_COLS = (
    "rcept_no",
    "rcept_date",
    "section_url",
    "corp_name",
    "atocid",
    "assocnote",
)


def _periodSuffixExpr() -> pl.Expr:
    """report_type 텍스트 → period suffix (Q1/Q2/Q3/Q4). selectReport SSOT 일관.

    사업보고서 → Q4 (annual alias), 반기보고서 → Q2, 분기보고서 03월 → Q1, 09월 → Q3.
    매칭 없으면 Q4.
    """
    rt = pl.col("report_type").cast(pl.Utf8).fill_null("")
    return (
        pl.when(rt.str.contains("사업보고서"))
        .then(pl.lit("Q4"))
        .when(rt.str.contains("반기보고서"))
        .then(pl.lit("Q2"))
        .when(rt.str.contains(r"분기보고서.*\d{4}\.03"))
        .then(pl.lit("Q1"))
        .when(rt.str.contains(r"분기보고서.*\d{4}\.09"))
        .then(pl.lit("Q3"))
        .otherwise(pl.lit("Q4"))
    )


def buildSectionsArtifact(
    stockCode: str,
    *,
    compression: str = "zstd",
) -> dict[str, int]:
    """docs.parquet → period sharded long parquet 영속화 (1 회 비용).

    SSOT 단순화: section 단위 long, cell = raw XML, 메타 통합.

    Args:
        stockCode: 종목코드 (6 자리).
        compression: parquet compression. default zstd (raw XML 압축률 80%+).

    Returns:
        ``{period: rowCount}`` dict — 저장된 period 별 row 수.

    Raises:
        없음 — docs.parquet 부재 / read 실패 silent + 빈 dict.
    """
    with _builderMode():
        try:
            from dartlab.core.dataLoader import loadData

            cols = ["year", "report_type", "section_order", "section_title", "section_content", *_META_COLS]
            df = loadData(stockCode, category="docs", columns=cols)
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            _log.warning("sections build 실패 (%s): %s", stockCode, exc)
            return {}
    if df is None or df.is_empty():
        return {}
    if "section_content" not in df.columns or "year" not in df.columns:
        return {}

    # period 매핑 — sectionsStorage.listAvailablePeriods 의 sort 와 호환.
    df = df.with_columns(pl.concat_str([pl.col("year").cast(pl.Utf8), _periodSuffixExpr()]).alias("period"))

    # chapter / topic 매핑 — section_title 의 Roman prefix 에서 chapter, title 자체가 topic.
    # 옛 시스템 (pipeline.sections) 의 chapter / topic canonical 매핑은 향후 마이그레이션.
    # 본 단순 빌더는 section_title 그대로 topic 으로 사용.
    df = df.with_columns(
        pl.col("section_title").str.extract(r"^([IVXivx]+)\.", 1).fill_null("").alias("chapter"),
        pl.col("section_title").alias("topic"),
    )

    # 비어있는 section_content row drop — sparse cell 제거.
    df = df.filter(pl.col("section_content").is_not_null() & (pl.col("section_content").str.len_chars() > 0))

    keepCols = (
        ["chapter", "topic", "section_order", "section_title", "section_content"]
        + [c for c in _META_COLS if c in df.columns]
        + ["period"]
    )
    df = df.select(keepCols)

    outDir = sectionsDir(stockCode)
    outDir.mkdir(parents=True, exist_ok=True)
    result: dict[str, int] = {}
    for periodTuple, periodDf in df.group_by("period", maintain_order=True):
        period = periodTuple[0] if isinstance(periodTuple, tuple) else periodTuple
        if not isinstance(period, str):
            continue
        path = sectionsPath(stockCode, period)
        try:
            periodDf.write_parquet(path, compression=compression)
            result[period] = periodDf.height
        except (OSError, pl.exceptions.ComputeError) as exc:
            _log.warning("sections period save 실패 (%s/%s): %s", stockCode, period, exc)
    return result


def clearSectionsArtifact(stockCode: str) -> int:
    """artifact 디렉터리의 모든 parquet 삭제 + 디렉터리 제거.

    Args:
        stockCode: 종목코드.

    Returns:
        삭제된 파일 수.
    """
    d = sectionsDir(stockCode)
    if not d.exists():
        return 0
    count = 0
    for p in d.glob("*.parquet"):
        try:
            p.unlink()
            count += 1
        except OSError:
            pass
    try:
        d.rmdir()
    except OSError:
        pass
    return count
