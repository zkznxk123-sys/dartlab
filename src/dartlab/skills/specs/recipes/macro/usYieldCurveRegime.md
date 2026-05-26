---
id: recipes.macro.usYieldCurveRegime
title: 미국 yield curve regime (10y-2y / 10y-3m 동시)
category: recipes
kind: recipe
scope: builtin
status: tested
purpose: 미국 국채 10y-2y + 10y-3m 두 spread 동시 추적. 둘 다 inversion (음수) 이면 *strong recession signal*. 단일 spread (10y-2y만) 함정 회피. FRED raw 직접.
whenToUse:
  - 미국 yield curve
  - inversion signal
  - 10y-2y 10y-3m
  - US recession indicator
examples:
  - 미국 yield curve inversion 신호 정량
  - 10y-2y + 10y-3m 동시 음수면 recession 신호
  - US 국채 spread 체제 — strong / soft / steepening
expectedOutputs:
  - 10y-2y spread + 10y-3m spread 단일값 (bp)
  - 두 spread 동시 inversion 여부 boolean
  - regime 라벨 (strong recession / soft inversion / steepening / normal)
linkedSkills:
  - engines.macro
  - engines.gather
  - recipes.macro.scenarioAnalysis
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
  tickers:
    - "DGS10"
    - "DGS2"
    - "DGS3MO"
falsifier:
  description: "단일 spread inversion 만으로 recession 단정 X — 두 spread 동시 + 지속 6 개월 임계."
lastUpdated: "2026-05-22"
---

## 공개 호출 방식

```python
import dartlab
import polars as pl

# FRED 시리즈
try:
    s10y = dartlab.macro.seriesFetch("DGS10").to_dicts()
    s2y = dartlab.macro.seriesFetch("DGS2").to_dicts()
    s3m = dartlab.macro.seriesFetch("DGS3MO").to_dicts()
except Exception:
    s10y = s2y = s3m = []

by_date = {}
for r in s10y:
    by_date.setdefault(str(r.get("date"))[:10], {})["t10y"] = float(r.get("value") or 0)
for r in s2y:
    by_date.setdefault(str(r.get("date"))[:10], {})["t2y"] = float(r.get("value") or 0)
for r in s3m:
    by_date.setdefault(str(r.get("date"))[:10], {})["t3m"] = float(r.get("value") or 0)

rows = []
for d in sorted(by_date.keys())[-60:]:
    v = by_date[d]
    if all(k in v for k in ("t10y", "t2y", "t3m")):
        rows.append({
            "date": d,
            "spread_10y_2y": v["t10y"] - v["t2y"],
            "spread_10y_3m": v["t10y"] - v["t3m"],
            "inversionBoth": v["t10y"] < v["t2y"] and v["t10y"] < v["t3m"],
        })

table = pl.DataFrame(rows) if rows else pl.DataFrame(
    schema={"date": pl.Utf8, "spread_10y_2y": pl.Float64, "spread_10y_3m": pl.Float64, "inversionBoth": pl.Boolean}
)

both_n = int(table["inversionBoth"].sum()) if table.height else 0
latest = table.tail(1).to_dicts()[0] if table.height else {}

emit_result(
    table=table,
    values={"inversionBothCount": both_n, "latestSpread10y2y": latest.get("spread_10y_2y"),
            "latestSpread10y3m": latest.get("spread_10y_3m")},
    date=latest.get("date"),
    sources=["dartlab://macro/fred"],
)
```

## 호출 동작

FRED DGS10/DGS2/DGS3MO 시리즈에서 두 spread 동시 추적. 두 spread 모두 음수 = `inversionBoth=True` = strong recession signal.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `date` | 일자 |
| `spread_10y_2y` | 10y - 2y |
| `spread_10y_3m` | 10y - 3m |
| `inversionBoth` | 둘 다 inversion |

## 연계 절차

1. recipes.macro.scenarioAnalysis - inversion 시 시나리오 grid.
2. recipes.macro.dollarFundingStress - 동시 달러 funding stress 확인.

## 기본 검증

- 두 시리즈 모두 raw 필요.
- 단일 spread 만으로 recession 단정 금지.
- *inversion* = recession 인과 단정 X — 통계 상관 (1955 이후 모든 recession 선행).
