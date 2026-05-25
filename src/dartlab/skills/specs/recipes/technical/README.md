---
id: recipes.technical.README
title: Technical 페르소나 — 초기 단계 (1 recipe)
purpose: 가격·수익률·팩터·차트 페르소나. quant 엔진의 L1.5 이하 조합으로 작성.
category: recipes
kind: curated
status: curated
whenToUse:
  - 테크니컬 분석 페르소나 커버리지 확인
  - quant 엔진과 technical 페르소나의 관계
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: limited
  pyodide:
    status: limited
linkedSkills:
  - engines.company
  - engines.gather
  - engines.quant
---

# Technical 페르소나

가격·수익률·팩터·차트 기반 분석. quant L2 엔진의 *직접 호출 금지* — L1.5 의 frame/scan/synth/reference 조합으로만 작성.

## 분류 기준

- 시점이 *price/return time series* 인가? → technical
- 시점이 *재무 시점·공시 시점* 인가? → fundamental
- 시점이 *거시 시리즈* 인가? → macro

## 1 차 진입 recipe

| recipe | 역할 |
|---|---|
| [recipes.technical.atrRegimeShift](/skills/recipes.technical.atrRegimeShift) | ATR 변동성 regime 전환 시점 검출 |
| [recipes.technical.breakoutPriceConfirmation](/skills/recipes.technical.breakoutPriceConfirmation) | 가격 breakout + 거래량 확인 |
| [recipes.technical.breakoutNewsConfirmation](/skills/recipes.technical.breakoutNewsConfirmation) | breakout 시점 ± news 보도 cross-check |
| [recipes.technical.disclosureAdjacentVolatility](/skills/recipes.technical.disclosureAdjacentVolatility) | 공시 ±N 거래일 변동성 분포 |
| [recipes.technical.macroRegimeSectorBreakout](/skills/recipes.technical.macroRegimeSectorBreakout) | 거시 regime × 섹터 breakout 결합 |
| [recipes.technical.momentumFlowDecouple](/skills/recipes.technical.momentumFlowDecouple) | 가격 모멘텀 vs 수급 decoupling 시점 |
| [recipes.technical.momentumFlowDivergence](/skills/recipes.technical.momentumFlowDivergence) | 가격↑ vs 수급↓ (또는 반대) divergence |
| [recipes.technical.momentumFlowSplit](/skills/recipes.technical.momentumFlowSplit) | 외인/기관/개인 별 momentum split |
| [recipes.technical.movingAverageConfluence](/skills/recipes.technical.movingAverageConfluence) | 5/20/60/120 MA confluence 점 |
| [recipes.technical.priceVolumeZScore](/skills/recipes.technical.priceVolumeZScore) | 거래량 z ≥ 2 row 의 +/- ret skew |
| [recipes.technical.rsiBollingerCluster](/skills/recipes.technical.rsiBollingerCluster) | RSI + Bollinger band 동시 신호 |
| [recipes.technical.sectorRelativeStrength](/skills/recipes.technical.sectorRelativeStrength) | 종목 ret vs 섹터 index ret 차 |
| [recipes.technical.quantTechnicalReview](/skills/recipes.technical.quantTechnicalReview) | quant 엔진 사용법 검토 |
