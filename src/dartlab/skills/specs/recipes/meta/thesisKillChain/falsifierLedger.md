---
id: recipes.meta.thesisKillChain.falsifierLedger
title: Thesis Kill-Chain Falsifier Ledger
category: recipes
kind: recipe
scope: builtin
status: observed
graphTier: L1.5
cluster: incubator.thesisKillChain
purpose: kill-chain path가 틀렸음을 보여줄 counter-evidence를 trigger별로 열어 thesis 붕괴 단정을 막는 L1/L1.5 절차다.
whenToUse:
  - thesis falsifier
  - kill-chain 반증
  - counter evidence
inputs:
  - propagationPath
  - tripwireMonitor
outputs:
  - falsifierLedger table
capabilityRefs:
  - Company.show
  - Company.disclosure
  - Company.gather
toolRefs:
  - EngineCall
  - RunPython
knowledgeRefs:
  - runtime.workbenchEvidenceFlow
  - operation.skillDevelopmentLoop
sourceRefs:
  - dartlab://skills/recipes.meta.thesisKillChain.falsifierLedger
requiredEvidence:
  - skillRef
  - target
  - tableRef
  - valueRef
  - sourceRef
  - executionRef
expectedOutputs:
  - claim supportingEvidence counterEvidenceNeeded status
visualRefs:
  - engines.viz.evidenceCoverage
visualGuidance:
  - "falsifierLedger는 table/표가 1차 산출물이며 evidenceCoverage로 open/notTriggered 수만 보조한다."
linkedSkills:
  - recipes.meta.thesisKillChain.propagationPath
  - recipes.meta.thesisKillChain.scenarioStoryboard
  - engines.company
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
  - counterEvidenceNeeded 없이 thesis 붕괴를 단정하지 않는다.
failureModes:
  - watch/risk를 결론으로 바로 승격
examples:
  - kill-chain 반증 조건 만들어줘
audiences:
  llm: open falsifier를 답변에 반드시 포함한다.
  agent: counterEvidenceNeeded를 후속 데이터 요청으로 연결한다.
  human: thesis가 깨진다는 주장 자체도 반증 대상임을 확인한다.
humanIntro: "falsifierLedger는 pre-mortem의 균형추다. thesis를 일부러 깨보되, 깨졌다는 주장도 근거 없이는 확정하지 않는다."
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
filings = [{"rcept_dt": "20260510", "report_nm": "전환사채 발행 결정"}]

memo = buildThesisKillChainMemo(target=target, thesis=thesis, filings=filings)

emit_result(
    table=memo["tables"]["falsifierLedger"],
    values=memo["headline"],
    date=memo["asOf"],
    sources=memo["sources"],
)
```

## 호출 동작

propagationPath의 각 claim에 counterEvidenceNeeded를 붙이고 open/notTriggered를 만든다.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `claim` | 반증 대상 주장 |
| `supportingEvidence` | watch/risk/missing |
| `counterEvidenceNeeded` | 필요한 반증 |
| `status` | open/notTriggered |

## 연계 절차

1. recipes.meta.thesisKillChain.scenarioStoryboard - open falsifier를 시나리오 한계로 포함.
2. recipes.meta.thesisKillChain.deepDive - 최종 답변에 open falsifier 노출.

## 기본 검증

- counterEvidenceNeeded가 비어 있으면 실패다.
- open falsifier가 있으면 확정 표현을 쓰지 않는다.
