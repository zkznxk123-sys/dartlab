---
id: engines.viz.evidenceCoverage
title: Viz - Evidence Coverage
kind: curated
scope: builtin
status: observed
category: engines
purpose: 분석 답변의 핵심 주장별 근거 충족 여부를 `evidence-coverage` ChartSpec 또는 coverage table 로 표현해 빈 주장과 검산 누락을 드러낸다.
whenToUse:
  - 근거 커버리지
  - 데이터 가용성
  - 보고서 검산
  - claim evidence matrix
inputs:
  - claims
  - evidence refs
  - requiredEvidence
  - coverage status
outputs:
  - chartType evidence-coverage ChartSpec
  - claim별 pass/missing/warning
  - coverage note
toolRefs:
  - RunPython
  - CompileVisual
knowledgeRefs:
  - engines.viz
  - runtime.workbenchEvidenceFlow
sourceRefs:
  - dartlab://skills/engines.viz.evidenceCoverage
requiredEvidence:
  - claim
  - evidenceRef
  - requiredEvidence
expectedOutputs:
  - evidence coverage spec
  - missing evidence list
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
  - 근거 없는 claim 을 chart 에서 pass 로 표시함
  - coverage chart 를 본문 결론처럼 해석함
forbidden:
  - evidenceRef 없는 claim 을 pass 처리 금지
  - coverage 를 투자 판단 지표로 단정 금지
examples:
  - 종합 보고서 claim별 근거 충족표
  - 데이터 가용성 우선 점검 coverage
linkedSkills:
  - engines.viz
  - runtime.workbenchEvidenceFlow
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-13'
---

## 절차

1. 답변에서 material claim 후보를 뽑고, 각 claim 에 필요한 `requiredEvidence` 를 붙인다.
2. 실제 수집된 `skillRef`, `tableRef`, `valueRef`, `dateRef`, `sourceRef`, `executionRef` 를 매칭한다.
3. `specEvidenceCoverage(items)` 를 사용해 pass/missing/warning 을 만들거나, 차트가 과하면 표로만 남긴다.
4. missing 이 있는 claim 은 최종 답변에서 단정 표현을 낮춘다.

## 공개 호출 방식

```python
from dartlab.viz.generators import specEvidenceCoverage

spec = specEvidenceCoverage(coverage_items)
```

## 호출 동작

- 입력 view 또는 rows 를 검산 가능한 ChartSpec 으로 변환한다.
- `evidenceBinding` 또는 `evidenceIds` 가 없으면 emit 하지 않는다.
- 데이터가 부족하면 값을 추정하지 않고 표, coverage note, 또는 bullet path 로 낮춘다.

## 대표 반환 형태

- `dict` ChartSpec: `chartType`, `title`, `series` 또는 `data`, `categories`, `evidenceBinding`, `meta`.
- Mermaid 계열은 diagram source 와 node/edge evidence refs 를 함께 남긴다.

## 기본 검증

- coverage item 은 claim text, required evidence, matched refs 를 모두 포함해야 한다.
- 차트는 결론 보강용이 아니라 검산/한계 섹션에 배치한다.
