---
id: recipes.meta.thesisKillChain.scenarioStoryboard
title: Thesis Kill-Chain Scenario Storyboard
category: recipes
kind: recipe
scope: builtin
status: observed
graphTier: L1.5
cluster: incubator.thesisKillChain
purpose: baseIntact, erosionCase, killChainCase 세 시나리오로 thesis pre-mortem을 정리하는 L1/L1.5 절차다.
whenToUse:
  - scenario storyboard
  - pre-mortem 시나리오
  - base erosion kill chain
inputs:
  - thesisIntake
  - propagationPath
  - tripwireMonitor
  - falsifierLedger
outputs:
  - scenarioStoryboard table
capabilityRefs:
  - Company.show
  - Company.gather
toolRefs:
  - EngineCall
  - RunPython
knowledgeRefs:
  - engines.viz
  - runtime.workbenchEvidenceFlow
sourceRefs:
  - dartlab://skills/recipes.meta.thesisKillChain.scenarioStoryboard
requiredEvidence:
  - skillRef
  - target
  - tableRef
  - valueRef
  - sourceRef
  - executionRef
expectedOutputs:
  - baseIntact erosionCase killChainCase
visualRefs:
  - engines.viz.scenarioVisuals
  - engines.viz.mermaidDiagram
visualGuidance:
  - "scenarioStoryboard table이 3개 scenario를 모두 가질 때만 engines.viz.scenarioVisuals chart를 사용한다."
linkedSkills:
  - recipes.meta.thesisKillChain.propagationPath
  - recipes.meta.thesisKillChain.falsifierLedger
  - recipes.meta.thesisKillChain.visualDecisionPack
gap:
  primary:
    - synth
    - viz
falsifier:
  description: "base/erosion/kill 세 시나리오가 모두 없으면 실패로 본다."
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
  - killChainCase만 제시하고 baseIntact 반례를 생략하지 않는다.
failureModes:
  - 시나리오가 소설처럼 되고 tripwire가 사라짐
examples:
  - thesis pre-mortem 시나리오 storyboard
audiences:
  llm: 세 시나리오를 모두 제시하고 monitoring 필드를 함께 둔다.
  agent: scenarioVisuals는 storyboard table이 있을 때만 사용한다.
  human: thesis 유지, 약화, 붕괴 경로를 한 화면에 비교한다.
humanIntro: "scenarioStoryboard는 pre-mortem을 사용자에게 전달하는 최종 형태다. 무너지는 경로만이 아니라 유지되는 조건도 같이 둔다."
lastUpdated: "2026-05-17"
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
    table=memo["tables"]["scenarioStoryboard"],
    values=memo["headline"],
    date=memo["asOf"],
    sources=memo["sources"],
)
```

## 호출 동작

thesisIntake, propagationPath, tripwireMonitor, falsifierLedger를 baseIntact, erosionCase, killChainCase로 요약한다.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `scenario` | baseIntact/erosionCase/killChainCase |
| `status` | ok/watch/risk/missing |
| `plot` | 시나리오 서술 |
| `requiredEvidence` | 필요한 근거 |
| `monitoring` | 후속 점검 |

## 연계 절차

1. recipes.meta.thesisKillChain.visualDecisionPack - scenario chart 가능 여부 확인.
2. recipes.meta.thesisKillChain.deepDive - 최종 답변으로 연결.

## 기본 검증

- scenario 3개가 모두 있어야 한다.
- monitoring이 없는 scenario row는 실패다.
