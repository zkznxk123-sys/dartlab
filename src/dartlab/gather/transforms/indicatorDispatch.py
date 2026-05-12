"""KRX wide pivot 의 target → indicator 함수 디스패치.

`gather("krx", "rsi14", ...)` 같은 호출에서 ``target`` 문자열을 파싱해
`gather/indicators.py` 의 vectorized 함수로 매핑하고 종목별 group 안에서 적용.

**규칙**:
    - target = raw 컬럼 (close, open, high, low, volume 등) → 그 컬럼 그대로 wide
    - target = indicator name (rsi14, ma20, macd, atr14, obv, ...) → 계산 후 wide
    - target = "raw" → long DataFrame 그대로 (escape hatch)

**파싱 컨벤션**:
    "ma{N}"   → vsma(close, period=N)        — 단순이평
    "ema{N}"  → vema(close, period=N)
    "wma{N}"  → vwma(close, period=N)
    "rsi{N}"  → vrsi(close, period=N)
    "atr{N}"  → vatr(high, low, close, period=N)
    "roc{N}"  → vroc(close, period=N)
    "cci{N}"  → vcci(high, low, close, period=N)
    "macd"    → vmacd(close) → macd line (default 12/26/9)
    "macdSignal" → vmacd(close) signal
    "macdHist"   → vmacd(close) histogram
    "bbUpper{N}" / "bbLower{N}" / "bbMid{N}" → vbollinger(close, N)
    "obv"     → vobv(close, volume)
    "mfi{N}"  → vmfi(high, low, close, volume, N)
    "adx{N}"  → vadx(high, low, close, N)
    ... (45 indicator 전부)

전종목 동시 적용은 Polars `over(stockCode)` + `map_groups` — 한 호출로 SIMD/multi-thread.
"""

from __future__ import annotations

import logging
import re
from typing import Callable

import numpy as np
import polars as pl

log = logging.getLogger(__name__)

# 표준 컬럼명 (KRX raw → quant 표준 매핑은 gatherKrx 가 처리, 여기선 quant 표준만)
_STD_CLOSE = "close"
_STD_OPEN = "open"
_STD_HIGH = "high"
_STD_LOW = "low"
_STD_VOLUME = "volume"


def _resolveIndicator(target: str) -> tuple[Callable, dict, list[str]]:
    """target 문자열 → (함수, kwargs, 필요한 컬럼 리스트).

    Returns
    -------
    (fn, kwargs, inputCols)
        fn: dartlab.core.indicators 의 함수
        kwargs: period 등 인자 dict
        inputCols: 함수에 전달할 OHLCV 컬럼 리스트 (예: ["close"], ["high", "low", "close"])
    """
    from dartlab.core import indicators as ind

    # camelCase / 대소문자 정규화 — "williamsR14" → "williamsr14", "ForceIndex13" → "forceindex13"
    t = target.strip().lower()
    m = re.match(r"^([a-z]+)(\d+)?$", t)
    if not m:
        raise ValueError(f"target 파싱 실패: {target!r}")
    name, periodStr = m.group(1), m.group(2)
    period = int(periodStr) if periodStr else None

    # 디스패치 표 — (함수, default period, input columns). key 는 모두 lowercase.
    table: dict[str, tuple[Callable, int | None, list[str]]] = {
        # 추세 (close 만)
        "ma": (ind.vsma, 20, [_STD_CLOSE]),
        "sma": (ind.vsma, 20, [_STD_CLOSE]),
        "ema": (ind.vema, 20, [_STD_CLOSE]),
        "wma": (ind.vwma, 20, [_STD_CLOSE]),
        "dema": (ind.vdema, 20, [_STD_CLOSE]),
        "tema": (ind.vtema, 20, [_STD_CLOSE]),
        "hma": (ind.vhma, 20, [_STD_CLOSE]),
        "macd": (ind.vmacd, None, [_STD_CLOSE]),  # MACD line (default 12/26/9, returns macd line)
        # 모멘텀 (close 만)
        "rsi": (ind.vrsi, 14, [_STD_CLOSE]),
        "roc": (ind.vroc, 12, [_STD_CLOSE]),
        "momentum": (ind.vmomentum, 10, [_STD_CLOSE]),
        "cmo": (ind.vcmo, 14, [_STD_CLOSE]),
        # high/low/close 필요
        "atr": (ind.vatr, 14, [_STD_HIGH, _STD_LOW, _STD_CLOSE]),
        "cci": (ind.vcci, 20, [_STD_HIGH, _STD_LOW, _STD_CLOSE]),
        "williamsr": (ind.vwilliamsR, 14, [_STD_HIGH, _STD_LOW, _STD_CLOSE]),
        "adx": (ind.vadx, 14, [_STD_HIGH, _STD_LOW, _STD_CLOSE]),
        # 거래량
        "obv": (ind.vobv, None, [_STD_CLOSE, _STD_VOLUME]),
        "mfi": (ind.vmfi, 14, [_STD_HIGH, _STD_LOW, _STD_CLOSE, _STD_VOLUME]),
        "adl": (ind.vadl, None, [_STD_HIGH, _STD_LOW, _STD_CLOSE, _STD_VOLUME]),
        "vwap": (ind.vvwap, None, [_STD_HIGH, _STD_LOW, _STD_CLOSE, _STD_VOLUME]),
        "nvi": (ind.vnvi, None, [_STD_CLOSE, _STD_VOLUME]),
        "pvi": (ind.vpvi, None, [_STD_CLOSE, _STD_VOLUME]),
        "pvt": (ind.vpvt, None, [_STD_CLOSE, _STD_VOLUME]),
        "forceindex": (ind.vforceIndex, 13, [_STD_CLOSE, _STD_VOLUME]),
        # 변동성
        "ulcer": (ind.vulcer, 14, [_STD_CLOSE]),
        # 특수 (close 만)
        "trix": (ind.vtrix, 15, [_STD_CLOSE]),
        "dpo": (ind.vdpo, 20, [_STD_CLOSE]),
    }

    if name not in table:
        valid = sorted(table.keys())
        raise ValueError(
            f"target indicator '{target}' 알 수 없음. 가용: {', '.join(valid)} "
            "(또는 raw 컬럼: close/open/high/low/volume/marketCap/...)"
        )

    fn, defaultPeriod, inputCols = table[name]
    if defaultPeriod is None:
        # period 없는 함수 (obv, vwap 등)
        return fn, {}, inputCols
    p = period if period is not None else defaultPeriod
    return fn, {"period": p}, inputCols


_DEFAULT_INDICATORS_ALL = (
    # 추세
    "sma5",
    "sma20",
    "sma60",
    "sma120",
    "ema12",
    "ema26",
    "ema60",
    "wma20",
    "dema20",
    "tema20",
    "hma20",
    # 모멘텀
    "rsi14",
    "rsi9",
    "roc12",
    "momentum10",
    "cmo14",
    # 변동성·추세필터
    "atr14",
    "adx14",
    "cci20",
    "williamsR14",
    "ulcer14",
    # 거래량
    "obv",
    "adl",
    "vwap",
    "mfi14",
    "forceIndex13",
    "nvi",
    "pvi",
    "pvt",
    # 특수
    "trix15",
    "dpo20",
)


def addIndicators(
    ohlcvDf: pl.DataFrame,
    indicators: bool | list[str] = True,
    *,
    closeCol: str = "close",
    highCol: str = "high",
    lowCol: str = "low",
    volumeCol: str = "volume",
    precision: int | None = 2,
) -> pl.DataFrame:
    """단일 종목 OHLCV DataFrame 에 보조지표 컬럼 일괄 추가.

    Capabilities:
        - ``indicators=True`` (기본): 30개 표준 지표 모두 추가 (`_DEFAULT_INDICATORS_ALL`)
        - ``indicators=list[str]``: 지정한 지표만 (예: ["ma20", "rsi14"])
        - ``gather("price", code, indicators=...)`` 가 호출

    AIContext:
        - 단일 종목이라 group_by 불필요 — close/high/low/volume 직접 NumPy 배열로 함수 호출
        - 입력 OHLCV 컬럼명은 quant 표준 (open/high/low/close/volume)

    Args:
        ohlcvDf: 단일 종목 OHLCV (날짜 asc 정렬 가정).
        indicators: True (모두) 또는 지표 이름 리스트.
        closeCol/highCol/lowCol/volumeCol: 컬럼명 override.

    Returns:
        pl.DataFrame — 입력 컬럼 + 지표 컬럼 추가.

    Raises:
        없음 — 미등록 지표나 컬럼 부족은 warning 후 스킵.

    Example:
        >>> df = addIndicators(ohlcv, indicators=["ma20", "rsi14"])
    """
    if not indicators or ohlcvDf.is_empty():
        return ohlcvDf
    names = list(_DEFAULT_INDICATORS_ALL) if indicators is True else list(indicators)

    colMap = {
        "close": closeCol,
        "high": highCol,
        "low": lowCol,
        "volume": volumeCol,
    }
    additions: list[pl.Series] = []
    for name in names:
        try:
            fn, kwargs, inputCols = _resolveIndicator(name)
        except ValueError as exc:
            log.warning("addIndicators: %s 스킵 (%s)", name, exc)
            continue
        actualCols = [colMap.get(c, c) for c in inputCols]
        if any(c not in ohlcvDf.columns for c in actualCols):
            log.warning("addIndicators: %s 컬럼 부족, 스킵 — 필요: %s", name, actualCols)
            continue
        args = [ohlcvDf[c].to_numpy().astype(np.float64) for c in actualCols]
        result = fn(*args, **kwargs)
        if isinstance(result, tuple):
            result = result[0]
        arr = np.asarray(result, dtype=np.float64)
        if precision is not None:
            arr = np.round(arr, precision)
        additions.append(pl.Series(name=name, values=arr))

    if not additions:
        return ohlcvDf
    return ohlcvDf.with_columns(additions)


def computeIndicator(
    longDf: pl.DataFrame,
    target: str,
    *,
    codeCol: str = "stockCode",
    dateCol: str = "date",
    precision: int | None = 2,
) -> pl.Series:
    """전종목 group 에서 indicator 계산 → date 순 Series 반환 (longDf 와 같은 길이).

    longDf 는 이미 quant 표준 컬럼명 (close/open/high/...) 으로 normalize 되어야 함.
    (gatherKrx 가 raw KRX 컬럼 → 표준 컬럼 변환 후 호출)

    Returns
    -------
    pl.Series — longDf 의 row 순서와 동일한 indicator 값 (NaN 포함).

    Raises
    ------
    ValueError
        ``target`` 이 미등록 indicator 이거나 필요 컬럼이 longDf 에 없을 때.

    Example
    -------
    >>> s = computeIndicator(longDf, "rsi14")
    """
    fn, kwargs, inputCols = _resolveIndicator(target)
    missing = [c for c in inputCols if c not in longDf.columns]
    if missing:
        raise ValueError(f"target {target!r} 에 필요한 컬럼 없음: {missing}")

    # 종목별 group 순회. 각 group 의 sorted (date asc) close/high/low/volume 추출 → 함수 적용.
    groups = longDf.sort([codeCol, dateCol]).group_by(codeCol, maintain_order=True)
    pieces: list[np.ndarray] = []
    for (_code,), gdf in groups:
        args = [gdf[c].to_numpy().astype(np.float64) for c in inputCols]
        result = fn(*args, **kwargs)
        if isinstance(result, tuple):
            # macd 등 multiple 반환 — 첫 번째만 (macd line). macdSignal/macdHist 는 별도 처리.
            result = result[0]
        pieces.append(np.asarray(result, dtype=np.float64))
    flat = np.concatenate(pieces) if pieces else np.array([], dtype=np.float64)
    if precision is not None:
        flat = np.round(flat, precision)
    # group 순서 (sorted by codeCol asc, dateCol asc) 와 longDf.sort 결과 일치.
    return pl.Series(name=target, values=flat)
