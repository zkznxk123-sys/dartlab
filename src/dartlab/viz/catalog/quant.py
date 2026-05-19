"""quant dashboard 카드 카탈로그 — 가격/기술/팩터/리스크/예측 5 section.

dartlab.quant 엔진의 axis 산출물을 viz 카드로 노출. 정체성: *가격 시계열* 기반.
재무 알파 (Altman/Piotroski) 는 financial 탭이 owner — quant 는 OHLCV +
기술지표 + 모멘텀 + 변동성 + 베타 + 예측 + 백테스트만.

5 section 매핑 (frontend SECTIONS array 와 1:1):

| section | cardKey 묶음 | quant axis 소스 |
|---|---|---|
| signal   | priceTrend · verdictKpi              | quant.verdict + gather.price |
| factor   | momentumKpi                          | quant.momentum |
| backtest | backtestComingSoon (placeholder)     | quant.strategy.* (속편) |
| risk     | volatilityKpi · betaKpi              | quant.volatility / quant.beta |
| forecast | forecastKpi                          | quant.benchmark.forecast |

첫 commit 은 6 카드 실값. backtest section 은 placeholder 1 카드 (kpiTile +
adapter 없음 → error envelope 우아한 빈 카드). 후속 commit 에서 backtest /
factor radar / phaseIndicator (regime) / event study 카드 채움.
"""

from __future__ import annotations

from dartlab.viz.schema import CatalogEntry

QUANT_CARDS: dict[str, CatalogEntry] = {
    # ─────────────────────────────────────────────────────────────
    # 1. signal — 가격 시계열 + 기술 종합 판정 (hero stack)
    # ─────────────────────────────────────────────────────────────
    "quantPriceTrend": {
        "kind": "candle",
        "title": "주가 캔들스틱",
        "topic": "price",
        "tab": "quant",
        "seriesPlan": [],  # adapter 가 동적 채움
        "options": {"yAxisFormat": "currency", "volumePane": True},
        "layout": {"colSpan": 12, "rowSpan": 5},
        "help": "최근 1년 OHLC 캔들스틱 + 거래량 하단 pane + SMA(20)/SMA(60) overlay (lightweight-charts).",
        "dataSpec": {"adapter": "quantPriceTrend"},
    },
    "quantVerdictKpi": {
        "kind": "kpiTile",
        "title": "기술 종합 판단",
        "topic": "price",
        "tab": "quant",
        "seriesPlan": [],
        "options": {"scoreMode": True},
        "layout": {"colSpan": 12, "rowSpan": 2},
        "help": "강세/중립/약세 + 종합 점수 (-5~+5) + RSI(14)·ADX·BB위치·SMA20/60 돌파.",
        "dataSpec": {"adapter": "quantVerdictKpi"},
    },
    "quantRsiTrend": {
        "kind": "trend",
        "title": "RSI(14)",
        "topic": "price",
        "tab": "quant",
        "seriesPlan": [],
        "options": {},
        "layout": {"colSpan": 12, "rowSpan": 2},
        "help": "Relative Strength Index 14일 — 70+ 과매수 / 30- 과매도 (Wilder 1978).",
        "dataSpec": {"adapter": "quantRsiTrend"},
    },
    "quantMacdTrend": {
        "kind": "trend",
        "title": "MACD",
        "topic": "price",
        "tab": "quant",
        "seriesPlan": [],
        "options": {},
        "layout": {"colSpan": 12, "rowSpan": 2},
        "help": "Moving Average Convergence Divergence — line · signal · histogram (Appel 1979). histogram 양수 = 모멘텀 강화.",
        "dataSpec": {"adapter": "quantMacdTrend"},
    },
    # ─────────────────────────────────────────────────────────────
    # 2. factor — 모멘텀 (Jegadeesh-Titman 12-1m + 52w high)
    # ─────────────────────────────────────────────────────────────
    "quantMomentumKpi": {
        "kind": "kpiTile",
        "title": "모멘텀 패널",
        "topic": "price",
        "tab": "quant",
        "seriesPlan": [],
        "options": {},
        "layout": {"colSpan": 12, "rowSpan": 2},
        "help": "12-1개월 (최근 1m skip) · 1개월 수익률 · 52주 신고가 비율 · crash risk (음의 skewness).",
        "dataSpec": {"adapter": "quantMomentumKpi"},
    },
    # ─────────────────────────────────────────────────────────────
    # 3. backtest 6 카드 — 8 style 일괄 backtest 1 회 + cache, 모든 카드 공유.
    # vectorBacktest (Moskowitz TSMOM · Avellaneda stat-arb · Turtle System 등 정통 룰)
    # ─────────────────────────────────────────────────────────────
    "quantEquityCurve": {
        "kind": "trend",
        "title": "Equity Curve — 8 style + Buy&Hold",
        "topic": "price",
        "tab": "quant",
        "seriesPlan": [],
        "options": {},
        "layout": {"colSpan": 12, "rowSpan": 4},
        "help": "본 종목으로 8 style (trendFollow/meanReversion/breakout/dipBuy/eventDriven/flowFollow/lowVolDefensive/seasonalKR) backtest. Buy&Hold baseline 과 비교 — 시작 1.0 normalize.",
        "dataSpec": {"adapter": "quantEquityCurve"},
    },
    "quantDrawdownChart": {
        "kind": "trend",
        "title": "Drawdown (best style)",
        "topic": "price",
        "tab": "quant",
        "seriesPlan": [],
        "options": {},
        "layout": {"colSpan": 12, "rowSpan": 2},
        "help": "Sharpe 1위 style 의 equity 에서 (equity / runMax − 1) — 자본 손실 크기 시계열.",
        "dataSpec": {"adapter": "quantDrawdownChart"},
    },
    "quantMonthlyHeatmap": {
        "kind": "matrix",
        "title": "월간 수익률 Heatmap (best style)",
        "topic": "price",
        "tab": "quant",
        "seriesPlan": [],
        "options": {},
        "layout": {"colSpan": 12, "rowSpan": 3},
        "help": "Sharpe 1위 style 의 월간 누적수익률. 행=연도 / 열=1~12월. 빨강=양수, 파랑=음수 diverging.",
        "dataSpec": {"adapter": "quantMonthlyHeatmap"},
    },
    "quantStyleMatrix": {
        "kind": "comparisonTable",
        "title": "8 style 성과 매트릭스",
        "topic": "price",
        "tab": "quant",
        "seriesPlan": [],
        "options": {},
        "layout": {"colSpan": 12, "rowSpan": 3},
        "help": "전략별 Sharpe / Sortino / MaxDD / WinRate / Expectancy / Turnover 비교. Sharpe 정렬 시 본 종목 적합 style 도출.",
        "dataSpec": {"adapter": "quantStyleMatrix"},
    },
    "quantRollingSharpe": {
        "kind": "trend",
        "title": "Rolling Sharpe (60d)",
        "topic": "price",
        "tab": "quant",
        "seriesPlan": [],
        "options": {},
        "layout": {"colSpan": 6, "rowSpan": 2},
        "help": "60 거래일 rolling Sharpe — 시간에 따른 전략 안정성. 1+ 양호, 0 이하 부진.",
        "dataSpec": {"adapter": "quantRollingSharpe"},
    },
    "quantAnnualReturns": {
        "kind": "trend",
        "title": "연도별 수익률 (best style)",
        "topic": "price",
        "tab": "quant",
        "seriesPlan": [],
        "options": {},
        "layout": {"colSpan": 6, "rowSpan": 2},
        "help": "Sharpe 1위 style 의 연별 누적수익률 bar — 어느 시장 cycle 에 잘 작동했는지.",
        "dataSpec": {"adapter": "quantAnnualReturns"},
    },
    # ─────────────────────────────────────────────────────────────
    # 4. risk — Bloomberg BETA 산점도 + 변동성 term + drawdown 분포 + Snowflake radar
    # ─────────────────────────────────────────────────────────────
    "quantBetaScatter": {
        "kind": "scatter",
        "title": "β 산점도 (시장 vs 종목)",
        "topic": "price",
        "tab": "quant",
        "seriesPlan": [],
        "options": {},
        "layout": {"colSpan": 6, "rowSpan": 4},
        "help": "Bloomberg BETA 정통 — 시장(KOSPI) 일별 수익률 X, 종목 일별 수익률 Y. OLS β/α/R² 산점도 분포.",
        "dataSpec": {"adapter": "quantBetaScatter"},
    },
    "quantVolatilityTerm": {
        "kind": "trend",
        "title": "변동성 Term Structure",
        "topic": "price",
        "tab": "quant",
        "seriesPlan": [],
        "options": {},
        "layout": {"colSpan": 6, "rowSpan": 4},
        "help": "5d / 20d / 60d / 120d rolling realized vol (연환산 %) 시계열. 단기 변동성 spike vs 장기 추세 비교.",
        "dataSpec": {"adapter": "quantVolatilityTerm"},
    },
    "quantDrawdownDistribution": {
        "kind": "trend",
        "title": "Drawdown 깊이 분포",
        "topic": "price",
        "tab": "quant",
        "seriesPlan": [],
        "options": {},
        "layout": {"colSpan": 6, "rowSpan": 3},
        "help": "Best style equity 의 모든 drawdown 깊이 히스토그램 — 0~2% / 2~5% / 5~10% / 10~15% / 15~20% / 20%+ 6 구간 빈도(일수).",
        "dataSpec": {"adapter": "quantDrawdownDistribution"},
    },
    "quantSnowflakeRadar": {
        "kind": "radar",
        "title": "Snowflake 5 axis",
        "topic": "price",
        "tab": "quant",
        "seriesPlan": [],
        "options": {},
        "layout": {"colSpan": 6, "rowSpan": 3},
        "help": "Simply Wall St 정통 5 차원 종합 — 기술 / 모멘텀 / 리스크(역) / 팩터 / 예측. 각 축 0~5 점.",
        "dataSpec": {"adapter": "quantSnowflakeRadar"},
    },
    # ─────────────────────────────────────────────────────────────
    # 5. forecast — Conformal fan chart + Monte Carlo paths + HMM regime phase
    # ─────────────────────────────────────────────────────────────
    "quantForecastFan": {
        "kind": "trend",
        "title": "Forecast Fan (20일 horizon)",
        "topic": "price",
        "tab": "quant",
        "seriesPlan": [],
        "options": {},
        "layout": {"colSpan": 12, "rowSpan": 4},
        "help": "20일 horizon Naive·AR(1)·ETS-Holt·Theta 자동 dispatch 점 예측 + 90% Conformal CI 상/하단. 가격 단위 price band.",
        "dataSpec": {"adapter": "quantForecastFan"},
    },
    "quantMonteCarloPaths": {
        "kind": "trend",
        "title": "Monte Carlo (GBM 200 path)",
        "topic": "price",
        "tab": "quant",
        "seriesPlan": [],
        "options": {},
        "layout": {"colSpan": 6, "rowSpan": 3},
        "help": "Geometric Brownian Motion 200 path × 20일 horizon. 25/50/75 percentile band + VaR(5%)/CVaR(5%) 표기.",
        "dataSpec": {"adapter": "quantMonteCarloPaths"},
    },
    "quantRegimePhase": {
        "kind": "phaseIndicator",
        "title": "HMM Regime",
        "topic": "price",
        "tab": "quant",
        "seriesPlan": [],
        "options": {},
        "layout": {"colSpan": 6, "rowSpan": 3},
        "help": "Hamilton 2-state HMM bull/bear regime — 약세 / 중립 / 상승 / 강한 상승 4 phase 중 현재 위치 + bullProb confidence.",
        "dataSpec": {"adapter": "quantRegimePhase"},
    },
}
"""quant 탭 7 카드 (signal 2 + factor 1 + backtest 1 + risk 2 + forecast 1).

backtest 1 은 adapter 없는 placeholder — error envelope 으로 빈 카드 graceful.
"""

# section 순서 = catalog 순서 = packing 순서 (sub 정렬 안 함).
QUANT_KEYS: list[str] = list(QUANT_CARDS.keys())
"""quant 탭 cardKey 리스트. frontend SECTIONS array 와 매칭 검증용."""

__all__ = ["QUANT_CARDS", "QUANT_KEYS"]
