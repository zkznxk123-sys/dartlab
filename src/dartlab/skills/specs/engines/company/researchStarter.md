---
id: engines.company.researchStarter
title: 기업 분석 시작 라우터
kind: curated
scope: builtin
status: unverified
category: engines
purpose: 종목 또는 기업 질문을 받았을 때 어떤 분석 skill과 capability로 시작할지 결정한다.
whenToUse:
  - 종목 분석 어떻게 시작
  - 기업 분석 시작
  - 삼성전자 분석 첫 단계
  - ticker 분석 첫 단계
inputs:
  - 기업명 또는 종목코드
  - 질문 목적
outputs:
  - selected engine skill
  - target
  - starter evidence checklist
capabilityRefs:
  - Company.analysis
  - Company.show
  - Company.credit
  - Company.quant
  - Company.story
  - macro
  - scan
  - industry
toolRefs:
  - search_reference
  - EngineCall
  - RunPython
  - finalize_answer
requiredEvidence:
  - target
  - skillRef
  - period
expectedOutputs:
  - 분석 skill 선택
  - 필요한 capabilityRefs
  - 근거 체크리스트
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
      - HuggingFace dartlab-data edgar/finance/{ticker}.parquet
    limitations:
      - live filings, macro 보강, 신규 수집은 서버 또는 로컬 Python 경로에서 수행한다.
failureModes:
  - 질문 목적을 보지 않고 종합 분석으로 바로 진행
  - 기업 식별 없이 Company 실행
  - macro/sector 맥락이 필요한데 생략
  - 단일 기업 축 분석을 screen/ranking 질문으로 오분류
  - Company 원자료가 있는데 scan snapshot만으로 재무 결론을 작성
forbidden:
  - 근거 없는 투자판단
  - Company 편의성 원칙을 dartlab 전체 사상으로 오해
  - “분석해줘” 질문을 코드 사용법 설명으로만 답하기
examples:
  - 종목 분석 어떻게 시작해?
  - 삼성전자 분석 첫 단계 알려줘
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-02"
---

## 절차

- 기업명, 종목코드, ticker 중 무엇이 입력됐는지 먼저 식별한다.
- 질문 목적이 수익성, 현금흐름, 신용, 공시, 비교, 밸류에이션, 배당, 지배구조 중 어디에 가까운지 skill 검색으로 고른다.
- 단일 기업과 특정 축이 함께 있으면 해당 engine skill과 Company.analysis/Company.show를 먼저 사용한다. scan skill은 “후보”, “랭킹”, “전체 종목”, “많이 오른” 같은 횡단 의도가 있을 때만 1차 경로가 된다.
- 목적이 불명확하면 engines.story.companyCausal를 기본 후보로 두되, macro와 scan 맥락도 함께 확인한다.
- 선택한 skill의 requiredEvidence를 실행 전 체크리스트로 둔다.
- 실행 가능한 분석 질문이면 첫 답변에서 사용법만 설명하지 말고 target, period, source table ref를 만든 뒤 검산 가능한 결론을 낸다. 데이터가 부족하면 어떤 Company topic 또는 prebuild가 부족한지 한계로 남긴다.

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


