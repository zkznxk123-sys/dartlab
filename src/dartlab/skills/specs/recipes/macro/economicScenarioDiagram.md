---
id: recipes.macro.economicScenarioDiagram
title: 경제 시나리오 인과 다이어그램
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: macro.scenario 또는 경제분석 결과를 Mermaid 인과 그래프로 emit 하여 충격 전파 경로를 시각화하는 절차. 트리거 — '시나리오 그래프', '인과 다이어그램', '충격 전파', '경제 흐름도'.
whenToUse:
  - 시나리오 그래프
  - 인과 다이어그램
  - 충격 전파
  - 경제 흐름도
  - mermaid
linkedSkills:
  - engines.macro.scenario
  - engines.viz
  - recipes.macro.tailRiskScenarioScan
  - recipes.macro.historicalPositioning
toolRefs:
  - RunPython
  - CompileVisual
requiredEvidence:
  - skillRef
  - sourceRef
  - executionRef
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: supported
gap:
  primary:
    - macro
    - viz
testUniverse:
  market: US
  asOfPolicy: latest
falsifier:
  description: "시나리오 이름 또는 충격 경로가 없으면 다이어그램을 만들지 않는다."
expectedNovelty:
  - scenarioDiagram
  - causalPath
  - visualNarrative
forbidden:
  - 원인과 결과가 검증되지 않은 임의 노드를 추가하지 않는다.
  - 시나리오 다이어그램을 실제 예측 경로로 단정하지 않는다.
  - 너무 많은 노드로 읽기 어려운 그래프를 만들지 않는다.
failureModes:
  - scenario meta에 transmission이 없어 일반 경로를 사용해야 함.
  - 다이어그램이 설명보다 장식으로 쓰임.
  - 조건부 충격 경로를 확률 예측으로 오해.
examples:
  - 2008 금융위기 충격 전파를 다이어그램으로 보여줘
  - 인플레이션 충격이 금리와 신용으로 가는 흐름도
  - 달러 스트레스 인과 그래프
lastUpdated: '2026-05-12'
---

## 공개 호출 방식

```python
import dartlab
from dartlab.viz import emitDiagram

scenarioName = "2008 금융위기"
try:
    scenario = dartlab.macro("scenario", scenarioName, market="US")
except Exception as exc:
    scenario = {"error": str(exc), "meta": {"description": scenarioName, "type": "신용 충격"}}
meta = scenario.get("meta") if isinstance(scenario, dict) else {}
description = (meta or {}).get("description") or scenarioName
scenarioType = (meta or {}).get("type") or "신용 충격"

source = f"""graph LR
  A["{scenarioName}"] --> B["{scenarioType}"]
  B --> C["금융상태 긴축"]
  C --> D["실물 경기 둔화"]
  D --> E["시장 가격 재평가"]
  E --> F["대응: rates/crisis/forecast 재점검"]
"""

emitDiagram("mermaid", source, title=f"{scenarioName} 충격 전파")

emit_result(
    table=[{"scenarioName": scenarioName, "type": scenarioType, "description": description}],
    values={"scenarioName": scenarioName, "scenarioType": scenarioType},
    date=None,
)
```

## 호출 동작

1. `macro("scenario", scenarioName)` 으로 scenario meta를 가져온다.
2. scenarioName, type, description을 고정한다.
3. 6개 이하 노드의 Mermaid graph로 충격 전파를 시각화한다.
4. 다이어그램과 함께 scenario meta를 tableRef로 남긴다.

## 대표 반환 형태

- `diagramSpec`: Mermaid graph.
- `tableRef`: scenarioName/type/description.
- `valueRef`: scenarioName, scenarioType.

## 연계 절차

1. 여러 scenario 비교는 `recipes.macro.tailRiskScenarioScan`.
2. 역사적 사건 비교는 `recipes.macro.historicalPositioning`.
3. 차트형 수치 비교는 `recipes.macro.economicStressMatrixChart`.

## 기본 검증

- 노드는 6개 이하로 유지한다.
- scenario type이 없으면 “조건부 충격” 같은 중립 레이블을 사용한다.
- 다이어그램은 설명 보조이며 확률 예측으로 말하지 않는다.
