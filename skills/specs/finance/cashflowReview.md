---
id: cashflowReview
title: 현금흐름 분석
kind: curated
scope: builtin
status: unverified
category: finance
purpose: 영업현금흐름, 투자, 재무활동, 이익의 현금 전환을 점검한다.
whenToUse:
  - 현금흐름 분석
  - 이익은 나는데 현금이 부족한지
  - FCF와 운전자본 변화
inputs:
  - 기업명 또는 종목코드
outputs:
  - cashflow thesis
  - 현금흐름 표
  - 품질 판단
capabilityRefs:
  - Company.analysis
  - Company.show
  - scan.cashflow
  - scan.quality
  - Company.credit
toolRefs:
  - search_reference
  - run_python
  - finalize_answer
knowledgeRefs:
  - cashflowConcepts
  - financialStatementConcepts
requiredEvidence:
  - target
  - period
  - metric
  - table
expectedOutputs:
  - cashflow thesis
  - CF 근거 표
  - 이익 품질
  - 한계
visualGuidance:
  - OCF, capex, FCF, 순이익 비교 표가 있을 때만 chart를 만든다.
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
      - HuggingFace dartlab-data dart/scan/finance-lite.parquet
    requiredSetup:
      - 현금흐름표가 포함된 Company finance snapshot을 확인한다.
    limitations:
      - 세부 운전자본 주석이 없는 snapshot에서는 원인 판단을 제한한다.
failureModes:
  - 순이익만 보고 현금흐름 판단
  - 투자현금흐름 지출을 모두 부정적으로 단정
  - 일회성 운전자본 변동을 구조 변화로 단정
forbidden:
  - CF 표 없이 현금 창출력 단정
  - 결손값을 0으로 대체
examples:
  - 삼양식품 현금흐름 분석해줘
  - 이익의 질이 좋은지 현금흐름으로 봐줘
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-02"
---

## 절차

- CF, IS, BS 관련 capability를 확인하고 같은 기간 기준으로 묶는다.
- OCF, capex, FCF, 순이익 또는 운전자본 변동을 표로 만든다.
- 현금흐름 품질 claim은 이익과 현금의 차이를 보여주는 ref에 묶는다.
- 세부 주석이 없으면 원인 판단을 제한한다.
