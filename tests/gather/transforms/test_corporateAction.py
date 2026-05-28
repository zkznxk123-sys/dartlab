"""dartlab.gather.transforms.corporateAction 단위 테스트.

CorporateActionEvent + buildAdjustmentSeries + adjustPrice 핵심 분기.
"""

from __future__ import annotations

import importlib
from datetime import date

import polars as pl
import pytest

from dartlab.gather.transforms.corporateAction import (
    SUPPORTED_ACTIONS,
    CorporateActionEvent,
    adjustPrice,
    buildAdjustmentSeries,
)

pytestmark = pytest.mark.unit


def test_smoke_import() -> None:
    importlib.import_module("dartlab.gather.transforms.corporateAction")


def test_SUPPORTED_ACTIONS_4_types() -> None:
    assert SUPPORTED_ACTIONS == frozenset({"split", "dividend", "merger", "spinoff"})


def test_buildAdjustmentSeries_empty_events() -> None:
    """빈 events → 빈 DataFrame (schema 보존)."""
    df = buildAdjustmentSeries([])
    assert df.is_empty()
    assert "cumulative_factor" in df.schema
    assert df.schema["cumulative_factor"] == pl.Float64


def test_buildAdjustmentSeries_single_split() -> None:
    """50:1 분할 단일 → factor 0.02 + cumulative 0.02."""
    events = [
        CorporateActionEvent("005930", date(2018, 5, 4), "split", 50.0, "dart"),
    ]
    df = buildAdjustmentSeries(events)
    assert df.height == 1
    assert df["factor"][0] == pytest.approx(0.02)
    assert df["cumulative_factor"][0] == pytest.approx(0.02)


def test_buildAdjustmentSeries_multiple_splits_cumulative() -> None:
    """동일 종목 분할 2 회 — cumulative_factor = 누적 곱."""
    events = [
        CorporateActionEvent("AAPL", date(2014, 6, 9), "split", 7.0),
        CorporateActionEvent("AAPL", date(2020, 8, 31), "split", 4.0),
    ]
    df = buildAdjustmentSeries(events)
    assert df.height == 2
    # 첫 분할 factor = 1/7, 둘째 = 1/4 → 누적 1/28
    assert df["cumulative_factor"][0] == pytest.approx(1 / 7)
    assert df["cumulative_factor"][1] == pytest.approx(1 / 28)


def test_buildAdjustmentSeries_asof_excludes_future_events() -> None:
    """asof=2018-01-01 → 2018-05-04 이벤트 제외."""
    events = [
        CorporateActionEvent("005930", date(2018, 5, 4), "split", 50.0),
    ]
    df = buildAdjustmentSeries(events, asof="2018-01-01")
    assert df.is_empty()


def test_buildAdjustmentSeries_unsupported_action_raises() -> None:
    events = [
        CorporateActionEvent("X", date(2024, 1, 1), "rights_issue", 1.0),
    ]
    with pytest.raises(ValueError, match="미지원 action_type"):
        buildAdjustmentSeries(events)


def test_buildAdjustmentSeries_dividend_factor_placeholder() -> None:
    """배당 event factor 는 현재 1.0 (후속 PR 에서 close 비율로)."""
    events = [
        CorporateActionEvent("005930", date(2024, 4, 1), "dividend", 700.0, "yahoo"),
    ]
    df = buildAdjustmentSeries(events)
    assert df["factor"][0] == 1.0


def test_adjustPrice_single_ticker_split() -> None:
    """단일 종목 분할 — 분할 전 가격에 1/ratio 적용."""
    prices = pl.DataFrame(
        {
            "date": [date(2018, 1, 1), date(2018, 5, 4), date(2018, 6, 1)],
            "close": [2_500_000.0, 50_000.0, 51_000.0],
        }
    )
    events = [
        CorporateActionEvent("005930", date(2018, 5, 4), "split", 50.0),
    ]
    out = adjustPrice(prices, events)
    # 분할 ex-date 이전 가격은 1/50 (= 0.02) 적용 → 50,000 으로 정규화
    assert "adjustment_factor" in out.columns
    # forward join — 2018-01-01 → 다가오는 split 의 cumulative 0.02 적용
    row_jan = out.filter(pl.col("date") == date(2018, 1, 1)).row(0, named=True)
    assert row_jan["close"] == pytest.approx(50_000.0)
    # 분할 이후 → factor 없음 → 원본 유지
    row_jun = out.filter(pl.col("date") == date(2018, 6, 1)).row(0, named=True)
    assert row_jun["close"] == pytest.approx(51_000.0)


def test_adjustPrice_empty_df() -> None:
    out = adjustPrice(pl.DataFrame(), [])
    assert out.is_empty()


def test_adjustPrice_no_events_returns_with_factor_1() -> None:
    prices = pl.DataFrame({"date": [date(2024, 1, 1)], "close": [100.0]})
    out = adjustPrice(prices, [])
    assert out["adjustment_factor"][0] == 1.0
    assert out["close"][0] == 100.0


def test_adjustPrice_missing_priceCol_raises() -> None:
    prices = pl.DataFrame({"date": [date(2024, 1, 1)], "foo": [100.0]})
    with pytest.raises(ValueError, match="priceCol"):
        adjustPrice(prices, [], priceCol="close")
