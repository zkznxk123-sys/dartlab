---
id: recipes.derivatives.optionFlowDetector
title: Option Flow Detector — unusual volume / open interest jump
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: 옵션 거래량 / 미결제약정 (open interest) z-score 급증 detection — 정보 비대칭 신호. unusual options activity 학술 (Pan-Poteshman 2006). **status=drafted**.
whenToUse:
  - option flow
  - unusual options
  - open interest jump
  - 옵션 거래량
  - 옵션 OI
linkedSkills:
  - engines.derivatives.ivSurface
  - engines.derivatives
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
    - quant
testUniverse:
  market: KR
  stockCodes:
    - "005930"
  asOfPolicy: latest
falsifier:
  description: unusual volume / OI jump 후 30d 시장 alpha 0 = signal 가치 약함.
  pythonCheck: |
    assert post_alpha_30d_abs >= 0.005
expectedNovelty:
  - volumeZ
  - oiZ
  - strikeCluster
forbidden:
  - 단일 strike 거래량 급증 = 절대 매수/매도 신호 X.
  - 만기 임박 옵션 거래량 급증은 차익거래 / 만기 청산 — noise.
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
iv = dartlab.derivatives("ivSurface", date="2026-05-28")
# volume_z / oi_z 컬럼 추출 + |z| > 2 strike cluster 식별
unusual = iv.filter(pl.col("volume_z") > 2)
```

## 호출 동작

strike × expiry 격자에서 volume z-score (252 일 baseline) + OI z 산출. |z| > 2 cluster 분류 (같은 strike 근처 5 행사가 동시 z↑ = cluster).

## 대표 반환 형태

DataFrame — `strike + expiry + volumeZ + oiZ + clusterFlag`.

## 연계 절차

1. 본 recipe → unusual flow detection.
2. cluster 발견 → underlying 종목 deep dive.
3. directional bias (콜 vs 풋) → `recipes.derivatives.putCallSkewSignal` 결합.
