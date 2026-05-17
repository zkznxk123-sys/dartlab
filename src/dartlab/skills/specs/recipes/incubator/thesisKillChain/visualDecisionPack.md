---
id: recipes.incubator.thesisKillChain.visualDecisionPack
title: Thesis Kill-Chain Visual Decision Pack
category: recipes
kind: recipe
scope: builtin
status: observed
graphTier: L1.5
cluster: incubator.thesisKillChain
purpose: scenarioStoryboard, propagationPath, evidenceCoverageAudit, headline metric에 맞는 observed viz surface만 선택하는 L1/L1.5 절차다.
whenToUse:
  - thesis kill-chain visualization
  - pre-mortem chart gate
  - observed viz decision
inputs:
  - scenarioStoryboard
  - propagationPath
  - evidenceCoverageAudit
outputs:
  - visualDecisionPack table
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
  - dartlab://skills/recipes.incubator.thesisKillChain.visualDecisionPack
requiredEvidence:
  - skillRef
  - target
  - tableRef
  - valueRef
  - sourceRef
  - executionRef
expectedOutputs:
  - visualRef별 ready/blocked
visualRefs:
  - engines.viz.scenarioVisuals
  - engines.viz.mermaidDiagram
  - engines.viz.evidenceCoverage
  - engines.viz.kpiRibbon
visualGuidance:
  - "사용 가능한 visualRef는 observed 상태의 scenarioVisuals, mermaidDiagram, evidenceCoverage, kpiRibbon으로 제한한다."
  - "requiredBinding이 blocked이면 chart 대신 tableRef를 답변한다."
linkedSkills:
  - recipes.incubator.thesisKillChain.scenarioStoryboard
  - recipes.incubator.thesisKillChain.deepDive
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
  - blocked visualRef를 emit하지 않는다.
failureModes:
  - scenario table 없이 scenarioVisuals emit
examples:
  - thesis kill-chain 시각화 가능 여부 확인
audiences:
  llm: visualDecisionPack의 ready visualRef만 사용한다.
  agent: 차트를 만들기 전 requiredBinding을 확인한다.
  human: pre-mortem을 어떤 완성도 높은 시각 요소로 보여줄 수 있는지 확인한다.
humanIntro: "visualDecisionPack은 pre-mortem을 차트로 보여주기 전에 근거 결합을 확인하는 게이트다."
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
    table=memo["tables"]["visualDecisionPack"],
    values=memo["headline"],
    date=memo["asOf"],
    sources=memo["sources"],
)
```

## 호출 동작

scenarioStoryboard, propagationPath, evidenceCoverageAudit 존재 여부로 scenarioVisuals, mermaidDiagram, evidenceCoverage, kpiRibbon의 ready/blocked를 결정한다.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `visualRef` | observed viz skill |
| `status` | ready/blocked |
| `requiredBinding` | 필요한 근거 결합 |
| `evidence` | 선택 사유 |

## 연계 절차

1. recipes.incubator.thesisKillChain.scenarioStoryboard - scenario chart source.
2. recipes.incubator.thesisKillChain.deepDive - 최종 visual gate.

## 기본 검증

- visualRefs는 observed viz만 포함한다.
- blocked visualRef를 emit하지 않는다.
