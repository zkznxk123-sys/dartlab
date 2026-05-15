"""경제 시나리오 기반 시뮬레이션 예측 엔진 (facade).

본체는 ``dartlab.analysis.forecast.simulation`` — 본 패키지 root 는 re-export.
중복 정의 (forecast/__init__.py 와 forecast/simulation.py 가 동일 1106 줄)
회귀를 제거하면서 외부 호출 BC 는 보존.

3-Layer 구조:
1. MacroScenario — 거시경제 변수 경로 (GDP, 금리, 환율, CPI)
2. SectorElasticity — 업종별 거시경제 감응도 (beta)
3. CompanySimulation — 기업 실적 시뮬레이션 (시나리오 + Monte Carlo + 스트레스)
"""

from __future__ import annotations

from dartlab.analysis.forecast.simulation import (
    BASELINE_FX,
    BASELINE_RATE,
    DEFAULT_ELASTICITY,
    PRESET_SCENARIOS,
    BacktestResult,
    MacroScenario,
    MonteCarloResult,
    SectorElasticity,
    SectorParams,
    SimulationResult,
    StressTestResult,
    _applyMacroShock,
    _extractBaseMetrics,
    _extractVolatility,
    _getActualRevChange,
    _getRevByYear,
    backtestSimulation,
    getElasticity,
    monteCarloForecast,
    simulateAllScenarios,
    simulateHistorical,
    simulateScenario,
    stressTest,
)

__all__ = [
    "BASELINE_FX",
    "BASELINE_RATE",
    "BacktestResult",
    "DEFAULT_ELASTICITY",
    "MacroScenario",
    "MonteCarloResult",
    "PRESET_SCENARIOS",
    "SectorElasticity",
    "SectorParams",
    "SimulationResult",
    "StressTestResult",
    "backtestSimulation",
    "getElasticity",
    "monteCarloForecast",
    "simulateAllScenarios",
    "simulateHistorical",
    "simulateScenario",
    "stressTest",
]
