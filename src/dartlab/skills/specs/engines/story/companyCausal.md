---
id: engines.story.companyCausal
title: 기업 6막 인과 분석
kind: curated
scope: builtin
status: unverified
category: engines
purpose: 한 기업을 경제, 섹터, 기업, 재무, 가치 신호의 연결로 검토한다.
whenToUse:
  - 기업 종합 분석
  - 6 막 인과
  - 경제→섹터→기업→재무→가치
  - 수익성 안정성 성장성
  - 경쟁력 평가
  - thesis 작성
inputs:
  - 기업명 또는 종목코드
outputs:
  - thesis
  - 근거 표
  - 리스크
capabilityRefs:
  - Company.analysis
  - Company.show
  - Company.quant
  - Company.story
  - scan
  - macro
toolRefs:
  - search_reference
  - RunPython
  - finalize_answer
knowledgeRefs:
  - dartlabCausalSixActs
  - financialStatementConcepts
requiredEvidence:
  - target
  - period
  - metric
  - table
expectedOutputs:
  - thesis
  - 근거 표
  - 리스크
  - 한계
visualGuidance:
  - 시계열 또는 비교 표가 있을 때만 chart를 만든다.
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
      - HuggingFace dartlab-data dart/finance/{stockCode}.parquet
      - HuggingFace dartlab-data dart/report/{stockCode}.parquet
    requiredSetup:
      - await dartlab.prefetch(stockCode) 후 Company(stockCode)를 생성한다.
    limitations:
      - live gather, 외부 macro API, OAuth ask는 브라우저 CORS/인증 제약으로 제외한다.
failureModes:
  - 단일 수치 (ROE 만 또는 PER 만) 로 6 막 종합 판단 — 경제·섹터·기업·재무·가치·전망 모두 묶어야
  - 업황/섹터 맥락 없이 경쟁력 판단 — engines.industry · engines.scan 결과와 연결 필수
  - 같은 기간 정렬 무시 — analysis · scan · macro 결과 period 일치 확인
  - 산업 분기 무시한 통합 평가 (제조 vs 금융 vs 바이오 차이)
  - thesis 와 risk 의 *대척점* 제시 누락 — 균형감 결여
  - 데이터 부재 항목을 *빈 자리* 로 둠 — limits 에 명시 필요
forbidden:
  - 근거 없는 투자판단 금지.
  - 숫자 없는 재무 판단 금지.
  - 6 막 중 일부만 보고 "종합" 단정 금지 — 모든 막의 evidence 또는 limits 명시.
  - 산업 분기 무시한 peer 비교 금지.
examples:
  - 삼성전자 6 막 종합 분석
  - 신한지주 (금융사) 6 막 — BIS·NIM·LCR 산업 분기
  - 사이클 회사 (반도체) 의 cycle phase + 인과
  - 신생 회사 (상장 2 년 미만) 6 막 한계 명시
  - thesis vs risk 대척 (균형 평가)
linkedSkills:
  - engines.story
  - engines.story.dartlabStory
  - engines.analysis
  - engines.macro
  - engines.industry
  - engines.scan
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-02"
---

## 절차

- 기업 식별과 사용 가능한 Company topic을 확인한다.
- macro, scan 또는 industry 맥락이 필요한지 reference에서 확인한다.
- Company.analysis와 원본 show 결과를 실행해 수치 근거를 만든다.
- 판단 claim은 대상, 기간, metric, value ref에 묶는다.

## 공개 호출 방식

- `c = dartlab.Company("005930")`
- `c.story()`
- `dartlab.story(c)`

## 호출 동작

- analysis, credit, macro, scan, quant 결과를 thesis/evidence/risk/limit 구조로 조립한다. 숫자 계산은 하위 엔진 결과 ref에 묶는다.
- 실행 전에 target, period/date, metric, source 또는 universe를 확인한다.
- 데이터가 없거나 runtime 제한이 있으면 값을 추정하지 않고 한계와 필요한 다음 수집 경로를 말한다.

## 대표 반환 형태

- report dict 또는 block list를 반환한다. 핵심 키는 thesis, evidenceBlocks, riskBlocks, limits, sourceRefs다.
- 전체 세부 필드는 공개 docstring/capability와 동기화한다. 코드/API 변경으로 이 설명이 오래되면 skill 갱신 누락으로 본다.

## 기본 검증

- 실행 결과는 tableRef, valueRef, dateRef, executionRef 중 필요한 근거로 남긴다.
- 최종 판단의 숫자 claim은 해당 table/value ref에 직접 묶는다.
- 스킬과 실제 공개 API의 호출 방식, 대표 반환 형태, 오류/제한 동작이 다르면 같은 변경에서 스킬을 갱신한다.


