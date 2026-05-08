---
id: engines.quant.damodaranValuation
title: 가치평가 가정 분해 검토
kind: curated
scope: builtin
status: unverified
category: engines
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
  - RunPython
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

## 공개 호출 방식

- `c = dartlab.Company("005930")`
- `c.quant()`
- `dartlab.quant("005930")`
- `dartlab.quant("005930", axis="valuation")`

## 호출 동작

- 가격, 밸류에이션, 모멘텀, 변동성, DCF/민감도 신호를 계산한다. 재무 원자료는 Company/scan에서 확인한다.
- 실행 전에 target, period/date, metric, source 또는 universe를 확인한다.
- 데이터가 없거나 runtime 제한이 있으면 값을 추정하지 않고 한계와 필요한 다음 수집 경로를 말한다.

## 대표 반환 형태

- dict 또는 DataFrame을 반환한다. 핵심 키는 valuation, momentum, volatility, assumptions, sensitivity, basis이며 가격은 원/달러, 비율은 %/배다.
- 전체 세부 필드는 공개 docstring/capability와 동기화한다. 코드/API 변경으로 이 설명이 오래되면 skill 갱신 누락으로 본다.

## 기본 검증

- 실행 결과는 tableRef, valueRef, dateRef, executionRef 중 필요한 근거로 남긴다.
- 최종 판단의 숫자 claim은 해당 table/value ref에 직접 묶는다.
- 스킬과 실제 공개 API의 호출 방식, 대표 반환 형태, 오류/제한 동작이 다르면 같은 변경에서 스킬을 갱신한다.


