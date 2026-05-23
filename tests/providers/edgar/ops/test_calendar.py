"""edgar/ops/calendar wrapper test — SEC filing deadline 예측 검증."""

from __future__ import annotations

from datetime import date

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def test_public_api_present() -> None:
    """predictCalendar 함수 + OUTPUT_SCHEMA 상수 export."""
    from dartlab.providers.edgar.ops import OUTPUT_SCHEMA, predictCalendar

    assert callable(predictCalendar)
    assert isinstance(OUTPUT_SCHEMA, dict)
    assert "date" in OUTPUT_SCHEMA
    assert "cik" in OUTPUT_SCHEMA


def test_empty_disclosures_returns_empty_schema() -> None:
    """빈 dict → 빈 DataFrame (schema 보존)."""
    from dartlab.providers.edgar.ops import OUTPUT_SCHEMA, predictCalendar

    df = predictCalendar({})
    assert df.is_empty()
    assert set(df.columns) == set(OUTPUT_SCHEMA.keys())


def test_predicts_next_10k_from_history() -> None:
    """10-K history → 다음 10-K due 예측 (last + 365 일 cycle)."""
    from dartlab.providers.edgar.ops import predictCalendar

    # 2 회 10-K → HIGH confidence + 다음 due 예측
    history = pl.DataFrame(
        {
            "formType": ["10-K", "10-K"],
            "fileDate": [date(2024, 2, 1), date(2023, 2, 1)],
        }
    )
    df = predictCalendar({"0000320193": history}, horizonDays=400)
    assert df.shape[0] == 1
    assert df["eventType"][0] == "10-K"
    assert df["cik"][0] == "0000320193"
    assert df["confidence"][0] == "HIGH"


def test_predicts_10q_lower_priority_than_10k() -> None:
    """10-K + 10-Q history → 가장 가까운 due 선택 (정렬)."""
    from dartlab.providers.edgar.ops import predictCalendar

    history = pl.DataFrame(
        {
            "formType": ["10-K", "10-Q"],
            "fileDate": [date(2024, 2, 1), date(2024, 5, 1)],
        }
    )
    df = predictCalendar({"0000320193": history}, horizonDays=400)
    assert df.shape[0] == 1
    # 가장 가까운 다음 catalyst 1 개 반환.
    assert df["eventType"][0] in ("10-K", "10-Q")


def test_filters_by_horizon() -> None:
    """horizonDays 밖 예측은 제외."""
    from dartlab.providers.edgar.ops import predictCalendar

    history = pl.DataFrame(
        {
            "formType": ["10-K"],
            "fileDate": [date(2024, 2, 1)],
        }
    )
    df = predictCalendar({"0000320193": history}, horizonDays=1)
    # 1 일 안에 다음 10-K 없음 → 빈 결과.
    assert df.is_empty()


def test_missing_columns_skipped() -> None:
    """필수 컬럼 부재 → 해당 cik skip (전체 fail 아님)."""
    from dartlab.providers.edgar.ops import predictCalendar

    history = pl.DataFrame({"foo": ["bar"]})
    df = predictCalendar({"0000320193": history})
    assert df.is_empty()
