---
id: recipes.macro.copperGoldRatio
title: Copper-Gold Ratio — risk on/off sentiment
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: Copper-Gold ratio (구리 / 금) — 성장 vs 안전 sentiment 정량. ratio ↑ = risk on (위험자산 alpha), ratio ↓ = risk off (defensive). 미국채 10Y yield 와 동행. **status=drafted**. 트리거 — 'copper-gold ratio', '구리 금 비율', 'risk on off', '성장 sentiment'.
whenToUse:
  - copper gold ratio
  - 구리 금 비율
  - risk on off
  - sentiment ratio
  - 위험자산 sentiment
linkedSkills:
  - engines.macro.commodityCycle
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
    - macro
    - quant
testUniverse:
  market: KR
  stockCodes:
    - "005930"
  asOfPolicy: latest
falsifier:
  description: copper-gold ratio vs US 10Y yield 상관 0 = 학술 정합 부재 = signal 가치 약.
  pythonCheck: |
    assert abs(corr_with_us10y) > 0.3
expectedNovelty:
  - ratio
  - ratioZ
  - regime
forbidden:
  - ratio 절대 신호 X — z + 다른 indicator 동행.
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
---

## 공개 호출 방식

```python
import dartlab
co = dartlab.macro("commodityCycle")
ratio = co["copperGoldRatio"]
us10y = dartlab.macro("rates", market="US")["us10y"]
```

## 호출 동작

LME 구리 / COMEX 금 ratio + 252 일 z + US 10Y yield 상관 + regime.

## 대표 반환 형태

dict — `ratio + ratioZ + regime + us10yCorr`.

## 연계 절차

1. 본 recipe → risk on/off sentiment.
2. risk on → 위험자산 / 신흥국 alpha 후보.
3. risk off → flight to quality (`recipes.meta.screen.qualityValueScreen`).
