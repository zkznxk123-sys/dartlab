---
id: engines.viz.tableBackedChart
title: 표 기반 시각 설명
kind: curated
scope: builtin
status: unverified
category: engines
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
  - evidenceBinding (chart 단위) 또는 evidenceIds (legacy) 가 비어 있는 차트
  - pointRefs 없이 datapoint drill-back 이 필요한 차트
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
- ChartSpec 직접 만들 때는 `dartlab.viz.refs.chartEvidenceBinding(...)` 으로 `evidenceBinding` 을 채운다 — `emit_chart` 는 evidence 회로 진입점이 없는 spec 을 거부한다.
- datapoint 단위 drill-back 이 필요한 series 는 `seriesPointRefs(...)` 로 `series[i].pointRefs` 를 채운다.

## 공개 호출 방식

- `result = c.analysis("financial", "수익성")`
- `chart = result.chart() 또는 dartlab.viz.tableBackedChart(table)`

## 호출 동작

- 표에서 파생 가능한 차트만 만든다. 단일값/근거 없는 장식 시각화는 만들지 않는다.
- 실행 전에 target, period/date, metric, source 또는 universe를 확인한다.
- 데이터가 없거나 runtime 제한이 있으면 값을 추정하지 않고 한계와 필요한 다음 수집 경로를 말한다.

## 대표 반환 형태

- ChartResult 또는 visual spec dict를 반환한다. 핵심 키는 data/tableRef, marks, x, y, unit, title, warnings다.
- 전체 세부 필드는 공개 docstring/capability와 동기화한다. 코드/API 변경으로 이 설명이 오래되면 skill 갱신 누락으로 본다.

## 기본 검증

- 실행 결과는 tableRef, valueRef, dateRef, executionRef 중 필요한 근거로 남긴다.
- 최종 판단의 숫자 claim은 해당 table/value ref에 직접 묶는다.
- 스킬과 실제 공개 API의 호출 방식, 대표 반환 형태, 오류/제한 동작이 다르면 같은 변경에서 스킬을 갱신한다.



