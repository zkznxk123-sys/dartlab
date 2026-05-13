---
id: engines.viz.mermaidDiagram
title: Viz - Mermaid 인과 다이어그램
kind: curated
scope: builtin
status: observed
category: engines
purpose: 숫자 표로만 설명하기 어려운 충격 전파, 공시 변화, 지배구조 연결, thesis falsifier 경로를 Mermaid diagram 으로 제한적으로 표현한다.
whenToUse:
  - Mermaid diagram
  - 인과 다이어그램
  - 충격 전파
  - 지배구조 network
  - thesis path
inputs:
  - nodes
  - edges
  - node evidence refs
  - diagram title
outputs:
  - mermaid source
  - diagramRef
toolRefs:
  - RunPython
knowledgeRefs:
  - engines.viz
sourceRefs:
  - dartlab://skills/engines.viz.mermaidDiagram
requiredEvidence:
  - node
  - edge
  - evidenceRef
expectedOutputs:
  - Mermaid graph LR source
  - 인과 경로 설명
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
  - 근거 없는 관계를 edge 로 그림
  - 노드가 많아져 diagram 이 분석이 아니라 장식이 됨
forbidden:
  - 근거 없는 edge 금지
  - 8노드 초과 diagram 금지
  - 수치나 문서 근거가 없는 thesis impact 단정 금지
examples:
  - 금리 상승 → 차입비용 → 이자보상배율 path
  - 공시 tone 변화 → 회계 리스크 → thesis risk path
linkedSkills:
  - engines.viz
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-13'
---

## 절차

1. edge 마다 근거 문장, 수치, 또는 분석 결과 ref 를 붙인다.
2. `graph LR` 을 기본으로 쓰고 6~8노드 이하로 제한한다.
3. 노드 라벨에는 가능한 한 방향성 또는 임계값을 포함한다.
4. 관계 근거가 부족하면 diagram 을 만들지 않고 bullet path 로 낮춘다.

## 공개 호출 방식

```python
from dartlab.viz import emit_diagram

source = "graph LR\n  A[금리 +100bp] --> B[이자비용 증가]\n  B --> C[ICR 하락]"
emit_diagram("mermaid", source)
```

## 호출 동작

- 입력 view 또는 rows 를 검산 가능한 ChartSpec 으로 변환한다.
- `evidenceBinding` 또는 `evidenceIds` 가 없으면 emit 하지 않는다.
- 데이터가 부족하면 값을 추정하지 않고 표, coverage note, 또는 bullet path 로 낮춘다.

## 대표 반환 형태

- `dict` ChartSpec: `chartType`, `title`, `series` 또는 `data`, `categories`, `evidenceBinding`, `meta`.
- Mermaid 계열은 diagram source 와 node/edge evidence refs 를 함께 남긴다.

## 기본 검증

- diagram 의 모든 edge 가 answer claim 또는 evidence ref 로 되짚어져야 한다.
- Mermaid 는 설명을 대체하지 않고 메커니즘 섹션에만 배치한다.
