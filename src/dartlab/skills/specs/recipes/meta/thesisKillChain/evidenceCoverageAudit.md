---
id: recipes.meta.thesisKillChain.evidenceCoverageAudit
title: Thesis Kill-Chain Evidence Coverage Audit
category: recipes
kind: recipe
scope: builtin
status: observed
graphTier: L1.5
cluster: incubator.thesisKillChain
purpose: pre-mortem 시나리오에 필요한 statements, filings, price, flow, consensus, scan, assumptions coverage를 확인하는 L1/L1.5 절차다.
whenToUse:
  - thesis evidence coverage
  - pre-mortem source audit
  - 시나리오 근거 결손
inputs:
  - raw input rows
outputs:
  - evidenceCoverageAudit table
capabilityRefs:
  - Company.show
  - Company.disclosure
  - Company.gather
  - scan.market
toolRefs:
  - EngineCall
  - RunPython
knowledgeRefs:
  - engines.company
  - engines.gather
  - engines.scan
sourceRefs:
  - dartlab://skills/recipes.meta.thesisKillChain.evidenceCoverageAudit
requiredEvidence:
  - skillRef
  - target
  - tableRef
  - dateRef
  - sourceRef
  - executionRef
expectedOutputs:
  - source별 rowCount latestDate requiredFor
visualRefs:
  - engines.viz.evidenceCoverage
visualGuidance:
  - "evidenceCoverageAudit table이 있을 때만 engines.viz.evidenceCoverage 표 시각화를 사용한다."
linkedSkills:
  - recipes.meta.thesisKillChain.fragilityMap
  - recipes.meta.thesisKillChain.deepDive
gap:
  primary:
    - synth
    - gather
falsifier:
  description: "coverage 결손을 숨기고 scenario를 만들면 실패로 본다."
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
  - 결손 source를 0으로 채우지 않는다.
failureModes:
  - statements 없이 fragilityMap을 정상처럼 표시
examples:
  - thesis kill chain source coverage 확인
audiences:
  llm: missing source는 답변 한계에 노출한다.
  agent: source coverage가 없는 visual은 blocked로 둔다.
  human: 시나리오가 어떤 근거에 기대고 있는지 먼저 본다.
humanIntro: "coverage audit은 시나리오의 바닥이다. 없는 데이터를 상상으로 채우지 않는다."
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
    table=memo["tables"]["evidenceCoverageAudit"],
    values=memo["headline"],
    date=memo["asOf"],
    sources=memo["sources"],
)
```

## 호출 동작

source별 `status`, `rowCount`, `latestDate`, `requiredFor`를 만든다.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `dataset` | source 이름 |
| `status` | ok/missing |
| `rowCount` | row 수 |
| `latestDate` | 최신 날짜 |
| `requiredFor` | 필요한 후속 판단 |

## 연계 절차

1. recipes.meta.thesisKillChain.fragilityMap - coverage가 있는 원자료만 사용.
2. recipes.meta.thesisKillChain.visualDecisionPack - coverage chart gate.

## 기본 검증

- evidenceCoverageAudit가 비어 있으면 실패다.
- missing source는 답변 한계로 표시한다.
