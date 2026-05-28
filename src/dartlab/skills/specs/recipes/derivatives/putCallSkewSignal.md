---
id: recipes.derivatives.putCallSkewSignal
title: Put-Call Skew Signal — extreme z 신호
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: 25Δ put-call skew z-score extreme (|z| > 2) 진입 시 시장 turning point 후보 — extreme high (z > 2) = 극단적 하방 우려 (contrarian long 신호), extreme low (z < -2) = 안일 (contrarian short). **status=drafted**. 트리거 — 'skew extreme', 'put-call skew', 'fear extreme', 'complacency 신호'.
whenToUse:
  - put-call skew signal
  - 25Δ skew extreme
  - contrarian signal
  - fear extreme
  - complacency
linkedSkills:
  - engines.derivatives.putCallSkew
  - engines.derivatives.vkospi
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
  description: extreme 진입 후 30d 시장 reverse 확률 historical 60% 미달 = signal 가치 약함.
  pythonCheck: |
    assert reverse_rate_30d >= 0.5
expectedNovelty:
  - skewZ
  - regime
  - reverseRate
forbidden:
  - extreme z 단일 시점 = 절대 reversal 신호 X — 학술 alpha 작음.
  - skew ↑ 단방향 해석 금지 (다양한 사유).
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
sk = dartlab.derivatives("putCallSkew", date="2026-05-28", expiry="30d")
if abs(sk["skewZ_30d"]) > 2:
    signal = "extreme_fear" if sk["skewZ_30d"] > 0 else "extreme_complacency"
```

## 호출 동작

skewZ 절댓값 > 2 시 extreme regime 진입 + historical 30d 시장 reverse rate 비교.

## 대표 반환 형태

dict — `skewZ + regime + signal + historicalReverseRate`.

## 연계 절차

1. 본 recipe → extreme z 신호 detection.
2. extreme fear → `recipes.meta.screen.qualityValueScreen` (flight to quality).
3. extreme complacency → 위험 자산 비중 감소 후보.
