---
id: peerComparisonReview
title: 동종 기업 비교 분석
kind: curated
scope: builtin
status: unverified
category: finance
purpose: 둘 이상의 기업을 같은 metric, 같은 기간, 같은 기준으로 비교해 상대 우위와 한계를 판단한다.
whenToUse:
  - 삼성전자와 SK하이닉스 비교
  - 두 기업 경쟁력 비교
inputs:
  - 비교 대상 목록
  - 비교 축 또는 metric
capabilityRefs:
  - Company.analysis
  - Company.show
  - Company.quant
  - scan
toolRefs:
  - search_reference
  - run_python
  - compile_visual
  - finalize_answer
knowledgeRefs:
  - financialStatementConcepts
visualRefs:
  - comparisonChart
requiredEvidence:
  - target
  - period
  - metric
  - table
expectedOutputs:
  - 동일축 비교표
  - 우위/열위 판단
  - 데이터 누락 한계
visualGuidance:
  - 같은 metric을 대상별로 나란히 비교하는 chart만 허용한다.
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
      - 비교 대상별로 await dartlab.prefetch(stockCode)를 먼저 수행한다.
    limitations:
      - 여러 종목 parquet를 브라우저 메모리에 올리므로 대상 수를 작게 유지한다.
      - live market/macro 보강은 서버 환경에서만 한다.
failureModes:
  - partial comparison
  - 서로 다른 기간/metric 혼합
forbidden:
  - 한쪽 수치만으로 우열 단정
examples:
  - 삼성전자와 SK하이닉스 경쟁력 비교
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-02"
---

## 절차

- 각 대상의 식별 결과를 확인한다.
- 같은 metric과 기간을 가진 evidence를 대상별로 만든다.
- 한쪽만 있는 수치로 강한 비교 결론을 내지 않는다.
- 비교 표가 있으면 visual을 만든다.
