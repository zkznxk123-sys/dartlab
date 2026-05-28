---
id: recipes.derivatives.vkospiRegime
title: VKOSPI Regime × Macro Cycle 정합
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: VKOSPI 4 regime × macro cycle 5 regime 정합 — calm/normal/elevated/panic vs expansion/slowdown/contraction/recovery/crisis. 시장 fear 와 macro cycle 일치성 진단. **status=drafted**. 트리거 — 'VKOSPI regime', '변동성 regime', 'fear gauge regime', 'macro cycle 정합'.
whenToUse:
  - VKOSPI regime
  - macro cycle 정합
  - fear gauge regime
  - volatility regime
linkedSkills:
  - engines.derivatives.vkospi
  - engines.macro.regimes
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
    - derivatives
    - macro
testUniverse:
  market: KR
  stockCodes:
    - "005930"
  asOfPolicy: latest
falsifier:
  description: 두 regime 항상 일치 = 신호 가치 0 (직교 신호여야 가치). historical 일치율 60-70% expectable.
  pythonCheck: |
    assert alignment_rate < 0.9
expectedNovelty:
  - vkospiRegime
  - macroRegime
  - alignment
forbidden:
  - 단일 시점 mismatch = 절대 매수/매도 신호 X.
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
vk = dartlab.derivatives("vkospi", date="2026-05-28")
mr = dartlab.macro("cycle", market="KR")
alignment = (vk["regime"] == "panic" and mr["regime"] == "crisis")
```

## 호출 동작

VKOSPI regime (4) × macro regime (5) cross-tab + alignment 정량화 + 직교 mismatch 패턴 (calm + crisis 또는 panic + expansion) 표기.

## 대표 반환 형태

dict — `vkospiRegime/macroRegime/alignment/divergenceFlag`.

## 연계 절차

1. 본 recipe → 두 regime 정합성.
2. divergence → `recipes.macro.scenarioDiagram` 시나리오 평가.
3. panic 지속 → flight to quality (recipes.meta.screen.qualityValueScreen).
