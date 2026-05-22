---
id: engines.viz.peerMatrix
title: Viz - Peer Matrix
kind: curated
scope: builtin
status: observed
category: engines
purpose: 동종 기업 × 지표 행렬을 `peer-matrix` ChartSpec 으로 만들어 밸류에이션, 수익성, 성장성, 안정성의 상대 위치를 한 번에 비교한다.
whenToUse:
  - peer 비교
  - 업종 benchmark
  - 상대 valuation
  - 후보군 비교
inputs:
  - peer rows
  - metrics
  - universe / industry
  - tableRef 또는 evidenceIds
outputs:
  - chartType peer-matrix ChartSpec
  - peer별 metric cell
  - pointRefs
toolRefs:
  - EngineCall
  - RunPython
  - CompileVisual
knowledgeRefs:
  - engines.viz
  - engines.analysis.peerComparison
  - engines.scan
sourceRefs:
  - dartlab://skills/engines.viz.peerMatrix
requiredEvidence:
  - universe
  - peerCount
  - metric
  - tableRef
  - executionRef
  - sourceRef
expectedOutputs:
  - peer-matrix spec
  - peer 대비 강점/약점 요약
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
    status: supported
failureModes:
  - 업종이 다른 회사를 같은 peer matrix 에 넣음
  - 결손 metric 을 0 점으로 처리함
  - universe size 를 숨기고 ranking 만 제시함
forbidden:
  - peerCount 2 미만 matrix 금지
  - tableRef 또는 evidenceIds 없는 peer chart 금지
  - 원자료 기준일이 다른 peer 값을 최신 비교처럼 표시 금지
examples:
  - 반도체 peer ROE/PER/PBR/부채비율 비교
  - 배터리 업종 성장성과 수익성 matrix
linkedSkills:
  - engines.viz
  - engines.analysis.peerComparison
  - engines.scan
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-13'
testUniverse:
  market: KR
  stockCodes:
    - "005930"
---

## 절차

1. 비교 universe 와 industry 기준을 먼저 답변에 고정한다.
2. peer rows 에 target 포함 여부와 metric 결손 수를 확인한다.
3. `specPeerMatrix(rows, metrics)` 를 사용하고 `categories` 는 회사명, `series` 는 metric 으로 둔다.
4. 결손 metric 이 많으면 chart 대신 coverage table 로 낮춘다.

## 공개 호출 방식

```python
from dartlab.viz.generators import specPeerMatrix

spec = specPeerMatrix(peer_rows, metrics=["roe", "operatingMargin", "per", "pbr", "debtRatio"])
```

## 호출 동작

- 입력 view 또는 rows 를 검산 가능한 ChartSpec 으로 변환한다.
- `evidenceBinding` 또는 `evidenceIds` 가 없으면 emit 하지 않는다.
- 데이터가 부족하면 값을 추정하지 않고 표, coverage note, 또는 bullet path 로 낮춘다.

## 대표 반환 형태

- `dict` ChartSpec: `chartType`, `title`, `series` 또는 `data`, `categories`, `evidenceBinding`, `meta`.
- Mermaid 계열은 diagram source 와 node/edge evidence refs 를 함께 남긴다.

## 기본 검증

- target 과 peer 모두 같은 기간·같은 metric 정의인지 확인한다.
- ranking 해석은 universe size 와 결손률을 같이 표기한다.
