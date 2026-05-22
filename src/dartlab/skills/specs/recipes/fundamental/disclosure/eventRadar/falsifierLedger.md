---
id: recipes.fundamental.disclosure.eventRadar.falsifierLedger
title: Event Radar Falsifier Ledger
category: recipes
kind: recipe
scope: builtin
status: observed
graphTier: L1.5
cluster: incubator.eventRadar
purpose: 이벤트·반응·내부자·자본 이벤트·컨센서스 신호마다 필요한 반증 조건을 열어 결론 과잉을 막는 L1/L1.5 절차다.
whenToUse:
  - event radar falsifier
  - 촉매 반증
  - 이벤트 결론 검산
inputs:
  - event radar memo tables
outputs:
  - falsifierLedger table
capabilityRefs:
  - Company.disclosure
  - Company.gather
  - scan.market
toolRefs:
  - EngineCall
  - RunPython
knowledgeRefs:
  - runtime.workbenchEvidenceFlow
  - operation.skillDevelopmentLoop
sourceRefs:
  - dartlab://skills/recipes.fundamental.disclosure.eventRadar.falsifierLedger
requiredEvidence:
  - skillRef
  - target
  - tableRef
  - valueRef
  - dateRef
  - sourceRef
  - executionRef
expectedOutputs:
  - claim별 supportingEvidence
  - counterEvidenceNeeded
  - open/notTriggered status
visualRefs:
  - engines.viz.evidenceCoverage
visualGuidance:
  - "falsifierLedger는 table/표가 1차 산출물이며 evidenceCoverage는 open/notTriggered 개수만 보조한다."
linkedSkills:
  - recipes.fundamental.disclosure.eventRadar.eventInbox
  - recipes.fundamental.disclosure.eventRadar.priceFlowReaction
  - recipes.fundamental.disclosure.eventRadar.deepDive
gap:
  primary:
    - synth
    - gather
falsifier:
  description: "open falsifier를 숨기면 실패로 본다."
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
  - open falsifier가 있는데 촉매 결론을 확정하지 않는다.
failureModes:
  - 반증 조건 없이 radarScore만 표시
examples:
  - 이벤트 레이더 반증 ledger
audiences:
  llm: helper fallback 결과의 falsifierLedger를 반드시 답변에 포함한다.
  agent: open falsifier 개수와 내용을 valueRef/tableRef에 묶는다.
  human: 촉매 후보가 틀릴 수 있는 이유를 먼저 확인한다.
humanIntro: "falsifierLedger는 이 팩의 안전장치다. 좋은 이벤트처럼 보여도 반증이 열려 있으면 결론은 보류한다."
lastUpdated: "2026-05-17"
testUniverse:
  market: KR
  stockCodes:
    - "005930"
---

## 공개 호출 방식

AI 도구 실행 순서는 `EngineCall` 우선이다. 아래 Python 블록은 확보한 L1/L1.5 근거를 `buildEventRadarMemo`로 묶는 **RunPython fallback** 절차다.

```python
import dartlab
from dartlab.synth.eventRadar import buildEventRadarMemo

target = "005930"
c = dartlab.Company(target)

def rows(value, limit=30):
    if hasattr(value, "head") and hasattr(value, "to_dicts"):
        return value.head(limit).to_dicts()
    if isinstance(value, list):
        return value[:limit]
    return []

try:
    filings = rows(c.disclosure(), limit=50)
except Exception:
    filings = []

try:
    price_rows = rows(c.gather("price"), limit=40)
except Exception:
    price_rows = []

try:
    flow_rows = rows(c.gather("flow"), limit=40)
except Exception:
    flow_rows = []

memo = buildEventRadarMemo(
    target=target,
    market=str(getattr(c, "market", "KR")),
    companyName=str(getattr(c, "corpName", target)),
    filings=filings,
    priceRows=price_rows,
    flowRows=flow_rows,
)

emit_result(
    table=memo["tables"]["falsifierLedger"],
    values=memo["headline"],
    date=memo["asOf"],
    sources=memo["sources"],
)
```

## 호출 동작

event, reaction, insider, capital, consensus 신호마다 supportingEvidence와 counterEvidenceNeeded를 만든다.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `claim` | 검증 중인 주장 |
| `supportingEvidence` | ok/watch/risk/missing |
| `counterEvidenceNeeded` | 필요한 반증 |
| `status` | open/notTriggered |

## 연계 절차

1. recipes.fundamental.disclosure.eventRadar.engineCandidateMemo - 반복 가능한 신호만 후보로 넘긴다.
2. recipes.fundamental.disclosure.eventRadar.deepDive - 최종 답변에 open falsifier를 포함한다.

## 기본 검증

- open falsifier가 있으면 확정 표현을 쓰지 않는다.
- counterEvidenceNeeded가 빈 문자열이면 실패다.
