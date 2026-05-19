---
id: recipes.meta.thesisKillChain.assumptionLedger
title: Thesis Kill-Chain Assumption Ledger
category: recipes
kind: recipe
scope: builtin
status: observed
graphTier: L1.5
cluster: incubator.thesisKillChain
purpose: 사용자 thesis를 revenueGrowth, marginDurability, cashConversion, balanceSheet, valuationSupport 등 testable assumption으로 분해하는 L1/L1.5 절차다.
whenToUse:
  - assumption ledger
  - thesis 가정 분해
  - testable assumptions
inputs:
  - thesisIntake
  - optional assumptions
outputs:
  - assumptionLedger table
capabilityRefs:
  - Company.show
toolRefs:
  - EngineCall
  - RunPython
knowledgeRefs:
  - operation.skillDevelopmentLoop
sourceRefs:
  - dartlab://skills/recipes.meta.thesisKillChain.assumptionLedger
requiredEvidence:
  - skillRef
  - target
  - tableRef
  - sourceRef
  - executionRef
expectedOutputs:
  - assumptionId별 claim과 evidenceNeeded
visualRefs:
  - engines.viz.evidenceCoverage
visualGuidance:
  - "assumptionLedger table은 표가 우선이며 coverage 상태만 evidenceCoverage로 보조한다."
linkedSkills:
  - recipes.meta.thesisKillChain.thesisIntake
  - recipes.meta.thesisKillChain.fragilityMap
gap:
  primary:
    - synth
    - gather
falsifier:
  description: "testable assumption 없이 fragility나 scenario를 만들면 실패로 본다."
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
  - 가정을 숫자 근거 없이 참이라고 두지 않는다.
failureModes:
  - thesis 문장을 그대로 결론으로 사용
examples:
  - thesis를 깨질 수 있는 가정으로 나눠줘
audiences:
  llm: assumption은 claim이 아니라 검증 대상이다.
  agent: evidenceNeeded를 다음 단계 호출 근거로 사용한다.
  human: 내가 믿는 문장을 테스트 가능한 행으로 나눈다.
humanIntro: "assumptionLedger는 thesis를 방어 가능한 단위로 쪼갠다. 여기서부터 pre-mortem이 실제 검증 절차가 된다."
lastUpdated: "2026-05-17"
---

## 공개 호출 방식

AI 도구 실행 순서는 `EngineCall` 우선이다. 아래 Python 블록은 확보한 L1/L1.5 근거를 `buildThesisKillChainMemo`로 묶는 **RunPython fallback** 절차다.

```python
from dartlab.synth.thesisKillChain import buildThesisKillChainMemo

target = "005930"
thesis = "매출 성장과 현금 전환이 유지되어 valuation discount가 해소된다"
assumptions = ["매출 성장이 둔화되지 않는다", "CFO가 순이익을 따라온다"]

memo = buildThesisKillChainMemo(target=target, thesis=thesis, assumptions=assumptions)

emit_result(
    table=memo["tables"]["assumptionLedger"],
    values=memo["headline"],
    date=memo["asOf"],
    sources=memo["sources"],
)
```

## 호출 동작

thesis 키워드와 명시 assumption을 합쳐 `assumptionId`, `claim`, `source`, `evidenceNeeded`를 만든다.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `assumptionId` | 가정 식별자 |
| `claim` | 검증할 가정 |
| `source` | parsedThesis/user/fallback |
| `status` | untested/missing |
| `evidenceNeeded` | 필요한 원자료 |

## 연계 절차

1. recipes.meta.thesisKillChain.fragilityMap - assumption을 깨는 지표 확인.
2. recipes.meta.thesisKillChain.propagationPath - trigger와 assumption 연결.

## 기본 검증

- assumptionId가 없는 row는 실패다.
- evidenceNeeded가 비어 있으면 실패다.
