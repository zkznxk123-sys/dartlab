---
id: engines.recipe.macroLiquidityCycle
title: 매크로 유동성 사이클 (금리 + 환율 + 유동성)
category: engines
kind: recipe
scope: builtin
status: unverified
purpose: 매크로 유동성 환경을 금리 + 환율 + 유동성 지표 + 위기 신호 4 축으로 종합 판정하는 절차. 종목 없이 매크로 분석 가능.
whenToUse:
  - 매크로 유동성
  - 금리 환경
  - 환율 환경
  - 유동성 사이클
  - 매크로 종합
  - 위기 신호
  - 거시 환경
linkedSkills:
  - engines.macro.marketReview
  - engines.macro.rates
  - engines.macro.liquidity
  - engines.macro.crisis
  - engines.macro.summary
toolRefs:
  - engine_call
  - run_python
requiredEvidence:
  - skillRef
  - tableRef
  - dateRef
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
    limitations:
      - browser 안에서는 macro 시계열 일부 한정
lastUpdated: '2026-05-06'
---

## 공개 호출 방식

```python
import dartlab

summary = dartlab.macro()
rates = dartlab.macro("rates")
liquidity = dartlab.macro("liquidity")
crisis = dartlab.macro("crisis")
final = dartlab.macro("summary")
```

## 호출 동작

매크로 종합 → 금리 곡선 → M2/유동성 → 위기 신호 → 최종 종합 판정.

1. macro() — 매크로 환경 한 시점
2. macro("rates") — 단기/장기 금리 + 곡선 형태
3. macro("liquidity") — M2 / 본원통화 / 신용 사이클
4. macro("crisis") — VIX / 신용스프레드 / 환율 변동성
5. macro("summary") — 최종 종합 판정

## 대표 반환 형태

- `tableRef` 5 개 (각 axis 별 시계열)
- `dateRef` 1 개 (최신 관측 시점)
- 답변 본문: 매크로 단계 (확장/둔화/침체/회복) + 근거 지표

## 연계 절차

1. engines.macro.marketReview — 매크로 환경 종합
2. engines.macro.rates — 금리 곡선
3. engines.macro.liquidity — 유동성 지표
4. engines.macro.crisis — 위기 신호
5. engines.macro.summary — 최종 종합

## 기본 검증

- 사이클 위치 (확장/둔화/침체/회복) + 근거 지표 (PMI/금리곡선/VIX).
- 금리 곡선 inversion 신호 명시.
- "유동성 풍부" 단정 X — M2 증가율 + 신용 스프레드 함께.
