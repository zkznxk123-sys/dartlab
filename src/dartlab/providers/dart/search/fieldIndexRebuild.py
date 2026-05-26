"""fieldIndex content 인덱스 빌드/배포 — fieldIndex.py 분할 (룰 3 LoC).

`fieldIndex.py` 824 LoC 가 룰 3 임계 (>800) 위반. rebuildMain / rebuildDelta /
pushContentIndex / pullContentIndex / _clearDelta (~360 줄) 를 본 모듈로 분리.
caller compat — fieldIndex.py 가 re-export.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import polars as pl

import dartlab.config as _cfg
from dartlab.core.dataConfig import DATA_RELEASES
from dartlab.core.logger import getLogger

# fieldIndex ↔ fieldIndexRebuild 양방향 import 회피 — 함수 본문 lazy import.
# fieldIndex.py 가 본 모듈의 rebuildMain / rebuildDelta 외 7 항목을 re-export 하므로
# module-level `from fieldIndex import ...` 시 direct import 가 partially initialized
# 로 실패. fieldIndex 의 9 항목 (CONTENT_LIMIT · _contentIndexDir · _getSegments ·
# _IncrementalBuilder · buildContentSegment · clearCache · loadSegment · saveSegment ·
# searchContent) 사용은 모두 함수 본문 안 → 각 함수 시작 lazy import.

_log = getLogger(__name__)


def rebuildMain(
    *,
    includeAllFilings: bool = True,
    includeDocs: bool = True,
    contentLimit: int | None = None,
    showProgress: bool = True,
) -> int:
    """main 세그먼트 풀리빌드 — 전체 docs + 과거 allFilings.

    스트리밍 빌드: 파일 단위로 읽고 즉시 빌더에 feed 후 해제 (메모리 안전).
    시간 오래 걸림 (4M 문서 기준 약 18분). 월 1회 실행 권장.

    Returns
    -------
    int : 인덱싱된 문서 수.

    Raises:
        없음.

    Example:
        >>> rebuildMain(...)

    Args:
        includeAllFilings: True 면 전체 공시 (수시 포함).
        includeDocs: True 면 docs sections 포함.
        contentLimit: 본문 최대 문자 수.
        showProgress: True 면 progress 로그.

    Returns:
        int — 인덱스 빌드 건수.
    """
    import gc

    from dartlab.providers.dart.openapi.allFilingsCollector import _META_SUFFIX, _allFilingsDir
    from dartlab.providers.dart.search.fieldIndex import (
        CONTENT_LIMIT,
        _IncrementalBuilder,
        clearCache,
        saveSegment,
    )

    if contentLimit is None:
        contentLimit = CONTENT_LIMIT
    builder = _IncrementalBuilder()
    metaRecs: list[dict] = []
    totalDocs = 0

    def feedDf(df: pl.DataFrame, source: str) -> int:
        """parquet DataFrame 의 각 row 를 builder 에 추가 + meta record 동행 — 빌드 건수 반환.

        Args:
            df: parquet DataFrame (``section_content`` + meta 컬럼 포함).
            source: 인덱스 라벨 (예 ``"main"`` / ``"delta"``).

        Returns:
            추가된 doc 수.

        Raises:
            없음.

        Example:
            >>> feedDf(df, "main")  # doctest: +SKIP
        """
        added = 0
        for row in df.iter_rows(named=True):
            content = (row.get("section_content") or "")[:contentLimit]
            builder.addDoc(content)
            metaRecs.append(  # noqa: F821
                {
                    "rcept_no": row.get("rcept_no") or "",
                    "section_order": int(row.get("section_order") or 0),
                    "corp_code": row.get("corp_code") or "",
                    "corp_name": row.get("corp_name") or "",
                    "stock_code": row.get("stock_code") or "",
                    "rcept_dt": str(row.get("rcept_dt") or ""),
                    "report_nm": row.get("report_nm") or "",
                    "section_title": row.get("section_title") or "",
                    "text": content[:500],
                    "source": source,
                }
            )
            added += 1
        return added

    t0 = time.perf_counter()

    if includeAllFilings:
        outDir = _allFilingsDir()
        files = sorted(f for f in outDir.glob("*.parquet") if _META_SUFFIX not in f.stem)
        if showProgress:
            _log.info(f"[main] allFilings 스트리밍: {len(files)}개 파일")
        for i, f in enumerate(files):
            try:
                df = pl.read_parquet(f).filter(pl.col("section_content").is_not_null())
            except (pl.exceptions.PolarsError, OSError):
                continue
            totalDocs += feedDf(df, "allFilings")
            del df
            if (i + 1) % 50 == 0:
                gc.collect()
                if showProgress:
                    elapsed = time.perf_counter() - t0
                    _log.info(f"  allFilings {i + 1}/{len(files)}: {totalDocs:,} docs, {elapsed:.0f}초")

    if includeDocs:
        from dartlab.core.dataLoader import _getDataRoot

        docsDir = _getDataRoot() / "dart" / "docs"
        docsFiles = sorted(docsDir.glob("*.parquet"))
        if showProgress:
            _log.info(f"[main] docs 스트리밍: {len(docsFiles)}개 파일")
        for i, f in enumerate(docsFiles):
            try:
                df = pl.read_parquet(f).filter(pl.col("section_content").is_not_null())
            except (pl.exceptions.PolarsError, OSError):
                continue
            totalDocs += feedDf(df, "docs")
            del df
            if (i + 1) % 200 == 0:
                gc.collect()
                if showProgress:
                    elapsed = time.perf_counter() - t0
                    _log.info(f"  docs {i + 1}/{len(docsFiles)}: {totalDocs:,} docs, {elapsed:.0f}초")

    if showProgress:
        _log.info(f"[main] 축적 완료: {totalDocs:,} 문서, finalize 시작")

    idx = builder.finalize()
    meta = pl.DataFrame(metaRecs)
    del metaRecs
    gc.collect()

    saveSegment(idx, meta, "main")
    clearCache()
    _clearDelta()

    if showProgress:
        elapsed = time.perf_counter() - t0
        _log.info(f"[main] 저장 완료. 총 {elapsed / 60:.1f}분, {idx['nDocs']:,} 문서.")

    return idx["nDocs"]


def rebuildDelta(sinceDate: str | None = None, daysBack: int = 30, showProgress: bool = True) -> int:
    """delta 세그먼트 빌드 — 최근 N일 allFilings.

    main 이후 추가된 allFilings만 포함.

    Parameters
    ----------
    sinceDate : YYYYMMDD. 이 날짜 이후만. None이면 daysBack 사용.
    daysBack : sinceDate 미지정 시 N일 전부터.

    Raises:
        없음.

    Example:
        >>> rebuildDelta(...)

    Args:
        sinceDate: 시작일 YYYYMMDD. None 이면 daysBack 사용.
        daysBack: 과거 N 일 (sinceDate 없을 때).
        showProgress: True 면 progress 로그.

    Returns:
        int — 인덱스 빌드 건수.
    """
    from datetime import datetime, timedelta

    from dartlab.providers.dart.openapi.allFilingsCollector import _META_SUFFIX, _allFilingsDir
    from dartlab.providers.dart.search.fieldIndex import (
        buildContentSegment,
        clearCache,
        saveSegment,
    )

    if sinceDate is None:
        sinceDate = (datetime.now() - timedelta(days=daysBack)).strftime("%Y%m%d")

    outDir = _allFilingsDir()
    files = sorted(f for f in outDir.glob("*.parquet") if _META_SUFFIX not in f.stem and f.stem >= sinceDate)

    if showProgress:
        _log.info(f"[delta] {sinceDate} 이후: {len(files)}개 파일")

    rows: list[dict] = []
    for f in files:
        try:
            df = pl.read_parquet(f).filter(pl.col("section_content").is_not_null())
        except (pl.exceptions.PolarsError, OSError):
            continue
        for row in df.iter_rows(named=True):
            row["source"] = "allFilings"
            rows.append(row)

    if showProgress:
        _log.info(f"[delta] 총 {len(rows):,} 문서")

    if not rows:
        _clearDelta()
        return 0

    idx, meta = buildContentSegment(rows, showProgress=showProgress)
    saveSegment(idx, meta, "delta")
    clearCache()
    return idx["nDocs"]


def _clearDelta() -> None:
    """delta 세그먼트 파일 제거."""
    from dartlab.providers.dart.search.fieldIndex import _contentIndexDir

    outDir = _contentIndexDir()
    for name in ("delta.npz", "delta_stems.json", "delta_meta.parquet", "delta_info.json"):
        p = outDir / name
        if p.exists():
            p.unlink()


# ── HF 동기화 ──


def pushContentIndex(token: str | None = None) -> None:
    """content 인덱스 (main + delta) 를 HF에 업로드.

    Args:
        token: 인자.

    Raises:
        없음.

    Example:
        >>> pushContentIndex(...)
    """
    from huggingface_hub import HfApi

    from dartlab.providers.dart.search.fieldIndex import _contentIndexDir

    outDir = _contentIndexDir()
    api = HfApi(token=token)
    names = [
        "main.npz",
        "main_stems.json",
        "main_meta.parquet",
        "main_info.json",
        "delta.npz",
        "delta_stems.json",
        "delta_meta.parquet",
        "delta_info.json",
    ]
    for name in names:
        src = outDir / name
        if not src.exists():
            continue
        api.upload_file(
            path_or_fileobj=str(src),
            path_in_repo=f"dart/contentIndex/{name}",
            repo_id="eddmpython/dartlab-data",
            repo_type="dataset",
        )


def pullContentIndex() -> int:
    """HF에서 content 인덱스 다운로드 (main + delta).

    Returns
    -------
    int : 다운로드 성공한 파일 수.

    Raises:
        없음.

    Example:
        >>> pullContentIndex(...)

    Returns:
        int — 인덱스 빌드 건수.
    """
    from huggingface_hub import hf_hub_download

    from dartlab.core.dataLoader import _getDataRoot
    from dartlab.providers.dart.search.fieldIndex import _contentIndexDir, clearCache

    outDir = _contentIndexDir()
    outDir.mkdir(parents=True, exist_ok=True)
    dataDir = _getDataRoot()  # dart/contentIndex/ 앞의 루트

    names = [
        "main.npz",
        "main_stems.json",
        "main_meta.parquet",
        "main_info.json",
        "delta.npz",
        "delta_stems.json",
        "delta_meta.parquet",
        "delta_info.json",
    ]
    ok = 0
    _log.info("[cyan]⬇ HF[/] contentIndex (%d 파일)", len(names))
    for name in names:
        try:
            hf_hub_download(
                repo_id="eddmpython/dartlab-data",
                repo_type="dataset",
                filename=f"dart/contentIndex/{name}",
                local_dir=str(dataDir),
            )
            ok += 1
        except (OSError, ConnectionError, ValueError):
            # HF Hub 다운로드 실패 (네트워크 / 인증 / 파일 부재) — 다음 파일 진행.
            continue
    clearCache()
    _log.info("[green]✓[/] contentIndex (%d/%d 파일)", ok, len(names))
    return ok


# ── 통계 ──


def contentStats() -> dict:
    """content 인덱스 통계.

    Args:
        (인자 자동 생성).

    Raises:
        없음.

    Example:
        >>> contentStats(...)

    Returns:
        dict — 결과 통계.
    """
    from dartlab.providers.dart.search.fieldIndex import _getSegments

    segments = _getSegments()
    out: dict = {}
    for name, (idx, meta) in segments.items():
        out[name] = {
            "nDocs": idx["nDocs"],
            "nStems": len(idx["stemDict"]),
            "nPostings": int(idx["offsets"][-1]),
            "avgDocLength": idx["avgDocLength"],
        }
    return out


def iterContent(
    query: str,
    *,
    corpCode: str | None = None,
    stockCode: str | None = None,
    limit: int = 10,
):
    """``searchContent`` 의 iterator pair (룰 10).

    Args:
        query: 자연어 쿼리.
        corpCode: corp_code 필터.
        stockCode: 종목코드 필터.
        limit: 반환 건수.

    Yields:
        검색 결과 row dict.

    Example:
        >>> for row in iterContent("매출", limit=5):
        ...     print(row.get("rcept_no"))

    Raises:
        없음.
    """
    from dartlab.providers.dart.search.fieldIndex import searchContent

    df = searchContent(query, corpCode=corpCode, stockCode=stockCode, limit=limit)
    if df is None or df.is_empty():
        return
    yield from df.iter_rows(named=True)
