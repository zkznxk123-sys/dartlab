---
id: recipes.fundamental.flow.programTradeImbalance
title: Program Trade Imbalance — 차익 vs 비차익 z
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: 프로그램매매 imbalance (차익거래 net + 비차익 net) z-score — 차익거래 net 신호 (KOSPI200 mispricing 정도) + 비차익 신호 (패시브 flow). **status=drafted**.
whenToUse:
  - 프로그램매매
  - program trade
  - 차익거래
  - 비차익
  - 인덱스 차익
linkedSkills:
  - engines.flow.programTrade
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
    - flow
    - scan
testUniverse:
  market: KR
  stockCodes:
    - "005930"
  asOfPolicy: latest
falsifier:
  description: 차익 + 비차익 imbalance 항상 0 근처 = data 수집 실패 또는 market dynamics 부재.
  pythonCheck: |
    assert imbalance_std > 0
expectedNovelty:
  - arbZ
  - nonArbZ
  - imbalanceRegime
forbidden:
  - 차익거래 net 단방향 해석 X (선물 mispricing 일시 보정).
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
pt = dartlab.flow("programTrade", date="2026-05-28")
imbalance = pt["arbitrageNet"] + pt["nonArbNet"]
```

## 호출 동작

일별 차익 + 비차익 net + 30 일 cumulative + 252 일 z + regime.

## 대표 반환 형태

dict — `arbZ + nonArbZ + cumImbalance + regime`.

## 연계 절차

1. 본 recipe → 프로그램매매 imbalance.
2. 비차익 cumulative net ↑ → 패시브 flow 확대 신호.
3. 차익 cumulative ≠ 0 → KOSPI200 선물 mispricing 지속.
