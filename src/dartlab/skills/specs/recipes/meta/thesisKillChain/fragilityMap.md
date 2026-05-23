---
id: recipes.meta.thesisKillChain.fragilityMap
title: Thesis Kill-Chain Fragility Map
category: recipes
kind: recipe
scope: builtin
status: tested
graphTier: L1.5
cluster: incubator.thesisKillChain
purpose: IS/BS/CF, price/flow, consensus 원자료에서 thesis를 깨기 쉬운 revenue, margin, cash, leverage, market, expectation 취약 지표를 계산하는 L1/L1.5 절차다.
whenToUse:
  - fragility map
  - thesis 취약 지표
  - kill-chain 지표
inputs:
  - Company.show IS BS CF
  - price flow consensus rows
outputs:
  - fragilityMap table
capabilityRefs:
  - Company.show
  - Company.gather
toolRefs:
  - EngineCall
  - RunPython
knowledgeRefs:
  - engines.company
  - engines.gather
  - engines.scan
sourceRefs:
  - dartlab://skills/recipes.meta.thesisKillChain.fragilityMap
requiredEvidence:
  - skillRef
  - tableRef
  - valueRef
  - dateRef
  - sourceRef
  - executionRef
expectedOutputs:
  - metric별 value status thesisBreak
visualRefs:
  - engines.viz.kpiRibbon
  - engines.viz.evidenceCoverage
visualGuidance:
  - "fragility count는 kpiRibbon chart로 보조하고 metric별 값은 table/표로 보존한다."
linkedSkills:
  - recipes.meta.thesisKillChain.assumptionLedger
  - recipes.meta.thesisKillChain.triggerCatalog
  - engines.company
gap:
  primary:
    - synth
    - gather
falsifier:
  description: "취약 지표 없이 scenarioStoryboard를 만들면 실패로 본다."
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
  - 결손값을 0으로 채우지 않는다.
failureModes:
  - 단일 가격 하락을 thesis 취약성으로 단정
examples:
  - thesis fragility map 만들어줘
audiences:
  llm: fragilityMap은 원자료에서 계산한 취약 지표이며 결론이 아니다.
  agent: watch/risk 지표를 triggerCatalog로 넘긴다.
  human: 어떤 숫자가 thesis를 가장 먼저 흔드는지 본다.
humanIntro: "fragilityMap은 thesis가 깨질 수 있는 수치 지점을 찾는다. 이 단계가 없으면 pre-mortem은 문장 놀이로 끝난다."
lastUpdated: "2026-05-17"
testUniverse:
  market: KR
  stockCodes:
    - "005930"
---

## 공개 호출 방식

AI 도구 실행 순서는 `EngineCall` 우선이다. 아래 Python 블록은 확보한 L1/L1.5 근거를 `buildThesisKillChainMemo`로 묶는 **RunPython fallback** 절차다.

```python
import dartlab
from dartlab.synth.thesisKillChain import buildThesisKillChainMemo

target = "005930"
thesis = "매출 성장과 현금 전환이 유지되어 valuation discount가 해소된다"
c = dartlab.Company(target)
statements = {}
for topic in ("IS", "BS", "CF"):
    try:
        statements[topic] = c.show(topic, freq="Y")
    except Exception:
        pass

memo = buildThesisKillChainMemo(target=target, thesis=thesis, statements=statements)

emit_result(
    table=memo["tables"]["fragilityMap"],
    values=memo["headline"],
    date=memo["asOf"],
    sources=memo["sources"],
)
```

## 호출 동작

revenueGrowth, operatingMarginTrend, cashConversion, debtToEquity, cashToDebt, priceReaction, flowPressure, consensusRevision을 만든다.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `metric` | 취약 지표 |
| `value` | 계산값 |
| `status` | ok/watch/risk/missing |
| `thesisBreak` | thesis가 깨지는 방식 |

## 연계 절차

1. recipes.meta.thesisKillChain.triggerCatalog - watch/risk 지표를 trigger로 전환.
2. recipes.meta.thesisKillChain.tripwireMonitor - 임계값과 모니터링 조건 생성.

## 기본 검증

- 결손 지표는 missing으로 둔다.
- watch/risk는 반드시 thesisBreak를 포함한다.
