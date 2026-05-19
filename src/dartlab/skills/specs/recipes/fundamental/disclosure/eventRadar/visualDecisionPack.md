---
id: recipes.fundamental.disclosure.eventRadar.visualDecisionPack
title: Event Radar Visual Decision Pack
category: recipes
kind: recipe
scope: builtin
status: observed
graphTier: L1.5
cluster: incubator.eventRadar
purpose: 이벤트 레이더 결과에서 사용할 수 있는 observed viz surface만 선택하고, evidenceBinding이 없으면 차트를 막는 L1/L1.5 절차다.
whenToUse:
  - event radar visualization
  - 촉매 레이더 차트
  - observed viz binding
inputs:
  - event radar memo tables
outputs:
  - visualDecisionPack table
capabilityRefs:
  - Company.gather
toolRefs:
  - EngineCall
  - RunPython
knowledgeRefs:
  - engines.viz
  - runtime.workbenchEvidenceFlow
sourceRefs:
  - dartlab://skills/recipes.fundamental.disclosure.eventRadar.visualDecisionPack
requiredEvidence:
  - skillRef
  - target
  - tableRef
  - valueRef
  - dateRef
  - sourceRef
  - executionRef
expectedOutputs:
  - visualRef별 ready/blocked
  - requiredBinding
visualRefs:
  - engines.viz.priceChart
  - engines.viz.kpiRibbon
  - engines.viz.evidenceCoverage
  - engines.viz.mermaidDiagram
visualGuidance:
  - "사용 가능한 visualRef는 observed 상태의 priceChart, kpiRibbon, evidenceCoverage, mermaidDiagram으로 제한한다."
  - "requiredBinding이 blocked이면 차트 대신 tableRef를 답변한다."
linkedSkills:
  - recipes.fundamental.disclosure.eventRadar.sourceCoverageAudit
  - recipes.fundamental.disclosure.eventRadar.deepDive
gap:
  primary:
    - viz
    - synth
falsifier:
  description: "근거 없는 시각화를 만들면 실패로 본다."
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: supported
  pyodide:
    status: limited
forbidden:
  - unverified viz skill을 visualRefs에 연결하지 않는다.
  - priceRows 없이 priceChart를 만들지 않는다.
failureModes:
  - blocked visual을 무시하고 차트 emit
examples:
  - 이벤트 레이더 시각화 가능 여부 확인
audiences:
  llm: visualDecisionPack의 ready visualRef만 사용한다.
  agent: 차트를 만들기 전 requiredBinding을 확인한다.
  human: 시각화가 가능한 결과와 아직 표로 봐야 하는 결과를 구분한다.
humanIntro: "visualDecisionPack은 사용자가 요청한 시각 요소 품질 게이트다. 완성도 높은 observed viz만 연결하고, 근거가 없으면 막는다."
lastUpdated: "2026-05-17"
---

## 공개 호출 방식

AI 도구 실행 순서는 `EngineCall` 우선이다. 아래 Python 블록은 확보한 L1/L1.5 근거를 `buildEventRadarMemo`로 묶는 **RunPython fallback** 절차다.

```python
import dartlab
from dartlab.synth.eventRadar import buildEventRadarMemo

target = "005930"
c = dartlab.Company(target)

def rows(value, limit=40):
    if hasattr(value, "head") and hasattr(value, "to_dicts"):
        return value.head(limit).to_dicts()
    if isinstance(value, list):
        return value[:limit]
    return []

try:
    price_rows = rows(c.gather("price"), limit=40)
except Exception:
    price_rows = []

try:
    filings = rows(c.disclosure(), limit=50)
except Exception:
    filings = []

memo = buildEventRadarMemo(
    target=target,
    market=str(getattr(c, "market", "KR")),
    companyName=str(getattr(c, "corpName", target)),
    filings=filings,
    priceRows=price_rows,
)

emit_result(
    table=memo["tables"]["visualDecisionPack"],
    values=memo["headline"],
    date=memo["asOf"],
    sources=memo["sources"],
)
```

## 호출 동작

priceRows, coverage, signal count를 기준으로 priceChart, kpiRibbon, evidenceCoverage, mermaidDiagram의 ready/blocked를 결정한다.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `visualRef` | observed viz skill |
| `status` | ready/blocked |
| `requiredBinding` | 필요한 근거 결합 |
| `evidence` | 선택 사유 |

## 연계 절차

1. recipes.fundamental.disclosure.eventRadar.sourceCoverageAudit - source coverage 확인.
2. recipes.fundamental.disclosure.eventRadar.deepDive - 최종 답변의 visual gate.

## 기본 검증

- visualRefs는 observed viz만 포함한다.
- blocked visualRef를 emit하지 않는다.
