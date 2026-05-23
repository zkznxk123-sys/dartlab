"""edgar/docs/fetch 수집 가능 universe — fetch.py 분할 (규칙 3 LoC).

buildEdgarCollectibleUniverse / prepareEdgarCollectibleUniverse + 캐시 헬퍼 +
SEC submissions JSON 파싱 (_getSubmissions / _findFilings / _mergeFilingArrays).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable

import httpx
import polars as pl

from dartlab.core.logger import getLogger
from dartlab.providers.edgar.docs.fetch import (
    HEADERS,
    SINCE_YEAR,
    _dedupeIssuerUniverse,
    _interleaveIssuerUniverse,
    _supportedRegularForms,
)

_log = getLogger(__name__)


def buildEdgarCollectibleUniverse(
    *,
    limit: int = 2000,
    sinceYear: int = SINCE_YEAR,
    forceRefresh: bool = False,
) -> pl.DataFrame:
    """EDGAR 수집 가능 universe 빌더 — ``prepareEdgarCollectibleUniverse`` shortcut.

    Args:
        limit: 최대 ticker 수.
        sinceYear: 시작 연도.
        forceRefresh: 캐시 무시.

    Returns:
        수집 가능 ticker DataFrame.

    Raises:
        없음.

    Example:
        >>> buildEdgarCollectibleUniverse(limit=500)
    """
    return prepareEdgarCollectibleUniverse(
        limit=limit,
        sinceYear=sinceYear,
        forceRefresh=forceRefresh,
    )


def prepareEdgarCollectibleUniverse(
    *,
    limit: int = 2000,
    sinceYear: int = SINCE_YEAR,
    forceRefresh: bool = False,
    progressPath: Path | None = None,
    flushEvery: int = 25,
    heartbeat: Callable[..., None] | None = None,
) -> pl.DataFrame:
    """EDGAR universe 평가 — supported regular filing 보유 여부 검증.

    Args:
        limit: 최대 평가 ticker 수.
        sinceYear: 시작 연도.
        forceRefresh: 캐시 무시 (전수 재평가).
        progressPath: jsonl progress 저장 경로.
        flushEvery: 캐시 flush 단위.
        heartbeat: stage 진행 콜백.

    Returns:
        수집 가능 ticker DataFrame (``has_supported_regular_filing=True``).

    Raises:
        httpx.HTTPError: SEC submissions API 호출 실패 시 (개별 ticker 는 skip).

    Example:
        >>> prepareEdgarCollectibleUniverse(limit=1000, forceRefresh=True)
    """
    from dartlab.core.dataLoader import _getDataRoot, loadEdgarListedUniverse

    cachePath = _getDataRoot() / "edgar" / "docsCollectibleUniverse.parquet"
    cacheDf = _loadCollectibleUniverseCache(cachePath, forceRefresh=forceRefresh)

    listed = (
        loadEdgarListedUniverse()
        .filter(pl.col("is_exchange_listed"))
        .select(["ticker", "cik", "title", "exchange"])
        .sort(["ticker", "cik"])
    )
    issuerUniverse = _dedupeIssuerUniverse(listed)

    if not cacheDf.is_empty():
        issuerUniverse = issuerUniverse.join(
            cacheDf.select(["cik", "has_supported_regular_filing", "supported_regular_forms", "last_checked"]),
            on="cik",
            how="left",
        )
    else:
        issuerUniverse = issuerUniverse.with_columns(
            pl.lit(None, dtype=pl.Boolean).alias("has_supported_regular_filing"),
            pl.lit(None, dtype=pl.Utf8).alias("supported_regular_forms"),
            pl.lit(None, dtype=pl.Utf8).alias("last_checked"),
        )

    evaluationUniverse = _interleaveIssuerUniverse(issuerUniverse)
    rows = evaluationUniverse.to_dicts()
    evaluatedBatch: list[dict[str, object]] = []
    selected: list[dict[str, object]] = []
    for idx, row in enumerate(rows, start=1):
        if heartbeat is not None:
            heartbeat(
                stage="prepare_universe",
                currentTicker=str(row["ticker"]),
                currentCik=str(row["cik"]),
                candidatesReady=len(selected),
                universeChecked=idx - 1,
            )

        if row.get("has_supported_regular_filing") is None or forceRefresh:
            try:
                submissions = _getSubmissions(str(row["cik"]))
                supportedForms = _supportedRegularForms(submissions, sinceYear)
                row["supported_regular_forms"] = ",".join(supportedForms)
                row["has_supported_regular_filing"] = bool(supportedForms)
                row["last_checked"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                universeStatus = "supported" if supportedForms else "unsupported_regular_forms"
            except httpx.HTTPError as exc:
                row["supported_regular_forms"] = None
                row["has_supported_regular_filing"] = None
                row["last_checked"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                universeStatus = "submissions_fetch_error"
                if progressPath is not None:
                    _appendJsonl(
                        progressPath,
                        {
                            "ticker": row["ticker"],
                            "cik": row["cik"],
                            "exchange": row["exchange"],
                            "status": universeStatus,
                            "reason": str(exc),
                            "last_checked": row["last_checked"],
                        },
                    )
                continue

            if progressPath is not None:
                _appendJsonl(
                    progressPath,
                    {
                        "ticker": row["ticker"],
                        "cik": row["cik"],
                        "exchange": row["exchange"],
                        "status": universeStatus,
                        "supported_regular_forms": row["supported_regular_forms"],
                        "last_checked": row["last_checked"],
                    },
                )

        evaluatedBatch.append(row)
        if row.get("has_supported_regular_filing"):
            selected.append(row)
        if flushEvery > 0 and len(evaluatedBatch) >= flushEvery:
            cacheDf = _mergeCollectibleUniverseCache(cachePath, cacheDf, evaluatedBatch)
            evaluatedBatch = []
        if limit > 0 and len(selected) >= limit:
            break

    if evaluatedBatch:
        cacheDf = _mergeCollectibleUniverseCache(cachePath, cacheDf, evaluatedBatch)

    result = pl.DataFrame(selected)
    if limit > 0 and result.height > limit:
        result = result.head(limit)
    if result.is_empty():
        return pl.DataFrame(
            schema={
                "candidate_order": pl.Int64,
                "ticker": pl.Utf8,
                "cik": pl.Utf8,
                "title": pl.Utf8,
                "exchange": pl.Utf8,
                "supported_regular_forms": pl.Utf8,
                "last_checked": pl.Utf8,
            }
        )
    result = result.with_row_index("candidate_order", offset=1)
    return result.select(
        [
            "candidate_order",
            "ticker",
            "cik",
            "title",
            "exchange",
            "supported_regular_forms",
            "last_checked",
        ]
    )


def _emptyCollectibleUniverseCache() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "ticker": pl.Utf8,
            "cik": pl.Utf8,
            "title": pl.Utf8,
            "exchange": pl.Utf8,
            "supported_regular_forms": pl.Utf8,
            "has_supported_regular_filing": pl.Boolean,
            "last_checked": pl.Utf8,
        }
    )


def _loadCollectibleUniverseCache(cachePath: Path, *, forceRefresh: bool) -> pl.DataFrame:
    if cachePath.exists() and not forceRefresh:
        return pl.read_parquet(cachePath)
    return _emptyCollectibleUniverseCache()


def _mergeCollectibleUniverseCache(
    cachePath: Path, cacheDf: pl.DataFrame, rows: list[dict[str, object]]
) -> pl.DataFrame:
    freshDf = pl.DataFrame(rows)
    if cacheDf.is_empty():
        merged = freshDf
    else:
        remaining = cacheDf.filter(~pl.col("cik").is_in(freshDf["cik"].to_list()))
        merged = pl.concat([remaining, freshDf], how="vertical_relaxed")
    cachePath.parent.mkdir(parents=True, exist_ok=True)
    merged.write_parquet(cachePath)
    return merged


def _appendJsonl(path: Path, record: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _resolveTickerMeta(ticker: str) -> dict[str, str]:
    from dartlab.providers.edgar.openapi.identity import resolveIssuer

    info = resolveIssuer(str(ticker).upper())
    return {
        "ticker": info["ticker"],
        "cik": info["cik"],
        "title": info["title"],
    }


def _getSubmissions(cik: str) -> dict:
    from dartlab.providers.edgar.openapi.submissions import getSubmissionsJson

    return getSubmissionsJson(cik)


def _mergeFilingArrays(submissions: dict, sinceYear: int) -> dict:
    from dartlab.providers.edgar.openapi.submissions import mergeSubmissionFilings

    return mergeSubmissionFilings(submissions, sinceYear=sinceYear)


def _findFilings(submissions: dict, sinceYear: int) -> list[dict]:
    from dartlab.providers.edgar.openapi.submissions import findRegularFilings

    rows = findRegularFilings(submissions, sinceYear=sinceYear)
    converted: list[dict] = []
    for row in rows:
        converted.append(
            {
                "formType": row["form"],
                "filingDate": row["filing_date"],
                "year": row["year"],
                "periodEnd": row["report_date"],
                "accessionNumber": row["accession_no"],
                "filingUrl": row["filing_url"],
            }
        )
    return converted
