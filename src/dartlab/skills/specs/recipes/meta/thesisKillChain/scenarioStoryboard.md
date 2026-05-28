---
id: recipes.meta.thesisKillChain.scenarioStoryboard
title: Thesis Kill-Chain Scenario Storyboard
category: recipes
kind: recipe
scope: builtin
status: tested
graphTier: L1.5
cluster: incubator.thesisKillChain
purpose: baseIntact, erosionCase, killChainCase 세 시나리오로 thesis pre-mortem을 정리하는 L1/L1.5 절차다. 트리거 — 'Thesis Kill-Chain Scenario Storyboard', 'scenario storyboard', 'scenarioStoryboard'.
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
    table=memo["tables"]["scenarioStoryboard"],
    values=memo["headline"],
    date=memo["asOf"],
    sources=memo["sources"],
)
```

## 호출 동작

### 1. 결론 도출

3 scenario storyboard (base/erosion/kill) 단정. 예: "storyboard 3 row — baseIntact status=ok plot='OPM 유지 + CFO/NI ≥ 1 + valuation discount 점진 해소' monitoring='4Q 실적 + consensus 모니터링' / erosionCase status=watch plot='OPM 1-2%p 압축 + cash conversion 약화 + discount 유지' monitoring='월간 fragility 재측정' / killChainCase status=risk plot='OPM 3%p+ 압축 + CB 추가 발행 + multiple compression' monitoring='tripwire trigger 발동 시 reversion 점검'. 3 scenario + 각 monitoring 완비."

### 2. 핵심 근거 수집

- thesisIntake (원문 + themes)
- propagationPath (path 4-8)
- tripwireMonitor (current + threshold)
- falsifierLedger (open/notTriggered)
- buildThesisKillChainMemo() → scenarioStoryboard table

### 3. 메커니즘 분석

```
4 source → 3 scenario 요약
   baseIntact:
     모든 assumption 유지 + tripwire ok 다수
     plot = "thesis 유지 시 시장 반응 + monitoring 시점"
   erosionCase:
     일부 assumption watch + tripwire 일부 risk
     plot = "thesis 약화 시작 + multiple 압축 추세"
   killChainCase:
     2+ assumption broken + tripwire 다수 risk
     plot = "thesis 붕괴 + valuation 완전 reset"
   ↓
각 scenario × (status + plot + requiredEvidence + monitoring) 필수:
   monitoring 없는 row → 실패 (forbidden)
   killChainCase 만 제시 + baseIntact 생략 → forbidden
   소설처럼 plot 만 + tripwire 사라짐 → failureMode
   ↓
3 scenario 모두 강제:
   사용자가 *유지되는 조건* + *약화되는 경로* + *붕괴되는 경로* 동시 비교
```

storyboard = pre-mortem 의 *최종 전달 형태*. 3 scenario 모두 + monitoring 강제 — 무너지는 경로만 보면 confirmation bias.

### 4. 반례·한계

- 3 scenario 모두 없으면 실패.
- killChainCase 만 + baseIntact 생략 → forbidden.
- monitoring 없는 row → failureMode.
- plot 이 너무 길어 tripwire 사라짐 → 운영 불가능.

### 5. 후속 모니터링

- 3 scenario ready → `recipes.meta.thesisKillChain.visualDecisionPack` 으로 chart 가능 여부.
- erosionCase + killChainCase 동시 risk → `recipes.meta.thesisKillChain.deepDive` 으로 최종 답변.
- baseIntact 만 ok → `recipes.meta.thesisKillChain.premortemQualityGate` 로 thesis 견조 confirm.

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
