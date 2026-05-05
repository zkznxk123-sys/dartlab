---
id: engines.analysis.dividendCapitalReturn
title: 배당과 주주환원 분석
kind: curated
scope: builtin
status: unverified
category: engines
purpose: 배당, 자사주, 총환원율을 이익과 현금흐름의 지속 가능성 관점에서 분석한다.
whenToUse:
  - 배당 매력 분석
  - 주주환원 정책 점검
  - 자사주와 배당 지속 가능성
inputs:
  - 기업명 또는 종목코드
outputs:
  - capital return thesis
  - 배당/환원 표
  - 지속 가능성
capabilityRefs:
  - Company.capital
  - Company.analysis
  - Company.show
  - scan.dividendTrend
  - scan.cashflow
toolRefs:
  - search_reference
  - run_python
  - finalize_answer
knowledgeRefs:
  - capitalAllocationConcepts
requiredEvidence:
  - target
  - period
  - metric
  - table
expectedOutputs:
  - shareholder return thesis
  - 배당/자사주 근거
  - 지속 가능성 한계
visualGuidance:
  - 배당성향, 배당수익률, 총환원율 시계열 표가 있을 때만 chart를 만든다.
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
      - HuggingFace dartlab-data dart/finance/{stockCode}.parquet
      - HuggingFace dartlab-data dart/report/{stockCode}.parquet
      - HuggingFace dartlab-data dart/scan/finance-lite.parquet
    requiredSetup:
      - 배당/자본 관련 Company snapshot 또는 scan prebuild를 확인한다.
    limitations:
      - 공시 당일 신규 주주환원 이벤트는 live filings가 가능한 서버 경로에서 보강한다.
failureModes:
  - 배당수익률만 보고 매력 단정
  - 이익과 현금흐름 지속 가능성 확인 누락
  - 일회성 자사주 매입을 반복 정책으로 단정
forbidden:
  - 근거 없는 배당 지속 가능성 단정
  - 주가 기준일 없는 배당수익률 판단
examples:
  - 배당 매력 분석해줘
  - 주주환원 정책 지속 가능한지 봐줘
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-02"
---

## 절차

- Company.capital과 현금흐름 관련 capability를 함께 확인한다.
- 배당성향, 배당수익률, 자사주, 총환원율을 기간별 표로 만든다.
- 지속 가능성은 이익과 OCF/FCF 근거가 있을 때만 판단한다.
- 주가 또는 배당 기준일 한계를 답변에 남긴다.

## 공개 호출 방식

- `c = dartlab.Company("005930")`
- `c.analysis()`
- `c.analysis("financial", "수익성")`
- `dartlab.analysis(c, axis="financial", sub="수익성")`

## 호출 동작

- Company 재무 snapshot과 표준 계정 매핑을 읽어 단일 기업의 재무 축을 계산한다. 인자 없이 호출하면 사용 가능한 axis/subaxis 가이드 DataFrame을 반환한다. 데이터가 없으면 값을 만들지 않고 None 또는 데이터 부재 메시지로 제한한다.
- 실행 전에 target, period/date, metric, source 또는 universe를 확인한다.
- 데이터가 없거나 runtime 제한이 있으면 값을 추정하지 않고 한계와 필요한 다음 수집 경로를 말한다.

## 대표 반환 형태

- 주로 DataFrame 또는 dict-like 결과를 반환한다. 핵심 컬럼/키는 period, metric/account, value, unit, basis, comment이며 금액 단위는 원/백만원, 비율은 % 또는 배수다.
- 전체 세부 필드는 공개 docstring/capability와 동기화한다. 코드/API 변경으로 이 설명이 오래되면 skill 갱신 누락으로 본다.

## 기본 검증

- 실행 결과는 tableRef, valueRef, dateRef, executionRef 중 필요한 근거로 남긴다.
- 최종 판단의 숫자 claim은 해당 table/value ref에 직접 묶는다.
- 스킬과 실제 공개 API의 호출 방식, 대표 반환 형태, 오류/제한 동작이 다르면 같은 변경에서 스킬을 갱신한다.


