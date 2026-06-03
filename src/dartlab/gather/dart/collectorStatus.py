"""DART 공시 수집 상태 helper — collector.py 분할 (룰 3 LoC).

`collector.py` 843 LoC 가 룰 3 임계 (>800) 위반. list / iter / stats 류 status
helper (~330 줄) 를 본 모듈로 분리. caller compat — collector.py 가 re-export.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

import dartlab.config as _cfg
from dartlab.core.dartClient import DartClient
from dartlab.core.dataConfig import DATA_RELEASES
from dartlab.core.logger import getLogger
from dartlab.gather.dart.corpCode import loadCorpCodes

_log = getLogger(__name__)


def _resolveDataDir() -> Path:
    """docs 데이터 디렉토리 (dartlab 캐시 경로) — collector.py 와 동일."""
    root = Path(_cfg.dataDir)
    d = root / DATA_RELEASES["docs"]["dir"]
    d.mkdir(parents=True, exist_ok=True)
    return d


def listUncollected(*, client: DartClient | None = None, limit: int | None = None) -> list[tuple[str, str]]:
    """아직 수집되지 않은 상장 종목 리스트.

    Args:
        client: DartClient (재사용 시).
        limit: 최대 항목 수. None 이면 무제한.

    Returns:
        ``[(종목코드, 회사명), ...]`` 리스트.

    Example:
        >>> listUncollected(limit=50)

    Raises:
        없음.

    SeeAlso:
        - ``DocsCollector`` 클래스 / ``collectMultiple`` — 본 모듈 entry.

    Requires:
        - dartlab
        - datetime
        - httpx
        - polars
        - random

    Capabilities:
        - DART 정기보고서 docs 수집 + 통계.

    Guide:
        - 운영자 수집 파이프라인 — 사용자 API 직접 호출 X.

    AIContext:
        internal collector — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 단일 키로 대량 수집 → 일 한도 초과.
            - quarters > 20 호출 시 부담.
        OutputSchema:
            - dict / pl.DataFrame / Path — 함수별.
        Prerequisites:
            - 인터넷 + DART_API_KEY + 종목코드.
        Freshness:
            - DART OpenAPI 실시간.
        Dataflow:
            - 종목 → DartClient → docs ZIP → HTML→text → parquet.
        TargetMarkets:
            - KR (DART) 정기보고서.
    """
    c = client or DartClient()
    codes = loadCorpCodes(c)

    listed = codes.filter(pl.col("stock_code").is_not_null() & (pl.col("stock_code").str.strip_chars() != ""))

    dataDir = _resolveDataDir()
    existing = {f.stem for f in dataDir.glob("*.parquet") if not f.name.startswith(".")}

    uncollected = listed.filter(~pl.col("stock_code").is_in(list(existing)))
    if limit is not None:
        uncollected = uncollected.head(limit)
    return list(
        zip(
            uncollected["stock_code"].to_list(),
            uncollected["corp_name"].to_list(),
        )
    )


def collectionStats(*, client: DartClient | None = None) -> dict:
    """수집 현황 통계.

    Args:
        client: 인자.

    Raises:
        없음.

    Example:
        >>> collectionStats(...)

    Returns:
        dict — 수집 통계.

    SeeAlso:
        - ``DocsCollector`` 클래스 / ``collectMultiple`` — 본 모듈 entry.

    Requires:
        - dartlab
        - datetime
        - httpx
        - polars
        - random

    Capabilities:
        - DART 정기보고서 docs 수집 + 통계.

    Guide:
        - 운영자 수집 파이프라인 — 사용자 API 직접 호출 X.

    AIContext:
        internal collector — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 단일 키로 대량 수집 → 일 한도 초과.
            - quarters > 20 호출 시 부담.
        OutputSchema:
            - dict / pl.DataFrame / Path — 함수별.
        Prerequisites:
            - 인터넷 + DART_API_KEY + 종목코드.
        Freshness:
            - DART OpenAPI 실시간.
        Dataflow:
            - 종목 → DartClient → docs ZIP → HTML→text → parquet.
        TargetMarkets:
            - KR (DART) 정기보고서.
    """
    c = client or DartClient()
    codes = loadCorpCodes(c)

    listed = codes.filter(pl.col("stock_code").is_not_null() & (pl.col("stock_code").str.strip_chars() != ""))

    dataDir = _resolveDataDir()
    existing = {f.stem for f in dataDir.glob("*.parquet") if not f.name.startswith(".")}
    collected = listed.filter(pl.col("stock_code").is_in(list(existing)))

    return {
        "totalListed": listed.height,
        "collected": collected.height,
        "uncollected": listed.height - collected.height,
    }


def listUncollectedKind(
    *,
    limit: int | None = None,
) -> list[tuple[str, str]]:
    """KRX KIND 기준 미수집 상장 종목 리스트.

    corp_code API 없이도 동작 (KIND HTML만 사용).

    Parameters
    ----------
    limit : int | None
        최대 개수. None이면 전체.

    Returns
    -------
    list
        [(종목코드, 회사명), ...]

    Raises:
        없음.

    Example:
        >>> listUncollectedKind(...)

    Args:
        limit: 최대 결과 수. None 이면 무제한.

    Returns:
        list[tuple[str, str]] — 종목 (코드, 이름) 페어 리스트.

    SeeAlso:
        - ``DocsCollector`` 클래스 / ``collectMultiple`` — 본 모듈 entry.

    Requires:
        - dartlab
        - datetime
        - httpx
        - polars
        - random

    Capabilities:
        - DART 정기보고서 docs 수집 + 통계.

    Guide:
        - 운영자 수집 파이프라인 — 사용자 API 직접 호출 X.

    AIContext:
        internal collector — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 단일 키로 대량 수집 → 일 한도 초과.
            - quarters > 20 호출 시 부담.
        OutputSchema:
            - dict / pl.DataFrame / Path — 함수별.
        Prerequisites:
            - 인터넷 + DART_API_KEY + 종목코드.
        Freshness:
            - DART OpenAPI 실시간.
        Dataflow:
            - 종목 → DartClient → docs ZIP → HTML→text → parquet.
        TargetMarkets:
            - KR (DART) 정기보고서.
    """
    from dartlab.core.listingResolver import getListingResolver

    resolver = getListingResolver()
    if resolver is None:
        return []
    kindDf = resolver.kindList()
    # 코넥스 제외, 종목코드 6자리 (영문자 포함 코드도 허용: 0001A0 등)
    kindDf = kindDf.filter(pl.col("시장구분") != "코넥스")
    kindDf = kindDf.filter(pl.col("종목코드").str.len_chars() == 6)

    dataDir = _resolveDataDir()
    existing = {f.stem for f in dataDir.glob("*.parquet") if not f.name.startswith(".")}

    uncollected = kindDf.filter(~pl.col("종목코드").is_in(list(existing)))

    result = list(
        zip(
            uncollected["종목코드"].to_list(),
            uncollected["회사명"].to_list(),
        )
    )
    if limit:
        result = result[:limit]
    return result


def iterUncollected(*, client: DartClient | None = None, limit: int | None = None):
    """``listUncollected`` 의 iterator pair (룰 10).

    Args:
        client: DartClient (재사용 시).
        limit: 최대 항목 수. None 이면 무제한.

    Yields:
        ``(종목코드, 회사명)`` 튜플.

    Raises:
        없음.

    Example:
        >>> for code, name in iterUncollected(limit=10):
        ...     print(code, name)

    SeeAlso:
        - ``DocsCollector`` 클래스 / ``collectMultiple`` — 본 모듈 entry.

    Requires:
        - dartlab
        - datetime
        - httpx
        - polars
        - random

    Capabilities:
        - DART 정기보고서 docs 수집 + 통계.

    Guide:
        - 운영자 수집 파이프라인 — 사용자 API 직접 호출 X.

    AIContext:
        internal collector — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 단일 키로 대량 수집 → 일 한도 초과.
            - quarters > 20 호출 시 부담.
        OutputSchema:
            - dict / pl.DataFrame / Path — 함수별.
        Prerequisites:
            - 인터넷 + DART_API_KEY + 종목코드.
        Freshness:
            - DART OpenAPI 실시간.
        Dataflow:
            - 종목 → DartClient → docs ZIP → HTML→text → parquet.
        TargetMarkets:
            - KR (DART) 정기보고서.
    """
    yield from listUncollected(client=client, limit=limit)


def iterUncollectedKind(*, limit: int | None = None):
    """``listUncollectedKind`` 의 iterator pair (룰 10).

    Args:
        limit: 최대 항목 수. None 이면 무제한.

    Yields:
        ``(종목코드, 회사명)`` 튜플.

    Raises:
        없음 (ListingResolver 부재 시 빈 generator).

    Example:
        >>> for code, name in iterUncollectedKind(limit=10):
        ...     print(code, name)

    SeeAlso:
        - ``DocsCollector`` 클래스 / ``collectMultiple`` — 본 모듈 entry.

    Requires:
        - dartlab
        - datetime
        - httpx
        - polars
        - random

    Capabilities:
        - DART 정기보고서 docs 수집 + 통계.

    Guide:
        - 운영자 수집 파이프라인 — 사용자 API 직접 호출 X.

    AIContext:
        internal collector — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 단일 키로 대량 수집 → 일 한도 초과.
            - quarters > 20 호출 시 부담.
        OutputSchema:
            - dict / pl.DataFrame / Path — 함수별.
        Prerequisites:
            - 인터넷 + DART_API_KEY + 종목코드.
        Freshness:
            - DART OpenAPI 실시간.
        Dataflow:
            - 종목 → DartClient → docs ZIP → HTML→text → parquet.
        TargetMarkets:
            - KR (DART) 정기보고서.
    """
    yield from listUncollectedKind(limit=limit)
