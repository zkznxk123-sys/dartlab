from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import polars as pl

from dartlab.analysis.financial import macroExposure


class _FakeCompany:
    stockCode = "FAKE"
    currency = "USD"

    def select(self, topic: str, items: list[str]):
        assert topic == "IS"
        assert items == ["매출액"]
        return SimpleNamespace(
            topic="IS",
            df=pl.DataFrame(
                {
                    "snakeId": ["sales"],
                    "항목": ["매출액"],
                    "2018": [100.0],
                    "2019": [105.0],
                    "2020": [114.0],
                    "2021": [130.0],
                    "2022": [150.0],
                    "2023": [180.0],
                    "2024": [220.0],
                }
            ),
        )


def _macro_frame(values: list[float]) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "date": [date(year, 12, 31) for year in range(2019, 2025)],
            "value": values,
        }
    )


def test_macro_sensitivity_exposes_quality_gate(monkeypatch):
    monkeypatch.setattr(macroExposure, "_getGather", lambda: object())
    monkeypatch.setattr(
        macroExposure,
        "_loadMacroIndicator",
        lambda _g, _series_id, _source: _macro_frame([105.0, 114.0, 130.0, 150.0, 180.0, 220.0]),
    )

    result = macroExposure.calcMacroSensitivity(_FakeCompany())

    assert result is not None
    assert result["selectedSource"] == "범용"
    assert result["selected"]

    row = result["selected"][0]
    assert row["nObs"] == 5
    assert row["window"] == "2020-2024 annual"
    assert row["frequency"] == "annual"
    assert row["lagMonths"] == 0
    assert row["coverage"] == "company"
    assert row["method"] == "annual_revenue_yoy_macro_yoy_ols"
    assert row["modelVersion"] == "macroExposure.v1"
    assert row["targetMetric"] == "annualRevenueYoY"
    assert row["minObs"] == 5
    assert row["sourceRef"] == "analysis.macroExposure:FAKE:FEDFUNDS"
    assert "Company.select:IS:매출액" in row["sourceRefs"]

    quality = result["exposureQuality"]
    assert quality["status"] == "quantCandidate"
    assert quality["missingEvidence"] == []
    assert quality["nObs"] == 5
    assert quality["method"] == "annual_revenue_yoy_macro_yoy_ols"
    assert quality["modelVersion"] == "macroExposure.v1"
    assert quality["targetMetric"] == "annualRevenueYoY"
    assert quality["minObs"] == 5
    assert quality["window"] == "2020-2024 annual"
    assert quality["sourceRef"].startswith("analysis.macroExposure:FAKE:")


def test_macro_sensitivity_blocks_quality_without_macro_observations(monkeypatch):
    monkeypatch.setattr(macroExposure, "_getGather", lambda: object())
    monkeypatch.setattr(macroExposure, "_loadMacroIndicator", lambda _g, _series_id, _source: None)

    result = macroExposure.calcMacroSensitivity(_FakeCompany())

    assert result is not None
    assert result["selected"] == []
    assert result["exposureQuality"]["status"] == "blocked"
    assert result["exposureQuality"]["coverage"] == "missing"
    assert result["exposureQuality"]["method"] == "annual_revenue_yoy_macro_yoy_ols"
    assert result["exposureQuality"]["modelVersion"] == "macroExposure.v1"
    assert result["exposureQuality"]["targetMetric"] == "annualRevenueYoY"
    assert result["exposureQuality"]["minObs"] == 5
    assert "sourceRef" in result["exposureQuality"]["missingEvidence"]


def test_public_annual_revenue_helper_opens_quant_candidate():
    years = ["2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025"]
    revenue = [100.0, 105.0, 114.0, 130.0, 150.0, 180.0, 220.0, 270.0]
    macro_annual = {
        ("ecos", "BASE_RATE"): {year: value for year, value in zip(range(2018, 2026), revenue)},
        ("ecos", "IPI"): {year: value for year, value in zip(range(2018, 2026), revenue)},
        ("ecos", "USDKRW"): {year: value for year, value in zip(range(2018, 2026), revenue)},
    }

    result = macroExposure.calcMacroExposureFromAnnualRevenue(
        stockCode="FAKE",
        years=years,
        revenue=revenue,
        macroAnnual=macro_annual,
    )

    quality = result["exposureQuality"]
    assert quality["status"] == "quantCandidate"
    assert quality["nObs"] == 6
    assert quality["rSquared"] == 1.0
    assert quality["method"] == "annual_revenue_yoy_macro_yoy_ols"
    assert quality["modelVersion"] == "macroExposure.v1"
    assert quality["targetMetric"] == "annualRevenueYoY"
    assert quality["minObs"] == 5
    assert quality["window"] == "2020-2025 annual"
    assert quality["sourceRef"].startswith("analysis.macroExposure:FAKE:")
    assert result["selected"]


def test_public_annual_revenue_helper_locks_low_sample():
    years = ["2021", "2022", "2023", "2024", "2025"]
    revenue = [100.0, 105.0, 114.0, 130.0, 150.0]
    macro_annual = {
        ("ecos", "BASE_RATE"): {year: value for year, value in zip(range(2021, 2026), revenue)},
        ("ecos", "IPI"): {year: value for year, value in zip(range(2021, 2026), revenue)},
        ("ecos", "USDKRW"): {year: value for year, value in zip(range(2021, 2026), revenue)},
    }

    result = macroExposure.calcMacroExposureFromAnnualRevenue(
        stockCode="FAKE",
        years=years,
        revenue=revenue,
        macroAnnual=macro_annual,
    )

    quality = result["exposureQuality"]
    assert quality["status"] == "qualitativeOnly"
    assert quality["nObs"] == 3
    assert "nObs>=5" in quality["missingEvidence"]
