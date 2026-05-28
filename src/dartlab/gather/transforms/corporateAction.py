"""Corporate Action SSOT — 분할/배당/합병/스핀오프 adjustment factor.

기존 ``transforms/adjustPrice.py`` 의 Stage 1 (가격 기반 자동 감지, 분할/무상만)
을 보완 — Stage 2 = *명시적* event 리스트 기반 누적 factor 계산.
DART 공시 + Yahoo dividends 등 외부 source 가 채우는 SSOT 인터페이스.

PIT 친화 — ``asof`` 이전 event 만 사용 → backtest look-ahead bias 0.

```python
events = [
    CorporateActionEvent(ticker="005930", effective_date=date(2018, 5, 4),
                         action_type="split", ratio=50.0, source="dart"),
]
adj = buildAdjustmentSeries(events)
prices_adjusted = adjustPrice(prices_df, events, asof="2020-12-31")
```
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date as _date

import polars as pl

log = logging.getLogger(__name__)

# 지원 action_type. 새 유형 추가 시 본 set 에만.
SUPPORTED_ACTIONS: frozenset[str] = frozenset({"split", "dividend", "merger", "spinoff"})


@dataclass(frozen=True, slots=True)
class CorporateActionEvent:
    """단일 corporate action — 명시적 SSOT 1 entry.

    Attributes:
        ticker: 종목 코드.
        effective_date: 적용 시작일 (예: 분할 ex-date, 배당락일).
        action_type: ``"split"``/``"dividend"``/``"merger"``/``"spinoff"``.
        ratio: split 비율 (예: 50.0 = 50:1 분할) 또는 배당금 (예: 700.0 원/주).
        source: ``"dart"``/``"yahoo"``/``"manual"`` — 출처 추적.
    """

    ticker: str
    effective_date: _date
    action_type: str
    ratio: float
    source: str = "manual"


def buildAdjustmentSeries(
    events: list[CorporateActionEvent],
    *,
    asof: str | _date | None = None,
) -> pl.DataFrame:
    """events 리스트 → ``(ticker, effective_date, cumulative_factor)`` DataFrame.

    Sig: ``buildAdjustmentSeries(events, *, asof=None) -> pl.DataFrame``

    Capabilities: split/dividend 누적 factor 계산 + asof 이전 events 만 사용.
    AIContext: PIT 친화 SSOT — backtest 의 adjustment factor 단일 진입.
    Guide: split ratio R = 분할비. 가격 조정 factor = 1/R. dividend 는 (close - div) / close 비율.
    When: 가격 시계열 조정 직전 (adjustPrice 의 입력).
    How: events 필터 (effective_date ≤ asof) → 종목별 sort → 누적 곱.

    Args:
        events: CorporateActionEvent 리스트. 빈 리스트 가능.
        asof: 이 시점까지 *알려진* event 만 사용. None 이면 전체.

    Returns:
        DataFrame schema:
            - ``ticker`` : pl.Utf8
            - ``effective_date`` : pl.Date
            - ``action_type`` : pl.Utf8
            - ``ratio`` : pl.Float64 — 본 event 의 비율/금액
            - ``factor`` : pl.Float64 — 본 event 단독 조정 계수 (split 1/ratio, dividend 1.0 placeholder)
            - ``cumulative_factor`` : pl.Float64 — 종목별 시간 누적 곱

    Raises:
        ValueError: 미지원 action_type.

    Example:
        >>> buildAdjustmentSeries([CorporateActionEvent("005930", date(2018, 5, 4), "split", 50.0)])

    See Also:
        ``adjustPrice`` — 본 series 를 가격에 적용.
        ``transforms/adjustPrice.detectEventsFromPrices`` — Stage 1 (가격 기반 자동 감지).
    """
    if not events:
        return pl.DataFrame(
            schema={
                "ticker": pl.Utf8,
                "effective_date": pl.Date,
                "action_type": pl.Utf8,
                "ratio": pl.Float64,
                "factor": pl.Float64,
                "cumulative_factor": pl.Float64,
            }
        )

    cutoff = _coerceDate(asof) if asof is not None else None

    rows: list[dict] = []
    for ev in events:
        if ev.action_type not in SUPPORTED_ACTIONS:
            raise ValueError(f"미지원 action_type: '{ev.action_type}'. 가능: {sorted(SUPPORTED_ACTIONS)}")
        if cutoff is not None and ev.effective_date > cutoff:
            continue
        factor = _eventFactor(ev)
        rows.append(
            {
                "ticker": ev.ticker,
                "effective_date": ev.effective_date,
                "action_type": ev.action_type,
                "ratio": float(ev.ratio),
                "factor": factor,
            }
        )

    if not rows:
        return pl.DataFrame(
            schema={
                "ticker": pl.Utf8,
                "effective_date": pl.Date,
                "action_type": pl.Utf8,
                "ratio": pl.Float64,
                "factor": pl.Float64,
                "cumulative_factor": pl.Float64,
            }
        )

    df = pl.DataFrame(rows).sort(["ticker", "effective_date"])
    df = df.with_columns(
        pl.col("factor").cum_prod().over("ticker").alias("cumulative_factor"),
    )
    return df


def adjustPrice(
    df: pl.DataFrame,
    events: list[CorporateActionEvent],
    *,
    asof: str | _date | None = None,
    priceCol: str = "close",
    dateCol: str = "date",
    tickerCol: str = "ticker",
) -> pl.DataFrame:
    """df 에 누적 adjustment factor 곱 적용 — split-adjusted close 반환.

    Sig: ``adjustPrice(df, events, *, asof=None, priceCol='close', dateCol='date', tickerCol='ticker') -> pl.DataFrame``

    Capabilities: 종목별 events factor 누적 → date 기준 lookup → priceCol × factor.
    AIContext: 백테스트 진입 가격 정규화 — 분할 전후 가격 비교 가능.
    Guide: df 에 ticker 컬럼 없으면 events[0].ticker 가정 (단일 종목).
    When: 가격 시계열 backtest 직전.
    How: buildAdjustmentSeries 호출 → date 기준 inner join (as-of) → multiply.

    Args:
        df: 가격 시계열 (date + close + 옵션 ticker).
        events: CorporateActionEvent 리스트.
        asof: PIT 컷오프.
        priceCol: 조정할 가격 컬럼 (기본 ``"close"``).
        dateCol: 날짜 컬럼 (기본 ``"date"``).
        tickerCol: 종목 컬럼 (기본 ``"ticker"``, 없으면 events 의 ticker 사용).

    Returns:
        조정된 DataFrame. priceCol 가 in-place 갱신 + ``"adjustment_factor"`` 컬럼 추가.

    Raises:
        ValueError: priceCol/dateCol 미존재.

    Example:
        >>> adjustPrice(prices, events, asof="2020-12-31")

    See Also:
        ``buildAdjustmentSeries``.
    """
    if df is None or df.is_empty():
        return df
    if priceCol not in df.columns:
        raise ValueError(f"priceCol '{priceCol}' df 컬럼에 없음: {df.columns}")
    if dateCol not in df.columns:
        raise ValueError(f"dateCol '{dateCol}' df 컬럼에 없음: {df.columns}")

    adj_series = buildAdjustmentSeries(events, asof=asof)
    if adj_series.is_empty():
        return df.with_columns(pl.lit(1.0).alias("adjustment_factor"))

    # 종목별로 effective_date 이전 가격에 cumulative_factor 적용.
    # 단순화: events 의 마지막 (최신) cumulative_factor 를 그 시점 이전 모든 가격에 적용.
    # (각 event ex-date 직전까지 곱) → as-of join 패턴.
    if tickerCol not in df.columns:
        if not events:
            return df.with_columns(pl.lit(1.0).alias("adjustment_factor"))
        df = df.with_columns(pl.lit(events[0].ticker).alias(tickerCol))

    # adj_series 를 ticker 별 (effective_date desc) backward fill 패턴으로 lookup.
    df_sorted = df.sort([tickerCol, dateCol])
    adj_sorted = adj_series.sort([tickerCol, "effective_date"])

    joined = df_sorted.join_asof(
        adj_sorted.select([tickerCol, "effective_date", "cumulative_factor"]),
        left_on=dateCol,
        right_on="effective_date",
        by=tickerCol,
        strategy="forward",
    )
    joined = joined.with_columns(
        pl.col("cumulative_factor").fill_null(1.0).alias("adjustment_factor"),
        (pl.col(priceCol) * pl.col("cumulative_factor").fill_null(1.0)).alias(priceCol),
    ).drop(["effective_date", "cumulative_factor"], strict=False)
    return joined


def _eventFactor(ev: CorporateActionEvent) -> float:
    """event 1 회의 가격 조정 계수 (split 1/ratio, 그 외 1.0 placeholder)."""
    if ev.action_type == "split":
        if ev.ratio <= 0:
            return 1.0
        return 1.0 / ev.ratio
    # dividend/merger/spinoff 의 정밀 factor 는 후속 PR (close 비율 필요).
    return 1.0


def _coerceDate(value: str | _date) -> _date:
    """str ISO → date. date 이면 그대로."""
    if isinstance(value, _date):
        return value
    return _date.fromisoformat(str(value)[:10])
