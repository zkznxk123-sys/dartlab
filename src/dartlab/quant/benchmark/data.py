"""quant 벤치마크 SSOT — KRX 시장·섹터·스타일 지수 기반 수익률."""

from __future__ import annotations

import logging
from datetime import date as _date
from datetime import timedelta
from typing import Any

import polars as pl

from dartlab.core.market import resolveMarket
from dartlab.core.polarsUtil import isEmptyDf
from dartlab.quant.benchmark.map import INDEX_ALIASES, indexExists, primaryIndustryNode, sectorCandidates

log = logging.getLogger(__name__)


_KR_DEFAULTS = {
    "KOSPI": ("KOSPI", "코스피"),
    "KOSDAQ": ("KOSDAQ", "코스닥"),
}


def _defaultStart(days: int = 420) -> str:
    return (_date.today() - timedelta(days=days)).isoformat()


def _stockMarket(stockCode: str | None) -> tuple[str | None, str]:
    """KRX 상장 목록에서 종목의 시장군을 찾는다."""
    if not stockCode:
        return None, "no_stock"
    try:
        # F4: gather 직접 호출 제거 → IndustryDataAccessor (정공법 B)
        from dartlab.core.di import getIndustryAccessor

        df = getIndustryAccessor().fetchListing(market="KR")
        if df is None or df.is_empty() or "short_code" not in df.columns:
            return None, "listing_empty"
        row = df.filter(pl.col("short_code") == stockCode).head(1)
        if row.is_empty():
            return None, "stock_not_found"
        market_code = row["marketCode"][0] if "marketCode" in row.columns else None
        market_eng = row["marketEngName"][0] if "marketEngName" in row.columns else None
        if market_code == "KSQ" or (isinstance(market_eng, str) and market_eng.startswith("KOSDAQ")):
            return "KOSDAQ", "listing"
        if market_code == "STK" or market_eng == "KOSPI":
            return "KOSPI", "listing"
    except Exception as exc:  # noqa: BLE001
        log.debug("KRX 상장시장 조회 실패(%s): %s", stockCode, type(exc).__name__)
    return None, "fallback"


def _resolveExplicit(benchmark: str) -> tuple[str, str]:
    key = str(benchmark).strip()
    if key in INDEX_ALIASES:
        return INDEX_ALIASES[key]
    upper = key.upper().replace(" ", "")
    if upper in INDEX_ALIASES:
        return INDEX_ALIASES[upper]
    if "코스닥" in key or "KOSDAQ" in upper:
        return "KOSDAQ", key
    if "KRX" in upper:
        return "KRX", key
    return "KOSPI", key


def _candidate(
    *,
    benchmarkType: str,
    indexMarket: str,
    indexName: str,
    reason: str,
    confidence: float,
    **extra: Any,
) -> dict[str, Any]:
    """표준 벤치마크 후보 dict를 만든다."""
    return {
        "benchmarkType": benchmarkType,
        "source": "krxIndex",
        "market": "KR",
        "indexMarket": indexMarket,
        "indexName": indexName,
        "symbol": indexName,
        "reason": reason,
        "confidence": confidence,
        **extra,
    }


def _marketCandidate(listedMarket: str | None, reason: str) -> dict[str, Any]:
    indexMarket, indexName = _KR_DEFAULTS.get(listedMarket or "KOSPI", _KR_DEFAULTS["KOSPI"])
    return _candidate(
        benchmarkType="market",
        indexMarket=indexMarket,
        indexName=indexName,
        reason=reason,
        confidence=1.0,
    )


def _latestSectorCandidate(stockCode: str, listedMarket: str | None) -> dict[str, Any] | None:
    """KRX 일별 가격의 SECT_TP_NM을 시장 섹터 지수 후보로 변환한다."""
    if not stockCode or listedMarket not in {"KOSPI", "KOSDAQ"}:
        return None
    try:
        from dartlab.gather.bulkData.hfBulk import loadFiltered

        raw = loadFiltered(start=_defaultStart(45), adjustment="raw")
        if isEmptyDf(raw) or not {"ISU_CD", "SECT_TP_NM", "BAS_DD"}.issubset(set(raw.columns)):
            return None
        rows = raw.filter(pl.col("ISU_CD") == stockCode).sort("BAS_DD", descending=True).head(1)
        if rows.is_empty():
            return None
        sectorName = rows["SECT_TP_NM"][0]
        if not sectorName or not indexExists(listedMarket, sectorName):
            return None
        return _candidate(
            benchmarkType="sector",
            indexMarket=listedMarket,
            indexName=str(sectorName),
            reason="price_sector",
            confidence=0.72,
            mappingSource="krxPriceSector",
        )
    except (ImportError, ValueError, TypeError, RuntimeError, pl.exceptions.PolarsError):
        return None


def _sectorCandidate(stockCode: str | None, listedMarket: str | None) -> dict[str, Any] | None:
    if not stockCode:
        return None
    node = primaryIndustryNode(stockCode)
    if node:
        industryId = node.get("industry")
        for cand in sectorCandidates(industryId, preferredMarket=listedMarket):
            if indexExists(cand["indexMarket"], cand["indexName"]):
                return {
                    **cand,
                    "market": "KR",
                    "reason": "industry_node",
                    "industryConfidence": node.get("confidence"),
                    "industrySource": node.get("source"),
                }
    return _latestSectorCandidate(stockCode, listedMarket)


def _styleCandidate(stockCode: str | None, listedMarket: str | None) -> dict[str, Any] | None:
    """시총 분위로 대형/중형/소형 스타일 지수 후보를 고른다."""
    if not stockCode or listedMarket not in {"KOSPI", "KOSDAQ"}:
        return None
    try:
        from dartlab.gather.bulkData.hfBulk import loadFiltered

        raw = loadFiltered(start=_defaultStart(45), adjustment="raw")
        required = {"ISU_CD", "MKT_NM", "BAS_DD", "MKTCAP"}
        if isEmptyDf(raw) or not required.issubset(set(raw.columns)):
            return None
        marketRows = raw.filter(pl.col("MKT_NM") == listedMarket)
        if marketRows.is_empty():
            return None
        latest = marketRows["BAS_DD"].max()
        latestRows = marketRows.filter(pl.col("BAS_DD") == latest).filter(pl.col("MKTCAP").is_not_null())
        row = latestRows.filter(pl.col("ISU_CD") == stockCode).head(1)
        if row.is_empty():
            return None
        total = latestRows.height
        marketCap = float(row["MKTCAP"][0])
        larger = latestRows.filter(pl.col("MKTCAP") > marketCap).height
        percentile = larger / total if total else 1.0
        if percentile <= 0.2:
            bucket = "large"
            label = "대형주"
        elif percentile <= 0.7:
            bucket = "mid"
            label = "중형주"
        else:
            bucket = "small"
            label = "소형주"
        prefix = "코스피" if listedMarket == "KOSPI" else "코스닥"
        indexName = f"{prefix} {label}"
        if not indexExists(listedMarket, indexName):
            return None
        return _candidate(
            benchmarkType="style",
            indexMarket=listedMarket,
            indexName=indexName,
            reason="market_cap_percentile",
            confidence=0.7,
            styleType="size",
            styleBucket=bucket,
            marketCap=marketCap,
            marketCapRank=larger + 1,
            marketCapUniverse=total,
        )
    except (ImportError, ValueError, TypeError, RuntimeError, pl.exceptions.PolarsError):
        return None


def _selectPrimary(stack: dict[str, Any], benchmarkMode: str) -> dict[str, Any]:
    mode = (benchmarkMode or "market").strip()
    if mode == "auto":
        mode = "sector"
    if mode in {"market", "sector", "style"}:
        selected = stack.get(mode)
        if selected:
            return selected
        fallback = {**stack["market"], "fallbackReason": f"{mode}_benchmark_unavailable"}
        return fallback
    return {**stack["market"], "fallbackReason": f"unknown_benchmarkMode:{benchmarkMode}"}


def resolveBenchmarkStack(
    stockCode: str | None = None,
    *,
    market: str = "auto",
    benchmark: str | None = None,
    benchmarkMode: str = "market",
    includeStyle: bool = True,
) -> dict[str, Any]:
    """종목의 시장·섹터·스타일 벤치마크 후보 스택을 만든다.

    Parameters
    ----------
    stockCode : str | None
        6자리 KR 종목코드 또는 US ticker.
    market : str
        "auto" | "KR" | "KOSPI" | "KOSDAQ" | "US".
    benchmark : str | None
        명시 벤치마크. 지정 시 모든 후보보다 우선한다.
    benchmarkMode : str
        "market" | "sector" | "style" | "auto". 기본 "market".
    includeStyle : bool
        True면 시총 분위 기반 style 후보까지 만든다. 계산 축은 메모리 절약을
        위해 False로 호출하고, ``benchmarkMode="style"`` 때는 자동으로 만든다.

    Returns
    -------
    dict
        primary : dict — 실제 사용할 벤치마크 후보
        market : dict — 상장시장 지수 후보
        sector : dict | None — 산업/업종 지수 후보
        style : dict | None — 대형/중형/소형 지수 후보
        candidates : list[dict] — 후보 목록

    Capabilities:
        - 종목 → 시장/섹터/style 3 축 벤치마크 후보 자동 결정
        - benchmark 명시 시 explicit 우선 + fallbackReason 동행

    Guide:
        ``benchmarkMode`` 가 ``"sector"`` 면 산업 지수 우선. ``"style"`` 면 시총 분위
        (대/중/소) 지수. ``"auto"`` 는 sector 로 매핑.

    When:
        β 계산 + factor 분해 + AI 벤치 선택 답변.

    How:
        시장 감지 → KR 분기 (KOSPI/KOSDAQ) → market/sector/style 후보 생성 → ``_selectPrimary``.

    Requires:
        stockCode 유효 + 시장 정보 가용.

    Raises:
        없음.

    Example:
        >>> resolveBenchmarkStack("005930", benchmarkMode="sector")["primary"]["indexName"]
        '코스피 200'

    SeeAlso:
        - resolveBenchmark : 단일 primary 추출
        - fetchBenchmarkOhlcv : 후속 OHLCV 로드

    AIContext:
        "이 종목 벤치마크" 답변 시 primary + candidates 인용.
    """
    actualMarket = resolveMarket(stockCode or "", market)
    if actualMarket == "US":
        symbol = benchmark or "^GSPC"
        primary = {
            "benchmarkType": "market" if not benchmark else "explicit",
            "source": "price",
            "market": "US",
            "indexMarket": "US",
            "indexName": "S&P500" if symbol in {"^GSPC", "S&P500"} else symbol,
            "symbol": "^GSPC" if symbol == "S&P500" else symbol,
            "reason": "explicit" if benchmark else "market",
            "confidence": 1.0,
        }
        return {"primary": primary, "market": primary, "sector": None, "style": None, "candidates": [primary]}

    listedMarket, reason = _stockMarket(stockCode)
    mUpper = (market or "").upper()
    if mUpper in _KR_DEFAULTS:
        listedMarket, reason = mUpper, "market"
    marketCand = _marketCandidate(listedMarket, reason)

    if benchmark:
        indexMarket, indexName = _resolveExplicit(benchmark)
        primary = _candidate(
            benchmarkType="explicit",
            indexMarket=indexMarket,
            indexName=indexName,
            reason="explicit",
            confidence=1.0,
        )
        return {
            "primary": primary,
            "market": marketCand,
            "sector": None,
            "style": None,
            "candidates": [primary, marketCand],
        }

    sectorCand = _sectorCandidate(stockCode, marketCand["indexMarket"])
    styleCand = None
    if includeStyle or benchmarkMode == "style":
        styleCand = _styleCandidate(stockCode, marketCand["indexMarket"])
    stack = {
        "market": marketCand,
        "sector": sectorCand,
        "style": styleCand,
    }
    candidates = [c for c in (marketCand, sectorCand, styleCand) if c]
    primary = _selectPrimary(stack, benchmarkMode)
    return {
        "primary": primary,
        "market": marketCand,
        "sector": sectorCand,
        "style": styleCand,
        "candidates": candidates,
    }


def resolveBenchmark(
    stockCode: str | None = None,
    *,
    market: str = "auto",
    benchmark: str | None = None,
    benchmarkMode: str = "market",
    includeStyle: bool = True,
) -> dict[str, Any]:
    """종목/시장/명시값을 공식 벤치마크 계약으로 해석한다.

    Parameters
    ----------
    stockCode : str | None
        6자리 KR 종목코드 또는 US ticker.
    market : str
        "auto" | "KR" | "KOSPI" | "KOSDAQ" | "US".
    benchmark : str | None
        명시 벤치마크. 예: "코스피 200", "코스닥 150", "KOSPI".

    Returns
    -------
    dict
        source : str
            "krxIndex" 또는 "price".
        indexMarket : str
            KRX 지수 endpoint 시장군 ("KOSPI"/"KOSDAQ"/"KRX") 또는 "US".
        indexName : str
            KRX 지수명 또는 US 심볼.
        reason : str
            explicit/listing/market/fallback.

    Capabilities:
        - ``resolveBenchmarkStack`` 의 primary 만 추출 + ``benchmarkMode/benchmarkStack`` 메타 포함
        - explicit benchmark 우선 후 시장 fallback

    Guide:
        단일 primary 만 필요시 사용. stack 전체가 필요하면 ``resolveBenchmarkStack`` 직접 호출.

    When:
        β/factor 계산 직전 단일 벤치 결정 + AI "사용한 벤치" 답변.

    How:
        ``resolveBenchmarkStack`` → primary dict + benchmarkMode 키 보강.

    Requires:
        stockCode + market 정보.

    Raises:
        없음.

    Example:
        >>> resolveBenchmark("005930")["indexName"]
        '코스피 200'

    SeeAlso:
        - resolveBenchmarkStack : 전체 stack
        - fetchBenchmarkOhlcv : OHLCV 로드

    AIContext:
        "벤치마크 무엇 사용했나" 답변 시 indexName + reason 인용.
    """
    stack = resolveBenchmarkStack(
        stockCode,
        market=market,
        benchmark=benchmark,
        benchmarkMode=benchmarkMode,
        includeStyle=includeStyle,
    )
    primary = dict(stack["primary"])
    primary["benchmarkMode"] = benchmarkMode
    primary["benchmarkStack"] = stack
    return primary


def _krxIndexToOhlcv(raw: pl.DataFrame, indexName: str) -> pl.DataFrame:
    """KRX 지수 raw row를 quant OHLCV schema로 변환한다."""
    if raw is None or raw.is_empty():
        return pl.DataFrame()
    df = raw.filter(pl.col("IDX_NM") == indexName)
    if df.is_empty():
        return pl.DataFrame()
    cols = {
        "BAS_DD": "date",
        "OPNPRC_IDX": "open",
        "HGPRC_IDX": "high",
        "LWPRC_IDX": "low",
        "CLSPRC_IDX": "close",
        "ACC_TRDVOL": "volume",
        "ACC_TRDVAL": "amount",
        "MKTCAP": "marketCap",
    }
    select_exprs = [pl.col(k).alias(v) for k, v in cols.items() if k in df.columns]
    out = df.select(select_exprs).sort("date")
    if "date" in out.columns:
        out = out.with_columns(pl.col("date").str.strptime(pl.Date, "%Y%m%d", strict=False))
    return out


def fetchBenchmarkOhlcv(
    stockCode: str | None = None,
    *,
    market: str = "auto",
    benchmark: str | None = None,
    benchmarkMode: str = "market",
    start: str | None = None,
    end: str | None = None,
    returnMeta: bool = False,
    includeStackDetail: bool = False,
) -> pl.DataFrame | tuple[pl.DataFrame | None, dict[str, Any]]:
    """quant용 벤치마크 OHLCV를 로드한다.

    KR은 ``krxIndex`` HF 데이터셋을 사용하고, US는 기존 ``price`` 경로를 유지한다.
    ``return_meta=True``면 결과 DataFrame과 ``benchmarkUsed`` metadata를 함께
    반환한다.

    Capabilities:
        - KR: HF krxIndex bulk + ``_krxIndexToOhlcv`` 정규화 → KOSPI/KOSDAQ/섹터 지수 OHLCV
        - US: GatherEntry("price") 경유 ^GSPC 또는 명시 심볼
        - returnMeta=True 시 nObs 카운트 포함 dict 메타 동행

    Args:
        stockCode: 6 자리 KR 종목코드 또는 US ticker.
        market: ``"auto" | "KR" | "KOSPI" | "KOSDAQ" | "US"``.
        benchmark: 명시 벤치. 우선순위 최상.
        benchmarkMode: ``"market" | "sector" | "style" | "auto"``.
        start: 시작일 ``YYYY-MM-DD``.
        end: 종료일.
        returnMeta: True 면 ``(df, meta)`` 반환.
        includeStackDetail: True 면 style 후보까지 빌드.

    Returns:
        pl.DataFrame | tuple[pl.DataFrame|None, dict] — OHLCV 또는 메타 포함.

    Guide:
        β/factor 계산의 표준 벤치 입력. KR 은 HF cache, US 는 Yahoo Finance.

    When:
        β/factor 분해 + AI 벤치 OHLCV 답변.

    How:
        ``resolveBenchmark`` → source 분기 → KRX bulk 또는 GatherEntry → df + meta.

    Requires:
        KR: HF krxIndex 다운로드. US: 네트워크 + GatherEntry.

    Raises:
        없음 — 실패 시 None 또는 ``(None, meta)``.

    Example:
        >>> df = fetchBenchmarkOhlcv("005930", benchmarkMode="market")
        >>> df.columns[:3]
        ['date', 'open', 'high']

    SeeAlso:
        - resolveBenchmark : 벤치 결정
        - factor.calc.decomposeFactor : β 분해

    AIContext:
        "벤치 시계열" 답변 시 indexName + nObs 인용.
    """
    meta = resolveBenchmark(
        stockCode,
        market=market,
        benchmark=benchmark,
        benchmarkMode=benchmarkMode,
        includeStyle=includeStackDetail or benchmarkMode == "style",
    )
    df: pl.DataFrame | None = None

    if meta["source"] == "krxIndex":
        try:
            from dartlab.gather.bulkData.hfIndexBulk import loadFiltered

            raw = loadFiltered(
                market=meta["indexMarket"],
                start=start or _defaultStart(),
                end=end,
            )
            df = _krxIndexToOhlcv(raw, meta["indexName"])
        except Exception as exc:  # noqa: BLE001
            log.warning("KRX 벤치마크 로드 실패(%s): %s", meta["indexName"], type(exc).__name__)
            df = None
    else:
        try:
            from dartlab.gather.entry import GatherEntry

            df = GatherEntry()("price", meta["symbol"], market="US", start=start, end=end)
        except Exception as exc:  # noqa: BLE001
            log.warning("US 벤치마크 로드 실패(%s): %s", meta["symbol"], type(exc).__name__)
            df = None

    if isEmptyDf(df):
        meta["nObs"] = 0
        return (None, meta) if returnMeta else None

    meta["nObs"] = int(df.height)
    return (df, meta) if returnMeta else df


def benchmarkSnapshot(
    stockCode: str,
    *,
    market: str = "auto",
    benchmark: str | None = None,
    benchmarkMode: str = "market",
    start: str | None = None,
    end: str | None = None,
) -> dict[str, Any]:
    """``quant("benchmark")`` 축 구현 — 벤치마크와 기간 수익률 요약.

    Capabilities:
        - fetchBenchmarkOhlcv → 기간 수익률 + 누적 + 통계 요약 dict
        - story 6 막 벤치 박스 표준 입력

    Args:
        stockCode: 종목코드.
        market: ``"auto" | "KR" | "US"`` 등.
        benchmark: 명시 벤치.
        benchmarkMode: ``"market" | "sector" | "style" | "auto"``.
        start: 시작일.
        end: 종료일.

    Returns:
        dict — benchmark/period/returns 등 요약. 데이터 없음 시 ``{error}``.

    Guide:
        Quant benchmark 축 표준. 단일 종목 ↔ 벤치 비교.

    When:
        Quant benchmark axis + AI 벤치 대비 성과 답변.

    How:
        ``fetchBenchmarkOhlcv`` → close 시계열 → 기간 % 수익률 산출.

    Requires:
        stockCode + 벤치 데이터.

    Raises:
        없음.

    Example:
        >>> benchmarkSnapshot("005930", benchmarkMode="sector")["benchmark"]
        {'indexName': '코스피 200', ...}

    SeeAlso:
        - fetchBenchmarkOhlcv : OHLCV
        - factor.decomposeFactor : 다변수

    AIContext:
        "벤치 대비 N% 초과" 답변 시 returns 요약 인용.
    """
    df, meta = fetchBenchmarkOhlcv(
        stockCode,
        market=market,
        benchmark=benchmark,
        benchmarkMode=benchmarkMode,
        start=start,
        end=end,
        returnMeta=True,
        includeStackDetail=True,
    )
    result: dict[str, Any] = {
        "stockCode": stockCode,
        "market": meta.get("market"),
        "benchmarkUsed": meta,
        "benchmarkStack": meta.get("benchmarkStack"),
    }
    if isEmptyDf(df):
        return {**result, "error": "벤치마크 데이터 없음"}

    close = df.get_column("close").to_list()
    dates = df.get_column("date").to_list()
    latest = float(close[-1])

    def _ret(days: int) -> float | None:
        if len(close) <= days or close[-days - 1] in (None, 0):
            return None
        return round((latest / float(close[-days - 1]) - 1.0) * 100, 2)

    return {
        **result,
        "startDate": str(dates[0]),
        "endDate": str(dates[-1]),
        "latestClose": latest,
        "return1m": _ret(21),
        "return3m": _ret(63),
        "return6m": _ret(126),
        "return1y": _ret(252),
    }


def calcBenchmark(stockCode: str, **kwargs: Any) -> dict[str, Any]:
    """quant registry용 얇은 래퍼.

    Example:
        >>> calcBenchmark("005930")

    Requires:
        benchmarkSnapshot 호출 가능 (KR/US 벤치마크 fetch).

    Raises:
        없음 (실패는 빈 dict).
    """
    return benchmarkSnapshot(stockCode, **kwargs)


# 0.10 BC 깸 — snake_case alias 제거.
