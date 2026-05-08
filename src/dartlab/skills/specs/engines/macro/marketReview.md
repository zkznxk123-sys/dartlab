---
id: engines.macro.marketReview
title: 거시 시장 환경 점검
kind: curated
scope: builtin
status: unverified
category: engines
purpose: 금리, 환율, 경기, 유동성 질문을 기업 분석의 상위 맥락으로 연결한다.
whenToUse:
  - 금리 환율 매크로
  - 경기 사이클과 시장 동향
  - 기업 분석 전에 거시 환경을 먼저 확인
inputs:
  - 시장 또는 국가
  - 기간
outputs:
  - macro thesis
  - 기준일
  - 기업/섹터 영향
capabilityRefs:
  - macro
  - Company.macro
  - scan
  - gather.macro
toolRefs:
  - search_reference
  - InspectDataset
  - RunPython
  - finalize_answer
knowledgeRefs:
  - dartlabCausalSixActs
  - macroCycleConcepts
requiredEvidence:
  - latestAsOf
  - metric
  - table
  - basis
expectedOutputs:
  - macro thesis
  - 기준일
  - 영향 경로
  - 한계
visualGuidance:
  - 금리, 환율, 지수처럼 2개 이상 관측값이 있는 표에서만 chart를 만든다.
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
      - HuggingFace dartlab-data macro snapshot
      - HuggingFace dartlab-data krx/indices parquet
    requiredSetup:
      - 사용 가능한 macro 또는 index snapshot을 RuntimeDatasetCatalog에서 먼저 확인한다.
    limitations:
      - live FRED, 환율, 금리 API 호출은 브라우저 CORS/인증 제약으로 제외한다.
failureModes:
  - 최신 관측일을 오늘로 오인
  - 단일 지표로 경기 판단
  - 기업 영향 경로 없이 수치만 나열
forbidden:
  - 기준일 없는 최근 매크로 판단
  - 데이터 없이 금리/환율 방향 단정
examples:
  - 금리 환율 매크로 상황 어때?
  - 최근 한국 경기 사이클을 보고 삼성전자에 미치는 영향 알려줘
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-02"
---

## 절차

- macro와 관련 dataset 후보를 찾고 최신 관측일을 확인한다.
- 금리, 환율, 유동성, 지수 중 질문에 필요한 metric을 같은 기준일로 묶는다.
- 기업 질문이 함께 있으면 macro에서 섹터, Company, 재무로 이어지는 영향 경로를 제한적으로 연결한다.
- 데이터 기준일과 live API 미사용 한계를 답변에 남긴다.

## 공개 호출 방식

- `dartlab.macro()`
- `dartlab.macro("KR")`
- `dartlab.macro("rates")`
- `c.macro()`

## 호출 동작

- 금리, 환율, 경기, 유동성 같은 시장 레벨 신호를 읽는다. 단일 기업 재무 계산을 대신하지 않고 상위 맥락으로 제공한다.
- 실행 전에 target, period/date, metric, source 또는 universe를 확인한다.
- 데이터가 없거나 runtime 제한이 있으면 값을 추정하지 않고 한계와 필요한 다음 수집 경로를 말한다.

## 대표 반환 형태

- macro table 또는 dict를 반환한다. 핵심 컬럼/키는 region, date/latestAsOf, indicator, value, unit, signal, basis다.
- 전체 세부 필드는 공개 docstring/capability와 동기화한다. 코드/API 변경으로 이 설명이 오래되면 skill 갱신 누락으로 본다.

## 기본 검증

- 실행 결과는 tableRef, valueRef, dateRef, executionRef 중 필요한 근거로 남긴다.
- 최종 판단의 숫자 claim은 해당 table/value ref에 직접 묶는다.
- 스킬과 실제 공개 API의 호출 방식, 대표 반환 형태, 오류/제한 동작이 다르면 같은 변경에서 스킬을 갱신한다.


