---
id: recipes.fundamental.credit.yieldCurveInversion
title: KGB Yield Curve Inversion — recession indicator
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: KGB 국고채 yield curve 역전 (10Y-2Y < 0 또는 10Y-3M < 0) 신호 — recession 1~2 년 선행 (US 학술 정통). KR 시장 partial 적용. **status=drafted**. 트리거 — 'yield curve 역전', '국고채 inversion', '2s10s', '3m10y', 'recession indicator'.
whenToUse:
  - yield curve inversion
  - 국고채 역전
  - 2s10s
  - 3m10y
  - recession indicator
linkedSkills:
  - engines.fixedIncome.kgbYieldCurve
  - engines.macro.cycles
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - valueRef
  - dateRef
  - executionRef
  - sourceRef
visualRefs:
  - engines.viz.tableBackedChart
gap:
  primary:
    - fixedIncome
    - macro
testUniverse:
  market: KR
  stockCodes:
    - "005930"
  asOfPolicy: latest
falsifier:
  description: KR 시장 역전 후 24 개월 recession 빈도 historical < 30% = signal 가치 약함.
  pythonCheck: |
    assert historical_recession_rate >= 0.3
expectedNovelty:
  - slope10y2y
  - slope10y3m
  - inversionDays
forbidden:
  - 역전 = recession 확정 X (1-2y lag + US 기반 학술, KR partial).
runtimeCompatibility:
  server:
    status: limited
  localPython:
    status: limited
  mcp:
    status: limited
  webAi:
    status: limited
  pyodide:
    status: limited
---

## 공개 호출 방식

```python
import dartlab
yc = dartlab.fixedIncome("kgbYieldCurve", date="2026-05-28")
inverted = yc["slope_10y_2y"] < 0
```

## 호출 동작

slope 10Y-2Y + 10Y-3M 시계열 + 역전 지속일 산출 + macro cycle phase 정합.

## 대표 반환 형태

dict — `slope10y2y + slope10y3m + inversionDays + macroPhase + recessionProb`.

## 연계 절차

1. 본 recipe → 역전 신호 + 지속일.
2. 역전 지속 > 90일 → recession 후보 시나리오.
3. `recipes.macro.qualityMacroBeta` defensive sector pivot.
