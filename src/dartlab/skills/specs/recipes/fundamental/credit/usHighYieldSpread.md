---
id: recipes.fundamental.credit.usHighYieldSpread
title: 미국 High Yield OAS spread regime (BofA HY OAS)
category: recipes
kind: recipe
scope: builtin
status: tested
purpose: ICE BofA US High Yield OAS spread 시계열 z-score. 4%p 이상 = stress, 8%p 이상 = crisis 임계. 단일 회사가 아닌 *credit market regime* 신호. FRED `BAMLH0A0HYM2` raw.
whenToUse:
  - US HY spread
  - high yield credit regime
  - OAS stress threshold
  - credit market 신호
linkedSkills:
  - engines.credit
  - engines.macro
  - engines.gather
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
  - "engines.viz.scenarioVisuals"
  - "engines.viz.tableBackedChart"
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
gap:
  primary:
    - macro
    - credit
testUniverse:
  market: US
  tickers:
    - "BAMLH0A0HYM2"
falsifier:
  description: "임계 단일값만으로 recession 결론 금지 — *지속 기간* + 다른 신호 (yield curve) 동행 필수."
lastUpdated: "2026-05-22"
---

## 공개 호출 방식

```python
import dartlab
import polars as pl
import statistics

try:
    rows = dartlab.macro.seriesFetch("BAMLH0A0HYM2").to_dicts()
except Exception:
    rows = []

values = [(str(r.get("date"))[:10], float(r.get("value") or 0)) for r in rows if r.get("value")]
values.sort(key=lambda x: x[0])
recent = values[-60:] if len(values) >= 60 else values

if len(recent) >= 30:
    mu = statistics.mean([v for _, v in recent[:-1]])
    sd = statistics.stdev([v for _, v in recent[:-1]]) if len(recent) > 2 else 0
    cur = recent[-1][1]
    z = (cur - mu) / sd if sd > 0 else None
    regime = "crisis" if cur >= 8 else "stress" if cur >= 4 else "normal"
else:
    cur = z = None
    regime = "insufficient"

table = pl.DataFrame([{"latestSpread": cur, "regime": regime, "zScore": z, "sampleN": len(recent)}])
emit_result(
    table=table,
    values={"spread": cur, "regime": regime, "z": z},
    date=recent[-1][0] if recent else None,
    sources=["dartlab://macro/fred/BAMLH0A0HYM2"],
)
```

## 호출 동작

BofA US HY OAS spread 시계열에서 최근 값 + 직전 60 일 baseline z-score + regime 분류 (>8% crisis, >4% stress, 그 외 normal).

## 대표 반환 형태

| column | 의미 |
|---|---|
| `latestSpread` | 최신 OAS spread (%) |
| `regime` | crisis / stress / normal |
| `zScore` | 60 일 baseline z |
| `sampleN` | 표본 |

## 연계 절차

1. recipes.macro.usYieldCurveRegime - yield curve 와 동시 본다.
2. recipes.fundamental.credit.cycleStressMap - 회사 credit cycle 영향.

## 기본 검증

- raw 누락 시 결론 X.
- 임계 4% / 8% 는 historical 평균 기반 — 시기별 정의 다름.
- 단일 시점만으로 recession 단정 X — 지속 6 개월 + yield curve 동행 추가.
