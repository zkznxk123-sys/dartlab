"""EDGAR sections artifact 빌더 — plan delegated-prancing-tower PR-E2.

filing 메타 + raw HTML + ``_splitItems`` 결과를 받아 period-sharded sections
parquet 으로 영속화. dual-write 강행 — fetch.py 의 ``fetchEdgarDocs`` 옛 path 가
docs.parquet emit 후 본 모듈의 ``buildSectionRowsFromFilings`` 호출로 sections
artifact 도 함께 emit. PR-E7 안전 게이트 통과 전까지 옛/신 양쪽 보존.

빌더 진입점 2 종:
- ``buildSectionRowsFromFilings`` — filing list + 옛 path 가 누적한 rows 위에서 sections
  row 동시 emit. fetch.py 내부 호출.
- ``buildEdgarSectionsForTicker`` — CLI/workflow 진입점. 1 ticker 의 전체 filing
  list 를 fetch + sections artifact 빌드 (옛 docs.parquet 도 dual-write).
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

import polars as pl

import dartlab.config as _cfg
from dartlab.providers.edgar.docs.sections.itemBoundary import (
    extractItemChunks,
    sanitizeRawHtml,
)
from dartlab.providers.edgar.docs.sections.sectionsStorage import (
    indexPath,
    sectionsDir,
    sectionsPath,
)

_log = logging.getLogger(__name__)

# content_raw 는 filing-level(전 block row 가 동일한 *전체 HTML* 공유). row 수만큼 중복
# 적재되어 거대 filing(예: 20-F 6.4MB × 4540 block ≈ 29GB)에서 polars Utf8 materialize
# 가 메모리 폭증·OOM-hang. 누적 content_raw bytes 가 본 가드를 넘으면 content_raw 를 비운다
# (분석용 content_plain 은 무손상; raw HTML 은 data/original 아카이브로 복구 가능).
# parquet dict-encoding 은 *disk* 만 dedup — in-memory 폭증은 별개 문제.
_CONTENT_RAW_MEM_CAP = 2_000_000_000  # 2GB


# sections artifact schema — pl.DataFrame 생성 시 명시. EDGAR filing meta 가 부재할
# 수 있어 nullable 양식 (Date / null) 강제.
_SECTIONS_SCHEMA: dict[str, pl.DataType] = {
    "topic": pl.Utf8,
    "blockType": pl.Utf8,
    "blockOrder": pl.Int64,
    "textNodeType": pl.Utf8,
    "textLevel": pl.Int64,
    "textPath": pl.Utf8,
    "period": pl.Utf8,
    "content_raw": pl.Utf8,
    "content_plain": pl.Utf8,
    "source_title": pl.Utf8,
    "ticker": pl.Utf8,
    "cik": pl.Utf8,
    "accession_no": pl.Utf8,
    "filing_date": pl.Utf8,
    "period_end": pl.Utf8,
    "form_type": pl.Utf8,
    "report_type": pl.Utf8,
    "period_key": pl.Utf8,
    "filing_url": pl.Utf8,
    "year": pl.Utf8,
}

_INDEX_SCHEMA: dict[str, pl.DataType] = {
    "period": pl.Utf8,
    "accession_no": pl.Utf8,
    "filing_date": pl.Utf8,
    "form_type": pl.Utf8,
    "period_key": pl.Utf8,
    "filing_url": pl.Utf8,
    "cik": pl.Utf8,
}


def buildSectionRowsFromFiling(
    *,
    items: list[dict],
    rawHtml: str,
    formType: str,
    meta: dict[str, Any],
) -> list[dict]:
    """filing 1 개 → section row dict list.

    Args:
        items: ``_splitItems`` 결과 ``[{"title": str, "content": str}]``.
        rawHtml: filing 원본 iXBRL HTML.
        formType: ``"10-K"`` / ``"10-Q"`` / ``"20-F"`` / ``"40-F"``.
        meta: filing-level meta dict — ticker/cik/accession_no/... (itemBoundary 가
            row 에 denormalize).

    Returns:
        row dict list. ``period`` 컬럼은 본 함수에서 ``meta["period_key"]`` 로 설정.

    Raises:
        없음.

    Example:
        >>> rows = buildSectionRowsFromFiling(items=items, rawHtml=raw, formType="10-K", meta=meta)  # doctest: +SKIP
    """
    rows = extractItemChunks(items, rawHtml, formType, meta)
    period = str(meta.get("period_key") or meta.get("year") or "")
    for r in rows:
        r["period"] = period
    return rows


def emitPeriodArtifacts(ticker: str, allRows: list[dict]) -> dict[str, int]:
    """ticker 의 누적 row 를 period 별 parquet 으로 emit (atomic rename).

    같은 ``period`` row 가 여러 filing 에서 나올 수 있음 (amendment 등) — 본 함수는
    period 별 group 후 *덮어쓰기*. 호출자가 dedup 책임 (``accession_no`` 기반).

    Args:
        ticker: US ticker.
        allRows: 전 filing 의 누적 row dict list.

    Returns:
        ``{"periodsWritten": N, "totalRows": M}``.

    Raises:
        없음 — 빈 입력 시 0 반환.

    Example:
        >>> emitPeriodArtifacts("AAPL", allRows)  # doctest: +SKIP
        {'periodsWritten': 31, 'totalRows': 919}
    """
    if not allRows:
        return {"periodsWritten": 0, "totalRows": 0}
    # 컬럼 단위 구성 — list-of-dict row-wise(pl.DataFrame(allRows, ...))는 polars
    # _sequence_of_dict_to_pydf 가 행마다 추론해 대형 입력(20-F 등 다수 row)에서 느림.
    # dict-of-list + 명시 schema 는 컬럼 직접 구성(빠른 경로).
    keys = [k for k in _SECTIONS_SCHEMA if k in allRows[0]]
    cols = {k: [r.get(k) for r in allRows] for k in keys}
    # content_raw(filing-level) in-memory 폭증 가드 — _CONTENT_RAW_MEM_CAP 참고.
    rawCol = cols.get("content_raw")
    if rawCol:
        rawBytes = 0
        for s in rawCol:
            rawBytes += len(s) if s else 0
            if rawBytes > _CONTENT_RAW_MEM_CAP:
                break
        if rawBytes > _CONTENT_RAW_MEM_CAP:
            _log.warning(
                "%s sections content_raw ~%.1fGB > %.1fGB cap — content_raw 생략(메모리 가드, content_plain 유지)",
                ticker,
                rawBytes / 1e9,
                _CONTENT_RAW_MEM_CAP / 1e9,
            )
            cols["content_raw"] = [""] * len(allRows)
    schema = {k: _SECTIONS_SCHEMA[k] for k in keys}
    for key, dtype in schema.items():
        if dtype == pl.Utf8:
            cols[key] = [None if value is None else str(value) for value in cols[key]]
    df = pl.DataFrame(cols, schema=schema)
    outDir = sectionsDir(ticker)
    outDir.mkdir(parents=True, exist_ok=True)
    periods = df["period"].drop_nulls().unique().to_list()
    written = 0
    for period in periods:
        if not period:
            continue
        sub = df.filter(pl.col("period") == period).sort("blockOrder")
        target = sectionsPath(ticker, period)
        tmp = target.with_suffix(".parquet.tmp")
        sub.write_parquet(str(tmp), compression="zstd")
        tmp.replace(target)
        written += 1
    return {"periodsWritten": written, "totalRows": int(df.height)}


def emitIndexArtifact(ticker: str, allFilings: list[dict]) -> Path | None:
    """``_index.parquet`` emit — period list + filing meta (accession_no 등).

    ``_loadLocalAccessionNos`` 가 본 산출물만 scan 해 freshness diff. 옛 docs.parquet
    전수 scan 대비 ~수십 배 작음.

    Args:
        ticker: US ticker.
        allFilings: filing meta dict list ([{period, accession_no, filing_date, ...}]).

    Returns:
        emitted index path 또는 None (입력 빈 list).

    Raises:
        없음.

    Example:
        >>> emitIndexArtifact("AAPL", filings)  # doctest: +SKIP
    """
    if not allFilings:
        return None
    rows: list[dict] = []
    for f in allFilings:
        rows.append(
            {
                "period": str(f.get("period_key") or f.get("year") or ""),
                "accession_no": str(f.get("accession_no") or ""),
                "filing_date": str(f.get("filing_date") or ""),
                "form_type": str(f.get("form_type") or ""),
                "period_key": str(f.get("period_key") or ""),
                "filing_url": str(f.get("filing_url") or ""),
                "cik": str(f.get("cik") or ""),
            }
        )
    df = pl.DataFrame(rows, schema=_INDEX_SCHEMA).unique(subset=["accession_no"], keep="last")
    outDir = sectionsDir(ticker)
    outDir.mkdir(parents=True, exist_ok=True)
    target = indexPath(ticker)
    tmp = target.with_suffix(".parquet.tmp")
    df.write_parquet(str(tmp), compression="zstd")
    tmp.replace(target)
    return target


def buildEdgarSectionsForTicker(
    ticker: str,
    *,
    sinceYear: int = 2009,
    incremental: bool = True,
    showProgress: bool = False,
) -> dict[str, int]:
    """1 ticker 전체 filing → sections artifact 빌드 (CLI/workflow 진입점).

    내부적으로 ``providers.edgar.docs.fetch.fetchEdgarDocs`` (옛 path) 를 호출 — 옛
    docs.parquet 도 동시 emit (dual-write). sections artifact 는 fetch.py 안 신규
    훅이 본 모듈 호출.

    ``incremental=True`` 시 ``loadSectionsIndex(ticker)`` 에서 기존 accession_no
    set 추출 후 미보유 accession 만 fetch. ``incremental=False`` 시 전체 재빌드.

    Args:
        ticker: US ticker.
        sinceYear: 시작 연도 (SEC filing fetch 범위).
        incremental: True 면 missing accession 만, False 면 전체 재빌드.
        showProgress: rich progress bar 표시.

    Returns:
        ``{"periodsWritten": N, "totalRows": M, "filingsProcessed": K}``.

    Raises:
        없음 — fetch 실패 ticker 는 0 반환 + warning log.

    Example:
        >>> buildEdgarSectionsForTicker("AAPL", incremental=True)  # doctest: +SKIP
    """
    from dartlab.core.dataLoader import _getDataRoot
    from dartlab.core.edgarClient import fetchEdgarDocs

    docsDir = _getDataRoot() / "edgar" / "docs"
    docsDir.mkdir(parents=True, exist_ok=True)
    docsPath = docsDir / f"{ticker.upper()}.parquet"
    try:
        # fetchEdgarDocs 가 옛 docs.parquet emit + 본 모듈의 sectionsBuilder 훅 호출
        # (PR-E2 fetch.py 패치). incremental=True 면 기존 accession_no 와 diff.
        fetchEdgarDocs(
            ticker,
            docsPath,
            sinceYear=sinceYear,
            showProgress=showProgress,
        )
    except (OSError, ValueError) as exc:
        _log.warning("buildEdgarSectionsForTicker fetch 실패 (%s): %s", ticker, exc)
        return {"periodsWritten": 0, "totalRows": 0, "filingsProcessed": 0}

    # fetchEdgarDocs 가 dual-write 완료 — 본 함수는 결과 카운트만 집계.
    from dartlab.providers.edgar.docs.sections.sectionsStorage import (
        hasSectionsArtifact,
        listAvailablePeriods,
        loadSectionsIndex,
    )

    if not hasSectionsArtifact(ticker):
        return {"periodsWritten": 0, "totalRows": 0, "filingsProcessed": 0}
    periods = listAvailablePeriods(ticker)
    idx = loadSectionsIndex(ticker)
    filings = 0 if idx is None else int(idx.height)
    # totalRows 정확 카운트 — 모든 period parquet의 height 합 (lazy scan 으로 메모리 0).
    if periods:
        totalRows = int(
            pl.scan_parquet([str(sectionsPath(ticker, p)) for p in periods]).select(pl.len()).collect().item()
        )
    else:
        totalRows = 0
    return {
        "periodsWritten": len(periods),
        "totalRows": totalRows,
        "filingsProcessed": filings,
    }


def removeSectionsArtifact(ticker: str) -> int:
    """ticker 의 sections artifact 디렉터리 삭제 — 테스트 / 강제 재빌드용.

    Args:
        ticker: US ticker.

    Returns:
        삭제된 파일 수.

    Raises:
        없음.

    Example:
        >>> removeSectionsArtifact("AAPL")  # doctest: +SKIP
    """
    d = sectionsDir(ticker)
    if not d.exists():
        return 0
    count = sum(1 for _ in d.glob("*"))
    shutil.rmtree(d, ignore_errors=True)
    return count
