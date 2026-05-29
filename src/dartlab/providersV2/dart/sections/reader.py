"""RUNTIME sections backend — sections parquet → wide canonical pivot.

``c.sections`` 가 wrap 하는 provider-agnostic backend. scan_parquet + columnar
projection 만 사용 (lxml/zip import 0 — BUILD 와 물리 분리).

LLM Specifications:
    AntiPatterns:
        - 옛 docs.parquet 호환 layer 신설 금지 — 신 sections artifact 만 backend.
        - pivot index 자동 추론 금지 — schema 동결 (chapter / sectionLeaf /
          blockLeaf / disclosureKey / xbrlClass).
        - in-memory 누적 read 금지 — pl.scan_parquet + columnar projection.
        - lxml / zipfile import 금지 — BUILD (``filings.build``) 전용.
    OutputSchema:
        - ``readSectionsLong(code, marketNs) -> pl.DataFrame`` 14 col long.
        - ``readSectionsWide(code, marketNs, valueColumn) -> pl.DataFrame``
          wide pivot (index = canonical key, columns = period, cell = raw XML).
    Prerequisites:
        - data/dart/sections/{code}/*.parquet (BUILD 결과).
        - data/bridge/sectionsBridge.parquet (disclosureKey fallback).
    Freshness:
        - sections parquet 변경 시 캐시 0 (매 호출 read).
    Dataflow:
        - sections *.parquet → polars scan → disclosureKey 부착 (BUILD 에서
          이미 채워짐, 없으면 canonical fallback) → wide pivot.
    TargetMarkets:
        - KR (DART) + US (EDGAR) 공통.
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl

import dartlab.config as _cfg

_log = logging.getLogger(__name__)


def _sectionsDir(code: str, marketNs: str = "kr") -> Path:
    """sections artifact read 디렉터리 (신 sections SSOT).

    KR: ``data/dart/sections/{code}/``
    US: ``data/edgar/sections/{cik_or_ticker}/`` ([추측] EDGAR builder 명세).
    """
    base = "dart" if marketNs == "kr" else "edgar"
    return Path(_cfg.dataDir) / base / "sections" / code


def scanSections(
    code: str,
    *,
    marketNs: str = "kr",
    periods: list[str] | None = None,
) -> pl.LazyFrame | None:
    """sections artifact LazyFrame (collect 0 — show/select 가 per-query 필터).

    런타임 경량화 핵심: scan_parquet 만 반환. 호출자가 canonical 키로 filter +
    필요한 컬럼만 select → collect 시점에 해당 섹션 contentRaw 만 materialize
    (전체 본문 ~180MB 로드 회피).

    Args:
        code: 종목코드.
        marketNs: 시장 namespace.
        periods: 특정 period 파일만 scan. None = 전체.

    Returns:
        LazyFrame 또는 None (artifact 없음).
    """
    d = _sectionsDir(code, marketNs)
    if not d.exists():
        return None
    files = sorted(d.glob("*.parquet"))
    if periods:
        files = [f for f in files if f.stem in set(periods)]
    if not files:
        return None
    return pl.scan_parquet([str(f) for f in files])


def readSectionsMeta(
    code: str,
    *,
    marketNs: str = "kr",
    periods: list[str] | None = None,
) -> pl.DataFrame | None:
    """sections 구조 board (contentRaw 제외) — canonical 키 × period presence.

    ``c.sections`` 의 cheap default — 어떤 섹션이 어느 기간에 있는지. contentRaw
    디코드 0 → 데이터 footprint <1MB (본문은 show 시점 per-query pull).

    Args:
        code: 종목코드.
        marketNs: 시장 namespace.
        periods: 특정 period 만.

    Returns:
        wide meta board (index = canonical key, cell = blockOrder = presence)
        또는 None.
    """
    return readSectionsWide(code, marketNs=marketNs, periods=periods, valueColumn="blockOrder")


def readSectionsLong(
    code: str,
    *,
    marketNs: str = "kr",
    periods: list[str] | None = None,
) -> pl.DataFrame | None:
    """sections long format read + disclosureKey 부착.

    Args:
        code: 종목코드.
        marketNs: 시장 namespace ("kr" / "us").
        periods: 특정 period 만. None = 전체.

    Returns:
        long DataFrame (14 col + disclosureKey) 또는 None (artifact 없음).
    """
    d = _sectionsDir(code, marketNs)
    if not d.exists():
        return None
    files = sorted(d.glob("*.parquet"))
    if periods:
        files = [f for f in files if f.stem in set(periods)]
    if not files:
        return None
    try:
        df = pl.read_parquet([str(f) for f in files])
    except (pl.exceptions.PolarsError, OSError) as exc:
        _log.warning("sections read 실패 %s: %s", code, exc)
        return None
    if df.is_empty():
        return None
    # disclosureKey 부착 — BUILD 에서 이미 채워짐. 옛 artifact (전부 null) 만 fallback.
    if "disclosureKey" not in df.columns or df["disclosureKey"].null_count() == df.height:
        from .canonical import resolveBatch

        if "disclosureKey" in df.columns:
            df = df.drop("disclosureKey")
        df = resolveBatch(df, marketNs=marketNs)
    return df


def readSectionsWide(
    code: str,
    *,
    marketNs: str = "kr",
    periods: list[str] | None = None,
    valueColumn: str = "contentRaw",
) -> pl.DataFrame | None:
    """sections wide pivot — index = canonical key, columns = period.

    Args:
        code: 종목코드.
        marketNs: 시장 namespace.
        periods: 특정 period 만.
        valueColumn: pivot cell value 컬럼 (default "contentRaw" = raw XML).

    Returns:
        wide DataFrame. row identity = (chapter, sectionLeaf, blockLeaf,
        disclosureKey, xbrlClass). 또는 None.
    """
    long = readSectionsLong(code, marketNs=marketNs, periods=periods)
    if long is None or long.is_empty():
        return None
    if valueColumn not in long.columns:
        return None
    # 최신기준 수평화 (요구 #7) — 과거 era 의 xbrlClass·제목 drift 를 (disclosureKey,
    # scope) 단일 행으로 정렬. scope 가 xbrlClass 를 대체해 era drift 흡수.
    from .canonical import anchorLatest

    long = anchorLatest(long)
    indexCols = ["chapter", "sectionLeaf", "blockLeaf", "disclosureKey", "scope"]
    indexCols = [c for c in indexCols if c in long.columns]
    if not indexCols or "period" not in long.columns:
        return None
    # pivot 전 collapse — 한 period 에 같은 canonical 행(특히 disclosureKey null
    # narrative)이 다중 블록이면 blockOrder 순 contentRaw concat (무손실). pivot
    # aggregate_function="first" 가 다중 블록 중 1개만 남겨 버리는 손실 방지.
    if valueColumn == "contentRaw":
        aggExpr = pl.col("contentRaw").str.join("")
    else:
        aggExpr = pl.col(valueColumn).first()
    try:
        collapsed = (
            long.sort("blockOrder")
            .group_by([*indexCols, "period"], maintain_order=True)
            .agg(aggExpr.alias(valueColumn))
        )
        return collapsed.pivot(
            values=valueColumn,
            index=indexCols,
            on="period",
            aggregate_function="first",
        )
    except (pl.exceptions.ComputeError, pl.exceptions.ShapeError) as exc:
        _log.warning("sections pivot 실패 %s: %s", code, exc)
        return None
