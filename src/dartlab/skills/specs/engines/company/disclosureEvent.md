---
id: engines.company.disclosureEvent
title: 공시 이벤트 중요도 검토
kind: curated
scope: builtin
status: unverified
category: engines
purpose: 기업 공시 목록과 가능한 경량 본문 근거를 확인해 중요한 이벤트 후보와 한계를 구분한다.
whenToUse:
  - 최근 공시 중요한 내용
  - DART 공시 영향 또는 리스크 질문
inputs:
  - 기업명 또는 종목코드
capabilityRefs:
  - Company.disclosure
  - Company.liveFilings
  - Company.readFiling
toolRefs:
  - search_reference
  - EngineCall
  - RunPython
  - finalize_answer
knowledgeRefs:
  - dartDisclosureStructure
requiredEvidence:
  - target
  - period
  - table
  - basis
expectedOutputs:
  - 중요 공시 후보
  - 판단 근거
  - 제목 기준 또는 본문 기준 한계
visualGuidance:
  - 공시 이벤트는 필요할 때 timeline/table 중심으로 설명한다.
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
      - HuggingFace dartlab-data dart/docs/{stockCode}.parquet
      - HuggingFace dartlab-data dart/report/{stockCode}.parquet
    requiredSetup:
      - await dartlab.prefetch(stockCode) 후 prefetched 공시/보고서 데이터만 사용한다.
    limitations:
      - liveFilings와 DART OpenAPI 직접 호출은 CORS 때문에 사용하지 않는다.
      - 본문 미조회 상태에서는 제목/프리빌드 기준 한계로 표시한다.
failureModes:
  - 제목 목록만 보고 영향 단정
  - sections 대량 로딩
forbidden:
  - 본문 근거 없는 영향 단정
examples:
  - 삼성전자 최근 공시 중요한 내용 찾아줘
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-02"
---

## 절차

- 공시 목록의 접수일, 제목, 유형을 확인한다.
- 가능한 경우 경량 본문 조회로 제목 기준 판단을 보강한다.
- 본문 미조회 상태에서는 제목 기준 우선순위라고 명시한다.

## 공개 호출 방식

- `c = dartlab.Company("005930")`
- `c.show()`
- `c.show("BS")`
- `c.index()`
- `c.trace()`

## 호출 동작

- 종목코드 또는 ticker를 target으로 고정하고 재무, 공시, 가격, 하위 엔진 호출의 단일 진입점을 제공한다. 무인자 호출은 사용 가능한 topic/axis 가이드를 반환한다.
- 실행 전에 target, period/date, metric, source 또는 universe를 확인한다.
- 데이터가 없거나 runtime 제한이 있으면 값을 추정하지 않고 한계와 필요한 다음 수집 경로를 말한다.

## 대표 반환 형태

- Company 객체 메서드는 topic별 DataFrame, dict, 또는 하위 엔진 결과를 반환한다. 핵심 식별자는 stockCode/ticker, companyName, period, topic, source, value, unit이다.
- 전체 세부 필드는 공개 docstring/capability와 동기화한다. 코드/API 변경으로 이 설명이 오래되면 skill 갱신 누락으로 본다.

## 기본 검증

- 실행 결과는 tableRef, valueRef, dateRef, executionRef 중 필요한 근거로 남긴다.
- 최종 판단의 숫자 claim은 해당 table/value ref에 직접 묶는다.
- 스킬과 실제 공개 API의 호출 방식, 대표 반환 형태, 오류/제한 동작이 다르면 같은 변경에서 스킬을 갱신한다.


