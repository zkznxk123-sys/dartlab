"""provider-agnostic c.sections backend — sectionsV5 parquet → wide pivot.

마스터 플랜 v5 §1 데이터 흐름 + §4 공개 API.

LLM Specifications:
    AntiPatterns:
        - 옛 docs.parquet 호환 layer 신설 금지 — 신 sectionsV5 만 backend.
        - pivot index 자동 추론 금지 — schema 동결 (chapter / sectionLeaf /
          blockLeaf / disclosureKey).
        - in-memory 누적 read 금지 — pl.scan_parquet + columnar projection.
    OutputSchema:
        - ``readSectionsLong(code, marketNs) -> pl.DataFrame`` 14 col long.
        - ``readSectionsWide(code, marketNs, valueColumn) -> pl.DataFrame``
          wide pivot (index = canonical key, columns = period, cell = raw XML).
    Prerequisites:
        - data/{provider}/sectionsV5/{code}/*.parquet (P-S4 빌드 결과).
        - data/bridge/sectionsBridge.parquet (P-S7 seed).
    Freshness:
        - sectionsV5 parquet 변경 시 캐시 0 (매 호출 read).
    Dataflow:
        - sectionsV5 *.parquet → polars scan → disclosureKey 부착 (없으면
          canonicalResolver lookup) → wide pivot.
    TargetMarkets:
        - KR (DART) + US (EDGAR) 공통.

마스터 플랜: v5 §2.1 + §4.
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl

import dartlab.config as _cfg
from dartlab.scan.sectionsNew.canonicalResolver import resolveBatch

_log = logging.getLogger(__name__)


def _sectionsDir(code: str, marketNs: str = "kr") -> Path:
    """sections artifact read 디렉터리 (신 sections SSOT).

    KR: ``data/dart/docs/{code}/`` (사용자 결정 — 옛 docs.parquet 위치 대체).
    US: ``data/edgar/sections/{cik_or_ticker}/`` ([추측] EDGAR builder 명세).
    """
    if marketNs == "kr":
        return Path(_cfg.dataDir) / "dart" / "docs" / code
    return Path(_cfg.dataDir) / "edgar" / "sections" / code


def readSectionsLong(
    code: str,
    *,
    marketNs: str = "kr",
    periods: list[str] | None = None,
) -> pl.DataFrame | None:
    """sectionsV5 long format read + disclosureKey 부착.

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
        _log.warning("sectionsV5 read 실패 %s: %s", code, exc)
        return None
    if df.is_empty():
        return None
    # disclosureKey 부착 (이미 있으면 그대로, 없으면 resolver)
    if df["disclosureKey"].null_count() == df.height:
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
    """sectionsV5 wide pivot — index = canonical key, columns = period.

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
    indexCols = ["chapter", "sectionLeaf", "blockLeaf", "disclosureKey", "xbrlClass"]
    indexCols = [c for c in indexCols if c in long.columns]
    if not indexCols or "period" not in long.columns:
        return None
    try:
        return long.pivot(
            values=valueColumn,
            index=indexCols,
            on="period",
            aggregate_function="first",
        )
    except (pl.exceptions.ComputeError, pl.exceptions.ShapeError) as exc:
        _log.warning("sectionsV5 pivot 실패 %s: %s", code, exc)
        return None
