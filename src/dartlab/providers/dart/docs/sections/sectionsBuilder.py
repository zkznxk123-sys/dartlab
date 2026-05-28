"""sections artifact 빌더 — wide DataFrame → period-shard long parquet 영속화.

본 모듈은 ``operation.sectionsRefactor`` 의 *SSOT 통합* 의 writer 진입점이다. 빌드는
sync stage 의 1 회 비용이고, 사용자 측은 ``sectionsStorage.py`` 의 read API 만 호출.

MVP 단계 (PR-1a):
    - 기존 ``Company(code).sections`` 호출 → wide DataFrame
    - period 컬럼을 long format 으로 melt
    - period 별로 split + ``data/dart/sections/{code}/{period}.parquet`` save
    - schema: topic / blockType / blockOrder / segmentKey / period / content

다음 단계:
    - content 컬럼을 content_raw / content_plain / content_table_struct 3 분리
    - segmentKey 의 sourceChunkIds 메타 추가 (raw XML lookup join 용)
    - rcept_no / rcept_date / doc_url 등 doc meta 컬럼 denormalize

본 모듈은 sync stage 에서만 호출. 런타임 호출 0 (sectionsStorage 가 read 전담).
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from pathlib import Path

import polars as pl

from dartlab.providers.dart.docs.sections.sectionsStorage import (
    _periodSortKey,
    sectionsDir,
    sectionsPath,
)

_log = logging.getLogger(__name__)


@contextmanager
def _forceRawSectionContent():
    """sectionsBuilder build 시 docs.parquet 의 stale mixed cache 무시.

    periodIter.iterPeriodSubsets 가 DARTLAB_SECTIONS_NO_MIXED env 인식. context 안에서
    raw section_content + 현재 xmlChunkToMixed 룰 (ALIGN/VALIGN 보존 등) 적용.
    context exit 시 env 원상복구.
    """
    KEY = "DARTLAB_SECTIONS_NO_MIXED"
    prev = os.environ.get(KEY)
    os.environ[KEY] = "1"
    try:
        yield
    finally:
        if prev is None:
            os.environ.pop(KEY, None)
        else:
            os.environ[KEY] = prev


def _isPeriodColumn(name: str) -> bool:
    """``"2025"`` / ``"2025Q1..Q4"`` 양식 매처. sections() 는 annual 을 ``"YYYYQ4"`` 로 emit."""
    if not name or len(name) < 4 or not name[:4].isdigit():
        return False
    if len(name) == 4:
        return True
    return name[4:] in ("Q1", "Q2", "Q3", "Q4")


_TABLE_BLOCK_RE = None  # lazy compile


def _extractTableStruct(content: str) -> str:
    """mixed content 에서 HTML ``<table>...</table>`` block 만 추출 (concat).

    plan snazzy-wibbling-origami PR-5b — finance pipeline (analysis/financial/* 60 모듈)
    의 향후 입력. ALIGN/VALIGN/rowspan/colspan 모두 보존된 HTML 표 구조만. paragraph 본문 +
    markdown heading 등 제거. 다중 ``<table>`` 발견 시 ``\\n\\n`` join.

    Args:
        content: ``content`` 컬럼 mixed string (markdown + HTML mixed).

    Returns:
        HTML ``<table>...</table>`` block 만의 concat string. 표 없으면 빈 문자열.
    """
    global _TABLE_BLOCK_RE
    if _TABLE_BLOCK_RE is None:
        import re as _re

        _TABLE_BLOCK_RE = _re.compile(r"<table[\s\S]*?</table>", _re.IGNORECASE)
    if not content or "<table" not in content:
        return ""
    matches = _TABLE_BLOCK_RE.findall(content)
    return "\n\n".join(matches) if matches else ""


def wideToLong(
    sectionsWide: pl.DataFrame,
    *,
    addPlain: bool = True,
    addTableStruct: bool = True,
) -> pl.DataFrame:
    """sections wide DataFrame → long format (period 컬럼 → row).

    PR-5a 이후: ``content_plain`` 컬럼 자동 추가 — HTML/markdown 태그 strip 결과. D.1
    분석 모듈 (sentiment / risk / search / disclosureDiff 등) 이 plain text 만 필요할 때
    ``Company.sectionsLong(columns=['topic','period','content_plain'])`` 으로 페이지 fault
    절약. polars columnar projection 으로 ``content`` (mixed) 컬럼은 RAM 0.

    Args:
        sectionsWide: 기존 ``Company.sections`` 출력. row meta + period 컬럼 N 개.
        addPlain: ``content_plain`` 컬럼 자동 생성 여부 (default True).

    Returns:
        long format DataFrame — meta cols + ``period`` + ``content`` (+ ``content_plain``).
        null content row 는 제거.

    Raises:
        없음.

    Example:
        >>> long = wideToLong(c.sections)  # doctest: +SKIP
        >>> set(long.columns) >= {"period", "content", "content_plain"}
        True
    """
    periodCols = [c for c in sectionsWide.columns if _isPeriodColumn(c)]
    if not periodCols:
        return sectionsWide.head(0)
    metaCols = [c for c in sectionsWide.columns if c not in periodCols]
    long = sectionsWide.unpivot(
        index=metaCols,
        on=periodCols,
        variable_name="period",
        value_name="content",
    )
    # sections cell value 가 polars Categorical dtype 인 경우 (메모리 최적화 결과) 가 있다 —
    # str.len_chars() 호출 위해 String cast 강제. 이미 String 이면 no-op.
    long = long.with_columns(pl.col("content").cast(pl.Utf8))
    # null 또는 빈 content row drop — sparse cell 제거. period-shard 저장 효율 ↑.
    long = long.filter(pl.col("content").is_not_null() & (pl.col("content").str.len_chars() > 0))
    if addPlain:
        # content_plain 컬럼 — HTML/markdown 태그 모두 strip. xmlAdapter.stripTagsFromCell SSOT.
        from dartlab.providers.dart.docs.sections.xmlAdapter import stripTagsFromCell

        long = long.with_columns(
            pl.col("content").map_elements(stripTagsFromCell, return_dtype=pl.Utf8).alias("content_plain")
        )
    if addTableStruct:
        # content_table_struct 컬럼 — HTML <table> block 만 추출 (ALIGN/rowspan/colspan 보존).
        # finance pipeline (analysis/financial/* 60 모듈) 의 향후 입력. 표 없는 row 는 "" 값.
        long = long.with_columns(
            pl.col("content").map_elements(_extractTableStruct, return_dtype=pl.Utf8).alias("content_table_struct")
        )
    return long


def saveSectionsByPeriod(
    stockCode: str,
    sectionsWide: pl.DataFrame,
    *,
    compression: str = "snappy",
) -> dict[str, int]:
    """wide DataFrame 을 period 별 parquet 으로 분할 저장.

    Args:
        stockCode: 종목코드.
        sectionsWide: ``Company.sections`` 출력 wide DataFrame.
        compression: parquet compression. default snappy (read 속도 우선).

    Returns:
        ``{period: rowCount}`` dict — 저장된 period 별 row 수.

    Raises:
        없음 — write 실패 시 warning + 부분 저장 결과 반환.

    Example:
        >>> result = saveSectionsByPeriod("005930", c.sections)  # doctest: +SKIP
        >>> result["2025Q3"]  # doctest: +SKIP
        2070
    """
    if sectionsWide is None or sectionsWide.is_empty():
        return {}
    long = wideToLong(sectionsWide)
    if long.is_empty():
        return {}
    outDir = sectionsDir(stockCode)
    outDir.mkdir(parents=True, exist_ok=True)
    result: dict[str, int] = {}
    for periodTuple, periodDf in long.group_by("period", maintain_order=True):
        period = periodTuple[0] if isinstance(periodTuple, tuple) else periodTuple
        if not isinstance(period, str):
            continue
        # period 컬럼 유지 — load 시 scan_parquet 결과에 period 식별 필수.
        # parquet dictionary encoding 으로 동일 값 반복은 사이즈 무시 (수 KB).
        path = sectionsPath(stockCode, period)
        try:
            periodDf.write_parquet(path, compression=compression)
            result[period] = periodDf.height
        except (OSError, pl.exceptions.ComputeError) as exc:
            _log.warning("sections period save 실패 (%s/%s): %s", stockCode, period, exc)
    return result


def _buildSectionsIndex(stockCode: str, compression: str = "snappy") -> bool:
    """docs.parquet 의 종목-period 메타 (rcept_no/rcept_dt/doc_url/corp_name/atocid) →
    ``data/dart/sections/{code}/_index.parquet`` save.

    plan snazzy-wibbling-origami PR-4b — docs.parquet 완전 폐기 path. sections artifact
    가 컬럼 schema 의 본문 (content/plain/table_struct) 만 보유 → 메타는 별도 작은
    파일 (~수 KB). callers (filingsCatalog 의 dartUrl 생성 / search 의 rcept_no 필터)
    가 _index.parquet 만 join 하면 docs.parquet 없이 동작.

    Args:
        stockCode: 종목코드.
        compression: parquet compression.

    Returns:
        bool — 메타 추출 + save 성공 시 True. docs.parquet 부재 또는 메타 컬럼 부재
        시 False (옛 호환).
    """
    import os as _os

    from dartlab.providers.dart.docs.sections.sectionsStorage import sectionsDir

    # 빌더 모드 표시 — dataLoader 가 합성 path 우회 → docs.parquet 직접 read.
    _os.environ["DARTLAB_BUILDER_MODE"] = "1"
    try:
        from dartlab.core.dataLoader import loadData

        # docs.parquet schema: year + report_type + rcept_no + rcept_date + section_url +
        # corp_name + atocid + assocnote. sections artifact 의 period 양식 (YYYY/YYYYQn)
        # 과 호환 위해 report_type 를 그대로 사용 (옛 schema 호환 — report_type 값이
        # "" 또는 "Q1" 등 양식).
        meta_cols = ["year", "report_type", "rcept_no", "rcept_date", "section_url", "corp_name", "atocid", "assocnote"]
        df = loadData(stockCode, category="docs", columns=meta_cols)
        if df is None or df.is_empty():
            return False
        availableCols = [c for c in meta_cols if c in df.columns]
        if "year" not in availableCols or "rcept_no" not in availableCols:
            return False
        # period 매핑 — sectionsBuilder periodIter 의 양식 (annual="YYYY", Q1/Q2/Q3="YYYYQn")
        # 과 일치. report_type 텍스트 패턴 (사업보고서 / 반기보고서 / 분기보고서 + 월) 으로
        # suffix 결정. selectReport SSOT (_REPORT_KIND_MAP) 와 동일 룰.
        if "report_type" in availableCols:
            rt = pl.col("report_type").cast(pl.Utf8).fill_null("")
            # sections artifact 의 periodKey 가 annual 도 Q4 alias 양식 ("YYYYQ4") 으로 emit
            # — periodIter SSOT 양식 일치. index 도 같은 양식으로 통일.
            suffix = (
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
            df = df.with_columns(pl.concat_str([pl.col("year").cast(pl.Utf8), suffix]).alias("period"))
        else:
            df = df.with_columns(pl.col("year").cast(pl.Utf8).alias("period"))
        keepCols = ["period"] + [c for c in availableCols if c not in ("year", "report_type")]
        index = df.select(keepCols).unique(subset=["period", "rcept_no"], keep="first")
        outDir = sectionsDir(stockCode)
        outDir.mkdir(parents=True, exist_ok=True)
        index.write_parquet(outDir / "_index.parquet", compression=compression)
        return True
    except (FileNotFoundError, ValueError, RuntimeError, pl.exceptions.ComputeError):
        return False
    finally:
        _os.environ.pop("DARTLAB_BUILDER_MODE", None)


def _buildSectionsRawXml(stockCode: str, compression: str = "zstd") -> bool:
    """docs.parquet 의 raw section_content (모든 XML 태그) → ``_raw.parquet`` save.

    plan snazzy-wibbling-origami — 사용자 비전 핵심. sections artifact 가 모든 DART
    XML 태그 (P/SPAN/TABLE/TD ALIGN/AUNIT/ADENO/CLASS/USERMARK 등) 보존. viewer 가
    raw XML 직접 사용. parser 룰 변경 시 sections 만 재빌드 (zip 재추출 0).

    schema: period / section_order / section_title / section_content / rcept_no.
    zstd compression — 종목당 ~수 MB (raw XML 압축률 80%+).

    Args:
        stockCode: 종목코드.
        compression: parquet compression. default zstd (raw XML 압축률 우선).

    Returns:
        bool — 성공 시 True. docs.parquet 부재 시 False.
    """
    import os as _os

    from dartlab.providers.dart.docs.sections.sectionsStorage import sectionsDir

    _os.environ["DARTLAB_BUILDER_MODE"] = "1"
    try:
        from dartlab.core.dataLoader import loadData

        raw_cols = ["year", "report_type", "section_order", "section_title", "section_content", "rcept_no"]
        df = loadData(stockCode, category="docs", columns=raw_cols)
        if df is None or df.is_empty():
            return False
        availableCols = [c for c in raw_cols if c in df.columns]
        if "section_content" not in availableCols:
            return False
        # period 매핑 (사업보고서 → Q4, 반기보고서 → Q2, 분기보고서 03/09 → Q1/Q3).
        if "report_type" in availableCols:
            rt = pl.col("report_type").cast(pl.Utf8).fill_null("")
            suffix = (
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
            df = df.with_columns(pl.concat_str([pl.col("year").cast(pl.Utf8), suffix]).alias("period"))
        else:
            df = df.with_columns(pl.col("year").cast(pl.Utf8).alias("period"))
        keepCols = ["period"] + [c for c in availableCols if c not in ("year", "report_type")]
        raw = df.select(keepCols).filter(
            pl.col("section_content").is_not_null() & (pl.col("section_content").str.len_chars() > 0)
        )
        outDir = sectionsDir(stockCode)
        outDir.mkdir(parents=True, exist_ok=True)
        raw.write_parquet(outDir / "_raw.parquet", compression=compression)
        return True
    except (FileNotFoundError, ValueError, RuntimeError, pl.exceptions.ComputeError) as exc:
        _log.warning("_buildSectionsRawXml (%s): %s", stockCode, exc)
        return False
    finally:
        _os.environ.pop("DARTLAB_BUILDER_MODE", None)


def buildSectionsArtifact(
    stockCode: str,
    *,
    compression: str = "snappy",
    forceRaw: bool = True,
) -> dict[str, int]:
    """zip → docs.parquet → ``Company.sections`` → period-shard parquet 영속화 (1 회 비용).

    sync stage 의 entry point. 본 함수는 다음을 수행:
        1. (``forceRaw=True``) docs.parquet 의 stale ``section_content_mixed`` 컬럼
           무시 → raw section_content + 현재 ``xmlChunkToMixed`` 룰 강제 적용.
           ALIGN/VALIGN 등 신 룰 변경분이 신 artifact 에 즉시 반영.
        2. ``Company(stockCode).sections`` 호출 → wide DataFrame (런타임 build).
           forceRaw 시 ~11s 추가 (raw → mixed 변환), 1 회 batch 비용.
        3. ``saveSectionsByPeriod`` 로 period 별 분할 + parquet 저장.

    런타임 (사용자 측) 은 본 함수 호출 0. ``sectionsStorage.loadSectionsWide`` 만 호출
    → mmap parquet → 콜드 1s 목표 달성.

    Args:
        stockCode: 종목코드 (6 자리).
        compression: parquet compression.
        forceRaw: True 시 mixed 사전계산 무시 + raw 에서 매번 변환 (신 룰 강제).
            False 시 옛 mixed cache 사용 (속도 ↑, ALIGN 신 룰 미반영).

    Returns:
        ``{period: rowCount}`` dict — 저장된 period 별 row 수. 빌드 실패 시 빈 dict.

    Raises:
        없음 — Company 생성 실패 또는 sections 빌드 실패 시 warning + 빈 dict.

    Example:
        >>> result = buildSectionsArtifact("005930")  # doctest: +SKIP
        >>> result["2025"]  # doctest: +SKIP
        2053
    """
    try:
        from dartlab import Company

        if forceRaw:
            with _forceRawSectionContent():
                c = Company(stockCode)
                sectionsWide = c.sections
        else:
            c = Company(stockCode)
            sectionsWide = c.sections
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        _log.warning("sections build 실패 (%s): %s", stockCode, exc)
        return {}
    if sectionsWide is None:
        _log.warning("sections build 결과 None (%s) — docs.parquet 부재?", stockCode)
        return {}
    result = saveSectionsByPeriod(stockCode, sectionsWide, compression=compression)
    # plan snazzy-wibbling-origami PR-4b — _index.parquet (docs 메타) + _raw.parquet (raw
    # XML 모든 태그) 동행 빌드. 사용자 비전 100%: sections artifact 가 모든 정보 보유,
    # docs.parquet 완전 폐기 가능.
    _buildSectionsIndex(stockCode, compression=compression)
    _buildSectionsRawXml(stockCode)
    return result


def clearSectionsArtifact(stockCode: str) -> int:
    """artifact 디렉터리의 모든 period parquet 삭제 + 디렉터리 제거.

    rebuild 전 청소 또는 stale artifact 정리 용도. ``_index.parquet`` 도 포함 삭제.

    Args:
        stockCode: 종목코드.

    Returns:
        삭제된 파일 수.

    Raises:
        없음 — OSError 는 무시 (best effort 삭제).

    Example:
        >>> clearSectionsArtifact("005930")  # doctest: +SKIP
        31
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
