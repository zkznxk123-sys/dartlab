"""dartlab.gather.transforms.pit 단위 테스트 — as-of 필터 + bitemporal 감지."""

from __future__ import annotations

import importlib
from datetime import date

import polars as pl
import pytest

from dartlab.gather.transforms.pit import applyAsOf, hasBitemporal

pytestmark = pytest.mark.unit


def test_smoke_import() -> None:
    importlib.import_module("dartlab.gather.transforms.pit")


def test_applyAsOf_none_returns_input() -> None:
    """asof=None → 원본 그대로."""
    df = pl.DataFrame({"date": [date(2024, 1, 1)], "value": [100.0]})
    out = applyAsOf(df, None)
    assert out.equals(df)


def test_applyAsOf_empty_df_returns_empty() -> None:
    df = pl.DataFrame()
    out = applyAsOf(df, "2024-12-31")
    assert out.is_empty()


def test_applyAsOf_fallback_date_column() -> None:
    """bitemporal 없으면 date 컬럼 필터."""
    df = pl.DataFrame(
        {
            "date": [date(2024, 1, 1), date(2024, 6, 1), date(2024, 12, 31)],
            "value": [10.0, 20.0, 30.0],
        }
    )
    out = applyAsOf(df, "2024-06-30")
    assert out.height == 2
    assert out["value"].to_list() == [10.0, 20.0]


def test_applyAsOf_bitemporal_both_columns() -> None:
    """business_time + knowledge_time 둘 다 ≤ asof."""
    df = pl.DataFrame(
        {
            "business_time": [date(2024, 1, 1), date(2024, 6, 1), date(2024, 12, 31)],
            "knowledge_time": [date(2024, 1, 2), date(2024, 6, 5), date(2025, 1, 5)],
            "value": [10.0, 20.0, 30.0],
        }
    )
    # asof=2024-12-31 — 3 번째 row 의 knowledge_time(2025-01-05) > asof → 제외
    out = applyAsOf(df, "2024-12-31")
    assert out.height == 2
    assert out["value"].to_list() == [10.0, 20.0]


def test_applyAsOf_bitemporal_restatement_excluded() -> None:
    """정정공시 restatement — 옛 시점에는 모르던 row 제외."""
    df = pl.DataFrame(
        {
            "business_time": [date(2024, 1, 1), date(2024, 1, 1)],
            "knowledge_time": [date(2024, 1, 2), date(2024, 12, 31)],  # 첫 보고 + 정정
            "value": [100.0, 110.0],  # 정정값
        }
    )
    # asof=2024-06-30 — 정정 (knowledge_time 2024-12-31) 모름 → 첫 보고만
    out = applyAsOf(df, "2024-06-30")
    assert out.height == 1
    assert out["value"][0] == 100.0


def test_applyAsOf_business_only_no_knowledge() -> None:
    """business_time 만 있고 knowledge_time 없으면 business 만 필터."""
    df = pl.DataFrame(
        {
            "business_time": [date(2024, 1, 1), date(2024, 6, 1)],
            "value": [10.0, 20.0],
        }
    )
    out = applyAsOf(df, "2024-03-01")
    assert out.height == 1
    assert out["value"][0] == 10.0


def test_applyAsOf_no_time_columns_returns_original() -> None:
    """date/business_time 모두 없으면 원본 반환 (logger.debug)."""
    df = pl.DataFrame({"foo": [1, 2, 3]})
    out = applyAsOf(df, "2024-12-31")
    assert out.equals(df)


def test_hasBitemporal_true() -> None:
    df = pl.DataFrame({"business_time": [date(2024, 1, 1)], "knowledge_time": [date(2024, 1, 2)], "value": [10.0]})
    assert hasBitemporal(df) is True


def test_hasBitemporal_false_only_date() -> None:
    df = pl.DataFrame({"date": [date(2024, 1, 1)], "value": [10.0]})
    assert hasBitemporal(df) is False


def test_hasBitemporal_false_only_business() -> None:
    df = pl.DataFrame({"business_time": [date(2024, 1, 1)], "value": [10.0]})
    assert hasBitemporal(df) is False


def test_hasBitemporal_none() -> None:
    assert hasBitemporal(None) is False
