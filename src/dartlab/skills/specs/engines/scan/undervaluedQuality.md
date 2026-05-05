---
id: engines.scan.undervaluedQuality
title: 저평가·수익성 종목 후보 찾기
kind: curated
scope: builtin
status: unverified
category: engines
purpose: scan과 재무 prebuild를 이용해 밸류에이션이 낮고 수익성 근거가 있는 후보 종목을 횡단면으로 찾는다.
whenToUse:
  - 스캔엔진으로 저평가 종목 찾기
  - 저평가이면서 수익성 좋은 종목
  - value quality screen
inputs:
  - universe
  - valuation metric
  - profitability metric
outputs:
  - candidate table
  - screening basis
capabilityRefs:
  - scan
  - Company.analysis
datasetRefs:
  - dart.scan.financeLite
toolRefs:
  - search_reference
  - inspect_dataset
  - run_python
  - finalize_answer
knowledgeRefs:
  - valuationPrinciples
  - financialStatementConcepts
requiredEvidence:
  - universe
  - input
  - filters
  - metric
  - formula
  - table
  - basis
  - executionRef
expectedOutputs:
  - 저평가 후보 표
  - 입력/유니버스
  - 필터
  - 계산식/지표
  - 수익성 보조 지표
  - 한계
visualGuidance:
  - 후보가 2개 이상이고 동일 metric이 있을 때만 ranking chart를 만든다.
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: limited
  pyodide:
    status: limited
    dataSources:
      - HuggingFace dartlab-data dart/scan/finance-lite.parquet
    requiredSetup:
      - finance-lite prebuild를 브라우저 런타임에 로드한다.
    limitations:
      - full scan 축 전체가 아니라 prebuild에 포함된 지표 기준 후보만 만든다.
failureModes:
  - 낮은 PER/PBR만 보고 저평가 단정
  - 수익성 또는 재무 안정성 확인 없이 후보를 결론으로 포장
  - 후보를 bullet 나열로만 내고 valuation/profitability evidence table을 빠뜨림
forbidden:
  - 후보 종목을 매수 추천으로 단정
  - universe와 기준일 없는 ranking
  - 입력/필터/계산식/표 근거 없는 후보 발굴 답변
examples:
  - 스캔엔진으로 저평가 종목 찾아줘
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-02"
---

## 절차

- `engines.scan` 기본 skill로 가능한 횡단면 축을 확인한다.
- valuation metric과 profitability metric이 같은 universe와 기준일에서 있는지 확인한다.
- `run_python`으로 후보 표를 만들고 value metric만 아니라 profitability 보조 지표를 같이 둔다.
- 최종 답변은 입력/유니버스, 필터, 계산식/지표, 결과를 명시하고 후보별 valuation/profitability evidence table을 본문에 렌더링한다.
- 낮은 valuation은 후보 조건이지 최종 투자 판단이 아니라고 한계를 남긴다.

## 공개 호출 방식

- `dartlab.scan()`
- `dartlab.scan("fields")`
- `dartlab.scan("ratio", universe="KR")`
- `dartlab.scan("account", account="revenue")`

## 호출 동작

- 시장/유니버스 횡단면에서 필터, 순위, peer 위치를 계산한다. 단일 종목 원자료 확인은 Company가 우선이다.
- 실행 전에 target, period/date, metric, source 또는 universe를 확인한다.
- 데이터가 없거나 runtime 제한이 있으면 값을 추정하지 않고 한계와 필요한 다음 수집 경로를 말한다.

## 대표 반환 형태

- ranking/filter DataFrame을 반환한다. 핵심 컬럼은 universe, asOf/latestAsOf, stockCode/ticker, name, metric, value, rank, basis다.
- 전체 세부 필드는 공개 docstring/capability와 동기화한다. 코드/API 변경으로 이 설명이 오래되면 skill 갱신 누락으로 본다.

## 기본 검증

- 실행 결과는 tableRef, valueRef, dateRef, executionRef 중 필요한 근거로 남긴다.
- 최종 판단의 숫자 claim은 해당 table/value ref에 직접 묶는다.
- 스킬과 실제 공개 API의 호출 방식, 대표 반환 형태, 오류/제한 동작이 다르면 같은 변경에서 스킬을 갱신한다.


