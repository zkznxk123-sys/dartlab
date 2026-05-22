---
id: recipes.macro.laborMarketTurningPoint
title: 노동시장 전환점 원자료 점검
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: 실업률, 신규실업수당, 비농업고용, 임금, Sahm rule 관련 원자료를 gather로 확인하고 macro.forecast와 대조해 노동시장 둔화의 전환점을 찾는 절차. 트리거 — '노동시장 둔화', '실업률', '고용 전환점', 'Sahm rule'.
whenToUse:
  - 노동시장 둔화
  - 실업률
  - 신규실업수당
  - 고용 전환점
  - Sahm rule
linkedSkills:
  - engines.gather
  - engines.macro
  - engines.company
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - dateRef
  - valueRef
  - executionRef
  - sourceRef
visualRefs:
  - "engines.viz.scenarioVisuals"
  - "engines.viz.tableBackedChart"
  - "engines.viz.mermaidDiagram"
visualGuidance:
  - "stress·민감도·충격 전파는 engines.viz.scenarioVisuals를 사용하고 assumption grid 또는 수치 임계가 없으면 scenario table로 낮춘다."
  - "표 기반 순위·추세는 engines.viz.tableBackedChart만 사용하고 tableRef/evidenceBinding이 없으면 차트 대신 검산 표로 낮춘다."
  - "메커니즘 diagram은 engines.viz.mermaidDiagram으로 8노드 이하만 만들고 모든 edge에 문장·수치·sourceRef 근거를 둔다."

gap:
  primary:
    - gather
    - macro
testUniverse:
  market: US
  asOfPolicy: latest
falsifier:
  description: "실업률 또는 신규실업수당 원자료가 없으면 노동시장 전환점 판정을 하지 않는다."
expectedNovelty:
  - laborRawTable
  - turningPointSignal
  - forecastCrossCheck
forbidden:
  - 고용지표 한 달치 변화로 추세 전환을 단정하지 않는다.
  - 임금 상승을 항상 경기 호조로만 해석하지 않는다.
  - Sahm rule 신호와 recession nowcast를 혼동하지 않는다.
failureModes:
  - 고용지표 revision이 커서 최신 발표치가 바뀔 수 있음.
  - 실업률과 신규실업수당의 선후행 차이.
  - 임금은 인플레이션과 노동수요를 동시에 반영.
examples:
  - 미국 노동시장 전환점 확인
  - 신규실업수당과 실업률로 경기 둔화 봐줘
  - Sahm rule 위험 점검
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

market = "US"
indicators = ["UNRATE", "ICSA", "PAYEMS", "AHEPA", "CIVPART", "JTSJOL"]
rows = []
for indicator in indicators:
    try:
        data = dartlab.gather("macro", indicator)
        rows.append({"indicator": indicator, "data": data, "ok": True})
    except Exception as exc:
        rows.append({"indicator": indicator, "error": str(exc), "ok": False})

try:
    forecast = dartlab.macro("forecast", market=market)
except Exception as exc:
    forecast = {"error": str(exc)}
try:
    cycle = dartlab.macro("cycle", market=market)
except Exception as exc:
    cycle = {"error": str(exc)}
try:
    summary = dartlab.macro("summary", market=market)
except Exception as exc:
    summary = {"error": str(exc)}

emit_result(
    table=rows,
    values={
        "market": market,
        "sahmRule": ((forecast.get("sahmRule") or {}).get("signal") if isinstance(forecast, dict) else None),
        "cyclePhase": cycle.get("phase") if isinstance(cycle, dict) else None,
        "summaryOverall": summary.get("overall") if isinstance(summary, dict) else None,
    },
    date=summary.get("latestAsOf") if isinstance(summary, dict) else None,
)
```

## 호출 동작

1. 노동시장 원자료를 gather로 모은다.
2. 실업률, 신규실업수당, 고용자수, 임금, 구인건수의 방향을 분리한다.
3. `macro("forecast")` 의 Sahm/침체확률 신호와 대조한다.
4. `macro("cycle")` 과 종합해 “둔화 초기/후기/판정불가”로 말한다.

## 대표 반환 형태

- `tableRef`: 노동시장 indicator별 원자료.
- `valueRef`: sahmRule, cyclePhase, summaryOverall.
- 답변 본문: 노동시장 전환 신호와 아직 버티는 신호.

## 연계 절차

1. 노동시장 둔화가 확인되면 `engines.macro` 로 침체확률과 LEI를 함께 확인한다.
2. 금리곡선 선행 신호와 비교하려면 `recipes.macro.yieldCurveStress` 로 이동한다.
3. 신용 스트레스가 동반되면 `recipes.fundamental.credit.cycleStressMap` 으로 확장한다.

## 기본 검증

- 한 지표만 성공하면 결론 대신 추가 데이터 필요로 표시한다.
- 신규실업수당과 실업률의 시차를 분리한다.
