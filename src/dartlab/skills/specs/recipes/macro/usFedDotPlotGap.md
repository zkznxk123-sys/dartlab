---
id: recipes.macro.usFedDotPlotGap
title: 미국 Fed dot plot vs market path 갭
category: recipes
kind: recipe
scope: builtin
status: curated
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
validatedAt: '2026-05-27'
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

### 1. 결론 도출

dot vs market 갭 + direction 단정. 예: "Fed SEP dot median 1y=4.0% / Fed funds futures 1y implied=3.2% → gap=+0.8%p (80bp) → marketDovish (시장이 Fed 보다 더 가파른 인하 기대). 직전 분기 +30bp 에서 확대 — divergence 강화."

### 2. 핵심 근거 수집

- Fed SEP dot plot median 1y target rate (FOMC 분기 발표, macro.referenceFetch('fed_sep_dot_median'))
- Fed funds futures 1y implied rate (macro.seriesFetch('FEDFUNDS') 또는 OBFR)
- gap = dotMedian1y - marketImplied1y (% pt)

### 3. 메커니즘 분석

```
Fed dot median (12M forward) - market futures implied (12M)
   ↓
gap > +50bp  → marketDovish (시장이 Fed 보다 비둘기)
              가능 원인:
                ① 시장은 경기 둔화 + 침체 baseline
                ② Fed 가 hawkish guidance 유지하나 실현 신뢰 약함
                ③ 인플레 둔화 추세 + 정책 lag 우려
gap ±50bp    → aligned
gap < -50bp  → marketHawkish (시장이 Fed 보다 매파)
              가능 원인:
                ① 인플레 재가속 + Fed 둔화 의지 불신
                ② 노동시장 강세 지속
```

direction = marketDovish + 직전 분기 대비 갭 확대 → divergence 강화 phase. 갭 클수록 정책 surprise risk ↑ (Fed 가 시장 기대와 다르게 행동할 가능성).

### 4. 반례·한계

- dot plot 은 FOMC 위원 18 명 median — distribution 양극화 시 median 만으로 hawkish/dovish 단정 약함.
- Fed funds futures 는 risk premium 포함 — pure expectation 아님.
- SEP 는 분기 update — 갭 측정 시점에 따라 후행.
- 단일 시점 갭 vs 추세 분리 — 분기별 추적 필요.

### 5. 후속 모니터링

- marketDovish + 갭 확대 → `recipes.macro.usYieldCurveRegime` 로 curve 반응 점검.
- marketHawkish + HY spread 확대 → `recipes.fundamental.credit.usHighYieldSpread` 로 신용 reaction.
- aligned 지속 → `recipes.macro.inflationBreadthWatch` 로 인플레 트리거 미리 점검.

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
