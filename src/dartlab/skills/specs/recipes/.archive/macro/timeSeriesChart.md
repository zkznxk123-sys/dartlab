---
id: recipes.macro.timeSeriesChart
title: 경제 원자료 시계열 차트
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: gather.macro 로 가져온 경제 원자료를 line chart 로 emit 하여 AI 답변에 인라인 그래프를 붙이는 절차. 트리거 — '경제 그래프', '거시 시계열', '차트로 보여줘', '금리 추이', '물가 추이'.
whenToUse:
  - 경제 그래프
  - 거시 시계열
  - 차트로 보여줘
  - 금리 추이
  - 물가 추이
  - macro time series chart
linkedSkills:
  - engines.gather
  - engines.viz
  - recipes.macro.yieldCurveStress
  - recipes.macro.inflationBreadthWatch
toolRefs:
  - EngineCall
  - RunPython
  - CompileVisual
requiredEvidence:
  - skillRef
  - tableRef
  - dateRef
  - valueRef
  - executionRef
  - evidenceBinding
  - sourceRef
visualRefs:
  - "engines.viz.tableBackedChart"
  - "engines.viz.scenarioVisuals"
visualGuidance:
  - "표 기반 순위·추세는 engines.viz.tableBackedChart만 사용하고 tableRef/evidenceBinding이 없으면 차트 대신 검산 표로 낮춘다."
  - "stress·민감도·충격 전파는 engines.viz.scenarioVisuals를 사용하고 assumption grid 또는 수치 임계가 없으면 scenario table로 낮춘다."

gap:
  primary:
    - gather
    - viz
testUniverse:
  market: US
  asOfPolicy: latest
falsifier:
  description: "조회한 원자료 DataFrame 이 비어 있으면 차트를 emit 하지 않는다."
expectedNovelty:
  - chartSpec
  - rawSeriesChart
  - visualEvidenceBinding
forbidden:
  - 추측 데이터로 차트를 만들지 않는다.
  - evidenceIds 또는 evidenceBinding 없는 차트 emit 금지.
  - 단일 최신값만 있는 데이터는 line chart 로 만들지 않는다.
failureModes:
  - 지표 코드가 HF 카탈로그에 없어 빈 DataFrame 또는 예외가 발생.
  - 일별/월별/분기별 지표가 한 차트에 섞여 축 해석이 왜곡.
  - 너무 긴 시계열을 그대로 emit 해 UI가 무거워짐.
examples:
  - FEDFUNDS 추이를 그래프로 보여줘
  - CPIAUCSL 최근 5년 차트
  - T10Y2Y 금리차 그래프
lastUpdated: '2026-05-13'
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
---

## 공개 호출 방식

```python
import dartlab
from dartlab.viz import emitChart

indicator = "FEDFUNDS"
df = dartlab.gather("macro", indicator)

rows = []
if df is not None and len(df) > 0:
    recent = df.tail(60)
    dates = [str(v)[:10] for v in recent.get_column("date").to_list()]
    values = [float(v) for v in recent.get_column("value").to_list() if v is not None]
    rows = [{"date": d, "value": v} for d, v in zip(dates[-len(values):], values)]

if rows:
    emitChart({
        "chartType": "line",
        "title": f"{indicator} 최근 추이",
        "categories": [row["date"] for row in rows],
        "series": [{"name": indicator, "data": [row["value"] for row in rows]}],
        "evidenceIds": [f"gather:macro:{indicator}"],
    })

emit_result(
    table=rows,
    values={"indicator": indicator, "points": len(rows), "latest": rows[-1]["value"] if rows else None},
    date=rows[-1]["date"] if rows else None,
    sources=["dartlab://gather/macro"],
)
```

## 호출 동작

1. `dartlab.gather("macro", indicator)` 로 원자료 시계열을 가져온다.
2. UI 과부하를 막기 위해 최근 60개 관측치만 차트화한다.
3. `emitChart` 에 `chartType`, `categories`, `series`, `evidenceIds` 를 넣어 stdout 마커를 낸다.
4. `emit_result` 에 같은 rows를 tableRef 로 남겨 차트와 표가 같은 근거를 공유하게 한다.

## 대표 반환 형태

- `chartSpec`: line chart.
- `tableRef`: date/value rows.
- `valueRef`: indicator, points, latest.
- `dateRef`: 최신 관측일.

## 연계 절차

1. 금리곡선이면 `recipes.macro.yieldCurveStress` 로 해석한다.
2. 물가 계열이면 `recipes.macro.inflationBreadthWatch` 로 확산성을 확인한다.
3. 차트가 필요한 모든 gather-first recipe에서 이 패턴을 재사용한다.

## 기본 검증

- `rows` 가 비어 있으면 차트를 emit 하지 않는다.
- `evidenceIds` 는 반드시 `gather:macro:{indicator}` 형식으로 남긴다.
- 차트와 `emit_result.table` 의 행이 같은 원자료에서 나온 것인지 확인한다.
