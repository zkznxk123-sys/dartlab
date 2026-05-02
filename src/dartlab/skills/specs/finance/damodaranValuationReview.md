---
id: damodaranValuationReview
title: 가치평가 가정 분해 검토
kind: curated
scope: builtin
status: unverified
category: finance
purpose: 성장, 마진, 재투자, 할인율, 터미널 가정을 분해해 가치평가 민감도와 한계를 검토한다.
whenToUse:
  - 다모다란식 가치평가
  - DCF 가정과 민감도 점검
capabilityRefs:
  - Company.analysis
  - Company.show
  - Company.quant
  - macro
toolRefs:
  - search_reference
  - run_python
  - finalize_answer
knowledgeRefs:
  - valuationPrinciples
requiredEvidence:
  - target
  - period
  - metric
  - table
  - basis
expectedOutputs:
  - valuation assumptions
  - sensitivity table
  - limits
visualGuidance:
  - 민감도 표가 있을 때만 heatmap/table visual을 고려한다.
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
    requiredSetup:
      - await dartlab.prefetch(stockCode) 후 재무/보고서 근거로 가정을 만든다.
    limitations:
      - 할인율, 금리, 시장가격 등 live macro/price 보강은 서버 환경에서 수행한다.
failureModes:
  - 할인율 근거 누락
  - 단일 숫자 목표가 단정
forbidden:
  - 출처 없는 할인율
  - 민감도 없는 DCF 결론
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-02"
---

## 절차

- 매출 성장률과 마진 추세를 실제 재무 데이터로 확인한다.
- 재투자율 또는 자본효율 가정의 근거를 확인한다.
- 할인율 또는 매크로 가정의 출처와 기준일을 밝힌다.
- 단일 목표가가 아니라 민감도 표와 한계를 함께 제시한다.
