---
id: companyCausalReview
title: 기업 6막 인과 분석
kind: curated
scope: builtin
status: unverified
category: finance
purpose: 한 기업을 경제, 섹터, 기업, 재무, 가치 신호의 연결로 검토한다.
whenToUse:
  - 특정 기업의 종합 분석
  - 수익성, 안정성, 성장성, 경쟁력 판단
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
  - run_python
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
  - 단일 수치로 종합 판단
  - 업황/섹터 맥락 없이 강한 경쟁력 판단
forbidden:
  - 근거 없는 투자판단
  - 숫자 없는 재무 판단
examples:
  - 삼성전자 수익성 분석해줘
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
