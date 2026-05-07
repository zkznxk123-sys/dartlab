---
id: engines.recipe.macroToCompany
title: 매크로 → 섹터 → 회사 영향 (transmission)
category: engines
kind: recipe
scope: builtin
status: unverified
purpose: 매크로 환경 변화가 특정 회사의 매출·영업이익·이자비용·환산손익에 어떻게 전이되는지 단계별로 추적하는 절차. 트리거 — '매크로 → 회사 전이', '금리 환율 회사 영향', '단계별 추적'.
whenToUse:
  - 금리가 회사에 미치는 영향
  - 환율이 회사에 미치는 영향
  - 매크로 영향
  - 거시 영향
  - macro sensitivity
  - 금리 인상 영향
  - 환율 영향
linkedSkills:
  - engines.macro.marketReview
  - engines.macro.rates
  - engines.analysis.macroSensitivity
  - engines.company.researchStarter
  - engines.analysis.financing
toolRefs:
  - engine_call
  - run_python
requiredEvidence:
  - skillRef
  - tableRef
  - valueRef
  - dateRef
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
    limitations:
      - browser 안에서는 macro snapshot 한정
lastUpdated: '2026-05-07'
---

## 공개 호출 방식

```python
import dartlab

# 매크로 환경 + 회사 진입 + sensitivity
macro = dartlab.macro()
c = dartlab.Company("005930")
sens = c.analysis("financial", "macro민감도")
financing = c.analysis("financial", "재무구조")
```

## 호출 동작

매크로 변수 (금리·환율·유가) → 회사 P&L 항목 (매출·원가·이자비용·외환환산) 의 elasticity 를 계산하고 시나리오별 영향을 표로 낸다.

1. 매크로 한 시점 snapshot (`dartlab.macro()`)
2. 회사 진입
3. macro sensitivity axis — elasticity 계산
4. 자본구조 (이자부 부채·달러 부채 비중) 점검

## 대표 반환 형태

- `tableRef` 2 개 (macro snapshot, sensitivity 표)
- `valueRef` 4+ 개 (환율 elasticity, 금리 elasticity, 유가 elasticity)
- `dateRef` 1 개 (분석 기준 시점)

## 연계 절차

1. engines.macro.marketReview — 현재 매크로 환경 (금리·환율·경기 사이클)
2. engines.macro.rates — 금리 변동 흐름 (필요 시)
3. engines.company.researchStarter — 회사 진입
4. engines.analysis.macroSensitivity — 매크로 변수별 회사 P&L elasticity
5. engines.analysis.financing — 자본구조 (이자부 부채·외화 부채 비중)

## 기본 검증

- elasticity 는 비율 (%, 배) — 단위 명시.
- 시나리오 (base/bull/bear) 가 있으면 가정 명시.
- 단발 추측 금지 — historic 추정 데이터로 뒷받침된 elasticity 만.
