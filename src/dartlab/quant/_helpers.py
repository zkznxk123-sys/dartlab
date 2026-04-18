"""quant 엔진 공용 헬퍼 — OHLCV fetch, market 감지, scan parquet 로드."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


# ── Market 감지 ──────────────────────────────────────────


def detect_market(stockCode: str) -> str:
    """종목코드에서 시장을 자동 감지.

    6자리 숫자 → KR, 알파벳 포함 → US.
    """
    if stockCode and stockCode.strip().isdigit() and len(stockCode.strip()) == 6:
        return "KR"
    return "US"


def resolve_market(stockCode: str, market: str = "auto") -> str:
    """market 파라미터 해석 — auto이면 종목코드 패턴으로 자동 감지.

    Parameters
    ----------
    stockCode : str
        종목코드 (예: "005930", "AAPL").
    market : str
        "KR" | "US" | "auto" (기본 "auto").

    Returns
    -------
    str
        "KR" 또는 "US"."""
    if market and market.lower() != "auto":
        return market.upper()
    return detect_market(stockCode)


# ── OHLCV fetch ──────────────────────────────────────────


def fetch_ohlcv(stockCode: str, **kwargs: Any):
    """gather("price")로 OHLCV 수집 — 실패 시 None.

    Parameters
    ----------
    stockCode : str
        종목코드 (예: "005930", "AAPL").
    **kwargs
        GatherEntry 전달 인자 (start, market 등).

    Returns
    -------
    pl.DataFrame | None
        date : date — 거래일
        open : float — 시가 (원)
        high : float — 고가 (원)
        low : float — 저가 (원)
        close : float — 종가 (원)
        volume : int — 거래량 (주)
        수집 실패 시 None."""
    try:
        from dartlab.gather.entry import GatherEntry

        g = GatherEntry()
        return g("price", stockCode, **kwargs)
    except (ImportError, ValueError, TypeError, RuntimeError):
        log.warning("OHLCV fetch 실패: %s", stockCode)
        return None


def fetch_benchmark(market: str = "KR", **kwargs: Any):
    """벤치마크 OHLCV 수집 — KR=KOSPI, US=S&P500.

    Parameters
    ----------
    market : str
        "KR" (KOSPI) 또는 "US" (S&P500).
    **kwargs
        GatherEntry 전달 인자 (start 등).

    Returns
    -------
    pl.DataFrame | None
        date : date — 거래일
        open : float — 시가
        high : float — 고가
        low : float — 저가
        close : float — 종가
        volume : int — 거래량
        수집 실패 시 None."""
    symbol = "KOSPI" if market == "KR" else "^GSPC"
    try:
        from dartlab.gather.entry import GatherEntry

        g = GatherEntry()
        return g("price", symbol, **kwargs)
    except (ImportError, ValueError, TypeError, RuntimeError):
        log.warning("벤치마크 fetch 실패: %s", symbol)
        return None


# ── scan parquet 로드 (메모리 안전) ──────────────────────


def _scan_data_root() -> Path:
    """data/ 루트 경로."""
    from dartlab.core.dataLoader import _getDataRoot

    return Path(_getDataRoot())


def load_scan_parquet(name: str, market: str = "KR"):
    """scan 프리빌드 parquet lazy scan 로드.

    Args:
        name: "finance", "changes" 또는 report/ 하위 이름
        market: "KR" | "US"

    Returns:
        pl.LazyFrame 또는 None
    """
    import polars as pl

    root = _scan_data_root()
    if market == "KR":
        base = root / "dart" / "scan"
    else:
        base = root / "edgar" / "scan"

    # finance.parquet 또는 report/ 하위
    path = base / f"{name}.parquet"
    if not path.exists():
        path = base / "report" / f"{name}.parquet"
    if not path.exists():
        log.warning("scan parquet 없음: %s", path)
        return None

    return pl.scan_parquet(path)


def load_shares_outstanding(market: str = "KR"):
    """발행주식수 프리빌드 LazyFrame 로드.

    KR: data/dart/scan/sharesOutstanding.parquet (보통주/우선주 분리)
    US: data/edgar/scan/sharesOutstanding.parquet (XBRL dei)

    scan 카테고리이므로 `_ensureScanData()` 가 자동으로 HF 에서 받아온다 —
    finance.parquet / changes.parquet 과 동일 패턴.

    Returns:
        pl.LazyFrame 또는 None
    """
    import polars as pl

    if market == "KR":
        from dartlab.scan._helpers import _ensureScanData

        scanDir = _ensureScanData()
        path = scanDir / "sharesOutstanding.parquet"
    else:
        root = _scan_data_root()
        path = root / "edgar" / "scan" / "sharesOutstanding.parquet"

    if not path.exists():
        log.warning("sharesOutstanding parquet 없음: %s", path)
        return None
    return pl.scan_parquet(path)


def load_docs_for_stock(stockCode: str):
    """단일 종목 docs parquet 로드.

    Returns:
        pl.DataFrame 또는 None
    """
    import polars as pl

    root = _scan_data_root()
    path = root / "dart" / "docs" / f"{stockCode}.parquet"
    if not path.exists():
        log.warning("docs parquet 없음: %s", path)
        return None

    return pl.read_parquet(path)


def load_changes_for_stock(stockCode: str):
    """changes.parquet에서 단일 종목 필터링.

    Returns:
        pl.DataFrame 또는 None
    """
    import polars as pl

    root = _scan_data_root()
    path = root / "dart" / "scan" / "changes.parquet"
    if not path.exists():
        return None

    lf = pl.scan_parquet(path)
    for col in ("stockCode", "종목코드", "corp_code"):
        try:
            return lf.filter(pl.col(col) == stockCode).collect()
        except pl.exceptions.ColumnNotFoundError:
            continue
    return None


# ── scan parquet에서 종목 백분위 계산 ────────────────────


def stock_percentile(lf, stockCode: str, col: str, stock_col: str = "stockCode", reverse: bool = False):
    """scan lazy frame에서 특정 종목의 컬럼 백분위를 계산.

    Args:
        lf: pl.LazyFrame (scan parquet)
        stockCode: 종목코드
        col: 백분위를 구할 컬럼명
        stock_col: 종목코드 컬럼명
        reverse: True이면 높은 값 = 낮은 백분위 (PBR 등)

    Returns:
        (value, percentile) 또는 (None, None)
    """
    import polars as pl

    try:
        # 종목코드 컬럼 자동 탐색
        schema_names = lf.collect_schema().names()
        actual_stock_col = None
        for c in (stock_col, "종목코드", "stockCode", "corp_code"):
            if c in schema_names:
                actual_stock_col = c
                break
        if actual_stock_col is None or col not in schema_names:
            return None, None

        # 이 종목의 값
        row = lf.filter(pl.col(actual_stock_col) == stockCode).select(col).collect()
        if len(row) == 0 or row.item() is None:
            return None, None

        val = float(row.item())

        # 전체 분포에서 백분위
        all_vals = lf.select(col).drop_nulls().collect().to_series()
        if len(all_vals) == 0:
            return val, None

        if reverse:
            pct = float((all_vals > val).sum() / len(all_vals))
        else:
            pct = float((all_vals < val).sum() / len(all_vals))

        return val, round(pct, 4)
    except (KeyError, ValueError, TypeError):
        return None, None


def load_allfilings_for_stock(stockCode: str, *, lookback_days: int | None = None):
    """allFilings parquet 에서 단일 종목 데이터 로드.

    `data/dart/allFilings/*.parquet` 일자별 전종목 파일에서 stock_code 로 필터.
    polars lazy scan + filter pushdown 으로 메모리 안전 (전체 스캔 가능).

    [Phase 4 R3 fix]
    - 이전: `parquets[-60:]` 슬라이싱으로 60일 한정 → eventDriven 5년 백테스트 막힘
    - 정정: 전체 일자 lazy scan, 컬럼 매칭 `stock_code` (snake_case) 우선
    - lookback_days 명시 시만 최근 N일로 제한 (호출자 책임)

    Args:
        stockCode: 6자리 종목코드 (예: '005930')
        lookback_days: None=전체 / 숫자=최근 N일

    Returns:
        pl.DataFrame 또는 None
    """
    import polars as pl

    root = _scan_data_root()
    adir = root / "dart" / "allFilings"
    if not adir.exists():
        return None

    parquets = sorted(adir.glob("*.parquet"))
    parquets = [p for p in parquets if "_meta" not in p.name]
    if not parquets:
        return None

    if lookback_days is not None and lookback_days > 0:
        parquets = parquets[-lookback_days:]

    # 컬럼명 우선순위: stock_code (snake) → stockCode → 종목코드 → corp_code
    candidate_cols = ("stock_code", "stockCode", "종목코드", "corp_code")

    frames: list = []
    for p in parquets:
        try:
            lf = pl.scan_parquet(p)
            schema = lf.collect_schema().names()
            matched_col = next((c for c in candidate_cols if c in schema), None)
            if matched_col is None:
                continue
            filtered = lf.filter(pl.col(matched_col) == stockCode).collect()
            if len(filtered) > 0:
                frames.append(filtered)
        except (OSError, pl.exceptions.ComputeError):
            continue

    if not frames:
        return None
    return pl.concat(frames, how="diagonal_relaxed")


# ── OHLCV → numpy 변환 ──────────────────────────────────


# ── 강건한 계정 추출 (DART finance.parquet) ──────────────


# 표준 키 → DART account_nm 정규식 패턴 (우선순위 순서, 첫 매치 사용)
_ACCOUNT_PATTERNS: dict[str, list[str]] = {
    "sales": [
        r"^매출액$",
        r"^수익\(매출액\)$",
        r"^수익$",
        r"^영업수익$",
        r"^매출$",
        r"매출액",
    ],
    "operating_profit": [
        r"^영업이익$",
        r"^영업이익\(손실\)$",
        r"^영업손익$",
        r"영업이익",
    ],
    "net_income": [
        r"^당기순이익$",
        r"^당기순이익\(손실\)$",
        r"^당기순손익$",
        r"^연결당기순이익$",
        r"^지배기업소유주지분순이익$",
        r"^지배기업의?\s*소유주에?\s*귀속되는?\s*당기순이익$",
        r"당기순이익",
    ],
    "total_assets": [r"^자산총계$"],
    "total_liabilities": [r"^부채총계$"],
    "total_equity": [
        r"^자본총계$",
        r"^지배기업소유주지분$",
    ],
    "operating_cf": [
        r"^영업활동현금흐름$",
        r"^영업활동으로?\s*인한?\s*현금흐름$",
        r"영업활동.*현금흐름",
    ],
    "investing_cf": [
        r"^투자활동현금흐름$",
        r"투자활동.*현금흐름",
    ],
    "financing_cf": [
        r"^재무활동현금흐름$",
        r"재무활동.*현금흐름",
    ],
}

# 표준 키 → 후보 sj_div 리스트
# IS = 별개 손익계산서, CIS = 포괄손익계산서 단일 양식. 일부 기업(SK하이닉스 등)은 CIS만 사용.
_ACCOUNT_SJ: dict[str, list[str]] = {
    "sales": ["IS", "CIS"],
    "operating_profit": ["IS", "CIS"],
    "net_income": ["IS", "CIS"],
    "total_assets": ["BS"],
    "total_liabilities": ["BS"],
    "total_equity": ["BS"],
    "operating_cf": ["CF"],
    "investing_cf": ["CF"],
    "financing_cf": ["CF"],
}


def _parse_amount(val) -> float | None:
    """문자열/숫자 → float. core.finance.helpers.parseNumStr SSOT."""
    if isinstance(val, (int, float)):
        return float(val)
    from dartlab.core.finance.helpers import parseNumStr

    return parseNumStr(val)


def extract_account(df, key: str) -> float | None:
    """DART finance.parquet의 단일 종목/단일 기간 DataFrame에서 표준 계정 추출.

    Args:
        df: pl.DataFrame — sj_div, account_nm, thstrm_amount 컬럼 보유
        key: 표준 키 ("sales", "operating_profit", "net_income", "total_assets", ...)

    Returns:
        float 또는 None. 우선순위 패턴 순회하며 첫 매치 사용.
    """
    import polars as pl

    patterns = _ACCOUNT_PATTERNS.get(key)
    sj_list = _ACCOUNT_SJ.get(key)
    if patterns is None or sj_list is None:
        return None
    if df is None or df.is_empty():
        return None

    for sj in sj_list:
        base = df.filter(pl.col("sj_div") == sj)
        if base.is_empty():
            continue
        for pat in patterns:
            try:
                rows = base.filter(pl.col("account_nm").str.contains(pat))
            except (pl.exceptions.ComputeError, AttributeError):
                continue
            if len(rows) == 0:
                continue
            amounts = rows.get_column("thstrm_amount").to_list()
            for amt in amounts:
                v = _parse_amount(amt)
                if v is not None:
                    return v
    return None


def extract_accounts(df, keys: list[str]) -> dict[str, float | None]:
    """여러 표준 계정 일괄 추출 — DART finance.parquet 용.

    Parameters
    ----------
    df : pl.DataFrame
        DART finance.parquet 의 단일 종목/단일 기간 DataFrame.
        sj_div, account_nm, thstrm_amount 컬럼 보유.
    keys : list[str]
        표준 계정 키 리스트
        ("sales", "operating_profit", "net_income", "total_assets",
         "total_liabilities", "total_equity", "operating_cf",
         "investing_cf", "financing_cf").

    Returns
    -------
    dict[str, float | None]
        키별 금액 (원). 매칭 실패 시 해당 키 = None.

    Examples
    --------
    >>> extract_accounts(df, ["sales", "net_income"])"""
    return {k: extract_account(df, k) for k in keys}


def ohlcv_to_arrays(df):
    """Polars OHLCV DataFrame → numpy 배열 dict.

    Returns:
        dict with keys: open, high, low, close, volume, date
        또는 빈 dict
    """
    import numpy as np

    if df is None or df.is_empty():
        return {}

    result = {}
    for col in ("open", "high", "low", "close", "volume"):
        if col in df.columns:
            result[col] = df.get_column(col).to_numpy().astype(np.float64)

    if "date" in df.columns:
        result["date"] = df.get_column("date").to_list()

    return result


# ── Strategy DSL 공용 헬퍼 (Phase B) ──────────────────────────────────────────


def tom_mask(dates) -> "Any":
    """Turn-of-the-Month boolean mask — KR 캘린더 시즌신호.

    KOSDAQ 에서 학술 검증된 월말 3거래일 + 월초 3거래일 효과를 boolean 시계열로 반환.
    학술 근거: Lakonishok-Smidt 1988, Korean Journal of Finance (KOSDAQ TOM, 2018+).

    seasonalKR 스타일 외에 다른 곳에서 만들지 말 것 (SSOT).

    Args:
        dates: list[date] 또는 polars Series of Date — OHLCV 의 date 컬럼

    Returns:
        numpy.ndarray[bool] 길이 N — 월말 3일/월초 3일 True
    """
    import numpy as np

    days = [d.day for d in dates]
    return np.array([(d <= 3 or d >= 25) for d in days], dtype=np.bool_)


def extractSignalSeries(arr: dict, fn, *, key: str | None = None, **kwargs):
    """벡터 신호 함수를 OHLCV 배열에 적용해 시계열 반환 (SSOT).

    Strategy DSL 이 dict-only analyze_xxx 함수의 시계열 분기 안에서 호출하는 단일
    공용 헬퍼. 다른 위치에 비슷한 wrapper 만들지 말 것.

    Args:
        arr: ohlcv_to_arrays() 결과 dict (close/high/low/volume/date 포함)
        fn: signals.py / indicators.py 의 v* 함수 (입력 시그니처 자동 감지)
        key: 결과 컬럼 명. None 이면 fn.__name__
        **kwargs: fn 에 전달할 추가 인자

    Returns:
        dict {key: NDArray} — 길이 보존
    """
    import inspect

    if not arr or "close" not in arr:
        return {}
    sig_params = list(inspect.signature(fn).parameters.keys())
    inputs = []
    for p in sig_params:
        if p in arr:
            inputs.append(arr[p])
        elif p in kwargs:
            inputs.append(kwargs.pop(p))
        else:
            break  # 나머지는 kwargs 로 전달
    out = fn(*inputs, **kwargs)
    return {key or fn.__name__: out}
