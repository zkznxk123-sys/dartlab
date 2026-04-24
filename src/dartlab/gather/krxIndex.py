"""KRX OpenAPI - 지수 일별 매매현황 (KRX/KOSPI/KOSDAQ 시장군별 전체 지수 패키지).

종목 (`krxApi.py`) 와 동일 패턴, endpoint 만 ``idx`` 카테고리.

Endpoint :
    POST https://data-dbg.krx.co.kr/svc/apis/idx/{krx|kospi|kosdaq}_dd_trd
    Headers : AUTH_KEY: <키>, Content-Type: application/json
    Body    : {"basDd": "YYYYMMDD"}

각 호출은 시장군 내 **수십 개 지수** 일별 OHLCV/거래량/시가총액 동시 반환 :
    KRX 통합   : KRX300, ESG, KRX-K (코리아밸류) 등
    KOSPI      : KOSPI 종합, KOSPI200, KOSPI100, 섹터 (자동차/반도체/금융/...),
                 스타일 (가치/성장/배당/모멘텀), 사이즈 (대형/중형/소형)
    KOSDAQ     : KOSDAQ 종합, KOSDAQ150, KOSDAQ TOP30, 섹터, 글로벌

활용 :
    - 섹터 로테이션 alpha (KOSPI 자동차 vs 반도체 vs 금융)
    - 스타일 팩터 검증 (KRX 공식 가치/성장/배당 = FF5 ground truth)
    - 다중 benchmark 회귀 (decomposeFactor)
    - Macro regime (섹터 분포 → 시장 regime)
    - ESG / 테마 지수

────────────────────────────────────────────────────────────
키 신청 (sto 종목 키와 별개 — KRX OpenAPI 카테고리별) :
    https://openapi.krx.co.kr → 마이페이지 → 인증키 신청
    "지수 (idx)" 카테고리 별도 체크 필수.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date as _date
from datetime import datetime, timedelta
from typing import Literal

import httpx
import polars as pl

from dartlab.gather.krxApi import _isFinalized, _normalizeDate

log = logging.getLogger(__name__)

_BASE_URL = "https://data-dbg.krx.co.kr/svc/apis/idx"
_ENDPOINT = {
    "KRX": "krx_dd_trd",
    "KOSPI": "kospi_dd_trd",
    "KOSDAQ": "kosdaq_dd_trd",
}

# KRX 지수 응답 schema cast (추정 컬럼 — 첫 호출 후 정확한 set 으로 확정).
# KRX 표준 idx 컬럼 (사전 자료 + 종목 endpoint 컨벤션 기반):
_INT_COLS = (
    "ACC_TRDVOL",  # 누적거래량
    "ACC_TRDVAL",  # 누적거래대금
    "MKTCAP",  # 시가총액
)
_FLOAT_COLS = (
    "CLSPRC_IDX",  # 종가지수
    "OPNPRC_IDX",  # 시가지수
    "HGPRC_IDX",  # 고가지수
    "LWPRC_IDX",  # 저가지수
    "CMPPREVDD_IDX",  # 전일대비
    "FLUC_RT",  # 등락률
)

# KRX raw 컬럼 → 표준 컬럼 rename (wide 모드 normalize 용)
_KRX_TO_STD = {
    "BAS_DD": "date",
    "IDX_CLSS": "indexClass",  # 지수 분류 (KOSPI / KOSPI200 / KOSPI 자동차 등)
    "IDX_NM": "indexName",
    "OPNPRC_IDX": "open",
    "HGPRC_IDX": "high",
    "LWPRC_IDX": "low",
    "CLSPRC_IDX": "close",
    "CMPPREVDD_IDX": "priceChange",
    "FLUC_RT": "fluctuationRate",
    "ACC_TRDVOL": "volume",
    "ACC_TRDVAL": "amount",
    "MKTCAP": "marketCap",
}


async def fetchKrxIndexBydd(
    basDd: str,
    *,
    market: Literal["KRX", "KOSPI", "KOSDAQ"] = "KOSPI",
    apiKey: str,
    client: httpx.AsyncClient | None = None,
) -> pl.DataFrame:
    """KRX OpenAPI - 하루치 시장군 전체 지수 OHLCV (raw, async).

    Parameters
    ----------
    basDd : str
        조회일자 (YYYY-MM-DD 또는 YYYYMMDD).
    market : str
        ``"KRX"`` (KRX 통합 지수군) | ``"KOSPI"`` | ``"KOSDAQ"``.
    apiKey : str
        KRX OpenAPI 인증키 (필수 명시) — idx 카테고리 권한 별도 신청 필요.
    client : httpx.AsyncClient | None

    Returns
    -------
    pl.DataFrame
        그 날 시장군 내 모든 지수 OHLCV + 거래량 + 시가총액. 컬럼은 KRX 응답 그대로.
        한 호출에 수십 행 (각 행 = 1 지수). 휴장일 또는 자료 없음 빈 DataFrame.

    Raises
    ------
    ValueError : apiKey 미지정 또는 market 잘못
    httpx.HTTPStatusError : 401 (idx 카테고리 권한 없음 — 신청 필요), 기타 HTTP 에러
    """
    if not apiKey:
        raise ValueError("apiKey 필수 — KRX OpenAPI 호출에는 키 필요")
    basDd = _normalizeDate(basDd)
    if not _isFinalized(basDd):
        log.warning(
            "KRX idx %s: today not finalized — KRX confirms after 17:00 KST",
            basDd,
        )
        return pl.DataFrame()

    if market not in _ENDPOINT:
        raise ValueError(f"market 은 'KRX' / 'KOSPI' / 'KOSDAQ' 만 허용: {market!r}")

    url = f"{_BASE_URL}/{_ENDPOINT[market]}"
    headers = {
        "AUTH_KEY": apiKey,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {"basDd": basDd}

    own = client is None
    if own:
        client = httpx.AsyncClient(timeout=30.0)
    try:
        resp = await client.post(url, headers=headers, json=payload)
        if resp.status_code == 401:
            raise httpx.HTTPStatusError(
                "KRX idx 카테고리 권한 없음 (HTTP 401). "
                "https://openapi.krx.co.kr 마이페이지에서 'idx 지수' 카테고리 별도 신청 필요. "
                "종목 (sto) 키와 분리 발급.",
                request=resp.request,
                response=resp,
            )
        resp.raise_for_status()
        data = resp.json()
    finally:
        if own:
            await client.aclose()

    return _parseKrxIndexResponse(data, market=market, basDd=basDd)


def _parseKrxIndexResponse(data: dict, *, market: str, basDd: str) -> pl.DataFrame:
    """KRX OpenAPI idx JSON 응답 → Polars DataFrame (schema cast SSOT)."""
    rows = data.get("OutBlock_1") or []
    if not rows:
        log.info("KRX idx %s %s: 빈 응답 (휴장일 또는 자료 없음)", market, basDd)
        return pl.DataFrame()

    df = pl.DataFrame(rows)
    casts = []
    for col in _INT_COLS:
        if col in df.columns:
            casts.append(pl.col(col).cast(pl.Int64, strict=False))
    for col in _FLOAT_COLS:
        if col in df.columns:
            casts.append(pl.col(col).cast(pl.Float64, strict=False))
    if casts:
        df = df.with_columns(casts)
    return df


async def fetchKrxIndexRange(
    start: str,
    end: str,
    *,
    market: Literal["KRX", "KOSPI", "KOSDAQ"] = "KOSPI",
    apiKey: str,
    concurrency: int = 5,
) -> pl.DataFrame:
    """KRX 지수 일자 범위 일괄 fetch (concat). 평일만 실제 호출."""
    startD = datetime.strptime(_normalizeDate(start), "%Y%m%d").date()
    endD = datetime.strptime(_normalizeDate(end), "%Y%m%d").date()
    if startD > endD:
        raise ValueError(f"start ({start}) > end ({end})")

    sem = asyncio.Semaphore(concurrency)
    out: list[pl.DataFrame] = []

    async with httpx.AsyncClient(timeout=30.0) as client:

        async def _one(d: _date):
            if d.weekday() >= 5:  # 토/일 skip
                return
            async with sem:
                try:
                    df = await fetchKrxIndexBydd(
                        d.strftime("%Y%m%d"),
                        market=market,
                        apiKey=apiKey,
                        client=client,
                    )
                    if not df.is_empty():
                        out.append(df)
                except httpx.HTTPStatusError as e:
                    log.warning("KRX idx %s %s: %s", market, d, e)

        tasks = []
        cur = startD
        while cur <= endD:
            tasks.append(_one(cur))
            cur += timedelta(days=1)
        await asyncio.gather(*tasks)

    if not out:
        return pl.DataFrame()
    return pl.concat(out, how="vertical_relaxed")


def gatherKrxIndex(
    target: str | None = "close",
    *,
    market: Literal["KRX", "KOSPI", "KOSDAQ"] = "KOSPI",
    start: str | None = None,
    end: str | None = None,
    apiKey: str | None = None,
    indexFilter: list[str] | None = None,
    indicators: list[str] | bool | str | None = "basic",
) -> pl.DataFrame:
    """KRX 지수 일별 매매현황 — 사용자 직접 호출 (Mode B).

    Capabilities:
        - 시장군 (KRX/KOSPI/KOSDAQ) 의 모든 지수 OHLCV + 거래량 + 시총
        - target 으로 단일 컬럼 wide pivot (행=지수, 열=일자) 또는 raw long
        - indicators 옵션 — 지수별 보조지표 자동 (기본 basic 9개)
        - indexFilter 로 특정 지수만 (예: ["KOSPI200", "KOSPI 자동차"])

    AIContext:
        - Mode A 운영자 cron 은 별도 (`scripts/build/buildKrxIndexData.py` 후속)
        - Mode C HF 자동 fallback 은 backfill HF publish 후
        - 현재는 Mode B (apiKey 명시) 만 동작

    Args:
        target: ``"close"`` / ``"volume"`` / ``"marketCap"`` / ``"raw"`` /
                보조지표 ("rsi14", "ma20", ...) 중 택1. 기본 ``"close"``.
        market: ``"KRX"`` | ``"KOSPI"`` | ``"KOSDAQ"``. 기본 ``"KOSPI"``.
        start: 시작일 (YYYY-MM-DD or YYYYMMDD). None 이면 최근 1년.
        end: 종료일. None 이면 today.
        apiKey: KRX OpenAPI 키 (idx 카테고리 권한 필수).
        indexFilter: 특정 indexName 만 (None 이면 시장군 전체).
        indicators: target=보조지표일 때만 (기본 "basic" 9개).

    Returns:
        pl.DataFrame
            wide: 행 = indexName, 열 = 일자, value = 지정 target
            raw : long DataFrame (원본 컬럼 보존)

    Raises:
        ValueError : apiKey 없음
        httpx.HTTPStatusError : 401 (idx 카테고리 권한 없음 — 신청 필요)

    Examples:
        >>> import dartlab, os
        >>> df = dartlab.gather("krxIndex", "close", market="KOSPI",
        ...                     start="2024-01-01", apiKey=os.environ["KRX_API_KEY"])
        >>> # KOSPI 시장 모든 지수 (KOSPI/KOSPI200/섹터/스타일/...) 일별 종가 wide

    Notes:
        - 키 활성화 전: HTTP 401 → friendly error message + 신청 안내
        - 단일 호출 응답에 수십 개 지수 → 시계열 빌드 시 1 호출 = 1일 분량
        - HF 자동 backfill (Mode C) 은 후속 트랙 (krxApi 와 동일 패턴 — 운영자 cron)
    """
    if not apiKey:
        raise ValueError(
            "apiKey 필수 — gather('krxIndex', ..., apiKey=...) 명시 또는 "
            "os.environ['KRX_API_KEY'] 사용. idx 카테고리 권한 별도 신청 필요 "
            "(https://openapi.krx.co.kr 마이페이지)."
        )

    # 일자 디폴트
    if start is None:
        startD = datetime.now().date() - timedelta(days=365)
    else:
        startD = datetime.strptime(_normalizeDate(start), "%Y%m%d").date()
    if end is None:
        endD = datetime.now().date()
    else:
        endD = datetime.strptime(_normalizeDate(end), "%Y%m%d").date()

    long_df = asyncio.run(
        fetchKrxIndexRange(
            startD.strftime("%Y%m%d"),
            endD.strftime("%Y%m%d"),
            market=market,
            apiKey=apiKey,
        )
    )
    if long_df.is_empty():
        return pl.DataFrame()

    # filter 적용
    if indexFilter:
        long_df = long_df.filter(pl.col("IDX_NM").is_in(indexFilter))

    if target == "raw":
        return long_df

    # standardize cols + wide pivot
    rename = {k: v for k, v in _KRX_TO_STD.items() if k in long_df.columns}
    std_df = long_df.rename(rename)

    # target 매핑
    if target in ("close", "open", "high", "low", "volume", "amount", "marketCap"):
        wide = std_df.pivot(values=target, index="indexName", on="date", aggregate_function="first").sort("indexName")
        return wide

    # 보조지표 — 단일 지수 OHLCV 에 addIndicators 적용 시 indexFilter 1개 필수
    if indexFilter and len(indexFilter) == 1:
        single = std_df.filter(pl.col("indexName") == indexFilter[0]).sort("date")
        if indicators == "basic":
            indicators = ["sma5", "sma20", "sma60", "ema12", "ema26", "rsi14", "macd", "atr14", "obv"]
        if indicators:
            from dartlab.gather._indicatorDispatch import addIndicators

            single = addIndicators(single, indicators=indicators)
        return single

    return std_df  # default: long form
