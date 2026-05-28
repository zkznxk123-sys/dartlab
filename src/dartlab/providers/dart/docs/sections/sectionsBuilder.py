"""sections artifact 빌더 — zip XML → period-sharded parquet 직접 (plan v4).

플로우:
    data/dart/original/docs/{code}/*.zip → ``_xmlFromZip`` → ``zipToTopicRows`` (v4
    sub-section walk + raw XML 보존) → period 별 그룹 → ``write_parquet`` (zstd /
    row_group 32K / statistics).

종목당 ~15s (005930 31 period 18s 측정). GitHub Actions 8 shard matrix 분산 ~ 1.5h
전체 2900+ 종목.

LLM Specifications:
    AntiPatterns:
        - ``Company.sections`` 호출 X — sectionsBuilder 가 자기 자신 sections 의
          input 이면 무한 chain.
        - ``loadData(category="docs")`` 호출 X — docs.parquet 의존 0 (sections 가 SSOT).
        - period 누적 dict (``_accumulatePeriodRows``) 호출 X — period sharded 양식
          이라 cross-period merge 는 사용자 측 ``loadSectionsWide`` pivot 에서.
        - content_plain / content_mixed 사전 계산 X (memory/feedback_no_content_plain_precompute.md).
          content_raw 단일 + runtime stripTagsExpr 만.
    OutputSchema:
        - ``data/dart/sections/{code}/{period}.parquet`` × N period.
        - 10 컬럼 (PROVIDER_AGNOSTIC_COLS SSOT): topic / blockType / blockOrder /
          textLevel / textPath / textSemanticPathKey / segmentKey / content_raw /
          period / rcept_no.
    Prerequisites:
        - ``data/dart/original/docs/{code}/*.zip`` 로컬 보유.
    Freshness:
        - parser 룰 변경 시 zip 재추출 0 (zip = SSOT). 5 baseline 빌드 검증 후 prod 반영.
    Dataflow:
        - zip → zipToTopicRows v4 → DataFrame (10 컬럼) → write_parquet (period 분리).
    TargetMarkets:
        - KR (DART). EDGAR 는 ``providers/edgar/docs/sections/`` 별도 builder 동일 schema.
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl

import dartlab.config as _cfg
from dartlab.providers.dart.docs.sections.sectionsStorage import (
    sectionsDir,
    sectionsPath,
)
from dartlab.providers.dart.docs.sections.zipToTopicRows import zipToTopicRows
from dartlab.providers.dart.openapi.zipCollector import _xmlFromZip

_log = logging.getLogger(__name__)

_ORIGINAL_DOCS_REL = "dart/original/docs"


def buildSectionsArtifact(
    stockCode: str,
    *,
    zipDir: Path | None = None,
    compression: str = "zstd",
    rowGroupSize: int = 32_768,
    dataPageSize: int = 65_536,
    forceRaw: bool = True,  # v4 noop — 항상 raw XML 양식.
) -> dict[str, int]:
    """종목 1 개 → ``data/dart/sections/{code}/{period}.parquet`` × N period.

    내부 단계:
        1. zip glob → 각 zip 별 ``_xmlFromZip`` → ``zipToTopicRows`` (v4 — TITLE 단위
           parseSectionsByTitle + raw XML walk + USERMARK B / heading marker 검출).
        2. row DF 의 ``period`` 컬럼 기준 그룹 — 같은 zip 안 다중 period 가능.
        3. period 별 write_parquet — zstd 압축 + row_group 32K (topic pushdown 최적)
           + statistics True (filter pushdown).

    Args:
        stockCode: 종목코드.
        zipDir: zip 디렉터리 override. None 이면 ``data/dart/original/docs/{code}``.
        compression: parquet compression (default ``zstd`` — 5~10x 압축).
        rowGroupSize: row group 사이즈 (default 32_768 — topic pushdown 최적).
        dataPageSize: data page 사이즈 (default 64KB — columnar projection 최적).
        forceRaw: noop v4 — 항상 raw XML 양식 (구 mixed cache path 폐기).

    Returns:
        ``{period: rowCount}`` dict. zip 디렉터리 부재 / 빈 zip 시 빈 dict.

    Raises:
        없음 — 실패 silent + ``log.warning``.

    Example:
        >>> buildSectionsArtifact("005930")
        {'2025Q4': 4376, '2025Q3': 2156, ...}
    """
    zipDirPath = zipDir or (Path(_cfg.dataDir) / _ORIGINAL_DOCS_REL / stockCode)
    if not zipDirPath.exists() or not zipDirPath.is_dir():
        _log.warning("zip 디렉터리 부재 (%s): %s", stockCode, zipDirPath)
        return {}
    zips = sorted(zipDirPath.glob("*.zip"))
    if not zips:
        _log.warning("zip 파일 0 (%s)", stockCode)
        return {}

    # zip → row DF (zipToTopicRows v4 가 10 컬럼 + period emit).
    # 옛 lossy chain (_expandStructuredRows / _periodDfToLong / xmlChunkToMixed) 호출 0.
    periodFrames: dict[str, list[pl.DataFrame]] = {}
    for zipPath in zips:
        try:
            xml = _xmlFromZip(zipPath)
        except (OSError, ValueError) as exc:
            _log.warning("zip read 실패 (%s/%s): %s", stockCode, zipPath.name, exc)
            continue
        if not xml:
            continue
        df = zipToTopicRows(xml, rcptNo=zipPath.stem, stockCode=stockCode)
        if df.is_empty():
            continue
        period = df["period"][0]
        if not period:
            continue
        periodFrames.setdefault(period, []).append(df)

    if not periodFrames:
        return {}

    outDir = sectionsDir(stockCode)
    outDir.mkdir(parents=True, exist_ok=True)
    result: dict[str, int] = {}
    for period, frames in periodFrames.items():
        periodDf = pl.concat(frames) if len(frames) > 1 else frames[0]
        path = sectionsPath(stockCode, period)
        try:
            periodDf.write_parquet(
                path,
                compression=compression,
                row_group_size=rowGroupSize,
                statistics=True,
                data_page_size=dataPageSize,
            )
            result[period] = periodDf.height
        except (OSError, pl.exceptions.ComputeError) as exc:
            _log.warning("sections period save 실패 (%s/%s): %s", stockCode, period, exc)

    return result


def clearSectionsArtifact(stockCode: str) -> int:
    """artifact 디렉터리의 모든 parquet 삭제 + 디렉터리 제거.

    Args:
        stockCode: 종목코드.

    Returns:
        삭제된 parquet 파일 수.
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


__all__ = ["buildSectionsArtifact", "clearSectionsArtifact"]
