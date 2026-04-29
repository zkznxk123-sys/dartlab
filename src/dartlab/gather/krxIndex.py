"""KRX 시장군별 지수 일별 매매현황.

Summary
-------
``gather("krxIndex", ...)`` 의 구현 모듈. KRX/KOSPI/KOSDAQ 시장군에 속한
공식 지수의 일별 OHLCV, 거래량, 거래대금, 시가총액을 제공한다.

Description
-----------
종목 가격 축인 ``gather("krx", ...)`` 와 같은 3모드 계약을 따른다.
사용자 기본 호출은 HuggingFace 데이터셋 ``krx/indices/raw-{YYYY}.parquet`` 를
읽고, ``apiKey`` 를 명시한 호출만 KRX OpenAPI ``idx`` endpoint 를 직접 친다.
운영자 cron 은 ``scripts/build/buildKrxIndexData.py`` 가 담당한다.

시장군 의미:
    - ``KRX``: KRX300, 코리아 밸류업, ESG, 테마/전략 지수.
    - ``KOSPI``: 코스피, 코스피 200/100/50, 섹터, 스타일, 사이즈 지수.
    - ``KOSDAQ``: 코스닥, 코스닥 150, 코스닥 글로벌, 코스닥 섹터 지수.

Endpoint
--------
POST ``https://data-dbg.krx.co.kr/svc/apis/idx/{krx|kospi|kosdaq}_dd_trd``
with header ``AUTH_KEY`` and JSON body ``{"basDd": "YYYYMMDD"}``.

Data Contract
-------------
Raw long schema:
    ``BAS_DD`` : str — 기준일 (YYYYMMDD)
    ``MARKET_GROUP`` : str — 시장군 (KRX/KOSPI/KOSDAQ)
    ``IDX_CLSS`` : str — KRX 지수 분류
    ``IDX_NM`` : str — 지수명
    ``CLSPRC_IDX`` : float — 종가지수 (포인트)
    ``OPNPRC_IDX`` : float — 시가지수 (포인트)
    ``HGPRC_IDX`` : float — 고가지수 (포인트)
    ``LWPRC_IDX`` : float — 저가지수 (포인트)
    ``CMPPREVDD_IDX`` : float — 전일대비 (포인트)
    ``FLUC_RT`` : float — 등락률 (%)
    ``ACC_TRDVOL`` : int — 누적 거래량 (주)
    ``ACC_TRDVAL`` : int — 누적 거래대금 (원)
    ``MKTCAP`` : int — 시가총액 (원)

Guide
-----
Use ``gather("krxIndex", "close", market="KOSPI")`` for benchmark, sector
rotation, style index, and macro regime analysis. Use ``target="raw"`` when
joining or validating exact KRX columns. Use ``apiKey=...`` only for immediate
direct API verification or operator backfill.

Notes
-----
KRX OpenAPI 인증키는 카테고리별 권한이 분리되어 있다. 종목(``sto``) 권한만
있는 키로는 ``idx`` endpoint 가 401을 반환할 수 있다. 이 경우
https://openapi.krx.co.kr 마이페이지에서 지수(``idx``) 카테고리를 별도 신청한다.

See Also
--------
``dartlab.gather.krxApi`` — 전종목 주식 가격/시총/발행주식수.
``dartlab.gather._hfIndexBulk`` — 사용자 기본 HF 로더.
``scripts/build/buildKrxIndexData.py`` — 운영자 bulk 수집 + HF push.
``ops/gather.md`` — gather 엔진 수집 계약 SSOT.
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
    "IDX_CLSS": "indexClass",  # 지수 분류 (KOSPI / 코스피 200 / KOSPI 자동차 등)
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
    """KRX OpenAPI idx JSON 응답을 raw long Polars DataFrame 으로 변환한다.

    Parameters
    ----------
    data : dict
        KRX OpenAPI JSON 응답. 정상 응답은 ``OutBlock_1`` list 를 포함한다.
    market : str
        요청한 시장군. 반환 데이터에 ``MARKET_GROUP`` 으로 보강된다.
    basDd : str
        요청 기준일. 빈 응답 로그의 맥락으로 사용한다.

    Returns
    -------
    pl.DataFrame
        KRX 원본 컬럼 + ``MARKET_GROUP``. 숫자 컬럼은 Int64/Float64 로 cast.
        휴장일 또는 자료 없음이면 빈 DataFrame.

    Notes
    -----
    ``MARKET_GROUP`` 은 ``IDX_CLSS`` 와 다르다. ``IDX_CLSS`` 는 KRX가 붙인
    지수 분류이고, ``MARKET_GROUP`` 은 어느 endpoint(KRX/KOSPI/KOSDAQ)에서
    온 row 인지 보존하는 dartlab 저장 계약이다.
    """
    rows = data.get("OutBlock_1") or []
    if not rows:
        log.info("KRX idx %s %s: 빈 응답 (휴장일 또는 자료 없음)", market, basDd)
        return pl.DataFrame()

    df = pl.DataFrame(rows).with_columns(pl.lit(market).alias("MARKET_GROUP"))
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
    retries: int = 3,
    sleepSec: float = 0.0,
) -> pl.DataFrame:
    """KRX 지수 범위를 일자별로 직접 수집한다.

    Parameters
    ----------
    start : str
        시작일 (YYYY-MM-DD 또는 YYYYMMDD).
    end : str
        종료일 (YYYY-MM-DD 또는 YYYYMMDD).
    market : {"KRX", "KOSPI", "KOSDAQ"}
        수집할 지수 시장군.
    apiKey : str
        KRX OpenAPI 인증키. idx 카테고리 권한이 필요하다.
    concurrency : int
        동시 요청 수. 운영자 bulk 수집은 KRX 차단을 피하기 위해 1을 권장한다.
    retries : int
        403/429/5xx 재시도 횟수. 최종 실패는 예외로 올려 결측 저장을 막는다.
    sleepSec : float
        성공 요청 뒤 대기 시간(초).

    Returns
    -------
    pl.DataFrame
        기간 내 raw long DataFrame. 평일만 호출하며 휴장일 row 는 제외된다.

    Raises
    ------
    ValueError
        start > end 또는 날짜 포맷 오류.
    httpx.HTTPStatusError
        인증/권한 오류 또는 재시도 후에도 남은 HTTP 오류.

    Notes
    -----
    HTTP 오류를 warning 으로 삼키지 않는다. bulk parquet 은 한 날짜 결측이
    누적되면 HF SSOT 자체가 오염되므로, retry 이후 실패는 작업 전체 실패로 둔다.
    """
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
                for attempt in range(retries + 1):
                    try:
                        df = await fetchKrxIndexBydd(
                            d.strftime("%Y%m%d"),
                            market=market,
                            apiKey=apiKey,
                            client=client,
                        )
                        if not df.is_empty():
                            out.append(df)
                        if sleepSec > 0:
                            await asyncio.sleep(sleepSec)
                        return
                    except httpx.HTTPStatusError as e:
                        status = e.response.status_code if e.response is not None else None
                        retryable = status in {403, 429} or (status is not None and status >= 500)
                        if attempt < retries and retryable:
                            await asyncio.sleep(min(30.0, 2.0 * (attempt + 1)))
                            continue
                        raise

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
    """KRX 시장군별 전체 지수 일별 매매현황을 반환한다.

    Summary
    -------
    ``dartlab.gather("krxIndex", target, ...)`` 의 축 구현. KRX/KOSPI/KOSDAQ
    시장군의 공식 지수를 지수명 x 날짜 wide matrix 또는 raw long DataFrame 으로
    반환한다.

    Description
    -----------
    기본 경로는 HF 데이터셋이다. ``apiKey`` 가 없으면
    ``DATA_RELEASES["krxIndices"]`` 의 ``krx/indices/raw-{YYYY}.parquet`` 를
    읽는다. ``apiKey`` 를 명시하면 KRX OpenAPI idx endpoint 를 직접 호출한다.
    호출 정신모델은 ``gather("krx", ...)`` 와 같다.

    Parameters
    ----------
    target : str | None
        반환할 값. ``"close"``, ``"open"``, ``"high"``, ``"low"``,
        ``"volume"``, ``"amount"``, ``"marketCap"``, ``"raw"`` 를 지원한다.
        특정 지수의 보조지표는 ``indexFilter`` 1개와 함께 지정한다.
    market : {"KRX", "KOSPI", "KOSDAQ"}
        지수 시장군. 기본 ``"KOSPI"``.
    start : str | None
        시작일. None 이면 최근 1년.
    end : str | None
        종료일. None 이면 오늘. KRX 확정 전 당일은 빈 응답일 수 있다.
    apiKey : str | None
        직접 API 호출용 KRX OpenAPI 키. None 이면 HF 데이터셋 사용.
    indexFilter : list[str] | None
        특정 지수명 필터. 예: ``["코스피 200"]``, ``["코스닥 150"]``.
    indicators : list[str] | bool | str | None
        ``indexFilter`` 가 단일 지수일 때 보조지표 추가. ``"basic"`` 은
        sma5/sma20/sma60/ema12/ema26/rsi14/macd/atr14/obv.

    Returns
    -------
    pl.DataFrame
        target != ``"raw"``:
            ``indexName`` : str — 지수명
            ``YYYYMMDD`` : float|int — 날짜별 target 값 (포인트, 주, 원)
        target == ``"raw"``:
            ``BAS_DD`` : str — 기준일 (YYYYMMDD)
            ``MARKET_GROUP`` : str — 시장군 (KRX/KOSPI/KOSDAQ)
            ``IDX_CLSS`` : str — KRX 지수 분류
            ``IDX_NM`` : str — 지수명
            ``CLSPRC_IDX`` : float — 종가지수 (포인트)
            ``OPNPRC_IDX`` : float — 시가지수 (포인트)
            ``HGPRC_IDX`` : float — 고가지수 (포인트)
            ``LWPRC_IDX`` : float — 저가지수 (포인트)
            ``ACC_TRDVOL`` : int — 누적 거래량 (주)
            ``ACC_TRDVAL`` : int — 누적 거래대금 (원)
            ``MKTCAP`` : int — 시가총액 (원)

    Raises
    ------
    ValueError
        market 이 KRX/KOSPI/KOSDAQ 가 아니거나 날짜 포맷이 잘못된 경우.
    httpx.HTTPStatusError
        apiKey 직접 호출에서 인증/권한/HTTP 오류가 발생한 경우.

    Examples
    --------
    >>> import dartlab
    >>> dartlab.gather("krxIndex", "close", market="KOSPI", start="2026-04-28", end="2026-04-28")
    >>> dartlab.gather("krxIndex", "raw", market="KRX", start="2020-01-01", end="2020-12-31")
    >>> dartlab.gather("krxIndex", "close", market="KOSPI", indexFilter=["코스피 200"])

    Notes
    -----
    ``market`` 의 의미는 ``gather("krx", ...)`` 와 다르다. ``krx`` 는 종목시장
    필터이고, ``krxIndex`` 는 지수 endpoint 시장군이다. 직접 API 호출에서
    HTTP 401 이 나면 KRX OpenAPI 마이페이지에서 idx 카테고리 권한을 신청한다.

    Guide
    -----
    When: 시장 벤치마크, 섹터 로테이션, 스타일 지수, 테마/ESG 지수, macro regime
    분석에 사용한다.
    How: 기본은 HF 데이터셋으로 재현 가능한 결과를 읽고, 당일 검증이나 운영자
    backfill 때만 ``apiKey`` 를 명시한다.
    Verified:
        - 2010-01-01~2026-04-28 KRX/KOSPI/KOSDAQ backfill 완료.
        - HF ``krx/indices`` 17개 parquet, 474,882 rows push 완료.

    See Also
    --------
    dartlab.gather.krxApi.gatherKrx : 전종목 가격/시총/발행주식수.
    dartlab.gather._hfIndexBulk.loadFiltered : HF 기본 로더.
    scripts/build/buildKrxIndexData.py : 운영자 bulk 수집 스크립트.
    """
    # 일자 디폴트
    if start is None:
        startD = datetime.now().date() - timedelta(days=365)
    else:
        startD = datetime.strptime(_normalizeDate(start), "%Y%m%d").date()
    if end is None:
        endD = datetime.now().date()
    else:
        endD = datetime.strptime(_normalizeDate(end), "%Y%m%d").date()

    if apiKey:
        long_df = asyncio.run(
            fetchKrxIndexRange(
                startD.strftime("%Y%m%d"),
                endD.strftime("%Y%m%d"),
                market=market,
                apiKey=apiKey,
            )
        )
    else:
        from dartlab.gather._hfIndexBulk import loadFiltered

        long_df = loadFiltered(
            market=market,
            start=startD.strftime("%Y%m%d"),
            end=endD.strftime("%Y%m%d"),
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
