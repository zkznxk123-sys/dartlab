---
id: recipes.incubator.thesisKillChain.deepDive
title: Thesis Kill-Chain Deep Dive
category: recipes
kind: recipe
scope: builtin
status: observed
entryHint: true
graphTier: L1.5
cluster: incubator.thesisKillChain
purpose: thesis intake, evidence coverage, assumption ledger, fragility map, trigger catalog, propagation path, tripwire, falsifier, scenario storyboard, visual gate를 한 번에 실행하는 pre-mortem 시나리오 최종 절차다.
whenToUse:
  - thesis kill-chain deep dive
  - 프리모템 전체 실행
  - 투자 논리 깨보기 전체
inputs:
  - thesis
  - Company.show 원표
  - filing/price/flow/consensus/scan rows
outputs:
  - deepDive step ledger
  - killRiskScore
  - open tripwire count
  - scenario storyboard
capabilityRefs:
  - Company.show
  - Company.disclosure
  - Company.gather
  - scan.market
  - scan.audit
  - scan.quality
toolRefs:
  - EngineCall
  - RunPython
knowledgeRefs:
  - operation.skillDevelopmentLoop
  - runtime.workbenchEvidenceFlow
  - engines.viz
sourceRefs:
  - dartlab://skills/recipes.incubator.thesisKillChain.deepDive
requiredEvidence:
  - skillRef
  - target
  - tableRef
  - valueRef
  - dateRef
  - sourceRef
  - executionRef
expectedOutputs:
  - 11단계 deepDive ledger
  - killRiskScore와 openTripwireCount
  - propagationPath와 scenarioStoryboard
  - visualDecisionPack
visualRefs:
  - engines.viz.scenarioVisuals
  - engines.viz.mermaidDiagram
  - engines.viz.evidenceCoverage
  - engines.viz.kpiRibbon
visualGuidance:
  - "scenarioStoryboard table이 있을 때만 engines.viz.scenarioVisuals chart를 사용한다."
  - "propagationPath는 engines.viz.mermaidDiagram diagram으로 8 edge 이하만 표시한다."
  - "coverage/falsifier 상태는 evidenceCoverage 표 시각화로만 보조한다."
  - "killRiskScore/openTripwireCount는 kpiRibbon chart로만 작게 보조한다."
linkedSkills:
  - recipes.incubator.thesisKillChain.thesisIntake
  - recipes.incubator.thesisKillChain.evidenceCoverageAudit
  - recipes.incubator.thesisKillChain.assumptionLedger
  - recipes.incubator.thesisKillChain.fragilityMap
  - recipes.incubator.thesisKillChain.triggerCatalog
  - recipes.incubator.thesisKillChain.propagationPath
  - recipes.incubator.thesisKillChain.tripwireMonitor
  - recipes.incubator.thesisKillChain.falsifierLedger
  - recipes.incubator.thesisKillChain.scenarioStoryboard
  - recipes.incubator.thesisKillChain.visualDecisionPack
gap:
  primary:
    - synth
    - gather
  secondary:
    - scan
    - viz
testUniverse:
  market: KR+US
  stockCodes:
    - "005930"
    - "247540"
    - "AAPL"
  asOfPolicy: latest
falsifier:
  description: "deepDive가 thesis 결론만 말하고 propagationPath, tripwire, falsifier를 누락하면 실패로 본다."
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
  - c.analysis, c.credit, c.quant, c.macro, c.industry, c.story를 호출하지 않는다.
  - thesis 지지 결론으로 답변을 시작하지 않는다.
  - blocked visualRef를 emit하지 않는다.
failureModes:
  - 기존 companyDeepAnalysis로 우회
  - scenarioStoryboard만 있고 tripwire가 없음
  - open falsifier를 숨김
examples:
  - 삼성전자 thesis kill-chain deep dive
  - 투자 논리 pre-mortem 전체 실행
audiences:
  llm: capabilityRefs는 EngineCall로 우선 호출하고 공개 호출 블록은 L1.5 memo builder용 RunPython fallback으로만 실행한다.
  agent: 답변은 assumption, fragility, propagation, tripwire, falsifier, scenario를 함께 묶는다.
  human: thesis가 깨지는 경로를 한 번에 실행하는 실제 사용 경로다.
humanIntro: "deepDive는 Thesis Kill-Chain 팩의 실제 사용 경로다. 투자 논리를 더 멋지게 만드는 게 아니라, 그 논리가 어디서부터 무너질 수 있는지 끝까지 추적한다."
lastUpdated: "2026-05-17"
---

## 공개 호출 방식

AI 도구 실행 순서는 `EngineCall` 우선이다. `Company.show`, `Company.disclosure`, `Company.gather`, `scan.market`, `scan.audit`, `scan.quality`는 엔진 호출로 근거를 먼저 확보한다. 아래 Python 블록은 확보한 L1/L1.5 근거를 `buildThesisKillChainMemo`로 묶는 **RunPython fallback** 절차다.

```python
import dartlab
from dartlab.synth.thesisKillChain import buildThesisKillChainMemo

target = "005930"
thesis = "매출 성장과 현금 전환이 유지되어 valuation discount가 해소된다"
c = dartlab.Company(target)

def rows(value, limit=30):
    if hasattr(value, "head") and hasattr(value, "to_dicts"):
        return value.head(limit).to_dicts()
    if isinstance(value, list):
        return value[:limit]
    return []

def gather_rows(axis, limit=30):
    try:
        return rows(c.gather(axis), limit=limit)
    except Exception:
        try:
            return rows(dartlab.gather(axis, target=target), limit=limit)
        except Exception:
            return []

statements = {}
for topic in ("IS", "BS", "CF"):
    try:
        statements[topic] = c.show(topic, freq="Y")
    except TypeError:
        statements[topic] = c.show(topic)
    except Exception:
        pass

try:
    filings = rows(c.disclosure(), limit=50)
except Exception:
    filings = []

memo = buildThesisKillChainMemo(
    target=target,
    thesis=thesis,
    market=str(getattr(c, "market", "KR")),
    companyName=str(getattr(c, "corpName", target)),
    statements=statements,
    filings=filings,
    priceRows=gather_rows("price", limit=40),
    flowRows=gather_rows("flow", limit=40),
    consensusRows=gather_rows("consensus", limit=12),
)

emit_result(
    table=memo["tables"]["deepDive"],
    values={
        "target": target,
        "killRiskScore": memo["headline"]["killRiskScore"],
        "openTripwires": memo["headline"]["openTripwireCount"],
        "openFalsifiers": memo["headline"]["openFalsifierCount"],
        "decisionStatus": memo["headline"]["decisionStatus"],
    },
    date=memo["asOf"],
    sources=memo["sources"],
)
```

## 호출 동작

`thesisIntake`부터 `visualDecisionPack`까지 한 번에 만들고, 마지막 `finalDecision` row는 killRiskScore와 decisionStatus만 요약한다.

## 대표 반환 형태

`deepDive : list[dict]`

| column | 의미 |
|---|---|
| `order` | 실행 순서 |
| `step` | 세부 ledger 이름 |
| `status` | missing/ok/watch/risk |
| `rowCount` | 해당 ledger row 수 |
| `evidence` | 대표 근거 |
| `nextAction` | 다음 조치 |

## 연계 절차

1. recipes.incubator.thesisKillChain.thesisIntake - thesis intake.
2. recipes.incubator.thesisKillChain.evidenceCoverageAudit - evidence coverage.
3. recipes.incubator.thesisKillChain.assumptionLedger - assumption ledger.
4. recipes.incubator.thesisKillChain.fragilityMap - fragility map.
5. recipes.incubator.thesisKillChain.triggerCatalog - trigger catalog.
6. recipes.incubator.thesisKillChain.propagationPath - propagation path.
7. recipes.incubator.thesisKillChain.tripwireMonitor - tripwire monitor.
8. recipes.incubator.thesisKillChain.falsifierLedger - falsifier ledger.
9. recipes.incubator.thesisKillChain.scenarioStoryboard - scenario storyboard.
10. recipes.incubator.thesisKillChain.visualDecisionPack - visual gate.

## 기본 검증

- 공개 호출 블록은 AST parse가 되어야 한다.
- 공개 호출 블록은 L2/L3 호출 문자열을 포함하면 실패다.
- scenarioStoryboard에는 baseIntact, erosionCase, killChainCase가 모두 있어야 한다.
- ready가 아닌 visualRef는 차트로 emit하지 않는다.
