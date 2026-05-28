---
id: recipes.meta.thesisKillChain.visualDecisionPack
title: Thesis Kill-Chain Visual Decision Pack
category: recipes
kind: recipe
scope: builtin
status: tested
graphTier: L1.5
cluster: incubator.thesisKillChain
purpose: scenarioStoryboard, propagationPath, evidenceCoverageAudit, headline metric에 맞는 observed viz surface만 선택하는 L1/L1.5 절차다. 트리거 — 'Thesis Kill-Chain Visual Decision Pack', 'visual decision pack', 'visualDecisionPack'.
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
  - dartlab://skills/recipes.meta.thesisKillChain.visualDecisionPack
requiredEvidence:
  - skillRef
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
  - recipes.meta.thesisKillChain.scenarioStoryboard
  - recipes.meta.thesisKillChain.deepDive
  - engines.company
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
    table=memo["tables"]["visualDecisionPack"],
    values=memo["headline"],
    date=memo["asOf"],
    sources=memo["sources"],
)
```

## 호출 동작

### 1. 결론 도출

4 visualRef ready/blocked + requiredBinding 단정. 예: "visualDecisionPack 4 row — scenarioVisuals ready (scenario 3 + monitoring 통과) / mermaidDiagram ready (propagationPath 4 edge + sourceRef 명시) / evidenceCoverage ready (audit 8 source) / kpiRibbon ready (premortemQualityScore + headline). 4 of 4 ready → 모든 viz emit 가능."

### 2. 핵심 근거 수집

- scenarioStoryboard (3 scenario base/erosion/kill)
- propagationPath (4-8 edge)
- evidenceCoverageAudit (8 source coverage)
- headline metric (premortemQualityScore)
- buildThesisKillChainMemo() → visualDecisionPack table

### 3. 메커니즘 분석

```
4 visualRef × (status + requiredBinding + evidence)
   scenarioVisuals:
     ready 조건  → scenarioStoryboard table 3 row + monitoring 필드 통과
     blocked 시 → scenario table 비어 있음 (engines.viz.scenarioVisuals 가이드 위반)
   mermaidDiagram:
     ready 조건  → propagationPath 4 edge 이하 + 각 edge sourceRef
     blocked 시 → path 0 또는 8 edge 초과
   evidenceCoverage:
     ready 조건  → evidenceCoverageAudit table 통과
     blocked 시 → audit 비어 있음
   kpiRibbon:
     ready 조건  → premortemQualityScore + qualityGateStatus headline
     blocked 시 → score 미산출
   ↓
forbidden 회피:
   unverified viz skill (incubator) → visualRefs 추가 X
   blocked visualRef emit → false visualization
   scenario table 없이 scenarioVisuals → failureMode 발동
   ↓
tableRef 우회:
   blocked viz 는 tableRef 로 답변
   chart 만들기 전 requiredBinding 확인 필수
```

visualDecisionPack = thesisKillChain 의 *시각화 품질 게이트*. observed viz 만 통과. blocked 시 chart 대신 tableRef 로 우회.

### 4. 반례·한계

- unverified viz skill 을 visualRefs 에 연결 → forbidden.
- blocked visualRef emit → 가짜 visualization.
- scenario table 없이 scenarioVisuals emit → failureMode.
- requiredBinding 정의 모호 → 실제 검증 불가.

### 5. 후속 모니터링

- 4 viz 모두 ready → `recipes.meta.thesisKillChain.deepDive` 의 최종 visual gate 통과.
- scenarioVisuals blocked → `recipes.meta.thesisKillChain.scenarioStoryboard` 로 3 scenario 보강.
- mermaidDiagram blocked → `recipes.meta.thesisKillChain.propagationPath` 로 path 추가.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `visualRef` | observed viz skill |
| `status` | ready/blocked |
| `requiredBinding` | 필요한 근거 결합 |
| `evidence` | 선택 사유 |

## 연계 절차

1. recipes.meta.thesisKillChain.scenarioStoryboard - scenario chart source.
2. recipes.meta.thesisKillChain.deepDive - 최종 visual gate.

## 기본 검증

- visualRefs는 observed viz만 포함한다.
- blocked visualRef를 emit하지 않는다.
