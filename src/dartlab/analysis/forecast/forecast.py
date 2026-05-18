"""시계열 예측 + 시나리오 분석 + 민감도 분석 엔진 — facade. 본체는 `_forecastTypes` / `_forecastMetric` / `_forecastScenario`."""

from __future__ import annotations

from dartlab.analysis.forecast._forecastMetric import (
    _marginLinkedForecast,
    forecastAll,
    forecastMetric,
)
from dartlab.analysis.forecast._forecastScenario import (
    scenarioAnalysis,
    sensitivityAnalysis,
)
from dartlab.analysis.forecast._forecastTypes import (
    ForecastResult,
    ScenarioResult,
    SensitivityResult,
)
from dartlab.core.utils.ols import _ols

__all__ = [
    "ForecastResult",
    "ScenarioResult",
    "SensitivityResult",
    "_marginLinkedForecast",
    "_ols",
    "forecastAll",
    "forecastMetric",
    "scenarioAnalysis",
    "sensitivityAnalysis",
]
