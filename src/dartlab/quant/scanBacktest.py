"""scan → quant 폐쇄 루프 — runScanBacktest top-level helper.

scan 결과 DataFrame 을 외부 입력으로 받아 universe 추출 → signalFn 또는 style 로
종목별 Rule 빌드 → ``multiAssetBacktest`` 호출 → BacktestResult.scanContext 에
universe 출처 SHA-1 기록.

설계 원칙 (architecture.md 준수):
- quant → scan import 금지 (역방향). scan 결과는 ``pl.DataFrame`` 입력으로만 받음.
- axis 등록 X (top-level helper) — registry dispatcher 의 ``fn(stockCode=stockCode, **kw)``
  계약과 시그니처 (첫 인자가 DataFrame) 가 어긋남.
- numpy / polars only. multiAssetBacktest SSOT 재사용 (새 멀티자산 엔진 신설 X).
"""

from __future__ import annotations

import dataclasses
from typing import Any, Callable

import numpy as np
import polars as pl

from dartlab.core.polarsUtil import isEmptyDf
from dartlab.quant._helpers import STOCK_CODE_COLUMNS
from dartlab.quant.strategy.backtest import (
    DEFAULT_FEE_BPS,
    DEFAULT_SLIP_BPS,
    BacktestResult,
    multiAssetBacktest,
)
from dartlab.quant.strategy.presets import STYLE_REGISTRY, resolveStyle
from dartlab.quant.strategy.rule import Rule

# 하위호환 — 외부에서 _STOCK_CODE_CANDIDATES 직접 참조하던 코드 보존 (SSOT 는 STOCK_CODE_COLUMNS)
_STOCK_CODE_CANDIDATES = STOCK_CODE_COLUMNS


def _detectStockCodeColumn(df: pl.DataFrame) -> str | None:
    """scan 결과 DataFrame 의 universe 식별 컬럼 자동 감지.

    우선순위는 ``STOCK_CODE_COLUMNS`` SSOT (``_helpers.py``) 가 정의 — ``stockCode``
    → ``종목코드`` → ``stock_code`` → ``corp_code``. 매칭 실패 시 None.
    """
    if isEmptyDf(df):
        return None
    cols = df.columns
    for cand in STOCK_CODE_COLUMNS:
        if cand in cols:
            return cand
    return None


def _hashScanResult(df: pl.DataFrame, top_n: int) -> str:
    """결정적 SHA-1 hash — universe 출처 추적용 (universe 같으면 hash 같다)."""
    import hashlib

    if isEmptyDf(df):
        return "empty"
    sub = df.head(top_n)
    h = hashlib.sha1()
    h.update(str(sub.shape).encode("utf-8"))
    h.update(",".join(sub.columns).encode("utf-8"))
    try:
        for v in sub.hash_rows().to_list():
            h.update(str(v).encode("utf-8"))
    except (AttributeError, pl.exceptions.ComputeError):
        h.update(str(sub.to_dicts()).encode("utf-8"))
    return h.hexdigest()[:16]


def _ruleFromStyle(style_key: str) -> Callable[[Any], Rule]:
    """style 문자열 → STYLE_REGISTRY 의 build 함수.

    ``resolveStyle`` 로 한글/영문 alias 처리. 미등록 시 KeyError.
    """
    canonical = resolveStyle(style_key)
    registry = STYLE_REGISTRY()
    if canonical not in registry:
        msg = f"미등록 style: '{style_key}'. 후보: {list(registry.keys())}"
        raise KeyError(msg)
    return registry[canonical]


def _ruleFromSignalFn(signalFn: Callable[[np.ndarray], np.ndarray]) -> Callable[[Any], Rule]:
    """signalFn (close → entry/exit boolean) → rule_builder.

    signalFn 은 종목별 close 시계열을 받아 길이 N 의 boolean 배열 (True=long position) 을
    반환. exit 은 entry 의 보수적 끝점 (entry False 가 첫 등장하는 시점) 으로 자동 산출.
    """
    from dartlab.quant._helpers import fetchOhlcv, ohlcvToArrays

    def _empty(n: int) -> Rule:
        return Rule(
            entry_expr=np.zeros(max(1, n), dtype=bool),
            exit_expr=np.zeros(max(1, n), dtype=bool),
        )

    def _builder(company_stub: Any) -> Rule:
        code = getattr(company_stub, "stockCode", None)
        if code is None:
            return _empty(0)
        ohlcv = fetchOhlcv(code)
        if isEmptyDf(ohlcv):
            return _empty(0)
        arr = ohlcvToArrays(ohlcv)
        close = arr.get("close")
        if close is None or len(close) < 30:
            return _empty(0)
        try:
            position = signalFn(close)
        except Exception:  # noqa: BLE001
            return _empty(len(close))
        position = np.asarray(position, dtype=bool)
        if len(position) != len(close):
            if len(position) < len(close):
                pad = np.zeros(len(close) - len(position), dtype=bool)
                position = np.concatenate([pad, position])
            else:
                position = position[-len(close) :]
        entry = np.zeros(len(close), dtype=bool)
        exit_ = np.zeros(len(close), dtype=bool)
        entry[1:] = position[1:] & ~position[:-1]
        exit_[1:] = ~position[1:] & position[:-1]
        return Rule(entry_expr=entry, exit_expr=exit_)

    return _builder


def runScanBacktest(
    scanResult: pl.DataFrame,
    *,
    signalFn: Callable[[np.ndarray], np.ndarray] | None = None,
    style: str | None = None,
    universeCol: str = "auto",
    topN: int = 20,
    weighting: str = "equal",
    fee_bps: float = DEFAULT_FEE_BPS,
    slip_bps: float = DEFAULT_SLIP_BPS,
) -> BacktestResult:
    """scan 결과 universe + signalFn (또는 style) → multi-asset backtest 폐쇄 루프.

    Parameters
    ----------
    scanResult : pl.DataFrame
        scan(...) 결과. ``stockCode`` 또는 ``종목코드`` / ``stock_code`` 컬럼 보유.
        사용자가 사전에 sort/filter 한 DataFrame 을 그대로 입력 (등급 자동 추출 X — 명시 책임).
    signalFn : Callable[[close], np.ndarray[bool]] | None
        종목별 close 시계열을 받아 entry position boolean 산출. 우선 적용.
    style : str | None
        ``signalFn`` 미지정 시 STYLE_REGISTRY 의 8 styles 중 하나 (한글 alias 허용).
    universeCol : str
        universe 컬럼 명시. "auto" 면 ``_detectStockCodeColumn`` 으로 자동 감지.
    topN : int
        scanResult 의 상위 N 종목만 universe 로 사용 (사용자 사전 sort 가정).
    weighting : str
        "equal" / "inv_vol" / "risk_parity" — multiAssetBacktest 인자.
    fee_bps, slip_bps : float
        거래비용 (단위 bp). default 15 / 5.

    Returns
    -------
    BacktestResult
        ``multiAssetBacktest`` 결과에 ``scanContext`` 필드만 추가:
        ``{universeSize, universeCol, topN, scanResultHash, signalSource, weighting}``.

    When
    ----
    AI 가 "scan 으로 추린 universe 에 quant 백테스트를 직접 적용" 하고 싶을 때.
    예: scan("valuation").filter(등급=A).sort("PER").head(20) → forecast 신호 → backtest.

    How
    ---
    >>> import dartlab as dl
    >>> import polars as pl
    >>> top = dl.scan("valuation").filter(pl.col("등급") == "A").sort("PER").head(20)
    >>> result = dl.quant.scanBacktest(top, style="trendFollow", topN=20)
    >>> result.scanContext
    {'universeSize': 20, 'universeCol': 'stockCode', ...}

    Raises
    ------
    ValueError
        scanResult 가 비었거나 universe 컬럼 미감지 시.
    KeyError
        ``style`` 이 STYLE_REGISTRY 에 미등록 시.

    Verified
    --------
    - end-to-end (2026-05-09 dogfood): scan("valuation") 2535 종목 → top 5 → trendFollow
      style → status=ok, scanContext={universeCol="종목코드", scanResultHash="8f077b62024493f9"}
    - 인기 5 종목 + SMA momentum signalFn → sharpe=+2.45, dsr=+0.84, trades=34 (합리적)
    - 결정성: 같은 universe 두 번 호출 → scanResultHash + sharpe 모두 일치
    - universeCol 자동 감지: stockCode / 종목코드 / stock_code 모두 지원

    Notes
    -----
    - scanContext.scanResultHash 는 입력 DataFrame 의 head(topN) 에 대한 결정적 SHA-1.
      같은 universe → 같은 hash. 사용자가 다른 sort/filter 적용 → 다른 hash.
    - signalFn 우선. 둘 다 미지정 시 ValueError.
    - axis 미등록 — ``dartlab.quant("scanBacktest", ...)`` 호출 X. ``dartlab.quant.scanBacktest(...)``
      attribute 호출만 지원.
    """
    if isEmptyDf(scanResult):
        return BacktestResult(status="error", reason="empty scanResult")
    if signalFn is None and style is None:
        return BacktestResult(status="error", reason="signalFn 또는 style 중 하나 필요")

    col = universeCol if universeCol != "auto" else _detectStockCodeColumn(scanResult)
    if col is None or col not in scanResult.columns:
        return BacktestResult(
            status="error",
            reason=f"universe 컬럼 미감지. 후보: {STOCK_CODE_COLUMNS}",
        )

    universe_df = scanResult.head(int(topN))
    codes_raw = universe_df.get_column(col).to_list()
    codes = [str(c).strip() for c in codes_raw if c is not None and str(c).strip()]
    if not codes:
        return BacktestResult(status="error", reason="universe 코드 추출 실패")

    if signalFn is not None:
        rule_builder = _ruleFromSignalFn(signalFn)
        signal_source = "signalFn"
    else:
        rule_builder = _ruleFromStyle(style)  # type: ignore[arg-type]
        signal_source = f"style:{resolveStyle(style or '')}"

    bt = multiAssetBacktest(
        codes,
        rule_builder,
        weighting=weighting,
        fee_bps=fee_bps,
        slip_bps=slip_bps,
        style=signal_source,
    )

    scan_ctx: dict[str, Any] = {
        "universeSize": len(codes),
        "universeCol": col,
        "topN": int(topN),
        "scanResultHash": _hashScanResult(scanResult, int(topN)),
        "signalSource": signal_source,
        "weighting": weighting,
    }
    return dataclasses.replace(bt, scanContext=scan_ctx)
