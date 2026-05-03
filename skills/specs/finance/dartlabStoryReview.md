---
id: dartlabStoryReview
title: DartLab 스토리형 분석
kind: curated
scope: builtin
status: unverified
category: finance
purpose: 여러 엔진의 근거를 thesis, evidence, risk, limit 구조로 조립한다.
whenToUse:
  - 기업을 이야기처럼 종합해달라는 질문
  - 보고서형 분석 요청
capabilityRefs:
  - Company.story
  - Company.analysis
  - Company.credit
  - Company.quant
toolRefs:
  - search_reference
  - run_python
  - finalize_answer
knowledgeRefs:
  - dartlabCausalSixActs
requiredEvidence:
  - target
  - period
  - metric
expectedOutputs:
  - thesis
  - evidence
  - risk
  - limits
visualGuidance:
  - story에는 설명 목적이 분명한 chart/table만 포함한다.
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
    status: supported
    dataSources:
      - HuggingFace dartlab-data dart/docs/{stockCode}.parquet
      - HuggingFace dartlab-data dart/finance/{stockCode}.parquet
      - HuggingFace dartlab-data dart/report/{stockCode}.parquet
    requiredSetup:
      - await dartlab.prefetch(stockCode) 후 Company(stockCode)를 생성한다.
    limitations:
      - 브라우저에서는 외부 API를 추가 호출하지 않고 prefetched parquet 기준으로만 작성한다.
failureModes:
  - 보고서 문장만 있고 수치 근거 없음
forbidden:
  - 검산 없는 서사형 투자판단
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-02"
---

## 절차

- story capability가 제공하는 report type과 한계를 확인한다.
- 필요한 하위 엔진 근거를 실행 결과로 확보한다.
- narrative는 숫자/날짜 claim ref를 가진 상태에서만 작성한다.
