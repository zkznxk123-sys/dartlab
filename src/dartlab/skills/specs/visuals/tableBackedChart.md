---
id: visuals.tableBackedChart
title: 표 기반 시각 설명
kind: curated
scope: builtin
status: unverified
category: visuals
purpose: 차트나 다이어그램을 장식이 아니라 검산 가능한 표에서 파생되는 설명 산출물로 만든다.
whenToUse:
  - 비교 차트
  - 랭킹 차트
  - 시각 설명이 필요한 분석
inputs:
  - tableRef
outputs:
  - visualRef
toolRefs:
  - compile_visual
requiredEvidence:
  - table
  - metric
expectedOutputs:
  - validated visual
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
    limitations:
      - 시각화는 브라우저 renderer가 지원하는 chart spec 범위로 제한한다.
failureModes:
  - 단일값 chart
  - 근거 없는 diagram
forbidden:
  - tableRef 없는 차트
  - 단일 막대 차트
examples:
  - 최근 상승률 순위표를 차트로 보여줘
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-02"
---

## 절차

- 먼저 실행 결과에서 tableRef가 있는지 확인한다.
- category와 metric이 각각 2개 이상 비교 가능한지 확인한다.
- `compile_visual`은 tableRef 기반으로만 호출한다.
- visual이 실패하면 답변에 차트를 주장하지 않는다.
