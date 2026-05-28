"""sections artifact SSOT read API — period sharded, raw XML 보존, 10 컬럼 단일 schema.

plan snazzy-wibbling-origami v4 사용자 비전 100%:
    - 10 컬럼 schema (PROVIDER_AGNOSTIC_COLS SSOT): topic / blockType / blockOrder /
      textLevel / textPath / textSemanticPathKey / segmentKey / content_raw / period / rcept_no.
    - 추가 컬럼 0 (content_plain / mixed / table_struct 사전 계산 금지 —
      memory/feedback_no_content_plain_precompute.md). runtime stripTagsExpr 만.
    - 추가 파일 0 (_index / _raw 폐기). period sharded parquet 가 SSOT.
    - sub-section row 양식 (1500+ row / period 005930 vs 옛 docs ~30 row).
      sub-section split + cross-period 매칭 — textSemanticPathKey / segmentKey.
    - docs.parquet 보존 (사용자 명시 — dual-write 룰).

저장:
    ``data/dart/sections/{code}/{period}.parquet``

호출:
    - ``loadSectionsLong`` — period sharded long read (메모리 절약, lazy projection).
    - ``loadSectionsWide`` — wide pivot (period 컬럼 N 개, cell = raw XML).
    - ``Company.sectionsRaw()`` — wide 그대로 (viewer / parser 룰).
    - ``Company.sections`` — wide + cell strip (polars native regex, ~0.3s).
    - ``sectionsCompat.loadDocsCompat`` — 옛 docs schema 호환 양식 (sub-section row →
      topic 단위 group_by aggregate).
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl

import dartlab.config as _cfg

_log = logging.getLogger(__name__)

_SECTIONS_REL = "dart/sections"


def sectionsDir(stockCode: str) -> Path:
    """종목별 sections artifact 디렉터리 path."""
    return Path(_cfg.dataDir) / _SECTIONS_REL / stockCode


def sectionsPath(stockCode: str, period: str) -> Path:
    """단일 period parquet path."""
    return sectionsDir(stockCode) / f"{period}.parquet"


def listAvailablePeriods(stockCode: str) -> list[str]:
    """저장된 period 목록 (newer first). 디렉터리 미생성 시 빈 list."""
    d = sectionsDir(stockCode)
    if not d.exists():
        return []
    periods = [p.stem for p in d.glob("*.parquet") if not p.stem.startswith("_")]
    return sorted(periods, key=_periodSortKey, reverse=True)


def _periodSortKey(period: str) -> tuple[int, int]:
    """period → (year, quarter rank). sectionsBuilder 가 annual 을 Q4 alias 로 emit."""
    if not period or len(period) < 4 or not period[:4].isdigit():
        return (-1, -1)
    year = int(period[:4])
    if period.endswith("Q1"):
        return (year, 1)
    if period.endswith("Q2"):
        return (year, 2)
    if period.endswith("Q3"):
        return (year, 3)
    if period.endswith("Q4"):
        return (year, 4)
    return (year, 4)


def hasSectionsArtifact(stockCode: str) -> bool:
    """artifact 가 1 개 이상 period 존재하면 True."""
    return bool(listAvailablePeriods(stockCode))


_HF_DOWNLOAD_ATTEMPTED: set[str] = set()


def _ensureFromHf(stockCode: str) -> bool:
    """artifact 부재 시 HF dataset 에서 lazy 다운로드 — 한 종목 디렉터리만.

    환경변수 ``DARTLAB_NO_HF_DOWNLOAD=1`` 또는 offline 시 skip.
    한 종목 1 회만 시도 (실패 시 반복 회피).
    """
    if hasSectionsArtifact(stockCode):
        return True
    import os as _os

    if _os.environ.get("DARTLAB_NO_HF_DOWNLOAD", "").strip() in ("1", "true", "True"):
        return False
    if stockCode in _HF_DOWNLOAD_ATTEMPTED:
        return False
    _HF_DOWNLOAD_ATTEMPTED.add(stockCode)
    try:
        from huggingface_hub import snapshot_download

        from dartlab.core.dataConfig import DATA_RELEASES, HF_REPO

        sectionsDirRel = DATA_RELEASES["sections"]["dir"]
        snapshot_download(
            repo_id=HF_REPO,
            repo_type="dataset",
            allow_patterns=[f"{sectionsDirRel}/{stockCode}/*.parquet"],
            local_dir=str(Path(_cfg.dataDir)),
        )
        return hasSectionsArtifact(stockCode)
    except Exception as exc:  # noqa: BLE001
        _log.warning("sections artifact HF 다운로드 실패 (%s): %s", stockCode, exc)
        return False


def loadSectionsLong(
    stockCode: str,
    *,
    periods: list[str] | None = None,
    columns: list[str] | None = None,
) -> pl.DataFrame | None:
    """sections artifact long format read — period sharded glob + columnar projection.

    schema (10 컬럼, PROVIDER_AGNOSTIC_COLS SSOT):
        topic / blockType / blockOrder / textLevel / textPath / textSemanticPathKey /
        segmentKey / content_raw / period / rcept_no.

    Args:
        stockCode: 종목코드.
        periods: 특정 period 만. None = 전체.
        columns: select 할 컬럼 list. None = 전체.

    Returns:
        long format DataFrame 또는 None (artifact 부재 / 변환 실패).
    """
    if not hasSectionsArtifact(stockCode):
        _ensureFromHf(stockCode)
    available = listAvailablePeriods(stockCode)
    if not available:
        return None
    targetPeriods = available if periods is None else [p for p in available if p in set(periods)]
    if not targetPeriods:
        return None
    files = [str(sectionsPath(stockCode, p)) for p in targetPeriods]
    try:
        scan = pl.scan_parquet(files)
        if columns:
            availableSchema = set(scan.collect_schema().names())
            wantedCols = [c for c in columns if c in availableSchema]
            if not wantedCols:
                return None
            scan = scan.select(wantedCols)
        return scan.collect()
    except (OSError, pl.exceptions.ComputeError, pl.exceptions.ShapeError) as exc:
        _log.warning("sectionsLong load 실패 (%s): %s", stockCode, exc)
        return None


# pivot index 에서 제외되는 컬럼 — period 별 다르거나 cell value 후보.
_AUX_COLS: frozenset[str] = frozenset({"rcept_no", "rcept_date", "section_url", "corp_name", "atocid", "assocnote"})
_CONTENT_COLS: frozenset[str] = frozenset({"content", "content_plain", "content_raw", "section_content_raw", "text"})
# internal carry 컬럼 — pivot index 에서 제외 (디버깅 / period 별 다른 값).
_INTERNAL_COLS: frozenset[str] = frozenset({"sortOrder", "majorNum", "orderSeq", "sourceTopic", "segmentKeyBase"})


def loadSectionsWide(
    stockCode: str,
    *,
    periods: list[str] | None = None,
    valueColumn: str = "content_raw",
) -> pl.DataFrame | None:
    """sections artifact wide pivot — period 컬럼 N 개 + meta.

    plan snazzy-wibbling-origami SSOT. content_raw (lossless XML→HTML, viewer
    SSOT) 가 default. 분석 path 는 ``Company.sections`` 가 runtime
    ``stripTagsExpr`` 적용 (polars SIMD ~50ms).

    추가 컬럼 0 룰 (memory/feedback_no_content_plain_precompute.md): sections
    artifact 의 content 컬럼 = content_raw 1 개. plain/mixed 사전 계산 금지.

    Args:
        stockCode: 종목코드.
        periods: 특정 period 만. None = 전체.
        valueColumn: pivot cell value (default ``content_raw``). 옛 호환 컬럼
            (``content`` / ``section_content_raw``) 도 지원 — 옛 schema artifact
            read 시 fallback.

    Returns:
        wide DataFrame — pivot index (meta + 수평화 axis) + period 컬럼 N. None
        시 fallback (artifact 부재 / valueColumn 부재 / schema mismatch).
    """
    long = loadSectionsLong(stockCode, periods=periods)
    if long is None or long.is_empty():
        return None
    if "period" not in long.columns or valueColumn not in long.columns:
        return None
    # 메타 + 보조 content + internal 컬럼은 pivot index 에서 제외.
    otherContent = _CONTENT_COLS - {valueColumn}
    dropCols = [c for c in _AUX_COLS | otherContent | _INTERNAL_COLS if c in long.columns]
    if dropCols:
        long = long.drop(dropCols)
    indexCols = [c for c in long.columns if c not in ("period", valueColumn)]
    try:
        return long.pivot(
            values=valueColumn,
            index=indexCols,
            on="period",
            aggregate_function="first",
        )
    except (pl.exceptions.ComputeError, pl.exceptions.ShapeError) as exc:
        _log.warning("sectionsWide pivot 실패 (%s): %s", stockCode, exc)
        return None


def stripTagsExpr(col: str) -> pl.Expr:
    """polars native regex tag strip — XML 태그 제거 + 다중 공백 정리.

    rust SIMD 가속. Python map_elements 대비 50x 빠름. ``Company.sections`` 가 wide
    cell 들에 본 expr 일괄 적용 → 0.3s 안 strip 완료.

    Args:
        col: 대상 컬럼명.

    Returns:
        pl.Expr — strip 결과 string.
    """
    return pl.col(col).str.replace_all(r"<[^>]+>", " ").str.replace_all(r"[ \t]+", " ").str.strip_chars()
