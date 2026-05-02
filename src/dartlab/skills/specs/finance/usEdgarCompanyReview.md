---
id: usEdgarCompanyReview
title: 미국 기업 EDGAR 분석
kind: curated
scope: builtin
status: unverified
category: finance
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
  - run_python
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
forbidden:
  - ticker 식별 없이 미국 기업 분석 시작
  - EDGAR 근거 없는 10-K/10-Q 판단
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
- Company.analysis, show, filings capability를 찾아 재무와 공시 근거를 분리한다.
- filing claim은 접수일, form, 제목 또는 본문 ref에 묶는다.
- fiscal period가 있는 경우 calendar period와 혼동하지 않도록 기준을 밝힌다.
