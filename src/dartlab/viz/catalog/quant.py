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
    # 3. backtest — placeholder (속편 commit 에서 equity curve + 8 style 매트릭스)
    # ─────────────────────────────────────────────────────────────
    "quantBacktestComingSoon": {
        "kind": "kpiTile",
        "title": "백테스트 (준비 중)",
        "topic": "price",
        "tab": "quant",
        "seriesPlan": [],
        "options": {},
        "layout": {"colSpan": 12, "rowSpan": 2},
        "help": "trendFollow / meanReversion / breakout / dipBuy / eventDriven / flowFollow / lowVolDefensive / seasonalKR 8 style equity curve + Sharpe/Sortino/MaxDD.",
        "dataSpec": {"adapter": "quantComingSoon", "label": "백테스트 엔진 wiring 진행 중"},
    },
    # ─────────────────────────────────────────────────────────────
    # 4. risk — 변동성 (GARCH) + 시장 베타 (CAPM)
    # ─────────────────────────────────────────────────────────────
    "quantVolatilityKpi": {
        "kind": "kpiTile",
        "title": "변동성 패널",
        "topic": "price",
        "tab": "quant",
        "seriesPlan": [],
        "options": {},
        "layout": {"colSpan": 6, "rowSpan": 2},
        "help": "20일 실현변동성 + GARCH(1,1) 조건부 변동성 + HAR-RV. 일별·연환산 동시 표시.",
        "dataSpec": {"adapter": "quantVolatilityKpi"},
    },
    "quantBetaKpi": {
        "kind": "kpiTile",
        "title": "시장 베타 (CAPM)",
        "topic": "price",
        "tab": "quant",
        "seriesPlan": [],
        "options": {},
        "layout": {"colSpan": 6, "rowSpan": 2},
        "help": "벤치마크 대비 베타 + R² + CAPM 기대수익률 + 상대강도. KR=KOSPI/KOSDAQ 자동 선택.",
        "dataSpec": {"adapter": "quantBetaKpi"},
    },
    # ─────────────────────────────────────────────────────────────
    # 5. forecast — 일별 수익률 예측 + Conformal CI
    # ─────────────────────────────────────────────────────────────
    "quantForecastKpi": {
        "kind": "kpiTile",
        "title": "수익률 예측 (Conformal)",
        "topic": "price",
        "tab": "quant",
        "seriesPlan": [],
        "options": {},
        "layout": {"colSpan": 12, "rowSpan": 2},
        "help": "5일 horizon Naive·AR(1)·ETS-Holt·Theta 자동 dispatch + 90% Conformal interval. point + lower/upper 표시.",
        "dataSpec": {"adapter": "quantForecastKpi"},
    },
}
"""quant 탭 7 카드 (signal 2 + factor 1 + backtest 1 + risk 2 + forecast 1).

backtest 1 은 adapter 없는 placeholder — error envelope 으로 빈 카드 graceful.
"""

# section 순서 = catalog 순서 = packing 순서 (sub 정렬 안 함).
QUANT_KEYS: list[str] = list(QUANT_CARDS.keys())
"""quant 탭 cardKey 리스트. frontend SECTIONS array 와 매칭 검증용."""

__all__ = ["QUANT_CARDS", "QUANT_KEYS"]
