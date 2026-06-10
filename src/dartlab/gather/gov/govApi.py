"""공공데이터포털 금융위원회_주식시세정보 raw fetch — KRX gather 미러.

`gather/krx/krxApi.py` 의 gov 판. 두 진입:
    fetchGovStock — 종목 하나 전체이력 (likeSrtnCd, 차트 SSOT).
    fetchGovBydd  — 하루치 전종목 (basDt, 일별 sync SSOT).
둘 다 raw gov 컬럼 DataFrame 반환. `normalizeGovFrame` 가 회사 schema 로 정규화
(KRX `krx/prices/company/{code}.parquet` 와 동일 컬럼).

라이선스: 공공누리/KOGL — 비상업 + 출처표시 재배포 가능 (KRX OpenAPI 제3자 제공 금지와 차이).
인증키(`DATA_GO_KR_KEY`, 디코딩 키)는 환경변수 자동 read 없음 — 명시 전달만 (KRX 규약 동일).
"""

from __future__ import annotations

import logging

import httpx
import polars as pl

log = logging.getLogger(__name__)

_GOV_ENDPOINT = "https://apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService/getStockPriceInfo"

# gov 응답 컬럼 → 회사 표준 schema (krx/prices/company 와 동일 컬럼·의미).
GOV_TO_STD = {
    "basDt": "date",
    "srtnCd": "stockCode",
    "itmsNm": "name",
    "mrktCtg": "market",
    "mkp": "open",
    "hipr": "high",
    "lopr": "low",
    "clpr": "close",
    "vs": "priceChange",
    "fltRt": "fluctuationRate",
    "trqu": "volume",
    "trPrc": "tradedValue",
    "mrktTotAmt": "marketCap",
    "lstgStCnt": "listedShares",
}

# 응답이 전부 string → 수치 컬럼 명시 cast (SSOT).
_GOV_NUM = ("clpr", "vs", "fltRt", "mkp", "hipr", "lopr", "trqu", "trPrc", "lstgStCnt", "mrktTotAmt")
_NUM_STD = (
    "open",
    "high",
    "low",
    "close",
    "priceChange",
    "fluctuationRate",
    "volume",
    "tradedValue",
    "marketCap",
    "listedShares",
)


def _parseItems(data: dict) -> list[dict]:
    """gov JSON 응답 → item dict 리스트 (단일 item 도 리스트화, 빈 응답 [])."""
    body = (data or {}).get("response", {}).get("body", {}) or {}
    items = (body.get("items") or {}).get("item")
    if not items:
        return []
    return items if isinstance(items, list) else [items]


def _totalCount(data: dict) -> int:
    body = (data or {}).get("response", {}).get("body", {}) or {}
    try:
        return int(body.get("totalCount") or 0)
    except (TypeError, ValueError):
        return 0


def _rawFrame(rows: list[dict]) -> pl.DataFrame:
    if not rows:
        return pl.DataFrame()
    df = pl.DataFrame(rows)
    casts = [pl.col(c).cast(pl.Float64, strict=False) for c in _GOV_NUM if c in df.columns]
    return df.with_columns(casts) if casts else df


def _get(params: dict, *, apiKey: str, client: httpx.Client | None) -> dict:
    """단일 gov 호출 → JSON. serviceKey(디코딩 키)는 httpx params 가 1회 URL-encode."""
    query = {"serviceKey": apiKey, "resultType": "json", **params}
    own = client is None
    cl = client or httpx.Client(timeout=30.0)
    try:
        resp = cl.get(_GOV_ENDPOINT, params=query)
        resp.raise_for_status()
        return resp.json()
    finally:
        if own:
            cl.close()


def fetchGovStock(
    code: str,
    *,
    apiKey: str,
    numOfRows: int = 4000,
    maxPages: int = 8,
    client: httpx.Client | None = None,
) -> pl.DataFrame:
    """종목 하나 전체이력 raw fetch (likeSrtnCd, 페이지 루프).

    Capabilities: 한 종목 전체 일별 OHLCV+시총+거래대금 raw (gov 원본 컬럼, 2020~).
    AIContext: 차트 회사별 parquet 의 source — likeSrtnCd 는 LIKE 라 srtnCd 정확매칭만 채택.

    Args:
        code: 종목코드 6자리.
        apiKey: 공공데이터포털 디코딩 인증키 (명시 필수).
        numOfRows: 페이지당 행수. maxPages: 최대 페이지 (이력 상한 가드).
        client: 재사용 httpx.Client (None 이면 자동 생성/종료).

    Returns:
        pl.DataFrame: gov raw 컬럼 (basDt/srtnCd/clpr/mkp/... 수치 cast). 빈 = 데이터 없음.

    Raises:
        ValueError: apiKey 빈 문자열.
        httpx.HTTPStatusError: gov 응답 4xx/5xx.

    Example:
        >>> df = fetchGovStock("005930", apiKey=key)  # 1578행(2020~)
    """
    if not apiKey:
        raise ValueError("apiKey 필수 — 공공데이터포털 호출에는 디코딩 인증키가 필요합니다")
    code = str(code).strip()
    rows: list[dict] = []
    seen: set[str] = set()
    for page in range(1, maxPages + 1):
        data = _get({"numOfRows": numOfRows, "pageNo": page, "likeSrtnCd": code}, apiKey=apiKey, client=client)
        items = _parseItems(data)
        if not items:
            break
        for r in items:
            if str(r.get("srtnCd")) != code:
                continue
            key = str(r.get("basDt"))
            if key in seen:
                continue
            seen.add(key)
            rows.append(r)
        if page * numOfRows >= _totalCount(data):
            break
    return _rawFrame(rows)


def fetchGovBydd(
    basDt: str,
    *,
    apiKey: str,
    numOfRows: int = 4000,
    maxPages: int = 4,
    client: httpx.Client | None = None,
) -> pl.DataFrame:
    """하루치 전종목 raw fetch (basDt, 페이지 루프).

    Capabilities: 그날 전 시장(~2877종목) OHLCV+시총 raw — 일별 sync 의 증분 source.
    AIContext: buildGovData 가 매일 어제 basDt 1콜로 전종목 증분 수집.

    Args:
        basDt: 기준일자 YYYYMMDD.
        apiKey: 공공데이터포털 디코딩 인증키 (명시 필수).
        numOfRows / maxPages / client: fetchGovStock 와 동일 규약.

    Returns:
        pl.DataFrame: 그날 전종목 gov raw 컬럼. 휴장일/미확정일은 빈 DataFrame.

    Raises:
        ValueError: apiKey 빈 문자열.
        httpx.HTTPStatusError: gov 응답 4xx/5xx.

    Example:
        >>> df = fetchGovBydd("20260609", apiKey=key)  # ~2877행
    """
    if not apiKey:
        raise ValueError("apiKey 필수 — 공공데이터포털 호출에는 디코딩 인증키가 필요합니다")
    basDt = str(basDt).replace("-", "").strip()
    rows: list[dict] = []
    for page in range(1, maxPages + 1):
        data = _get({"numOfRows": numOfRows, "pageNo": page, "basDt": basDt}, apiKey=apiKey, client=client)
        items = _parseItems(data)
        if not items:
            break
        rows.extend(items)
        if page * numOfRows >= _totalCount(data):
            break
    return _rawFrame(rows)


def normalizeGovFrame(df: pl.DataFrame) -> pl.DataFrame:
    """raw gov DataFrame → 회사 표준 schema (krx/prices/company 동일 컬럼).

    Capabilities: gov 원본 컬럼을 date/stockCode/name/market/OHLC/.../marketCap 으로 rename+cast.
    AIContext: 회사별 parquet (gov/prices/{code}.parquet) 의 최종 schema 보장 — KRX 회사 parquet 과 호환.

    Args:
        df: fetchGovStock/fetchGovBydd 의 raw gov DataFrame.

    Returns:
        pl.DataFrame: date(str)·stockCode(str)·name·market·open·high·low·close·priceChange·
            fluctuationRate·volume·tradedValue·marketCap·listedShares. (stockCode+date 정렬)

    Raises:
        없음 — 빈/컬럼 누락 입력은 빈/부분 DataFrame 으로 그대로 반환 (예외 미발생).

    Example:
        >>> std = normalizeGovFrame(fetchGovStock("005930", apiKey=key))
    """
    if df.is_empty():
        return df
    rename = {k: v for k, v in GOV_TO_STD.items() if k in df.columns}
    out = df.rename(rename)
    casts = [pl.col(c).cast(pl.Float64, strict=False) for c in _NUM_STD if c in out.columns]
    if "date" in out.columns:
        casts.append(pl.col("date").cast(pl.Utf8))
    if "stockCode" in out.columns:
        casts.append(pl.col("stockCode").cast(pl.Utf8))
    out = out.with_columns(casts)
    keep = [v for v in GOV_TO_STD.values() if v in out.columns]
    out = out.select(keep)
    if "stockCode" in out.columns and "date" in out.columns:
        out = out.filter(pl.col("stockCode").str.len_chars() == 6).sort(["stockCode", "date"])
    return out
