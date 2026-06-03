"""DART docs↔sections 합성 로더 — providers 도메인 read (LoaderProvider DIP).

옛 위치: ``core/dataLoader.py`` (``_loadDocsFromSections`` / ``_trySynthesizeDocsFromSections``).
core 가 ``importlib.import_module("dartlab.providers...")`` 로 런타임 dispatch 하던
역방향 스멜을 제거하고, 도메인 read 합성을 providers 로 정위치한다 — EDGAR
``EdgarDocsLoader`` 가 동일 이관(Cut 7-step2)을 끝낸 검증 선례와 동형.

핵심:
- ``DartDocsLoader.load(...)`` — 신규 element-granular sections artifact 를 옛 docs.parquet
  호환 (section-granular) DataFrame 으로 재구성 (read path, 디스크 write 0).
- ``DartDocsLoader.synthesizeToPath(...)`` — sections artifact → docs.parquet 호환 schema
  로 1 회 합성 저장 (ensure path, 빌더 모드 재귀 회피).

core/dataLoader.loadData 의 ``category=="docs"`` 분기가 ``getLoader("docs")`` 로 본
로더를 dispatch. module load 시점에 ``_registerDartDocsLoader()`` 가 등록.
"""

from __future__ import annotations

import os as _os
from pathlib import Path

import polars as pl

from dartlab.providers.dart.docs.sections.sectionsStorage import (
    _ensureFromHf,
    hasSectionsArtifact,
    loadSectionsIndex,
    loadSectionsLong,
    loadSectionsRawXml,
    sectionsDir,
)


def _docsReportTypeExpr() -> pl.Expr:
    """period (YYYYQn) → 옛 docs.parquet report_type 문자열 합성.

    selectReport 호환 — annual=사업보고서, semi=반기보고서, Q1/Q3=분기보고서 (월 .03/.09).
    """
    year = pl.col("period").str.slice(0, 4)
    q = pl.col("period").str.slice(4)
    return (
        pl.when(q == "Q1")
        .then(pl.format("분기보고서 ({}.03)", year))
        .when(q == "Q2")
        .then(pl.format("반기보고서 ({}.06)", year))
        .when(q == "Q3")
        .then(pl.format("분기보고서 ({}.09)", year))
        .otherwise(pl.format("사업보고서 ({}.12)", year))
        .alias("report_type")
    )


class DartDocsLoader:
    """``docs`` 카테고리의 도메인 read 로더 (LoaderProvider DIP 구현).

    core/dataLoader.loadData 가 직접 합성 대신 registry dispatch (``getLoader("docs")``).
    module load 시점에 ``_registerDartDocsLoader()`` 가 등록.
    """

    category = "docs"

    def load(
        self,
        stockCode: str,
        *,
        columns: list[str] | None = None,
        sinceYear: int | None = None,
        predicate: "pl.Expr | None" = None,
    ) -> pl.DataFrame:
        """신규 sections artifact → 옛 docs.parquet 호환 (section-granular) DataFrame.

        Capabilities: element-granular sections artifact (``data/dart/docs/{code}/{period}.parquet``)
            를 ``(period, chapter, sectionLeaf)`` 로 group + ``contentRaw`` concat 해
            옛 docs.parquet 호환 (section_content/section_title/report_type/year/rcept_no
            + 메타) row 로 재구성한다. 디스크 write 0 (read path).
        AIContext: ``c.show(...)`` 등 docs 본문 조회 시 core.loadData(category="docs")
            가 본 메서드로 dispatch. evidence 는 반환 DataFrame 자체.
        Guide: 빌더 모드(DARTLAB_BUILDER_MODE) 가 아닐 때의 docs read 단일 경로.
        When: 사용자/엔진이 공시 본문(섹션)을 읽으려 할 때.
        How: ``getLoader("docs").load(stockCode, columns=..., sinceYear=..., predicate=...)``
            — core.loadData 가 내부 dispatch. section_content 는 비싼 컬럼이라
            ``columns`` 미요청 시 concat skip (메모리 가드).
        Requires: sections artifact (로컬 또는 HF lazy download). 네트워크는 artifact
            부재 시 HF 단일 종목 디렉터리 다운로드뿐.
        Raises: 없음 — 빈/부재 artifact 는 빈 DataFrame 으로 흡수.
        Example:
            >>> DartDocsLoader().load("005930", columns=["section_title"])  # doctest: +SKIP
        SeeAlso: ``synthesizeToPath`` (ensure path), ``sectionsStorage``,
            ``providers.edgar.docs.loader.EdgarDocsLoader``.
        """
        if not hasSectionsArtifact(stockCode):
            _ensureFromHf(stockCode)
        d = sectionsDir(stockCode)
        files = sorted(d.glob("*.parquet")) if d.exists() else []
        if not files:
            return pl.DataFrame()

        # 메모리 가드 — section_content (raw XML concat) 가 비싼 컬럼. caller 가 명시적으로
        # 요청 안 하면 (예: corp_name 만) concat skip → +수백MB 회피. 신규 artifact 의 필요
        # 컬럼만 lazy projection + sinceYear lazy 필터로 element row scan 량 축소 + streaming.
        needContent = columns is None or "section_content" in columns
        srcCols = ["period", "chapter", "sectionLeaf", "blockOrder", "rceptNo", "atocId", "aassocnote"]
        if needContent:
            srcCols.append("contentRaw")
        lf = pl.scan_parquet([str(f) for f in files]).select(srcCols)
        if sinceYear is not None:
            lf = lf.filter(pl.col("period").str.slice(0, 4).cast(pl.Int32, strict=False) >= sinceYear)

        aggs = [
            pl.col("blockOrder").min().alias("_minOrder"),
            pl.col("rceptNo").first().alias("rcept_no"),
            pl.col("atocId").first().alias("atocid"),
            pl.col("aassocnote").first().alias("assocnote"),
        ]
        if needContent:
            aggs.insert(0, pl.col("contentRaw").str.join("").alias("section_content"))
        grouped = (
            lf.sort("blockOrder")
            .group_by(["period", "chapter", "sectionLeaf"], maintain_order=True)
            .agg(aggs)
            .collect(engine="streaming")
        )
        if grouped.is_empty():
            return pl.DataFrame()

        # 옛 docs.parquet schema 재현 (section_content_mixed 제외).
        corpName = None
        try:
            from dartlab.core.listingResolver import getListingResolver

            resolver = getListingResolver()
            if resolver is not None:
                corpName = resolver.codeToName(stockCode)
        except Exception:  # noqa: BLE001 — 이름 조회 실패는 비치명 (corp_name null fallback)
            corpName = None

        df = grouped.with_columns(
            pl.col("period").str.slice(0, 4).alias("year"),
            _docsReportTypeExpr(),
            pl.coalesce([pl.col("sectionLeaf"), pl.col("chapter")]).alias("section_title"),
            pl.col("_minOrder").rank("ordinal").over("period").cast(pl.Int64).alias("section_order"),
            pl.lit(stockCode).alias("stock_code"),
            pl.lit(corpName).cast(pl.Utf8).alias("corp_name"),
            pl.col("rcept_no").str.slice(0, 8).alias("rcept_date"),
            pl.format("https://dart.fss.or.kr/dsaf001/main.do?rcpNo={}", pl.col("rcept_no")).alias("section_url"),
        ).drop("_minOrder")

        if predicate is not None:
            df = df.filter(predicate)
        if columns:
            available = [c for c in columns if c in df.columns]
            if available:
                df = df.select(available)
        from dartlab.core.dataLoaderNormalize import normalizeLoadedFrame

        return normalizeLoadedFrame(df, "docs")

    def synthesizeToPath(self, stockCode: str, dest: Path) -> bool:
        """sections artifact 가 있으면 docs.parquet 호환 schema 로 합성 저장 (1 회).

        Capabilities: 빌더 측 zip → docs.parquet 양식 호환 (section_title/section_content/
            year/report_kind 컬럼) 으로 변환하여 ``dest`` 에 저장. ``_raw.parquet`` 우선
            (raw XML 전 태그 보존), 옛 종목 부재 시 long fallback.
        AIContext: core.loadData/_ensureLocalParquet 의 docs ensure 경로 — 로컬 docs.parquet
            부재 시 HF 다운로드 전에 본 합성을 시도. evidence 는 dest 파일.
        Guide: 호출자(core)의 후속 path(mmap/predicate) 와 schema 호환 — 분석 모듈 95+
            caller 무변경 동작.
        When: docs 로컬 parquet 이 없고 sections artifact 로 합성 가능할 때.
        How: ``getLoader("docs").synthesizeToPath(stockCode, dest)`` — core 가 내부 dispatch.
            실패(빌더 모드·artifact 부재) 시 False → core 가 HF 다운로드 fallback.
        Requires: sections artifact (로컬 또는 HF lazy download). 빌더 모드
            (``DARTLAB_BUILDER_MODE=1``) 는 무한 루프 방지 위해 우회.
        Raises: 없음 — 합성 실패/예외는 False 로 흡수.
        Example:
            >>> DartDocsLoader().synthesizeToPath("005930", Path("data/dart/docs/005930.parquet"))  # doctest: +SKIP
        SeeAlso: ``load`` (read path), ``sectionsStorage.loadSectionsRawXml``.
        """
        if _os.environ.get("DARTLAB_BUILDER_MODE", "").strip() in ("1", "true", "True"):
            return False
        # sections artifact 부재 시 HF lazy download 시도 — 한 종목 디렉터리만 (~수 MB).
        if not hasSectionsArtifact(stockCode):
            if not _ensureFromHf(stockCode):
                return False
        # _raw.parquet 우선 — 사용자 비전 100% (raw XML 모든 태그 보존). 신 schema 종목 보유,
        # 옛 종목 부재 시 long fallback (mixed → section_content alias, lossy).
        rawXml = loadSectionsRawXml(stockCode)
        if rawXml is not None and not rawXml.is_empty():
            try:
                year = pl.col("period").str.slice(0, 4)
                suffix = pl.col("period").str.slice(4)
                synthesized = rawXml.with_columns(year.alias("year"), suffix.alias("report_kind"))
                index = loadSectionsIndex(stockCode)
                if index is not None and not index.is_empty():
                    # _raw 가 이미 rcept_no 보유 — _index 의 rcept_no 제외 (중복 차단).
                    indexCols = [c for c in index.columns if c not in ("period", "rcept_no")]
                    if indexCols:
                        synthesized = synthesized.join(
                            index.select(["period"] + indexCols).unique(subset=["period"]),
                            on="period",
                            how="left",
                        )
                dest.parent.mkdir(parents=True, exist_ok=True)
                synthesized.write_parquet(dest, compression="snappy")
                from dartlab.core.logger import getLogger

                _log = getLogger(__name__)
                _log.info(
                    "docs.parquet 합성 (%s, _raw.parquet → %d rows): %s",
                    stockCode,
                    synthesized.height,
                    dest.name,
                )
                return True
            except (pl.exceptions.ComputeError, pl.exceptions.SchemaError, OSError):
                pass  # fallback to long-based synthesis below
        # 옛 schema fallback — long format (mixed → section_content alias, raw XML lossy).
        long = loadSectionsLong(stockCode, columns=None)
        if long is None or long.is_empty():
            return False
        try:
            # period (YYYY 또는 YYYYQn) → year + reportKind 분리. sections 가 annual 을 YYYYQ4
            # 양식으로 emit (sectionsBuilder)
            year = pl.col("period").str.slice(0, 4)
            suffix = pl.col("period").str.slice(4)
            plainCol = "content_plain" if "content_plain" in long.columns else "content"
            synthesized = long.with_columns(
                year.alias("year"),
                suffix.alias("report_kind"),
                pl.col(plainCol).alias("section_content"),
                pl.col("topic").alias("section_title"),
            )
            # _index.parquet 의 메타 (rcept_no/rcept_dt/doc_url/corp_name/atocid) join — period
            # 기준. 옛 종목 (index 부재) 은 메타 컬럼 부재 → 호출자 메타 의존 path 만 실패.
            index = loadSectionsIndex(stockCode)
            if index is not None and not index.is_empty():
                indexCols = [c for c in index.columns if c != "period"]
                synthesized = synthesized.join(index.select(["period"] + indexCols), on="period", how="left")
            dest.parent.mkdir(parents=True, exist_ok=True)
            synthesized.write_parquet(dest, compression="snappy")
            from dartlab.core.logger import getLogger

            _log = getLogger(__name__)
            _log.info(
                "docs.parquet 합성 (%s, sections artifact → %d rows, index=%s): %s",
                stockCode,
                synthesized.height,
                index is not None,
                dest.name,
            )
            return True
        except (pl.exceptions.ComputeError, pl.exceptions.SchemaError, OSError):
            return False

    def ensure(
        self,
        stockCode: str,
        path: Path,
        *,
        sinceYear: int | None = None,
        asOf: str | None = None,
        refresh: str | bool = "auto",
    ) -> None:
        """docs 로컬 parquet 보장 — best-effort 합성 (LoaderProvider Protocol 정합).

        Requires: sections artifact (로컬 또는 HF). 합성 실패 시 HF docs.parquet
            다운로드 fallback 은 호출자(core/_ensureLocalParquet) 책임.
        Raises: 없음.
        Example:
            >>> DartDocsLoader().ensure("005930", Path("data/dart/docs/005930.parquet"))  # doctest: +SKIP
        """
        self.synthesizeToPath(stockCode, path)


def _registerDartDocsLoader() -> None:
    """import 시점 등록 — circular import 회피용 함수 lazy import."""
    from dartlab.core.loaders import registerLoader

    registerLoader(DartDocsLoader())


_registerDartDocsLoader()
