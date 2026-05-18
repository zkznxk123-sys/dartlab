"""Strategy 평가 메트릭 — facade. 본체는 `_metricsBasic` / `_metricsOverfitting` / `_metricsIC`.

외부 의존 0. numpy + math 만. 정규분포 CDF/PPF 는 자체 구현 (Abramowitz-Stegun).

학술 근거:
- Sharpe (1966) — Sharpe Ratio
- Sortino & van der Meer (1991) — Sortino Ratio
- Bailey & López de Prado (2014) — Deflated Sharpe Ratio (DSR)
- Bailey, Borwein, López de Prado, Zhu (2015) — Probability of Backtest Overfitting (PBO)
- López de Prado (2018) — AFML Combinatorial Purged Cross-Validation (CPCV)
- Grinold & Kahn (2000) — Active Portfolio Management Ch.5-8

SSOT: 메트릭 함수는 본 3 모듈 한 곳. quant/_helpers.py 등에 중복 금지.
"""

from __future__ import annotations

from ._metricsBasic import (
    TRADING_DAYS,
    expectancy,
    exposure,
    mdd,
    profitFactor,
    sharpe,
    sortino,
    turnover,
    winrate,
)
from ._metricsIC import (
    breadthFromFrequency,
    calcIR,
    factorDecayRate,
    fundamentalLawIR,
    icSignificance,
    impliedIRFromICDistribution,
    pearsonCorr,
    rollingTimeSeriesZscore,
    spearmanCorr,
)
from ._metricsOverfitting import (
    _normCdf,
    _normPpf,
    cpcvSplits,
    dsr,
    pbo,
)

__all__ = [
    "TRADING_DAYS",
    "_normCdf",
    "_normPpf",
    "breadthFromFrequency",
    "calcIR",
    "cpcvSplits",
    "dsr",
    "expectancy",
    "exposure",
    "factorDecayRate",
    "fundamentalLawIR",
    "icSignificance",
    "impliedIRFromICDistribution",
    "mdd",
    "pbo",
    "pearsonCorr",
    "profitFactor",
    "rollingTimeSeriesZscore",
    "sharpe",
    "sortino",
    "spearmanCorr",
    "turnover",
    "winrate",
]
