---
id: recipes.meta.thesisKillChain.triggerCatalog
title: Thesis Kill-Chain Trigger Catalog
category: recipes
kind: recipe
scope: builtin
status: tested
graphTier: L1.5
cluster: incubator.thesisKillChain
purpose: fragilityMap, filings, scan primitive에서 thesis를 흔드는 촉발 조건을 모으는 L1/L1.5 절차다.
whenToUse:
  - trigger catalog
  - thesis 촉발 조건
  - break trigger
inputs:
  - fragilityMap rows
  - filing rows
  - scan primitive rows
outputs:
  - triggerCatalog table
capabilityRefs:
  - Company.disclosure
  - scan.market
toolRefs:
  - EngineCall
  - RunPython
knowledgeRefs:
  - engines.company
  - engines.scan
sourceRefs:
  - dartlab://skills/recipes.meta.thesisKillChain.triggerCatalog
requiredEvidence:
  - skillRef
  - tableRef
  - valueRef
  - dateRef
  - sourceRef
  - executionRef
expectedOutputs:
  - triggerId trigger source status evidence
visualRefs:
  - engines.viz.evidenceCoverage
visualGuidance:
  - "triggerCatalog는 table/표가 1차 산출물이며 evidenceCoverage로 source 상태만 보조한다."
linkedSkills:
  - recipes.meta.thesisKillChain.fragilityMap
  - recipes.meta.thesisKillChain.propagationPath
  - engines.company
gap:
  primary:
    - synth
    - scan
falsifier:
  description: "trigger 없이 propagationPath를 만들면 실패로 본다."
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
  - 공시 제목만으로 thesis 파괴를 확정하지 않는다.
failureModes:
  - 정기 공시를 risk trigger로 오인
examples:
  - thesis를 흔드는 trigger catalog
audiences:
  llm: trigger는 시나리오의 시작점이지 결론이 아니다.
  agent: triggerId를 propagationPath와 falsifierLedger에 연결한다.
  human: 어떤 사건이나 지표가 thesis 붕괴를 시작할 수 있는지 본다.
humanIntro: "triggerCatalog는 균열의 시작점을 모은다. 하나의 trigger가 바로 결론이 되지는 않는다."
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
try:
    filings = c.disclosure().head(50).to_dicts()
except Exception:
    filings = []

memo = buildThesisKillChainMemo(target=target, thesis=thesis, filings=filings)

emit_result(
    table=memo["tables"]["triggerCatalog"],
    values=memo["headline"],
    date=memo["asOf"],
    sources=memo["sources"],
)
```

## 호출 동작

watch/risk fragility, filing risk keyword, scan primitive score를 trigger row로 변환한다.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `triggerId` | 촉발 조건 id |
| `trigger` | 지표 또는 공시 제목 |
| `source` | fragilityMap/filing/scan |
| `status` | watch/risk/missing |
| `evidence` | trigger 근거 |

## 연계 절차

1. recipes.meta.thesisKillChain.propagationPath - trigger를 assumption에 연결.
2. recipes.meta.thesisKillChain.falsifierLedger - counter-evidence 작성.

## 기본 검증

- triggerId가 없으면 실패다.
- filing trigger는 routine filing 반증을 남긴다.
