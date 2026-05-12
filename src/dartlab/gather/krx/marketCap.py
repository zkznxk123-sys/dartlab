"""시가총액 합성 — 일별 종가 × 분기별 발행주식수.

데이터 소스:
- KR: data/dart/scan/sharesOutstanding.parquet (DART docs `4. 주식의 총수 등` 파싱)
- US: data/edgar/scan/sharesOutstanding.parquet (XBRL dei `EntityCommonStockSharesOutstanding`)
- 종가: gather("price", stockCode) — 시장별 fallback 체인

합성 방식: as-of backward join으로 가장 최근 보고서의 outstanding 을
다음 보고서가 나올 때까지 forward-fill 한다. 분기 사이 무상/유상증자는
다음 분기 보고서까지 stale 하다 (capitalChange 보강은 후속 트랙).

반환 컬럼:
    date, close, volume, commonOutstanding, preferredOutstanding,
    marketCap, marketCapTotal

    - marketCap = close × commonOutstanding (보통주 시총)
    - marketCapTotal = close × (commonOutstanding + preferredOutstanding)

호출 패턴:
    >>> from dartlab.gather.krx.marketCap import marketCap
    >>> df = marketCap("005930")          # 일별 시계열
    >>> snap = marketCapSnapshot("005930") # 최신 한 점

src/dartlab/gather/README.md 4축 외 보조 모듈. analysis(L2) import 금지.
"""

from __future__ import annotations

import logging

import polars as pl

from dartlab.core.market import resolveMarket
from dartlab.core.polarsUtil import isEmptyDf

# 이전: quant._helpers.fetchOhlcv (gather entry wrapper) — gather 자체이므로 직접 호출.
# 이전: quant._helpers.loadSharesOutstanding — gather/_hfBulk + scan parquet wrapper —
# scan._helpers / _hfBulk 직접 호출 (lazy, scan 미설치 환경 graceful).
from dartlab.gather.entry import GatherEntry


def fetchOhlcv(stockCode: str, *, limit: int | None = None, **kwargs):
    """gather("price") 직접 호출 — quant._helpers wrapper 우회 (단방향 정책).

    Parameters
    ----------
    stockCode : str
        종목코드/티커.
    limit : int | None
        반환 행수 상한. None이면 전체.

    Returns
    -------
    object | None
        gather("price") 결과 (PriceSnapshot 또는 DataFrame). 위임 실패 시 None.

    Raises
    ------
    없음
        ImportError/ValueError/TypeError/RuntimeError 는 흡수.

    Example
    -------
    >>> snap = fetchOhlcv("005930", market="KR")
    """
    try:
        g = GatherEntry()
        result = g("price", stockCode, **kwargs)
        if limit is not None and limit > 0 and result is not None and hasattr(result, "head"):
            return result.head(limit)
        return result
    except (ImportError, ValueError, TypeError, RuntimeError):
        log.warning("OHLCV fetch 실패: %s", stockCode)
        return None


def loadSharesOutstanding(market: str = "KR"):
    """발행주식수 LazyFrame — scan parquet 직접 로드.

    KR/US 모두 dataDir 의 표준 경로에서 read-only 로드 (auto-download 책임은
    호출자 측 — story/scan 이 미리 _ensureScanData 호출). gather 는 scan 위
    layer 라 scan import 안 함 (단방향 정책).

    Parameters
    ----------
    market : str
        시장 코드. ``"KR"`` 이면 ``data/dart/scan``, 그 외는 ``data/edgar/scan``.

    Returns
    -------
    pl.LazyFrame | None
        발행주식수 LazyFrame. parquet 파일 부재 시 None + warning 로그.

    Raises
    ------
    없음
        파일 부재는 None 반환.

    Example
    -------
    >>> lf = loadSharesOutstanding("KR")
    """
    from pathlib import Path

    import polars as pl

    from dartlab.core.dataConfig import dataDir

    base = Path(dataDir()) / ("dart" if market == "KR" else "edgar") / "scan"
    path = base / "sharesOutstanding.parquet"

    if not path.exists():
        log.warning("sharesOutstanding parquet 없음: %s — scan 으로 미리 다운로드 필요", path)
        return None
    return pl.scan_parquet(path)


log = logging.getLogger(__name__)


def _stockSharesSeries(stockCode: str, market: str) -> pl.DataFrame | None:
    """단일 종목의 발행주식수 분기 시계열.

    Parameters
    ----------
    stockCode : str
        종목코드/티커 (예: "005930", "AAPL").
    market : str
        시장 코드 ("KR" 또는 "US").

    Returns
    -------
    pl.DataFrame | None
        발행주식수 시계열. 컬럼:

        - rcept_date : Date — 보고서 접수일
        - outstandingShares : float — 보통주 발행주식수 (주)
        - preferredOutstanding : float — 우선주 발행주식수 (주)

        데이터 없거나 파싱 실패 시 None.
    """
    lf = loadSharesOutstanding(market)
    if lf is None:
        return None
    try:
        if market == "KR":
            df = (
                lf.filter(pl.col("stock_code") == stockCode)
                .select(
                    [
                        "rcept_date",
                        "outstandingShares",
                        "preferredOutstanding",
                    ]
                )
                .collect(engine="streaming")
            )
        else:
            df = (
                lf.filter(pl.col("ticker") == stockCode.upper())
                .select(["end", "val"])
                .rename({"end": "rcept_date", "val": "outstandingShares"})
                .with_columns(pl.lit(0.0).alias("preferredOutstanding"))
                .collect(engine="streaming")
            )
    except (pl.exceptions.PolarsError, pl.exceptions.ColumnNotFoundError):
        return None
    if df.is_empty():
        return None
    # rcept_date 를 Date 로 정규화
    if df.schema["rcept_date"] == pl.Utf8:
        df = df.with_columns(pl.col("rcept_date").str.to_date(format="%Y%m%d", strict=False))
    return df.drop_nulls("rcept_date").sort("rcept_date")


def marketCap(
    stockCode: str,
    *,
    market: str = "auto",
    start: str | None = None,
    end: str | None = None,
) -> pl.DataFrame | None:
    """시가총액 일별 시계열.

    KR (2026-04-24 정정 — Phase A): KRX OpenAPI ``MKTCAP`` + ``LIST_SHRS`` 컬럼 직접 사용.
    이전엔 DART 분기 sharesOutstanding × 일별 close 합성 (분기-일별 mismatch 로 부정확).
    이제 KRX 가 일별로 정확히 계산한 시총 그대로 — `gather/_hfBulk.loadFiltered` 경유.

    US: 기존 sharesOutstanding × close 합성 유지 (EDGAR XBRL).

    Parameters
    ----------
    stockCode : str
        종목코드/티커 (예: "005930", "AAPL").
    market : str
        시장 코드 ("KR", "US", "auto"). "auto"이면 종목코드로 추론.

    Returns
    -------
    pl.DataFrame | None
        일별 시가총액 시계열. 컬럼:

        - date : Date — 거래일
        - close : float — 종가 (원 또는 해당 통화)
        - volume : int — 거래량 (주)
        - commonOutstanding : float — 보통주 발행주식수 (주, KR 은 ``LIST_SHRS``)
        - preferredOutstanding : float — 우선주 발행주식수 (주, KR 은 별도 ISU_CD 거래)
        - marketCap : float — 보통주 시가총액 (원, KR 은 ``MKTCAP`` 직접)
        - marketCapTotal : float — 전체 시가총액 (원). KR 은 marketCap 동일 (우선주 별도 ISU_CD 로 합산 시 별도 호출).

        데이터 없으면 None.

    Raises
    ------
    없음
        HF/주가/sharesOutstanding 부재는 warning 로그 + None 반환.

    Example
    -------
    >>> df = marketCap("005930", market="KR", start="2024-01-01")
    """
    market = resolveMarket(stockCode, market)

    if market == "KR":
        # KRX 일별 시총 직접 사용 — DART 합성 폐기 (Phase A)
        from dartlab.gather.bulkData.hfBulk import loadFiltered

        df = loadFiltered(stockCode=stockCode, start=start, end=end, adjustment="raw")
        if df is None or df.is_empty():
            log.warning("marketCap: KR HF 데이터 없음 %s (HF 미빌드 또는 종목 미수집)", stockCode)
            return None
        return df.select(
            [
                pl.col("BAS_DD").str.to_date("%Y%m%d", strict=False).alias("date"),
                pl.col("TDD_CLSPRC").cast(pl.Float64).alias("close"),
                pl.col("ACC_TRDVOL").alias("volume"),
                pl.col("LIST_SHRS").cast(pl.Float64).alias("commonOutstanding"),
                pl.lit(0.0).alias("preferredOutstanding"),
                pl.col("MKTCAP").cast(pl.Float64).alias("marketCap"),
                pl.col("MKTCAP").cast(pl.Float64).alias("marketCapTotal"),
            ]
        ).sort("date")

    # US — 기존 sharesOutstanding × close 합성 (EDGAR XBRL)
    px = fetchOhlcv(stockCode)
    if px is None or not isinstance(px, pl.DataFrame) or px.is_empty():
        log.warning("marketCap: 주가 없음 %s", stockCode)
        return None

    shares = _stockSharesSeries(stockCode, market)
    if shares is None:
        log.warning("marketCap: 발행주식수 없음 %s", stockCode)
        return None

    if px.schema["date"] != pl.Date:
        px = px.with_columns(pl.col("date").cast(pl.Date, strict=False))

    px = px.sort("date").select(["date", "close", "volume"])

    merged = px.join_asof(  # polars-streaming-unsupported: asof
        shares,
        left_on="date",
        right_on="rcept_date",
        strategy="backward",
    )
    merged = merged.rename({"outstandingShares": "commonOutstanding"})
    merged = merged.with_columns(
        [
            pl.col("preferredOutstanding").fill_null(0.0),
            (pl.col("close") * pl.col("commonOutstanding")).alias("marketCap"),
            (pl.col("close") * (pl.col("commonOutstanding") + pl.col("preferredOutstanding").fill_null(0.0))).alias(
                "marketCapTotal"
            ),
        ]
    )
    return merged.drop("rcept_date") if "rcept_date" in merged.columns else merged


def marketCapSnapshot(
    stockCode: str,
    *,
    market: str = "auto",
    start: str | None = None,
    end: str | None = None,
) -> dict | None:
    """최신 시가총액 한 점.

    Parameters
    ----------
    stockCode : str
        종목코드/티커 (예: "005930", "AAPL").
    market : str
        시장 코드 ("KR", "US", "auto"). "auto"이면 종목코드로 추론.

    Returns
    -------
    dict | None
        최신 시가총액 스냅샷. 키:

        - stockCode : str — 종목코드
        - market : str — 시장 코드
        - date : Date — 기준일
        - close : float — 종가 (원)
        - commonOutstanding : float — 보통주 발행주식수 (주)
        - preferredOutstanding : float — 우선주 발행주식수 (주)
        - marketCap : float — 보통주 시가총액 (원)
        - marketCapTotal : float — 전체 시가총액 (원)

        데이터 없으면 None.

    Raises
    ------
    없음
        marketCap() 이 None 반환 시 None.

    Example
    -------
    >>> snap = marketCapSnapshot("005930", market="KR")
    """
    # 디폴트: 최근 30일 (snapshot 은 최신 한 점만 필요 — 전체 연도 fetch 회피)
    if start is None and end is None:
        from datetime import date as _d
        from datetime import timedelta as _td

        end_d = _d.today()
        start = (end_d - _td(days=30)).strftime("%Y-%m-%d")
        end = end_d.strftime("%Y-%m-%d")
    df = marketCap(stockCode, market=market, start=start, end=end)
    if isEmptyDf(df):
        return None
    df = df.drop_nulls("marketCap")
    if df.is_empty():
        return None
    last = df.sort("date").row(-1, named=True)
    return {
        "stockCode": stockCode,
        "market": resolveMarket(stockCode, market),
        "date": last["date"],
        "close": last["close"],
        "commonOutstanding": last["commonOutstanding"],
        "preferredOutstanding": last["preferredOutstanding"],
        "marketCap": last["marketCap"],
        "marketCapTotal": last["marketCapTotal"],
    }


def marketCapAll(
    *,
    start: str | None = None,
    end: str | None = None,
    market: str = "ALL",
) -> pl.DataFrame | None:
    """일별 전종목 시가총액 — wide pivot (행 = 회사, 열 = 일자, KR 전용).

    Capabilities:
        - KRX OpenAPI ``MKTCAP`` 컬럼 직접 사용 (DART 합성 폐기 — 분기-일별 mismatch 회피)
        - dartlab 표준 wide schema: ``stockCode + corpName + 일자들``
        - quant `factorBuild`, `valueFactor`, scan valuation 의 횡단면 시총 source
        - `gather("krx", "marketCap", ...)` 와 동등 (별도 진입점이 아니라 marketCap 영역 SSOT)

    AIContext:
        - Phase A2 — Phase B (FF5 size proxy → 진짜 시총) 의 전제
        - 호출자: `quant/factorBuild.py`, `quant/valueFactor.py`, `scan/valuation/`

    Args:
        start: 기간 시작 (YYYY-MM-DD).
        end: 기간 종료. None 이면 end=start (단일일자).
        market: ``"KOSPI"`` | ``"KOSDAQ"`` | ``"ALL"`` (기본).

    Returns:
        pl.DataFrame — wide pivot:
            stockCode : str
            corpName : str
            {YYYYMMDD} : Int64 — 일자별 시총 (원)

        데이터 없으면 None.

    Raises:
        ValueError: start 가 None 일 때.

    Example:
        >>> df = marketCapAll(start="2024-01-01", end="2024-01-31", market="KOSPI")
    """
    if start is None:
        raise ValueError("marketCapAll: start 필수 (단일일자도 start 만)")
    from dartlab.gather.krx.krxApi import gatherKrx

    return gatherKrx("marketCap", start=start, end=end, market=market)
