---
id: creditRiskReview
title: 신용 위험 분석
kind: curated
scope: builtin
status: unverified
category: finance
purpose: 기업의 재무 안정성, 차입 부담, 현금흐름 방어력을 신용 관점에서 점검한다.
whenToUse:
  - 기업 신용 위험
  - 재무 안정성 분석
  - 부채와 이자보상 위험
inputs:
  - 기업명 또는 종목코드
outputs:
  - credit thesis
  - 위험 근거
  - 완화 요인
capabilityRefs:
  - Company.credit
  - credit
  - Company.analysis
  - Company.show
  - scan.debt
  - scan.cashflow
toolRefs:
  - search_reference
  - run_python
  - finalize_answer
knowledgeRefs:
  - creditRiskConcepts
requiredEvidence:
  - target
  - period
  - metric
  - table
expectedOutputs:
  - credit thesis
  - 위험 요인
  - 완화 요인
  - 한계
visualGuidance:
  - 부채, 현금흐름, 이자보상 추세 표가 있을 때만 chart를 만든다.
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
    requiredSetup:
      - Company 재무 snapshot을 먼저 prefetch한다.
    limitations:
      - 신용등급 외부 실시간 조회는 서버 또는 로컬 Python 환경에서만 가능하다.
failureModes:
  - 부채비율 하나만 보고 신용 결론
  - 현금흐름과 만기 구조 확인 누락
  - 금융업과 비금융업 기준 혼동
forbidden:
  - 근거 없는 등급 단정
  - 결손값을 0으로 간주
examples:
  - 기업 신용 위험 봐줘
  - 대우건설 재무 안정성 분석해줘
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-02"
---

## 절차

- Company.credit와 재무 안정성 관련 capability를 확인한다.
- 부채, 이자보상, 영업현금흐름, 유동성 지표를 같은 기간 기준으로 만든다.
- 위험 요인과 완화 요인을 별도 ref로 구분한다.
- 금융업이면 일반 부채비율 해석 한계를 남긴다.
