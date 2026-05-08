---
id: engines.company.usEdgarReview
title: 미국 기업 EDGAR 분석
kind: curated
scope: builtin
status: unverified
category: engines
purpose: 미국 ticker 또는 EDGAR 공시 질문을 Company, EDGAR filings, 재무 근거로 분석한다.
whenToUse:
  - 미국 주식 분석
  - EDGAR filings
  - 10-K 10-Q 공시 확인
  - AAPL NVDA TSLA 같은 ticker 질문
inputs:
  - ticker
  - 질문 주제
outputs:
  - company thesis
  - filing evidence
  - 한계
capabilityRefs:
  - OpenEdgar
  - Company.analysis
  - Company.show
  - Company.filings
  - Company.liveFilings
  - Company.readFiling
  - Company.quant
toolRefs:
  - search_reference
  - RunPython
  - finalize_answer
knowledgeRefs:
  - edgarFilingConcepts
  - dartlabCausalSixActs
requiredEvidence:
  - target
  - period
  - metric
  - table
  - basis
expectedOutputs:
  - filing-backed thesis
  - 재무 근거 표
  - 한계
visualGuidance:
  - 기간별 재무 표 또는 peer 비교 표가 있을 때만 chart를 만든다.
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
      - HuggingFace dartlab-data edgar/finance/{ticker}.parquet
      - HuggingFace dartlab-data edgar/docs/{ticker}.parquet
    requiredSetup:
      - ticker별 prefetched EDGAR snapshot이 있는지 먼저 확인한다.
    limitations:
      - SEC live API와 신규 filings 조회는 서버 또는 로컬 Python 경로에서 수행한다.
failureModes:
  - DART 전용 절차를 미국 ticker에 적용
  - filing 본문 없이 공시 영향 단정
  - fiscal period와 calendar period 혼동
  - EDGAR table/value ref 없이 매출, 마진, 현금흐름 같은 숫자 claim을 제출
  - ticker snapshot이 없는데 한국 Company/DART 경로로 우회
  - 검산 실패 후 같은 숫자 문장을 반복해 unable_to_finalize로 종료
forbidden:
  - ticker 식별 없이 미국 기업 분석 시작
  - EDGAR 근거 없는 10-K/10-Q 판단
  - numeric ref가 없을 때 정량 재무 결론을 단정
examples:
  - AAPL 분석해줘
  - NVDA 최근 EDGAR filings에서 중요한 내용 찾아줘
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-02"
---

## 절차

- ticker를 식별하고 EDGAR Company 경로가 가능한지 확인한다.
- EDGAR prefetched finance/docs snapshot 또는 OpenEdgar/Company.liveFilings 경로가 있는지 먼저 확인한다. 없으면 데이터 부재를 한계로 좁혀 말하고 DART 전용 경로로 대체하지 않는다.
- Company.analysis, Company.show, Company.filings/readFiling capability를 찾아 재무와 공시 근거를 분리한다.
- 재무 숫자는 EDGAR finance table/value ref가 있을 때만 말한다. 숫자 claim은 period, metric, value가 들어간 supporting ref에 직접 묶는다.
- filing claim은 접수일, form, 제목 또는 본문 ref에 묶는다.
- fiscal period가 있는 경우 calendar period와 혼동하지 않도록 기준을 밝힌다.
- 검산이 숫자 claim을 거절하면, ref로 뒷받침되는 filing/데이터 가용성 중심의 좁은 답변으로 줄인다.

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


