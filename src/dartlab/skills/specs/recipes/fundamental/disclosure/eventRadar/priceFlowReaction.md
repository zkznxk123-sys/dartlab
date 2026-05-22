---
id: recipes.fundamental.disclosure.eventRadar.priceFlowReaction
title: Event Radar Price Flow Reaction
category: recipes
kind: recipe
scope: builtin
status: observed
graphTier: L1.5
cluster: incubator.eventRadar
purpose: gather price/flow 원자료로 이벤트 전후 가격·거래량·수급 반응을 확인하는 L1/L1.5 절차다.
whenToUse:
  - price flow reaction
  - 이벤트 주가 반응
  - 거래량 수급 확인
inputs:
  - price rows
  - flow rows
outputs:
  - priceFlowReaction table
capabilityRefs:
  - Company.gather
  - scan.market
toolRefs:
  - EngineCall
  - RunPython
knowledgeRefs:
  - engines.gather
  - engines.scan
sourceRefs:
  - dartlab://skills/recipes.fundamental.disclosure.eventRadar.priceFlowReaction
requiredEvidence:
  - skillRef
  - target
  - tableRef
  - valueRef
  - dateRef
  - sourceRef
  - executionRef
expectedOutputs:
  - priceChangePct
  - volumeRatio
  - foreign/institution net flow
visualRefs:
  - engines.viz.priceChart
  - engines.viz.kpiRibbon
visualGuidance:
  - "priceRows의 date/close/volume이 있을 때만 engines.viz.priceChart를 사용한다."
linkedSkills:
  - recipes.fundamental.disclosure.eventRadar.eventInbox
  - recipes.fundamental.disclosure.eventRadar.falsifierLedger
  - engines.company
gap:
  primary:
    - gather
    - synth
falsifier:
  description: "시장 전체 움직임이나 stale flow를 반증하지 않으면 실패로 본다."
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
  - 가격 급등락만으로 이벤트 원인을 단정하지 않는다.
failureModes:
  - 거래정지·액면분할을 가격 반응으로 오해
examples:
  - 공시 후 주가와 수급 반응 확인
audiences:
  llm: price/flow는 EngineCall로 먼저 가져오고 helper fallback은 계산 ledger만 만든다.
  agent: priceChart는 raw price row가 있을 때만 선택한다.
  human: 이벤트가 시장에서 실제로 반응했는지 확인한다.
humanIntro: "priceFlowReaction은 이벤트 후보와 시장 반응을 연결하지만, 원인 단정은 하지 않는다. 가격·거래량·수급은 falsifier와 함께 읽는다."
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
    flow_rows = rows(c.gather("flow"), limit=40)
except Exception:
    flow_rows = []

memo = buildEventRadarMemo(
    target=target,
    market=str(getattr(c, "market", "KR")),
    companyName=str(getattr(c, "corpName", target)),
    priceRows=price_rows,
    flowRows=flow_rows,
)

emit_result(
    table=memo["tables"]["priceFlowReaction"],
    values=memo["headline"],
    date=memo["asOf"],
    sources=memo["sources"],
)
```

## 호출 동작

최근 2개 price row로 `priceChangePct`와 `volumeRatio`를 계산하고, 최신 flow row의 외국인·기관 순매수를 함께 둔다.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `date` | 기준일 |
| `close` | 최신 종가 |
| `priceChangePct` | 직전 대비 변화율 |
| `volumeRatio` | 직전 대비 거래량 배수 |
| `netFlow` | 외국인+기관 순매수 |
| `status` | ok/watch/risk/missing |

## 연계 절차

1. recipes.fundamental.disclosure.eventRadar.eventInbox - 어떤 이벤트가 있었는지 확인.
2. recipes.fundamental.disclosure.eventRadar.falsifierLedger - market-wide move 반증.

## 기본 검증

- priceRows가 없으면 priceChart를 만들지 않는다.
- priceChangePct와 volumeRatio는 직전 row가 없으면 None으로 둔다.
