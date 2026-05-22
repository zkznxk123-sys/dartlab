---
id: recipes.fundamental.disclosure.eventRadar.insiderOwnershipSignal
title: Event Radar Insider Ownership Signal
category: recipes
kind: recipe
scope: builtin
status: observed
graphTier: L1.5
cluster: incubator.eventRadar
purpose: gather insiderTrading, ownership, majorShareholders 원자료로 내부자·주요주주 변화 신호를 확인하는 L1/L1.5 절차다.
whenToUse:
  - insider ownership signal
  - 내부자 거래
  - 주요주주 지분 변화
inputs:
  - insider rows
  - ownership rows
outputs:
  - insiderOwnershipSignal table
capabilityRefs:
  - Company.gather
toolRefs:
  - EngineCall
  - RunPython
knowledgeRefs:
  - engines.gather
  - engines.scan
sourceRefs:
  - dartlab://skills/recipes.fundamental.disclosure.eventRadar.insiderOwnershipSignal
requiredEvidence:
  - skillRef
  - target
  - tableRef
  - valueRef
  - dateRef
  - sourceRef
  - executionRef
expectedOutputs:
  - insider/holder direction
  - amount 또는 지분 변화
visualRefs:
  - engines.viz.evidenceCoverage
visualGuidance:
  - "내부자·주요주주 row는 table/표가 우선이며 source coverage만 engines.viz.evidenceCoverage로 보조한다."
linkedSkills:
  - recipes.fundamental.disclosure.eventRadar.falsifierLedger
  - recipes.fundamental.disclosure.eventRadar.deepDive
gap:
  primary:
    - gather
    - synth
falsifier:
  description: "계획 매도, 주식보상, treasury transfer를 반증하지 않으면 실패로 본다."
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
  - 내부자 매수·매도를 선행 정보로 단정하지 않는다.
failureModes:
  - 계획 매도를 부정적 신호로 단정
examples:
  - 내부자 매수와 주요주주 지분 변화 확인
audiences:
  llm: insider/ownership row를 EngineCall로 확보한 뒤 helper fallback으로 정리한다.
  agent: holder, direction, amount, date를 함께 제시한다.
  human: 지분 변화가 이벤트 레이더의 보조 촉매인지 확인한다.
humanIntro: "insiderOwnershipSignal은 거래 방향을 표시하지만 의도는 해석하지 않는다. 계획 매도와 데이터 지연은 반드시 반증 조건으로 남긴다."
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

def rows(value, limit=20):
    if hasattr(value, "head") and hasattr(value, "to_dicts"):
        return value.head(limit).to_dicts()
    if isinstance(value, list):
        return value[:limit]
    return []

try:
    insider_rows = rows(c.gather("insiderTrading"), limit=20)
except Exception:
    insider_rows = []

try:
    ownership_rows = rows(c.gather("ownership"), limit=20)
except Exception:
    ownership_rows = []

memo = buildEventRadarMemo(
    target=target,
    market=str(getattr(c, "market", "KR")),
    companyName=str(getattr(c, "corpName", target)),
    insiderRows=insider_rows,
    ownershipRows=ownership_rows,
)

emit_result(
    table=memo["tables"]["insiderOwnershipSignal"],
    values=memo["headline"],
    date=memo["asOf"],
    sources=memo["sources"],
)
```

## 호출 동작

내부자 거래와 지분 변화 row에서 holder, direction, amount, status를 추출한다.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `date` | 거래 또는 공시 날짜 |
| `holder` | 내부자 또는 주요주주 |
| `direction` | buy/sell/ownershipChange/snapshot |
| `amount` | 수량 또는 지분 변화 |
| `status` | ok/watch/missing |

## 연계 절차

1. recipes.fundamental.disclosure.eventRadar.eventInbox - 관련 공시 이벤트 확인.
2. recipes.fundamental.disclosure.eventRadar.falsifierLedger - 계획 거래 반증.

## 기본 검증

- holder가 없으면 unknown으로 표시하고 단정하지 않는다.
- amount 부호만으로 의도를 해석하지 않는다.
