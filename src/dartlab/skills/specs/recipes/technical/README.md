---
id: recipes.technical.README
title: Technical 페르소나 — 초기 단계 (1 recipe)
purpose: 가격·수익률·팩터·차트 페르소나. quant 엔진의 L1.5 이하 조합으로 작성.
category: recipes
kind: index
status: published
whenToUse:
  - 테크니컬 분석 페르소나 커버리지 확인
  - quant 엔진과 technical 페르소나의 관계
---

# Technical 페르소나

가격·수익률·팩터·차트 기반 분석. 현재 1 recipe (quantTechnicalReview) 로 시작. quant L2 엔진의 *직접 호출 금지* — L1.5 의 frame/scan/synth/reference 조합으로만 작성.

## 분류 기준

- 시점이 *price/return time series* 인가? → technical
- 시점이 *재무 시점·공시 시점* 인가? → fundamental
- 시점이 *거시 시리즈* 인가? → macro

## 현재 recipes

- `recipes.technical.quantTechnicalReview` — quant 엔진 사용법 검토 (cross-cutting 성격이라 차후 fundamental/quality 또는 meta 로 재분류 검토 가능)

## 커버 확장 후보

- 모멘텀 신호 (12-1, 6-1, 3-1) panel 비교
- 변동성 regime breakout
- 페어 z-score
- 팩터 expected return decomposition
