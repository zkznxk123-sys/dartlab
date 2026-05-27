---
id: recipes.macro.usYieldCurveRegime
title: 미국 yield curve regime (10y-2y / 10y-3m 동시)
category: recipes
kind: recipe
scope: builtin
status: curated
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
validatedAt: '2026-05-27'
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

### 1. 결론 도출

dual spread inversion + regime 단정. 예: "최신 60일: 10y-2y = -0.45% / 10y-3m = +0.08% → inversionBoth=False (10y-3m 정상화). 60일 안 inversionBoth=True 일수 18일 (30% 비중) → soft inversion (단일 spread만 음수) phase — strong recession 임계 미달."

### 2. 핵심 근거 수집

- FRED DGS10 (10y), DGS2 (2y), DGS3MO (3m) — macro.seriesFetch 3 시리즈
- 일자별 spread 계산: spread_10y_2y, spread_10y_3m
- inversionBoth = (10y < 2y) AND (10y < 3m)
- 최근 60일 + 누적 inversionBoth 일수

### 3. 메커니즘 분석

```
3 시리즈 → 일자별 join → 2 spread + boolean
   spread_10y_2y > 0  → 정상 (long > short)
   spread_10y_2y < 0  → 부분 inversion
   spread_10y_3m > 0  → 단기 정상
   spread_10y_3m < 0  → 단기 inversion (정책금리 vs 장기 mismatch)
   ↓
4 regime 판정:
   둘 다 음수 (inversionBoth) + 60일 누적 ≥ 30일 → strong recession signal
   1 spread 만 음수                                 → soft inversion (대기)
   둘 다 양수 + 추세 확장                            → steepening (회복 후)
   둘 다 양수 + 평탄                                 → normal
   ↓
historical 패턴:
   1955-2024 US — inversionBoth 발생 후 12-18M 침체 (10/10)
   2022-2024 inversionBoth 후 침체 미발현 (예외 가능성)
   inversion 해제 후 침체 도래까지 lag 잔존
```

dual spread inversion = strong signal — 단일 spread (10y-2y 만) 함정 회피. 10y-3m 도 동시 음수 필요. 통계 상관 (인과 아님) — 1955 이후 모든 recession 선행 패턴.

### 4. 반례·한계

- 두 시리즈 raw 필요 — 하나만 결손 시 결론 X.
- 60일 window 너무 짧으면 일시 inversion 으로 strong recession 오인.
- 2022-2024 inversion 후 침체 미발현 — 모델 예외 패턴 검증 필요.
- *상관* 아니라 *인과* 단정 금지 — Fed 정책 → curve 형성 → 침체 도래 mechanism.

### 5. 후속 모니터링

- inversionBoth=True + 60일 누적 ≥ 30일 → `recipes.macro.tailRiskScenarioScan` 으로 침체 시나리오.
- soft inversion (1 spread 만) → `recipes.macro.usFedDotPlotGap` 으로 Fed-시장 갭 점검.
- inversion + HY spread 확대 → `recipes.fundamental.credit.usHighYieldSpread` 로 credit market 동조 확인.

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
