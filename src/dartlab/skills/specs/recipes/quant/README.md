---
id: recipes.quant.README
title: Quant 페르소나 — 팩터 5 축
purpose: value · momentum · quality · low-vol · size 5 팩터 단일 회사 적용 + cross-section rank. dartlab quant 엔진 위 recipe 층.
category: recipes
kind: curated
status: curated
whenToUse:
  - 팩터 분석 페르소나 진입
  - value / momentum / quality / low-vol / size 5 축 확인
  - 단일 회사 팩터 점수
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: supported
  pyodide:
    status: supported
linkedSkills:
  - engines.quant
  - engines.scan
  - engines.company
---

# Quant 페르소나 — 팩터 5 축

학술적으로 검증된 5 팩터 (Fama-French value/size + Jegadeesh momentum + Frazzini-Pedersen-Asness QMJ + low-volatility) 를 단일 회사에 적용한 recipe 셋트.

## 1 차 진입 5

| recipe | 학술 근거 |
|---|---|
| [recipes.quant.valueFactor](/skills/recipes.quant.valueFactor) | Fama-French 1992 (B/M, E/P, CF/P composite) |
| [recipes.quant.momentumFactor](/skills/recipes.quant.momentumFactor) | Jegadeesh-Titman 1993 (12-1m return) |
| [recipes.quant.qualityFactor](/skills/recipes.quant.qualityFactor) | Frazzini-Pedersen-Asness QMJ 2014 |
| [recipes.quant.lowVolFactor](/skills/recipes.quant.lowVolFactor) | Ang-Hodrick-Xing-Zhang 2006 low-vol anomaly |
| [recipes.quant.sizeFactor](/skills/recipes.quant.sizeFactor) | Fama-French 1992 SMB |

## 정체성

generic LLM 의 *"이 종목 quality 높음"* 추론이 아닌, 학술 정의 식 그대로 계산 + cross-section percentile rank. 단일 score 가 아닌 *축별 분리 표기* 강행.
