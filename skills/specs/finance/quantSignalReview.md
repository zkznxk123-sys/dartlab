---
id: quantSignalReview
title: 퀀트 신호 교차검토
kind: curated
scope: builtin
status: unverified
category: finance
purpose: 가격, 변동성, 밸류에이션, 모멘텀 신호를 같은 기준일에서 확인해 계량 판단을 보조한다.
whenToUse:
  - 이 종목 기술적으로 어떤지
  - 모멘텀과 변동성 같이 봐줘
capabilityRefs:
  - Company.quant
  - quant
toolRefs:
  - search_reference
  - run_python
  - compile_visual
  - finalize_answer
knowledgeRefs:
  - quantSignalConcepts
requiredEvidence:
  - target
  - metric
  - latestAsOf
  - table
expectedOutputs:
  - 신호 요약
  - 근거 표
  - 한계
visualGuidance:
  - 신호 여러 개를 비교하는 표가 있을 때만 chart를 만든다.
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
      - HuggingFace dartlab-data krx/prices parquet
      - HuggingFace dartlab-data dart/scan/finance-lite.parquet
    requiredSetup:
      - 가격 신호는 HF 가격 parquet 또는 이미 prefetched 데이터가 있을 때만 계산한다.
    limitations:
      - gather("price") 같은 외부 가격 API 호출은 브라우저 CORS 때문에 사용하지 않는다.
      - 가격 데이터가 없으면 재무/valuation-lite 기반 보조 신호로 제한한다.
failureModes:
  - 가격 기준일 누락
  - 단일 신호로 강한 판단
forbidden:
  - 근거 없는 매수/매도 단정
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-02"
---

## 절차

- 대상과 가격 데이터 기준일을 확인한다.
- quant capability의 사용 가능한 metric을 확인한다.
- 모멘텀/변동성/밸류에이션 신호를 같은 기준으로 계산한다.
