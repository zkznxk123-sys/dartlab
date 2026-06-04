"""회귀 가드 — Company.panel(asOf=) 가 미래 fiscal period 컬럼 drop.

Look-ahead bias 방지 — 백테스트 / 과거 시점 분석 재현 시 미래 정보 누설 차단.
TauricResearch/TradingAgents stockstats_utils.filter_financials_by_date 패턴 차용.
"""

from __future__ import annotations

import polars as pl
import pytest


@pytest.mark.unit
def test_dart_filter_period_columns_by_asof_q1_drops_q2_q3_q4() -> None:
    from dartlab.providers.dart.company import _filterPeriodColumnsByAsOf

    df = pl.DataFrame(
        {
            "snakeId": ["total_assets", "revenue"],
            "항목": ["자산총계", "매출액"],
            "2024Q1": [100.0, 50.0],
            "2024Q2": [110.0, 55.0],
            "2024Q3": [120.0, 60.0],
            "2024Q4": [130.0, 65.0],
            "2023": [90.0, 45.0],
        }
    )
    filtered = _filterPeriodColumnsByAsOf(df, "2024Q1")
    assert "2024Q1" in filtered.columns
    assert "2023" in filtered.columns
    assert "2024Q2" not in filtered.columns
    assert "2024Q3" not in filtered.columns
    assert "2024Q4" not in filtered.columns
    # metadata 컬럼은 유지
    assert "snakeId" in filtered.columns
    assert "항목" in filtered.columns


@pytest.mark.unit
def test_dart_filter_period_columns_by_asof_iso_date_2024_03_31() -> None:
    """ISO date YYYY-MM-DD 도 받아야 함 — 분기 변환."""
    from dartlab.providers.dart.company import _filterPeriodColumnsByAsOf

    df = pl.DataFrame(
        {
            "snakeId": ["x"],
            "2024Q1": [1.0],
            "2024Q2": [2.0],
            "2024Q4": [4.0],
        }
    )
    filtered = _filterPeriodColumnsByAsOf(df, "2024-03-31")
    assert "2024Q1" in filtered.columns
    assert "2024Q2" not in filtered.columns
    assert "2024Q4" not in filtered.columns


@pytest.mark.unit
def test_dart_filter_period_columns_unparseable_asof_passthrough() -> None:
    from dartlab.providers.dart.company import _filterPeriodColumnsByAsOf

    df = pl.DataFrame({"snakeId": ["x"], "2024Q1": [1.0]})
    # 미인식 asOf → 원본 그대로 (drop X — 안전)
    filtered = _filterPeriodColumnsByAsOf(df, "garbage")
    assert "2024Q1" in filtered.columns


@pytest.mark.unit
def test_edgar_filter_period_columns_by_asof_2023() -> None:
    """EDGAR 는 분기 컬럼 + 연간 컬럼 (예: 2024Q3, 2023, 2022). 2023 시점 → 2024 컬럼 drop."""
    from dartlab.providers.edgar.company import _filterPeriodColumnsByAsOf

    df = pl.DataFrame(
        {
            "account": ["total_assets"],
            "2024Q3": [110.0],
            "2024": [115.0],
            "2023Q3": [100.0],
            "2023": [105.0],
            "2022": [90.0],
        }
    )
    filtered = _filterPeriodColumnsByAsOf(df, "2023")
    assert "2023" in filtered.columns
    assert "2023Q3" in filtered.columns
    assert "2022" in filtered.columns
    assert "2024" not in filtered.columns
    assert "2024Q3" not in filtered.columns


@pytest.mark.unit
def test_dart_parse_asof_iso_quarter_year() -> None:
    from dartlab.providers.dart.company import _parseAsof

    assert _parseAsof("2024Q1") == (2024, 1)
    assert _parseAsof("2024q3") == (2024, 3)
    assert _parseAsof("2024-06-30") == (2024, 2)
    assert _parseAsof("2024") == (2024, None)
    assert _parseAsof("garbage") == (None, None)
    assert _parseAsof("") == (None, None)
