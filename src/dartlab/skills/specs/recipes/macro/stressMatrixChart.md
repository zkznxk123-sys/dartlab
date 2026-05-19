---
id: recipes.macro.stressMatrixChart
title: 경제 스트레스 매트릭스 차트
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: 금리, 인플레이션, 노동시장, 달러, 신용 스트레스 지표를 gather 원자료로 모아 bar chart 또는 heatmap 형태로 emit 하는 절차. 트리거 — '스트레스 그래프', '경제 위험 차트', '리스크 매트릭스', 'stress matrix'.
whenToUse:
  - 스트레스 그래프
  - 경제 위험 차트
  - 리스크 매트릭스
  - stress matrix
  - macro stress chart
linkedSkills:
  - engines.gather
  - engines.viz
  - recipes.macro.tailRiskScenarioScan
  - recipes.macro.dollarFundingStress
  - recipes.fundamental.credit.cycleStressMap
toolRefs:
  - EngineCall
  - RunPython
  - CompileVisual
requiredEvidence:
  - skillRef
  - tableRef
  - valueRef
  - dateRef
  - evidenceBinding
visualRefs:
  - "engines.viz.scenarioVisuals"
  - "engines.viz.tableBackedChart"
visualGuidance:
  - "stress·민감도·충격 전파는 engines.viz.scenarioVisuals를 사용하고 assumption grid 또는 수치 임계가 없으면 scenario table로 낮춘다."
  - "표 기반 순위·추세는 engines.viz.tableBackedChart만 사용하고 tableRef/evidenceBinding이 없으면 차트 대신 검산 표로 낮춘다."

runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
gap:
  primary:
    - gather
    - viz
testUniverse:
  market: US
  asOfPolicy: latest
falsifier:
  description: "성공한 스트레스 지표가 3개 미만이면 매트릭스 차트로 emit 하지 않는다."
expectedNovelty:
  - stressScoreChart
  - visualRiskRanking
  - rawIndicatorMatrix
forbidden:
  - 정규화 기준 없이 서로 다른 단위 값을 그대로 합산하지 않는다.
  - 임계값을 투자 권고로 표현하지 않는다.
  - evidence 없는 bar/heatmap emit 금지.
failureModes:
  - 지표 단위가 bp, %, index 로 섞임.
  - 최신값만 쓰면 방향성이 사라짐.
  - 일부 지표 결손 시 전체 스트레스 점수가 왜곡.
examples:
  - 경제 위험 지표를 그래프로 보여줘
  - VIX HY 금리차 실업률을 한 번에 차트화
  - 스트레스 높은 순서 bar chart
lastUpdated: '2026-05-13'
---

## 공개 호출 방식

```python
import dartlab
from dartlab.viz import emitChart

indicators = ["T10Y2Y", "CPIAUCSL", "UNRATE", "VIXCLS", "BAMLH0A0HYM2", "DTWEXBGS"]
rows = []
for indicator in indicators:
    try:
        df = dartlab.gather("macro", indicator)
        if df is None or len(df) == 0:
            rows.append({"indicator": indicator, "ok": False, "reason": "empty"})
            continue
        vals = df.get_column("value").drop_nulls().to_list()
        if not vals:
            rows.append({"indicator": indicator, "ok": False, "reason": "no_values"})
            continue
        latest = float(vals[-1])
        prev = float(vals[-13]) if len(vals) >= 13 else float(vals[0])
        change = latest - prev
        rows.append({"indicator": indicator, "latest": latest, "change": change, "ok": True})
    except Exception as exc:
        rows.append({"indicator": indicator, "ok": False, "reason": str(exc)})

chartRows = [row for row in rows if row.get("ok")]
if len(chartRows) >= 3:
    emitChart({
        "chartType": "bar",
        "title": "경제 스트레스 원자료 변화",
        "categories": [row["indicator"] for row in chartRows],
        "series": [{"name": "change", "data": [row["change"] for row in chartRows]}],
        "evidenceIds": [f"gather:macro:{row['indicator']}" for row in chartRows],
    })

emit_result(
    table=rows,
    values={"indicatorCount": len(indicators), "chartCount": len(chartRows)},
    date=None,
)
```

## 호출 동작

1. 스트레스 후보 지표를 gather로 수집한다.
2. 각 지표의 최신값과 12관측치 전 대비 변화를 계산한다.
3. 성공 지표가 3개 이상이면 bar chart 를 emit 한다.
4. 실패 지표는 `reason` 으로 남겨 데이터 결손을 숨기지 않는다.

## 대표 반환 형태

- `chartSpec`: bar chart.
- `tableRef`: indicator/latest/change/ok/reason.
- `valueRef`: indicatorCount, chartCount.

## 연계 절차

1. 달러/환율 신호가 크면 `recipes.macro.dollarFundingStress`.
2. 신용/스프레드 신호가 크면 `recipes.fundamental.credit.cycleStressMap`.
3. 금리곡선 신호가 크면 `recipes.macro.yieldCurveStress`.

## 기본 검증

- 단위가 다르므로 `change`는 순위 힌트이지 통합 점수가 아니다.
- 성공 지표 3개 미만이면 차트를 emit 하지 않는다.
- bar chart 뒤에는 어떤 지표가 어떤 단위인지 표로 함께 설명한다.
