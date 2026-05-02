---
id: dividendCapitalReturnReview
title: 배당과 주주환원 분석
kind: curated
scope: builtin
status: unverified
category: finance
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
