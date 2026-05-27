---
id: recipes.fundamental.credit.usHighYieldSpread
title: 미국 High Yield OAS spread regime (BofA HY OAS)
category: recipes
kind: recipe
scope: builtin
status: curated
purpose: ICE BofA US High Yield OAS spread 시계열 z-score. 4%p 이상 = stress, 8%p 이상 = crisis 임계. 단일 회사가 아닌 *credit market regime* 신호. FRED `BAMLH0A0HYM2` raw.
whenToUse:
  - US HY spread
  - high yield credit regime
  - OAS stress threshold
  - credit market 신호
examples:
  - 미국 HY spread 가 지금 stress 구간이야
  - BofA OAS spread regime — 4%p / 8%p 임계
  - 글로벌 credit market 위기 신호
expectedOutputs:
  - 현재 OAS spread (%p) + z-score (장기 평균 대비)
  - regime 라벨 (normal / stress / crisis — 4%p / 8%p 임계)
  - 시계열 chart (24mo OAS + z-score band)
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
validatedAt: '2026-05-27'
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

### 1. 결론 도출

latestSpread + regime + zScore 단정. 예: "BofA US HY OAS = 4.2% (latest) → regime=stress (4%p 임계 초과). 60일 baseline mean 3.5% / std 0.4 → z = +1.8 (현재 평균 대비 1.8σ 위) — credit market 진입 stress 초기, crisis 임계 (8%) 까지 3.8%p 여유."

### 2. 핵심 근거 수집

- FRED 'BAMLH0A0HYM2' (ICE BofA US HY OAS) — macro.seriesFetch
- 최근 60 일 (sampleN ≥ 30) baseline mean + std
- 최신 spread vs baseline → z-score
- regime 임계: < 4% (normal) / 4-8% (stress) / ≥ 8% (crisis)

### 3. 메커니즘 분석

```
HY OAS 시계열 → 최근 60 일 + 최신 값
   mean(60일) + std(60일) → baseline
   z = (latest - mean) / std
   ↓
regime 판정:
   spread < 4%      → normal (정상)
   4% ≤ spread < 8% → stress (긴장 — 회사채 issue 비용 ↑)
   spread ≥ 8%      → crisis (위기 — 2008 / 2020 수준)
   ↓
z-score 보조:
   z > +2          → 평균 대비 급등 (regime 전환 후보)
   |z| < 1         → 안정 추세
   z < -2          → 평균 대비 급락 (compression — 자산가격 동행 가능)
```

크레딧 cycle 의 가장 빠른 신호. yield curve + HY spread 동시 신호 시 recession nowcast 강 (Tobin / Bernanke 학계 결과). 단일 시점 임계 초과만으로 recession 단정 X — 지속 기간 (≥ 3 개월) 필수.

### 4. 반례·한계

- 임계 4%/8% 는 historical 평균 기반 — 시기별 정의 다름 (현재 baseline 은 1997-2024).
- 60 일 baseline 짧음 — regime shift 시 z 후행.
- HY index 구성 (B/CCC 비중) 시기별 변화 — apple-to-apple 비교 한계.
- US-only — KR 시장 spread 분리 필요.

### 5. 후속 모니터링

- stress 진입 → `recipes.macro.tailRiskScenarioScan` 으로 신용 시나리오 매핑.
- stress + yield curve inversion → `recipes.macro.usFedDotPlotGap` 으로 Fed-시장 갭 점검.
- crisis 진입 → `recipes.fundamental.credit.cycleStressMap` 으로 회사별 credit cycle 영향.

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
