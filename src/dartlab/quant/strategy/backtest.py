"""Vectorized backtest 엔진 — long-only, next-bar 시가 체결.

numpy/polars 만 사용. vectorbt/zipline/backtrader 의존 0.

처리:
    - entry/exit boolean 시계열 → trades(entry_idx, exit_idx, pnl)
    - 다음 봉 시가 체결, 수수료 15bp, 슬리피지 5bp
    - sizing/stop 은 Rule 에 명시된 경우만 적용
    - position 1/0 (long-only v1)

출력: BacktestResult dataclass — equity/returns/trades/sharpe/sortino/mdd/dsr/.../

walkForward + cpcv 로 OOS Sharpe + DSR + PBO 산출 가능.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import numpy as np
import polars as pl

from dartlab.core.polarsUtil import isEmptyDf

from .metrics import (
    cpcvSplits,
    dsr,
    expectancy,
    exposure,
    mdd,
    pbo,
    profitFactor,
    sharpe,
    sortino,
    turnover,
    winrate,
)
from .rule import Rule

# 체결/비용 상수
DEFAULT_FEE_BPS = 15.0  # 양방향 합산 (진입 + 청산)
DEFAULT_SLIP_BPS = 5.0
# ADV 비례 슬리피지: 거래량의 X% 이상 진입 시 추가 충격 비용 (bp/% impact)
DEFAULT_IMPACT_BPS_PER_PCT = 2.0
# 갭 임계: open[t+1]/close[t] 가 이 비율 초과 시 갭 위험 알림 (slippage 가중)
GAP_THRESHOLD_PCT = 0.03


@dataclass(frozen=True)
class BacktestResult:
    """백테스트 결과 — equity/trades/metrics + overfitting guards."""

    # 시계열
    equity: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))
    returns: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))
    positions: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))
    trades: pl.DataFrame | None = None

    # 표준 메트릭
    sharpe: float = 0.0
    sortino: float = 0.0
    mdd: float = 0.0
    winrate: float = 0.0
    profitFactor: float = 0.0
    expectancy: float = 0.0
    turnover: float = 0.0
    exposure: float = 0.0

    # Overfitting guards
    dsr: float = 0.0
    pbo: float | None = None

    # 메타
    style: str | None = None
    period: tuple[date | None, date | None] = (None, None)
    oos: bool = False
    cpcv: dict | None = None
    scanContext: dict | None = None  # scanBacktest 호출 시 universe 출처 추적

    # NotApplicable sentinel (KR-only style on US)
    status: str = "ok"  # "ok" | "not_applicable" | "error"
    reason: str | None = None

    def __repr__(self) -> str:
        if self.status != "ok":
            return f"BacktestResult(status={self.status!r}, reason={self.reason!r})"
        return (
            f"BacktestResult(style={self.style}, sharpe={self.sharpe:+.2f}, "
            f"mdd={self.mdd * 100:+.1f}%, dsr={self.dsr:.2f}, "
            f"trades={self.trades.height if self.trades is not None else 0}, "
            f"oos={self.oos})"
        )

    @classmethod
    def not_applicable(cls, *, style: str, reason: str) -> "BacktestResult":
        """KR-only 스타일을 US 에서 호출 시 sentinel."""
        return cls(status="not_applicable", reason=reason, style=style)


# ── 핵심 백테스트 ───────────────────────────────────────────────────────────


def vectorBacktest(
    close: np.ndarray,
    rule: Rule,
    *,
    open_: np.ndarray | None = None,
    high: np.ndarray | None = None,
    low: np.ndarray | None = None,
    volume: np.ndarray | None = None,
    dates: list | None = None,
    fee_bps: float = DEFAULT_FEE_BPS,
    slip_bps: float = DEFAULT_SLIP_BPS,
    impact_bps_per_pct: float = DEFAULT_IMPACT_BPS_PER_PCT,
    capital_pct_of_adv: float = 0.0,
    style: str | None = None,
    n_trials: int = 1,
    exec_mode: str = "next_open",
) -> BacktestResult:
    """단일 룰 백테스트 — long-only, 정밀 체결 모델.

    체결 모델 (정밀화 v2):
    - **next_open**: entry[t] True → t+1 시가 체결 (default)
    - **close**: entry[t] True → t 종가 체결 (테스트/sanity)
    - **gap 처리**: open[t+1]/close[t] 변동률 ≥ GAP_THRESHOLD_PCT 면 추가 슬리피지
    - **ADV impact**: capital_pct_of_adv > 0 시 거래량 비율에 비례한 충격 비용
    - **intrabar stop**: stop level 이 [low[t], high[t]] 안에 있으면 stop 가격 정확 체결
    - **last bar 청산**: 열린 포지션은 close[-1] 강제 마감

    Args:
        close: 일별 종가 (NDArray[float64])
        rule: Rule 객체 (entry_expr, exit_expr, sizing, stop)
        open_, high, low: optional, 정밀 체결 / 갭 / intrabar stop 용
        volume: optional, ADV impact 계산용 (capital_pct_of_adv > 0 시)
        dates: optional, period 메타
        fee_bps: 양방향 수수료 (basis points, 한쪽씩 절반 적용)
        slip_bps: 기본 슬리피지 (bps)
        impact_bps_per_pct: 충격 비용 (1% ADV 진입 시 N bps 추가)
        capital_pct_of_adv: 진입 자본의 거래량 대비 비율 (0 = 무시)
        style: 스타일 식별자
        n_trials: DSR 정정용 시도 횟수
        exec_mode: "next_open" | "close"

    Returns:
        BacktestResult
    """
    n = len(close)
    if n < 30 or len(rule) != n:
        return BacktestResult(
            status="error",
            reason=f"length mismatch or too short: close={n}, rule={len(rule)}",
            style=style,
        )

    # 체결 가격 선택
    if exec_mode == "close":
        exec_price = close
    else:
        exec_price = open_ if open_ is not None else close

    base_cost = (fee_bps + slip_bps) / 1e4 / 2.0  # 한쪽

    # ADV impact (거래량 비례)
    def _impact_cost(t_idx: int) -> float:
        """t_idx 봉의 거래량 대비 진입 비율 → impact bps 추가."""
        if volume is None or capital_pct_of_adv <= 0 or t_idx >= len(volume):
            return 0.0
        # capital_pct_of_adv = 우리 진입 자본 / 평균 일거래량 (%)
        return (capital_pct_of_adv * impact_bps_per_pct) / 1e4 / 2.0

    # gap 가중 (open[t+1] vs close[t])
    def _gap_cost(t_idx: int) -> float:
        if open_ is None or t_idx + 1 >= n:
            return 0.0
        gap_pct = abs(open_[t_idx + 1] - close[t_idx]) / max(close[t_idx], 1e-9)
        if gap_pct >= GAP_THRESHOLD_PCT:
            return gap_pct * 0.5  # 갭의 50% 추가 슬리피지
        return 0.0

    # 포지션 시계열
    pos = np.zeros(n, dtype=np.int8)
    in_pos = False
    entry_idx = -1
    entry_price = 0.0
    trades: list[dict] = []

    # stop 시계열 (옵션)
    stop_series: np.ndarray | None = None
    if rule.stop and high is not None and low is not None:
        stop_series = _build_stop_series(close, high, low, rule.stop)

    for t in range(n - 1):
        # 청산 조건 체크 (홀딩 중일 때만)
        if in_pos:
            should_exit = bool(rule.exit_expr[t])
            stop_hit_intrabar = False
            stop_price_used = None

            # intrabar stop: 당일 low 가 stop 을 뚫었으면 stop 가격으로 체결
            if (
                stop_series is not None
                and not np.isnan(stop_series[t])
                and low is not None
                and low[t] <= stop_series[t]
            ):
                stop_hit_intrabar = True
                stop_price_used = float(stop_series[t])
                should_exit = True

            if should_exit:
                if stop_hit_intrabar and stop_price_used is not None:
                    # intrabar stop: 정확한 stop 가격 (다음 봉 아님)
                    exit_raw = stop_price_used
                    exit_t = t
                else:
                    # next-bar 시가 체결 (또는 close 모드)
                    exit_raw = exec_price[t + 1] if exec_mode != "close" else close[t]
                    exit_t = t + 1 if exec_mode != "close" else t
                cost = base_cost + _impact_cost(t) + _gap_cost(t)
                exit_price = exit_raw * (1 - cost)
                pnl = (exit_price - entry_price) / entry_price
                trades.append(
                    {
                        "entry_idx": entry_idx,
                        "exit_idx": exit_t,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "pnl": pnl,
                        "bars_held": exit_t - entry_idx,
                        "exit_reason": "stop" if stop_hit_intrabar else "signal",
                        "cost_bps": cost * 1e4 * 2,
                    }
                )
                in_pos = False
                pos[t + 1] = 0
                continue

        # 진입 조건 체크 (현금 상태에서만)
        if not in_pos and bool(rule.entry_expr[t]):
            entry_raw = exec_price[t + 1] if exec_mode != "close" else close[t]
            cost = base_cost + _impact_cost(t) + _gap_cost(t)
            entry_price = entry_raw * (1 + cost)
            entry_idx = t + 1 if exec_mode != "close" else t
            in_pos = True
            pos[t + 1] = 1
        else:
            pos[t + 1] = pos[t]

    # 마지막 봉 청산 (열린 포지션 강제 마감)
    if in_pos:
        cost = base_cost + _impact_cost(n - 1)
        exit_price = close[-1] * (1 - cost)
        pnl = (exit_price - entry_price) / entry_price
        trades.append(
            {
                "entry_idx": entry_idx,
                "exit_idx": n - 1,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "pnl": pnl,
                "bars_held": n - 1 - entry_idx,
                "exit_reason": "force_close",
                "cost_bps": cost * 1e4 * 2,
            }
        )

    # 일별 수익률 (포지션 기반)
    daily_ret = np.zeros(n, dtype=np.float64)
    for i in range(1, n):
        if pos[i] == 1:
            daily_ret[i] = (close[i] - close[i - 1]) / close[i - 1]
    equity = np.cumprod(1.0 + daily_ret)

    # trades DataFrame
    trades_df = (
        pl.DataFrame(trades)
        if trades
        else pl.DataFrame(
            schema={
                "entry_idx": pl.Int64,
                "exit_idx": pl.Int64,
                "entry_price": pl.Float64,
                "exit_price": pl.Float64,
                "pnl": pl.Float64,
                "bars_held": pl.Int64,
                "exit_reason": pl.Utf8,
                "cost_bps": pl.Float64,
            }
        )
    )

    pnls = np.array([t["pnl"] for t in trades], dtype=np.float64)

    sh = sharpe(daily_ret)
    so = sortino(daily_ret)
    md = mdd(equity)
    wr = winrate(pnls)
    pf = profitFactor(pnls)
    ex = expectancy(pnls)
    to = turnover(pos.astype(np.float64))
    expo = exposure(pos.astype(np.float64))
    ds = dsr(sh, daily_ret, n_trials=n_trials)

    period = (None, None)
    if dates and len(dates) >= 2:
        period = (dates[0], dates[-1])

    return BacktestResult(
        equity=equity,
        returns=daily_ret,
        positions=pos.astype(np.float64),
        trades=trades_df,
        sharpe=sh,
        sortino=so,
        mdd=md,
        winrate=wr,
        profitFactor=pf,
        expectancy=ex,
        turnover=to,
        exposure=expo,
        dsr=ds,
        style=style,
        period=period,
        oos=False,
    )


def _build_stop_series(close, high, low, stop_spec) -> np.ndarray:
    """rule.stop dict → 시계열 stop level."""
    method = stop_spec.get("method", "atr")
    kw = stop_spec.get("kwargs", {})
    if method == "atr":
        from dartlab.quant.signals import vAtrTrailingStop

        k = kw.get("k", 3.0)
        period = kw.get("period", 14)
        return vAtrTrailingStop(close, high, low, atrPeriod=period, multiplier=k)
    if method == "fixed_pct":
        pct = kw.get("pct", 0.05)
        return close * (1 - pct)
    return np.full(len(close), np.nan, dtype=np.float64)


# ── Walk-forward + CPCV ─────────────────────────────────────────────────────


def walkForward(
    close: np.ndarray,
    rule: Rule | None = None,
    *,
    train: int = 252,
    test: int = 63,
    step: int = 63,
    open_: np.ndarray | None = None,
    high: np.ndarray | None = None,
    low: np.ndarray | None = None,
    dates: list | None = None,
    style: str | None = None,
    fee_bps: float = DEFAULT_FEE_BPS,
    slip_bps: float = DEFAULT_SLIP_BPS,
    rule_factory=None,
) -> BacktestResult:
    """Walk-forward OOS 백테스트.

    Sliding window 로 train(IS) → test(OOS) 반복. test 구간 수익률만 누적해서
    OOS Sharpe/MDD/DSR 계산. PBO 는 segments 비교로 산출.

    Args:
        close: 가격 시계열
        rule: 정적 Rule (전체 시계열에 한 번 빌드 — 기존 동작). rule_factory 가
            우선 적용, rule 무시.
        rule_factory: ``Callable[[is_close: np.ndarray, oos_len: int], Rule]`` —
            fold 마다 IS 구간만 보고 fit, 반환 Rule 의 length 는 train+test.
            forecast 모델처럼 IS fit + OOS predict 패턴에 사용. None 이면 기존
            정적 rule 슬라이스 동작 유지 (backward compat).
        train: in-sample window 크기
        test: out-of-sample window 크기
        step: 다음 fold 시작 간격

    Returns:
        BacktestResult (oos=True, pbo 채워짐)

    Notes
    -----
    rule_factory 사용 예 (forecast 모델 OOS 검증):

    >>> def factory(is_close, oos_len):
    ...     # IS 에서 forecast 모델 fit, 다음 oos_len 일 entry/exit 예측
    ...     fcst = forecast_model.fit(is_close).predict(oos_len)
    ...     entry = np.zeros(len(is_close) + oos_len, dtype=bool)
    ...     entry[len(is_close):] = fcst > threshold  # OOS 만 entry
    ...     exit_ = np.zeros_like(entry)
    ...     return Rule(entry_expr=entry, exit_expr=exit_)
    ...
    >>> walkForward(close, rule=None, rule_factory=factory, train=252, test=63)
    """
    if rule is None and rule_factory is None:
        return BacktestResult(
            status="error",
            reason="rule 또는 rule_factory 중 하나 필수",
            style=style,
            oos=True,
        )

    n = len(close)
    if n < train + test:
        return BacktestResult(
            status="error",
            reason=f"insufficient data for walk-forward: n={n}, need {train + test}",
            style=style,
            oos=True,
        )

    is_sharpes: list[float] = []
    oos_sharpes: list[float] = []
    oos_returns_all: list[np.ndarray] = []
    refit_count = 0

    start = 0
    while start + train + test <= n:
        is_end = start + train
        oos_end = is_end + test
        is_close = close[start:is_end]
        oos_close = close[is_end:oos_end]

        if rule_factory is not None:
            # IS 마다 재학습 — Rule length 는 train+test 이어야 함 (IS+OOS 일관)
            try:
                fold_rule = rule_factory(is_close, test)
            except Exception as exc:  # noqa: BLE001
                return BacktestResult(
                    status="error",
                    reason=f"rule_factory 호출 실패 (fold start={start}): {type(exc).__name__}: {exc}",
                    style=style,
                    oos=True,
                )
            if not isinstance(fold_rule, Rule) or len(fold_rule) != train + test:
                return BacktestResult(
                    status="error",
                    reason=f"rule_factory 반환 Rule length 가 train+test ({train + test}) 와 불일치",
                    style=style,
                    oos=True,
                )
            refit_count += 1
            is_rule = Rule(
                entry_expr=fold_rule.entry_expr[:train],
                exit_expr=fold_rule.exit_expr[:train],
                sizing=fold_rule.sizing,
                stop=fold_rule.stop,
                meta=fold_rule.meta,
            )
            oos_rule = Rule(
                entry_expr=fold_rule.entry_expr[train:],
                exit_expr=fold_rule.exit_expr[train:],
                sizing=fold_rule.sizing,
                stop=fold_rule.stop,
                meta=fold_rule.meta,
            )
        else:
            # 정적 rule 슬라이스 (기존 동작)
            is_rule = Rule(
                entry_expr=rule.entry_expr[start:is_end],
                exit_expr=rule.exit_expr[start:is_end],
                sizing=rule.sizing,
                stop=rule.stop,
                meta=rule.meta,
            )
            oos_rule = Rule(
                entry_expr=rule.entry_expr[is_end:oos_end],
                exit_expr=rule.exit_expr[is_end:oos_end],
                sizing=rule.sizing,
                stop=rule.stop,
                meta=rule.meta,
            )

        is_bt = vectorBacktest(
            is_close,
            is_rule,
            open_=open_[start:is_end] if open_ is not None else None,
            high=high[start:is_end] if high is not None else None,
            low=low[start:is_end] if low is not None else None,
            fee_bps=fee_bps,
            slip_bps=slip_bps,
        )
        is_sharpes.append(is_bt.sharpe)

        oos_bt = vectorBacktest(
            oos_close,
            oos_rule,
            open_=open_[is_end:oos_end] if open_ is not None else None,
            high=high[is_end:oos_end] if high is not None else None,
            low=low[is_end:oos_end] if low is not None else None,
            fee_bps=fee_bps,
            slip_bps=slip_bps,
        )
        oos_sharpes.append(oos_bt.sharpe)
        oos_returns_all.append(oos_bt.returns)

        start += step

    if not oos_returns_all:
        return BacktestResult(
            status="error",
            reason="no walk-forward folds",
            style=style,
            oos=True,
        )

    aggregated_returns = np.concatenate(oos_returns_all)
    equity = np.cumprod(1.0 + aggregated_returns)

    sh = sharpe(aggregated_returns)
    so = sortino(aggregated_returns)
    md = mdd(equity)
    ds = dsr(sh, aggregated_returns, n_trials=len(oos_sharpes))

    # PBO: IS 가 [trial=1, segment=k], OOS 도 동일.
    # rule_factory path 에서는 IS region 이 보통 학습용 (entry/exit 모두 False) 이라
    # IS sharpe = 0 → IS vs OOS 비교 무의미 → PBO 1.0 은 가짜. None 으로 표시.
    if refit_count > 0:
        pbo_val = None
    else:
        is_mat = np.array([is_sharpes])
        oos_mat = np.array([oos_sharpes])
        pbo_val = pbo(is_mat, oos_mat)

    period = (None, None)
    if dates and len(dates) >= 2:
        period = (dates[0], dates[-1])

    return BacktestResult(
        equity=equity,
        returns=aggregated_returns,
        positions=np.array([], dtype=np.float64),
        trades=None,
        sharpe=sh,
        sortino=so,
        mdd=md,
        dsr=ds,
        pbo=pbo_val,
        style=style,
        period=period,
        oos=True,
        cpcv={
            "is_sharpes": is_sharpes,
            "oos_sharpes": oos_sharpes,
            "n_folds": len(oos_sharpes),
            "refit_count": refit_count,
        },
    )


def multiAssetBacktest(
    stock_codes: list[str],
    rule_builder,
    *,
    weighting: str = "equal",
    fee_bps: float = DEFAULT_FEE_BPS,
    slip_bps: float = DEFAULT_SLIP_BPS,
    style: str | None = None,
) -> BacktestResult:
    """멀티 종목 포트폴리오 백테스트.

    각 종목별 단일 백테스트 → 일별 수익률 → 가중 결합.

    Args:
        stock_codes: 종목 리스트 (예: ['005930', '000660', ...])
        rule_builder: callable(company) -> Rule (스타일 build 함수 또는 사용자 정의)
        weighting: "equal" | "inv_vol" | "risk_parity"
        fee_bps/slip_bps: 거래비용

    Returns:
        BacktestResult — 가중 결합 결과
    """
    from dataclasses import dataclass

    from dartlab.quant._helpers import fetchOhlcv, ohlcvToArrays

    if not stock_codes:
        return BacktestResult(status="error", reason="empty stock_codes", style=style)

    @dataclass
    class _Stub:
        stockCode: str

    # 1) 종목별 백테스트
    individual: dict[str, BacktestResult] = {}
    return_series: dict[str, np.ndarray] = {}
    min_len = float("inf")

    for code in stock_codes:
        ohlcv = fetchOhlcv(code)
        if isEmptyDf(ohlcv):
            continue
        arr = ohlcvToArrays(ohlcv)
        if "close" not in arr or len(arr["close"]) < 60:
            continue
        rule = rule_builder(_Stub(stockCode=code))
        if hasattr(rule, "status") and rule.status == "not_applicable":
            continue
        if not isinstance(rule, Rule):
            continue
        if len(rule) != len(arr["close"]):
            continue
        bt = vectorBacktest(
            arr["close"],
            rule,
            open_=arr.get("open"),
            high=arr.get("high"),
            low=arr.get("low"),
            volume=arr.get("volume"),
            fee_bps=fee_bps,
            slip_bps=slip_bps,
        )
        if bt.status != "ok":
            continue
        individual[code] = bt
        return_series[code] = bt.returns
        min_len = min(min_len, len(bt.returns))

    if not individual:
        return BacktestResult(status="error", reason="no valid backtests", style=style)

    # 2) 길이 정렬 (가장 짧은 종목 기준)
    min_len = int(min_len)
    aligned = np.zeros((len(return_series), min_len), dtype=np.float64)
    codes_ordered = list(return_series.keys())
    for i, code in enumerate(codes_ordered):
        r = return_series[code]
        aligned[i] = r[-min_len:]

    # 3) 가중치 계산
    n_assets = len(codes_ordered)
    if weighting == "equal":
        weights = np.full(n_assets, 1.0 / n_assets, dtype=np.float64)
    elif weighting == "inv_vol":
        vols = np.array([np.std(aligned[i]) for i in range(n_assets)])
        inv = 1.0 / np.maximum(vols, 1e-9)
        weights = inv / inv.sum()
    elif weighting == "risk_parity":
        # ERC 단순화: inv vol 기반 (full ERC 는 portfolio.py 호출)
        vols = np.array([np.std(aligned[i]) for i in range(n_assets)])
        inv = 1.0 / np.maximum(vols, 1e-9)
        weights = inv / inv.sum()
    else:
        return BacktestResult(status="error", reason=f"unknown weighting: {weighting}", style=style)

    # 4) 포트폴리오 일별 수익률
    portfolio_ret = (weights[:, None] * aligned).sum(axis=0)
    equity = np.cumprod(1.0 + portfolio_ret)

    # 5) 메트릭
    sh = sharpe(portfolio_ret)
    so = sortino(portfolio_ret)
    md = mdd(equity)
    ds = dsr(sh, portfolio_ret, n_trials=n_assets)

    # 모든 trades 합산
    all_trades_list = []
    for code, bt in individual.items():
        if bt.trades is not None and bt.trades.height > 0:
            tdf = bt.trades.with_columns(pl.lit(code).alias("stock_code"))
            all_trades_list.append(tdf)
    all_trades = pl.concat(all_trades_list) if all_trades_list else None

    return BacktestResult(
        equity=equity,
        returns=portfolio_ret,
        positions=np.array([], dtype=np.float64),
        trades=all_trades,
        sharpe=sh,
        sortino=so,
        mdd=md,
        winrate=winrate(
            np.array(
                [
                    t["pnl"]
                    for code in individual
                    for t in (individual[code].trades.to_dicts() if individual[code].trades is not None else [])
                ],
                dtype=np.float64,
            )
        )
        if individual
        else 0.0,
        dsr=ds,
        style=f"{style}_x{n_assets}" if style else f"multi_x{n_assets}",
        oos=False,
        cpcv={
            "n_assets": n_assets,
            "codes": codes_ordered,
            "weighting": weighting,
            "weights": weights.tolist(),
            "individual_sharpes": {c: float(individual[c].sharpe) for c in codes_ordered},
        },
    )


def cpcv(
    close: np.ndarray,
    rule: Rule,
    *,
    n_splits: int = 6,
    n_test: int = 2,
    embargo: int = 5,
    open_: np.ndarray | None = None,
    high: np.ndarray | None = None,
    low: np.ndarray | None = None,
    style: str | None = None,
) -> BacktestResult:
    """Combinatorial Purged Cross-Validation 백테스트 (Lopez AFML).

    n_splits 개 그룹 → n_test 개 조합 모두 test. 각 조합의 OOS Sharpe 평균 + DSR.

    Args:
        n_splits: 분할 수
        n_test: test 그룹 수
        embargo: test 양 끝 purge 관측치

    Returns:
        BacktestResult (oos=True, cpcv 메타 채워짐)
    """
    n = len(close)
    fold_sharpes: list[float] = []
    fold_returns: list[np.ndarray] = []

    for train_idx, test_idx in cpcvSplits(n, n_splits, n_test, embargo):
        if len(test_idx) < 30:
            continue
        sub_close = close[test_idx]
        sub_rule = Rule(
            entry_expr=rule.entry_expr[test_idx],
            exit_expr=rule.exit_expr[test_idx],
            sizing=rule.sizing,
            stop=rule.stop,
            meta=rule.meta,
        )
        sub_bt = vectorBacktest(
            sub_close,
            sub_rule,
            open_=open_[test_idx] if open_ is not None else None,
            high=high[test_idx] if high is not None else None,
            low=low[test_idx] if low is not None else None,
        )
        fold_sharpes.append(sub_bt.sharpe)
        fold_returns.append(sub_bt.returns)

    if not fold_returns:
        return BacktestResult(status="error", reason="no cpcv folds", style=style, oos=True)

    aggregated = np.concatenate(fold_returns)
    equity = np.cumprod(1.0 + aggregated)
    sh = sharpe(aggregated)
    md = mdd(equity)
    ds = dsr(sh, aggregated, n_trials=len(fold_sharpes))

    return BacktestResult(
        equity=equity,
        returns=aggregated,
        positions=np.array([], dtype=np.float64),
        trades=None,
        sharpe=sh,
        sortino=sortino(aggregated),
        mdd=md,
        dsr=ds,
        style=style,
        oos=True,
        cpcv={"fold_sharpes": fold_sharpes, "n_folds": len(fold_sharpes), "n_splits": n_splits, "n_test": n_test},
    )


# ── Deprecated snake_case aliases ────────────────────────
from dartlab.quant._helpers import _deprecatedAlias as _dep

walk_forward = _dep(walkForward, "walk_forward")
vector_backtest = _dep(vectorBacktest, "vector_backtest")
multi_asset_backtest = _dep(multiAssetBacktest, "multi_asset_backtest")
