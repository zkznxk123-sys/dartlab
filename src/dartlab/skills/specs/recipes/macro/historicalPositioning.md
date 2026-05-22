---
id: recipes.macro.historicalPositioning
title: 현재 매크로 위치의 역사적 비교
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: 현재 거시 상태를 1997 아시아 위기, 2008 금융위기, 2020 COVID, 2022 인플레 긴축 같은 역사적 충격과 나란히 비교해 지금의 위치를 설명하는 절차. 트리거 — '2008과 비교', '과거 위기 대비', '현재 위치', '역사적 percentile'.
whenToUse:
  - 과거 위기 비교
  - 2008 대비 현재
  - 2020 COVID 대비
  - 현재 매크로 위치
  - historical positioning
linkedSkills:
  - engines.macro
  - engines.company
  - engines.scan
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
    - macro
    - scenario
testUniverse:
  market: KR
  asOfPolicy: latest
falsifier:
  description: "비교 대상 시나리오의 meta/period/outcome 없이 현재와 비교하면 역사적 비교 recipe로 부적합하다."
expectedNovelty:
  - historicalAnalogue
  - scenarioDelta
  - crisisComparison
forbidden:
  - 역사적 사건을 현재와 동일하다고 단정하지 않는다.
  - 시나리오 override 결과를 실제 현재 데이터로 말하지 않는다.
  - 단일 사건 하나만 골라 결론을 고정하지 않는다.
failureModes:
  - 사건별 기간이 다르고 지표 빈도가 달라 직접 수치 비교가 왜곡됨.
  - 1997 KR 위기와 2008 US 위기를 같은 시장 기준으로 섞음.
  - scenario 결과의 delta와 현재 summary를 구분하지 못함.
examples:
  - 지금은 2008 금융위기와 얼마나 비슷한가
  - 현재 한국 거시 상황을 1997/2008/2020과 비교
  - 2022 인플레 긴축과 지금 금리 환경 비교
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

market = "KR"
try:
    current = dartlab.macro("summary", market=market)
except Exception as exc:
    current = {"error": str(exc)}
cycle = dartlab.macro("cycle", market=market)
crisis = dartlab.macro("crisis", market=market)

scenarioNames = ["1997 아시아 위기", "2008 금융위기", "2020 COVID", "2022 인플레 긴축"]
comparisons = []
for name in scenarioNames:
    try:
        scenario = dartlab.macro("scenario", name, market=market)
    except Exception as exc:
        scenario = {"error": str(exc)}
    comparisons.append({"scenarioName": name, "scenario": scenario})

emit_result(
    table=comparisons,
    values={
        "market": market,
        "currentOverall": current.get("overall") if isinstance(current, dict) else None,
        "currentScore": current.get("score") if isinstance(current, dict) else None,
        "cyclePhase": cycle.get("phase") if isinstance(cycle, dict) else None,
        "crisisZone": ((crisis.get("recessionDashboard") or {}).get("zone") if isinstance(crisis, dict) else None),
    },
    date=current.get("latestAsOf") if isinstance(current, dict) else None,
)
```

## 호출 동작

1. 현재 `summary`, `cycle`, `crisis` 를 먼저 고정한다.
2. 1997/2008/2020/2022 대표 충격을 `macro("scenario", name)` 으로 호출한다.
3. 각 scenario의 meta, delta, outcome을 현재 summary와 구분해 비교한다.
4. 가장 가까운 사건 1개를 고르기보다, 닮은 축과 다른 축을 분리한다.

## 대표 반환 형태

- `tableRef`: 역사적 사건별 scenario 결과와 delta.
- `valueRef`: 현재 overall/score, cyclePhase, crisisZone.
- `dateRef`: 현재 macro 기준일과 scenario period.
- 답변 본문: 닮은 점, 다른 점, 현재 판단에서 버려야 할 과거 아날로그.

## 연계 절차

1. 위기 유사성이 높으면 `recipes.fundamental.credit.cycleStressMap`.
2. scenario 손실 분포가 필요하면 `recipes.macro.tailRiskScenarioScan`.
3. 한국 시장 적용이 핵심이면 `recipes.macro.koreaMacroStressMap`.

## 기본 검증

- 현재 데이터와 scenario override를 같은 행에 두되 `current` / `scenario` 라벨을 분리한다.
- 비교 결과에는 최소 2개 이상의 역사적 사건을 포함한다.
- 가장 유사한 사건을 말할 때도 “완전 동일” 표현은 금지한다.
