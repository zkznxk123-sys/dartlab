"""scenarioSim native panel contract tests."""

from __future__ import annotations

import polars as pl

from dartlab.analysis.forecast.scenarioSim import _quarterlyValues


def testQuarterlyValuesResolvesNativePanelAccountLabels():
    df = pl.DataFrame(
        {
            "account": ["매출액", "매출총이익", "영업이익"],
            "label": ["매출액 (주27)", "매출총이익", "영업이익"],
            "2024Q1": ["1,000", "400", "120"],
            "2024Q2": ["2,000", "800", "240"],
            "2024Q3": ["3,000", "1,200", "360"],
            "2024Q4": ["4,000", "1,600", "480"],
        }
    )

    assert _quarterlyValues(df, "sales", "2024") == [1000.0, 2000.0, 3000.0, 4000.0]
    assert _quarterlyValues(df, "gross_profit", "2024") == [400.0, 800.0, 1200.0, 1600.0]
    assert _quarterlyValues(df, "operating_profit", "2024") == [120.0, 240.0, 360.0, 480.0]
