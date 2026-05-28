---
id: recipes.macro.oilCycleImpact
title: Oil Cycle Impact — KR 산업별 sensitivity
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: WTI 사이클 × KR 산업별 sensitivity — 정유/석유화학 (positive) vs 항공/물류 (negative). 회사 단위 oil beta 산출. **status=drafted**. 트리거 — '유가 영향', 'oil cycle', 'WTI impact', 'oil beta', '정유 항공 sensitivity'.
whenToUse:
  - oil cycle
  - WTI impact
  - 유가 영향
  - oil beta
  - 정유주
  - 항공주
linkedSkills:
  - engines.macro.commodityCycle
  - engines.scan
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
    - industry
testUniverse:
  market: KR
  stockCodes:
    - "010950"
    - "020560"
  asOfPolicy: latest
falsifier:
  description: 산업별 oil sensitivity 0 = 유가 영향 없음 = recipe 가치 0.
  pythonCheck: |
    assert max_industry_sensitivity > 0.1
expectedNovelty:
  - oilLevel
  - oilZ
  - industrySensitivity
forbidden:
  - 단일 산업 단방향 해석 X (시장 cycle / 환율 / 정책 cross-impact).
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
wti = co["wti"]
oil_beta = dartlab.Company("010950").scan("macroBeta")["wtiBeta"]
```

## 호출 동작

WTI z + 산업별 평균 oil beta + 회사 단위 oil beta 산출.

## 대표 반환 형태

dict — `wti + wtiZ + industrySensitivity + companyBeta`.

## 연계 절차

1. 본 recipe → 유가 cycle 영향.
2. WTI z > 1 → 정유주 outperform 후보.
3. `recipes.industry.sectorMomentumLeadership` 결합.
