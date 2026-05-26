---
id: recipes.macro.usFedDotPlotGap
title: 미국 Fed dot plot vs market path 갭
category: recipes
kind: recipe
scope: builtin
status: tested
purpose: Fed dot plot 의 median target rate (FOMC SEP) vs market implied path (Fed funds futures) 의 1y 갭. 갭 > +50bp = market dovish, < -50bp = market hawkish. *market vs Fed* 정합성 점검.
whenToUse:
  - Fed dot plot
  - market implied path
  - dot plot vs market
  - Fed funds futures
examples:
  - Fed dot plot 과 market 갭 — 시장이 더 비둘기파인가
  - FOMC SEP median target vs Fed funds futures 1y 갭
  - 시장이 Fed 보다 hawkish / dovish 어느 쪽
expectedOutputs:
  - Fed dot plot median target rate + market implied 1y rate
  - 갭 (bp) 단일값
  - 라벨 (dovish 갭 > +50bp / hawkish 갭 < -50bp / 정합)
linkedSkills:
  - engines.macro
  - engines.gather
  - recipes.macro.usYieldCurveRegime
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
    - gather
testUniverse:
  market: US
falsifier:
  description: "FOMC SEP 또는 Fed funds futures raw 누락 시 결론 X. 단일 시점 dot 만 보고 추세 단정 금지."
lastUpdated: "2026-05-22"
---

## 공개 호출 방식

```python
import dartlab
import polars as pl

# Fed dot plot (FOMC SEP median)
try:
    dot = dartlab.macro.referenceFetch("fed_sep_dot_median")
    dot_1y = float(dot.get("y1_median", 0))
except Exception:
    dot_1y = None

# Fed funds futures implied (FRED OBFR or CME)
try:
    futures = dartlab.macro.seriesFetch("FEDFUNDS").to_dicts()[-1]
    market_1y = float(futures.get("value") or 0)
except Exception:
    market_1y = None

gap = (dot_1y - market_1y) if (dot_1y is not None and market_1y is not None) else None
direction = "marketDovish" if (gap is not None and gap > 0.5) else \
            "marketHawkish" if (gap is not None and gap < -0.5) else "aligned"

table = pl.DataFrame([{"dotMedian1y": dot_1y, "marketImplied1y": market_1y, "gap": gap, "direction": direction}])
emit_result(
    table=table,
    values={"gap": gap, "direction": direction},
    date=None,
    sources=["dartlab://macro/fed_sep", "dartlab://macro/fred/FEDFUNDS"],
)
```

## 호출 동작

Fed SEP 의 1y forward median rate (dot) vs Fed funds futures 의 1y implied rate. 갭 > +50bp = market 이 Fed 보다 dovish (시장이 더 내릴 것 기대), < -50bp = market hawkish.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `dotMedian1y` | Fed SEP 1y median |
| `marketImplied1y` | futures implied |
| `gap` | dot - market (% pt) |
| `direction` | marketDovish/marketHawkish/aligned |

## 연계 절차

1. recipes.macro.usYieldCurveRegime - curve + dot 정합.
2. recipes.fundamental.credit.usHighYieldSpread - 갭 + credit market 반응.

## 기본 검증

- 두 raw 모두 필요.
- 단일 시점만으로 추세 결론 금지 — quarterly SEP 갱신 추적.
- *시장이 옳다* 단정 X — 갭 자체가 정량 사실.
