---
id: recipes.meta.thesisKillChain.thesisIntake
title: Thesis Kill-Chain Thesis Intake
category: recipes
kind: recipe
scope: builtin
status: observed
graphTier: L1.5
cluster: incubator.thesisKillChain
purpose: 사용자 thesis를 받아 growth, margin, cash, balance sheet, valuation, event, macro, governance theme으로 파싱하는 pre-mortem 시작 절차다.
whenToUse:
  - thesis intake
  - 투자 thesis 파싱
  - 프리모템 시작
inputs:
  - 사용자 thesis
  - optional assumptions
outputs:
  - thesisIntake table
capabilityRefs:
  - Company.show
toolRefs:
  - EngineCall
  - RunPython
knowledgeRefs:
  - operation.skillDevelopmentLoop
sourceRefs:
  - dartlab://skills/recipes.meta.thesisKillChain.thesisIntake
requiredEvidence:
  - skillRef
  - tableRef
  - sourceRef
  - executionRef
expectedOutputs:
  - thesis text
  - parsed themes
visualRefs:
  - engines.viz.kpiRibbon
visualGuidance:
  - "themeCount는 kpiRibbon chart의 보조 숫자로만 표시하고 thesis 원문 table을 보존한다."
linkedSkills:
  - recipes.meta.thesisKillChain.assumptionLedger
  - recipes.meta.thesisKillChain.deepDive
  - engines.company
gap:
  primary:
    - synth
    - gather
falsifier:
  description: "thesis가 비어 있는데 scenario를 만들면 실패로 본다."
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
  - thesis 없이 투자 결론을 만들지 않는다.
failureModes:
  - thesis 원문을 잃고 일반 분석으로 전환
examples:
  - 이 thesis를 깨는 관점으로 파싱
audiences:
  llm: thesis 원문을 먼저 보존하고, theme은 보조 분류로만 사용한다.
  agent: thesisIntake가 missing이면 사용자에게 thesis 보강을 요구한다.
  human: 내가 믿는 문장을 testable assumption으로 바꾸는 첫 단계다.
humanIntro: "thesisIntake는 프리모템의 입력 잠금이다. 원문을 잃으면 이후 시나리오는 일반 분석으로 흐른다."
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

memo = buildThesisKillChainMemo(target=target, thesis=thesis)

emit_result(
    table=memo["tables"]["thesisIntake"],
    values=memo["headline"],
    date=memo["asOf"],
    sources=memo["sources"],
)
```

## 호출 동작

thesis 원문을 보존하고 핵심 theme을 파싱한다. 비어 있으면 `status=missing`으로 둔다.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `thesis` | 사용자 thesis 원문 |
| `themeCount` | 파싱된 theme 수 |
| `themes` | growth/margin/cash 등 |
| `status` | ok/missing |

## 연계 절차

1. recipes.meta.thesisKillChain.assumptionLedger - theme을 testable assumption으로 전환.
2. recipes.meta.thesisKillChain.deepDive - 전체 pre-mortem 실행.

## 기본 검증

- thesis 원문이 table에 남아 있어야 한다.
- missing이면 scenarioStoryboard를 확정하지 않는다.
