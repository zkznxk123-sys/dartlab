"""Vectorized backtest 엔진 — long-only, next-bar 시가 체결.

numpy/polars 만 사용. vectorbt/zipline/backtrader 의존 0.

처리:
    - entry/exit boolean 시계열 → trades(entry_idx, exit_idx, pnl)
    - 다음 봉 시가 체결, 수수료 15bp, 슬리피지 5bp
    - sizing/stop 은 Rule 에 명시된 경우만 적용
    - position 1/0 (long-only v1)

출력: BacktestResult dataclass — equity/returns/trades/sharpe/sortino/mdd/dsr/.../

walk_forward + cpcv 로 OOS Sharpe + DSR + PBO 산출 가능.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

import numpy as np
import polars as pl

from .metrics import (
    cpcv_splits,
    dsr,
    expectancy,
    exposure,
    mdd,
    pbo,
    profit_factor,
    sharpe,
    sortino,
    turnover,
    winrate,
)
from .rule import Rule

# 체결/비용 상수
DEFAULT_FEE_BPS = 15.0  # 양방향 합산 (진입 + 청산)
DEFAULT_SLIP_BPS = 5.0


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
    profit_factor: float = 0.0
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

    # NotApplicable sentinel (KR-only style on US)
    status: str = "ok"  # "ok" | "not_applicable" | "error"
    reason: str | None = None

    def __repr__(self) -> str:
        if self.status != "ok":
            return f"BacktestResult(status={self.status!r}, reason={self.reason!r})"
        return (
            f"BacktestResult(style={self.style}, sharpe={self.sharpe:+.2f}, "
            f"mdd={self.mdd*100:+.1f}%, dsr={self.dsr:.2f}, "
            f"trades={self.trades.height if self.trades is not None else 0}, "
            f"oos={self.oos})"
        )

    @classmethod
    def not_applicable(cls, *, style: str, reason: str) -> "BacktestResult":
        """KR-only 스타일을 US 에서 호출 시 sentinel."""
        return cls(status="not_applicable", reason=reason, style=style)


# ── 핵심 백테스트 ───────────────────────────────────────────────────────────


def vector_backtest(
    close: np.ndarray,
    rule: Rule,
    *,
    open_: np.ndarray | None = None,
    high: np.ndarray | None = None,
    low: np.ndarray | None = None,
    dates: list | None = None,
    fee_bps: float = DEFAULT_FEE_BPS,
    slip_bps: float = DEFAULT_SLIP_BPS,
    style: str | None = None,
    n_trials: int = 1,
) -> BacktestResult:
    """단일 룰 백테스트 — long-only, next-bar 시가 체결.

    Args:
        close: 일별 종가 (NDArray[float64])
        rule: Rule 객체 (entry_expr, exit_expr, sizing, stop)
        open_, high, low: optional, 다음 봉 시가 체결 / ATR stop 용
        dates: optional, period 메타 정보
        fee_bps: 양방향 수수료 (basis points)
        slip_bps: 진입/청산 슬리피지
        style: 스타일 식별자 (BacktestResult.style 에 기록)
        n_trials: DSR 정정용 시도 횟수

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

    # next-bar 시가 체결: entry[t] 가 True 면 t+1 시가에 체결
    exec_price = open_ if open_ is not None else close
    cost_per_side = (fee_bps + slip_bps) / 1e4 / 2.0  # 한쪽

    # 포지션 시계열 (1=홀딩, 0=현금)
    pos = np.zeros(n, dtype=np.int8)
    in_pos = False
    entry_idx = -1
    entry_price = 0.0
    trades: list[dict] = []

    # ATR stop 시계열 (옵션)
    stop_series: np.ndarray | None = None
    if rule.stop and high is not None and low is not None:
        stop_series = _build_stop_series(close, high, low, rule.stop)

    for t in range(n - 1):
        # 청산 조건 체크 (홀딩 중일 때만)
        if in_pos:
            should_exit = bool(rule.exit_expr[t])
            # stop 도달
            if stop_series is not None and not np.isnan(stop_series[t]) and close[t] <= stop_series[t]:
                should_exit = True
            if should_exit:
                exit_price = exec_price[t + 1] * (1 - cost_per_side)
                pnl = (exit_price - entry_price) / entry_price
                trades.append(
                    {
                        "entry_idx": entry_idx,
                        "exit_idx": t + 1,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "pnl": pnl,
                        "bars_held": t + 1 - entry_idx,
                    }
                )
                in_pos = False
                pos[t + 1] = 0
                continue

        # 진입 조건 체크 (현금 상태에서만)
        if not in_pos and bool(rule.entry_expr[t]):
            entry_price = exec_price[t + 1] * (1 + cost_per_side)
            entry_idx = t + 1
            in_pos = True
            pos[t + 1] = 1
        else:
            pos[t + 1] = pos[t]

    # 마지막 봉 청산 (열린 포지션 강제 마감)
    if in_pos:
        exit_price = close[-1] * (1 - cost_per_side)
        pnl = (exit_price - entry_price) / entry_price
        trades.append(
            {
                "entry_idx": entry_idx,
                "exit_idx": n - 1,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "pnl": pnl,
                "bars_held": n - 1 - entry_idx,
            }
        )

    # 일별 수익률 (포지션 기반)
    daily_ret = np.zeros(n, dtype=np.float64)
    for i in range(1, n):
        if pos[i] == 1:
            daily_ret[i] = (close[i] - close[i - 1]) / close[i - 1]
    equity = np.cumprod(1.0 + daily_ret)

    # trades DataFrame
    trades_df = pl.DataFrame(trades) if trades else pl.DataFrame(
        schema={
            "entry_idx": pl.Int64,
            "exit_idx": pl.Int64,
            "entry_price": pl.Float64,
            "exit_price": pl.Float64,
            "pnl": pl.Float64,
            "bars_held": pl.Int64,
        }
    )

    pnls = np.array([t["pnl"] for t in trades], dtype=np.float64)

    sh = sharpe(daily_ret)
    so = sortino(daily_ret)
    md = mdd(equity)
    wr = winrate(pnls)
    pf = profit_factor(pnls)
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
        profit_factor=pf,
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


def walk_forward(
    close: np.ndarray,
    rule: Rule,
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
) -> BacktestResult:
    """Walk-forward OOS 백테스트.

    Sliding window 로 train(IS) → test(OOS) 반복. test 구간 수익률만 누적해서
    OOS Sharpe/MDD/DSR 계산. PBO 는 segments 비교로 산출.

    Args:
        close, rule: vector_backtest 와 동일
        train: in-sample window 크기
        test: out-of-sample window 크기
        step: 다음 fold 시작 간격

    Returns:
        BacktestResult (oos=True, pbo 채워짐)
    """
    n = len(close)
    if n < train + test:
        return BacktestResult(
            status="error",
            reason=f"insufficient data for walk-forward: n={n}, need {train+test}",
            style=style,
            oos=True,
        )

    is_sharpes: list[float] = []
    oos_sharpes: list[float] = []
    oos_returns_all: list[np.ndarray] = []

    start = 0
    while start + train + test <= n:
        is_end = start + train
        oos_end = is_end + test

        # IS 구간
        is_close = close[start:is_end]
        is_rule = Rule(
            entry_expr=rule.entry_expr[start:is_end],
            exit_expr=rule.exit_expr[start:is_end],
            sizing=rule.sizing,
            stop=rule.stop,
            meta=rule.meta,
        )
        is_bt = vector_backtest(
            is_close,
            is_rule,
            open_=open_[start:is_end] if open_ is not None else None,
            high=high[start:is_end] if high is not None else None,
            low=low[start:is_end] if low is not None else None,
            fee_bps=fee_bps,
            slip_bps=slip_bps,
        )
        is_sharpes.append(is_bt.sharpe)

        # OOS 구간
        oos_close = close[is_end:oos_end]
        oos_rule = Rule(
            entry_expr=rule.entry_expr[is_end:oos_end],
            exit_expr=rule.exit_expr[is_end:oos_end],
            sizing=rule.sizing,
            stop=rule.stop,
            meta=rule.meta,
        )
        oos_bt = vector_backtest(
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

    # PBO: IS 가 [trial=1, segment=k], OOS 도 동일
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
        cpcv={"is_sharpes": is_sharpes, "oos_sharpes": oos_sharpes, "n_folds": len(oos_sharpes)},
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

    for train_idx, test_idx in cpcv_splits(n, n_splits, n_test, embargo):
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
        sub_bt = vector_backtest(
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
