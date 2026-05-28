"""금융상품 ID 양방향 매핑 — Ticker ↔ ISIN ↔ CUSIP ↔ FIGI ↔ LEI.

OpenFIGI v3 API (무인증 25 req/min, 5 ID/req = 125 ID/min) + 로컬 parquet cache.
30,000 종목 1 회 cache 박은 후 영구 — 재호출 시 즉시 hit.

```python
from dartlab.gather.mapping.symbology import tickerToFigi, isinToTicker

# 1) ticker → FIGI (글로벌 ID)
figi = tickerToFigi("AAPL", exchCode="US")  # "BBG000B9XRY4"

# 2) ISIN → ticker
ticker, exch = isinToTicker("US0378331005")  # ("AAPL", "US")
```

cache 파일: ``data/symbology/figiCache.parquet`` (gitignore /data/).
schema: ``(id_type, id_value, exch_code, figi, ticker, name, market_sector, security_type)``.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import httpx
import polars as pl

log = logging.getLogger(__name__)

_OPENFIGI_URL = "https://api.openfigi.com/v3/mapping"
_CACHE_DIR = Path("data/symbology")
_CACHE_FILE = _CACHE_DIR / "figiCache.parquet"

# 무인증 quota — 25 req/min × 5 ID/req. 인증 시 60 req/min × 10 ID/req.
_MAX_BATCH_SIZE = 5
_MIN_REQUEST_INTERVAL = 60.0 / 25  # 2.4 초/req (안전 마진 포함)


def lookupBulk(
    items: list[dict],
    *,
    apiKey: str | None = None,
    timeout: float = 15.0,
) -> list[dict]:
    """OpenFIGI v3 bulk mapping — raw 응답 반환.

    Sig: ``lookupBulk(items, *, apiKey=None, timeout=15.0) -> list[dict]``

    Capabilities: items 를 ``_MAX_BATCH_SIZE`` 청크로 나눠 POST + rate-limit sleep.
    AIContext: 모든 high-level 헬퍼 (tickerToFigi 등) 의 backend. 직접 호출 가능.
    Guide: items[i] = ``{"idType": "TICKER"|"ISIN"|"CUSIP"|"FIGI", "idValue": "...", "exchCode": "US"}``.
    When: cache miss 시 OpenFIGI live lookup.
    How: 5 ID 청크 → POST → 응답 list[{"data": [...]}] flatten → list[dict].

    Args:
        items: lookup 요청 리스트. 각 dict 필수: idType, idValue.
        apiKey: OpenFIGI API key. None 이면 무인증 (25 req/min).
        timeout: HTTP 타임아웃 (초).

    Returns:
        list[dict] — items 와 동일 길이. 각 dict ``{"figi", "ticker", "name", ...}``
        또는 ``{"error": "..."}`` (lookup 실패 시).

    Raises:
        httpx.HTTPError: 네트워크 실패 (재시도는 caller).

    Example:
        >>> lookupBulk([{"idType": "TICKER", "idValue": "AAPL", "exchCode": "US"}])

    See Also:
        ``tickerToFigi`` · ``isinToTicker`` — 캐시 통합 헬퍼.
    """
    if not items:
        return []
    headers = {"Content-Type": "application/json", "User-Agent": "dartlab-symbology/1.0"}
    if apiKey:
        headers["X-OPENFIGI-APIKEY"] = apiKey
    out: list[dict] = []
    with httpx.Client(headers=headers, timeout=timeout) as client:
        for chunk_start in range(0, len(items), _MAX_BATCH_SIZE):
            chunk = items[chunk_start : chunk_start + _MAX_BATCH_SIZE]
            if chunk_start > 0:
                time.sleep(_MIN_REQUEST_INTERVAL)
            try:
                resp = client.post(_OPENFIGI_URL, json=chunk)
                resp.raise_for_status()
                payload = resp.json()
            except httpx.HTTPError as exc:
                log.warning("OpenFIGI lookup 실패 (chunk %d): %s", chunk_start, exc)
                out.extend({"error": str(exc)} for _ in chunk)
                continue
            for entry in payload:
                if "data" in entry and entry["data"]:
                    # 다중 매치 시 첫 entry 만 (OpenFIGI 가 primary 우선)
                    out.append(entry["data"][0])
                else:
                    out.append({"error": entry.get("error", "no_match")})
    return out


def loadCache() -> pl.DataFrame:
    """로컬 parquet cache 로드 → DataFrame. 파일 없으면 빈 DF.

    Sig: ``loadCache() -> pl.DataFrame``

    Capabilities: cache parquet 읽기. 없으면 SCHEMA 만 매칭한 빈 DF.
    AIContext: tickerToFigi 등 헬퍼의 cache hit 진입.
    Guide: schema 변경 시 cache 폐기 후 재빌드.
    When: 매 lookup 호출 직전 (lazy).
    How: ``pl.read_parquet`` 또는 신규 DataFrame.

    Returns:
        DataFrame schema: ``id_type, id_value, exch_code, figi, ticker, name``.

    Raises:
        없음 — 읽기 실패 시 빈 DF.

    Example:
        >>> cache = loadCache()

    See Also:
        ``saveCache``.
    """
    schema = {
        "id_type": pl.Utf8,
        "id_value": pl.Utf8,
        "exch_code": pl.Utf8,
        "figi": pl.Utf8,
        "ticker": pl.Utf8,
        "name": pl.Utf8,
    }
    if not _CACHE_FILE.exists():
        return pl.DataFrame(schema=schema)
    try:
        return pl.read_parquet(_CACHE_FILE)
    except (OSError, pl.exceptions.PolarsError) as exc:
        log.warning("figiCache.parquet 읽기 실패 — 빈 cache 반환: %s", exc)
        return pl.DataFrame(schema=schema)


def saveCache(df: pl.DataFrame) -> None:
    """cache DataFrame 을 parquet 으로 저장. 디렉터리 자동 생성.

    Sig: ``saveCache(df) -> None``

    Capabilities: parquet write + 디렉터리 생성.
    AIContext: 신규 lookup 결과를 cache 에 영구화 시 호출.
    Guide: append 패턴은 caller 책임 (loadCache → concat → saveCache).
    When: live lookup 직후.
    How: mkdir + write_parquet.

    Args:
        df: 저장할 DataFrame.

    Returns:
        None.

    Raises:
        OSError: 디스크 쓰기 실패.

    Example:
        >>> saveCache(updated_df)

    See Also:
        ``loadCache``.
    """
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    df.write_parquet(_CACHE_FILE)


def tickerToFigi(
    ticker: str,
    *,
    exchCode: str | None = None,
    apiKey: str | None = None,
    useCache: bool = True,
) -> str | None:
    """ticker → FIGI (글로벌 종목 ID). cache hit 우선.

    Sig: ``tickerToFigi(ticker, *, exchCode=None, apiKey=None, useCache=True) -> str | None``

    Capabilities: cache 조회 → miss 시 OpenFIGI live → 결과 cache 추가.
    AIContext: 사용자 ticker 입력 → 글로벌 ID 변환 — 다중 거래소 정규화 진입.
    Guide: exchCode 미지정 시 ticker 매치 첫 entry. 명시 권장.
    When: 사용자가 글로벌 자산 ID 필요 시.
    How: loadCache → filter (id_type=TICKER, id_value=ticker, exch=exchCode) → hit 면 figi /
        miss 면 lookupBulk → cache update → saveCache.

    Args:
        ticker: 종목 코드 (예: ``"AAPL"``, ``"005930"``).
        exchCode: OpenFIGI exchange code (``"US"``, ``"KS"``, ``"LN"`` 등).
        apiKey: OpenFIGI API key.
        useCache: False 면 cache 우회 (강제 live).

    Returns:
        FIGI 12자 문자열 또는 None (lookup 실패).

    Raises:
        없음 — 모든 예외 흡수.

    Example:
        >>> tickerToFigi("AAPL", exchCode="US")
        'BBG000B9XRY4'

    See Also:
        ``isinToTicker`` · ``figiToTicker``.
    """
    if useCache:
        cache = loadCache()
        if not cache.is_empty():
            f = cache.filter(
                (pl.col("id_type") == "TICKER")
                & (pl.col("id_value") == ticker)
                & ((pl.col("exch_code") == exchCode) if exchCode else pl.lit(True))
            )
            if not f.is_empty() and f["figi"][0]:
                return f["figi"][0]

    req: dict = {"idType": "TICKER", "idValue": ticker}
    if exchCode:
        req["exchCode"] = exchCode
    results = lookupBulk([req], apiKey=apiKey)
    if not results or "error" in results[0]:
        return None
    figi = results[0].get("figi")
    if useCache and figi:
        _appendToCache(
            "TICKER",
            ticker,
            exchCode or "",
            figi,
            ticker=results[0].get("ticker", ticker),
            name=results[0].get("name", ""),
        )
    return figi


def isinToTicker(
    isin: str,
    *,
    apiKey: str | None = None,
    useCache: bool = True,
) -> tuple[str, str] | None:
    """ISIN → (ticker, exchCode). cache hit 우선.

    Sig: ``isinToTicker(isin, *, apiKey=None, useCache=True) -> tuple[str, str] | None``

    Capabilities: ISIN 12자 → OpenFIGI mapping → ticker + 거래소 추출.
    AIContext: 사용자 ISIN 입력 → ticker 변환 (handlePrice 자동 감지 진입).
    Guide: 다중 매치 시 OpenFIGI primary listing 첫 entry.
    When: 사용자 입력이 ISIN 형식 (12자 영숫자) 일 때.
    How: cache filter (id_type=ISIN) → miss 면 live → cache update.

    Args:
        isin: 12자 ISIN 문자열.
        apiKey: OpenFIGI API key.
        useCache: cache 사용 여부.

    Returns:
        ``(ticker, exchCode)`` 튜플 또는 None.

    Raises:
        없음.

    Example:
        >>> isinToTicker("US0378331005")
        ('AAPL', 'US')

    See Also:
        ``tickerToFigi`` · ``figiToTicker``.
    """
    if useCache:
        cache = loadCache()
        if not cache.is_empty():
            f = cache.filter((pl.col("id_type") == "ISIN") & (pl.col("id_value") == isin))
            if not f.is_empty() and f["ticker"][0]:
                return f["ticker"][0], f["exch_code"][0] or ""

    results = lookupBulk([{"idType": "ISIN", "idValue": isin}], apiKey=apiKey)
    if not results or "error" in results[0]:
        return None
    ticker = results[0].get("ticker")
    exch = results[0].get("exchCode", "")
    if not ticker:
        return None
    if useCache:
        _appendToCache("ISIN", isin, exch, results[0].get("figi", ""), ticker=ticker, name=results[0].get("name", ""))
    return ticker, exch


def figiToTicker(
    figi: str,
    *,
    apiKey: str | None = None,
    useCache: bool = True,
) -> tuple[str, str] | None:
    """FIGI → (ticker, exchCode). cache hit 우선.

    Sig: ``figiToTicker(figi, *, apiKey=None, useCache=True) -> tuple[str, str] | None``

    Capabilities: FIGI 12자 → ticker 역매핑.
    AIContext: FIGI 만 가진 사용자 입력 → ticker 변환.
    Guide: FIGI 는 unique 라 다중 매치 없음.
    When: 사용자가 FIGI 직접 입력.
    How: cache filter (id_type=FIGI) → miss 면 live.

    Args:
        figi: 12자 FIGI 문자열 (예: ``"BBG000B9XRY4"``).
        apiKey: OpenFIGI API key.
        useCache: cache 사용 여부.

    Returns:
        ``(ticker, exchCode)`` 또는 None.

    Raises:
        없음.

    Example:
        >>> figiToTicker("BBG000B9XRY4")
        ('AAPL', 'US')

    See Also:
        ``tickerToFigi`` · ``isinToTicker``.
    """
    if useCache:
        cache = loadCache()
        if not cache.is_empty():
            f = cache.filter((pl.col("id_type") == "FIGI") & (pl.col("id_value") == figi))
            if not f.is_empty() and f["ticker"][0]:
                return f["ticker"][0], f["exch_code"][0] or ""

    results = lookupBulk([{"idType": "FIGI", "idValue": figi}], apiKey=apiKey)
    if not results or "error" in results[0]:
        return None
    ticker = results[0].get("ticker")
    exch = results[0].get("exchCode", "")
    if not ticker:
        return None
    if useCache:
        _appendToCache("FIGI", figi, exch, figi, ticker=ticker, name=results[0].get("name", ""))
    return ticker, exch


def _appendToCache(
    idType: str,
    idValue: str,
    exchCode: str,
    figi: str,
    *,
    ticker: str = "",
    name: str = "",
) -> None:
    """단일 row cache 추가 — load + concat + save.

    내부 헬퍼. 직접 호출 금지. 향후 다중 row 누적 best-effort 패턴 가능.
    """
    try:
        cache = loadCache()
        row = pl.DataFrame(
            {
                "id_type": [idType],
                "id_value": [idValue],
                "exch_code": [exchCode],
                "figi": [figi],
                "ticker": [ticker],
                "name": [name],
            }
        )
        merged = pl.concat([cache, row], how="diagonal_relaxed").unique(
            subset=["id_type", "id_value", "exch_code"], keep="last"
        )
        saveCache(merged)
    except (OSError, pl.exceptions.PolarsError) as exc:
        log.debug("symbology cache append 실패 (silent): %s", exc)
