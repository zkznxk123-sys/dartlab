---
id: recipes.fundamental.credit.krCorporateSpreadWidening
title: KR Corporate Spread Widening — by rating
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: KR 회사채 spread (AAA~BBB) widening 신호 — 252 일 z > 1 진입 시 신용 risk regime 진입. risk-off detection. **status=drafted**.
whenToUse:
  - 회사채 spread 확대
  - corporate spread widening
  - 신용 risk regime
  - 회사채 신호
linkedSkills:
  - engines.fixedIncome.krCorporateSpread
  - engines.credit
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
    - credit
testUniverse:
  market: KR
  stockCodes:
    - "005930"
  asOfPolicy: latest
falsifier:
  description: spread widening 후 30d 주가 평균 reaction 0 = signal 가치 없음.
  pythonCheck: |
    assert abs(avg_stock_reaction_30d) > 0
expectedNovelty:
  - spreadZ
  - regime
  - ratingDelta
forbidden:
  - 단일 일자 spread 변동 절대 신호 X — z 동행.
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
cs_aaa = dartlab.fixedIncome("krCorporateSpread", rating="AAA", tenor="3Y", days=30)
cs_bbb = dartlab.fixedIncome("krCorporateSpread", rating="BBB", tenor="3Y", days=30)
delta = cs_bbb["spread"][-1] - cs_aaa["spread"][-1]   # rating delta
```

## 호출 동작

전 rating (AAA~BBB) × 3Y/5Y tenor spread z 산출 + delta (AAA vs BBB) + regime (compressed/normal/widening/extreme).

## 대표 반환 형태

DataFrame — `rating · tenor · spread · z252 · regime`.

## 연계 절차

1. 본 recipe → spread widening regime.
2. extreme widening → risk-off 시장 → `recipes.macro.qualityMacroBeta` flight to quality.
3. dCR rating 결합 → `recipes.fundamental.credit.creditQuantConsensus`.
