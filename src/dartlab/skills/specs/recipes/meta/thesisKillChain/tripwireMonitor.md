---
id: recipes.meta.thesisKillChain.tripwireMonitor
title: Thesis Kill-Chain Tripwire Monitor
category: recipes
kind: recipe
scope: builtin
status: observed
graphTier: L1.5
cluster: incubator.thesisKillChain
purpose: fragility metric별 current, threshold, action을 정리해 thesis가 깨지는 조기 경보선을 만드는 L1/L1.5 절차다.
whenToUse:
  - tripwire monitor
  - thesis 조기 경보
  - kill-chain 임계값
inputs:
  - fragilityMap
  - triggerCatalog
outputs:
  - tripwireMonitor table
capabilityRefs:
  - Company.show
  - Company.gather
toolRefs:
  - EngineCall
  - RunPython
knowledgeRefs:
  - runtime.workbenchEvidenceFlow
sourceRefs:
  - dartlab://skills/recipes.meta.thesisKillChain.tripwireMonitor
requiredEvidence:
  - skillRef
  - target
  - tableRef
  - valueRef
  - dateRef
  - sourceRef
  - executionRef
expectedOutputs:
  - tripwire current threshold status action
visualRefs:
  - engines.viz.kpiRibbon
  - engines.viz.evidenceCoverage
visualGuidance:
  - "openTripwireCount는 kpiRibbon chart로 보조하고 tripwireMonitor는 table/표로 제시한다."
linkedSkills:
  - recipes.meta.thesisKillChain.fragilityMap
  - recipes.meta.thesisKillChain.falsifierLedger
gap:
  primary:
    - synth
    - gather
falsifier:
  description: "threshold 없이 tripwire를 만들면 실패로 본다."
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
  - threshold 없는 watch/risk를 만들지 않는다.
failureModes:
  - current 값만 표시하고 action 누락
examples:
  - 이 thesis의 tripwire 만들어줘
audiences:
  llm: tripwire는 사용자가 나중에 재검사할 수 있게 current/threshold/action을 함께 둔다.
  agent: watch/risk tripwire는 falsifierLedger로 연결한다.
  human: thesis를 계속 들고 가도 되는지 판단할 조기 경보선이다.
humanIntro: "tripwireMonitor는 시나리오를 운영 가능한 체크리스트로 바꾼다. 경보선이 없으면 좋은 pre-mortem도 실행되지 않는다."
lastUpdated: "2026-05-17"
testUniverse:
  market: KR
  stockCodes:
    - "005930"
---

## 공개 호출 방식

AI 도구 실행 순서는 `EngineCall` 우선이다. 아래 Python 블록은 확보한 L1/L1.5 근거를 `buildThesisKillChainMemo`로 묶는 **RunPython fallback** 절차다.

```python
from dartlab.synth.thesisKillChain import buildThesisKillChainMemo

target = "005930"
thesis = "매출 성장과 현금 전환이 유지되어 valuation discount가 해소된다"
priceRows = [{"date": "2026-05-11", "close": 90000}, {"date": "2026-05-10", "close": 100000}]

memo = buildThesisKillChainMemo(target=target, thesis=thesis, priceRows=priceRows)

emit_result(
    table=memo["tables"]["tripwireMonitor"],
    values=memo["headline"],
    date=memo["asOf"],
    sources=memo["sources"],
)
```

## 호출 동작

fragility metric마다 threshold와 action을 붙여 monitoring row를 만든다.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `tripwire` | 모니터링 지표 |
| `current` | 현재값 |
| `threshold` | watch/risk 임계 |
| `status` | ok/watch/risk/missing |
| `action` | 다음 조치 |

## 연계 절차

1. recipes.meta.thesisKillChain.falsifierLedger - watch/risk 반증 조건.
2. recipes.meta.thesisKillChain.scenarioStoryboard - tripwire를 시나리오로 변환.

## 기본 검증

- threshold와 action이 없는 row는 실패다.
- missing tripwire는 결론에 쓰지 않는다.
