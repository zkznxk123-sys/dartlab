---
id: engines.analysisUsage
title: analysis 엔진 재무 인과 사용 지도
kind: curated
scope: builtin
status: unverified
category: engines
purpose: 단일 기업의 재무 원인, 가치, 전망, 리스크를 analysis 축 조합으로 해석하는 절차를 설명한다.
whenToUse:
  - 수익성, 성장성, 안정성, 현금흐름, 가치평가를 원인까지 분석할 때
  - 기업 재무제표의 변화 원인을 축별로 분해할 때
  - story나 credit의 근거를 재무 축으로 보강할 때
capabilityRefs:
  - analysis
  - Company.analysis
  - Company.show
  - Company.trace
  - scan
toolRefs:
  - search_reference
  - run_python
datasetRefs:
  - dart.finance
requiredEvidence:
  - target
  - axis
  - metric
  - period
  - value
  - table
expectedOutputs:
  - axis-level financial evidence
  - causal interpretation
  - limits and missing data notes
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: limited
    notes:
      - Web AI는 finance-lite snapshot에서 가능한 축 위주로 실행한다.
  pyodide:
    status: limited
    dataSources:
      - HuggingFace dartlab-data finance-lite
    limitations:
      - 전체 서버 finance 축과 동일한 coverage를 보장하지 않는다.
failureModes:
  - analysis guide table만 보고 실제 분석 결과처럼 답변
  - 단일 비율 하나로 수익성/안정성 전체 결론을 단정
  - 기간, 단위, 연결/별도 기준을 숨김
forbidden:
  - API parameters/returns를 SkillSpec에 중복하지 않는다.
  - 근거 축 없이 재무 원인 서사를 생성하지 않는다.
examples:
  - 수익성 악화는 수익성 축과 비용구조 축을 같이 확인하면 원가/판관비 원인을 분리할 수 있다.
  - 배당 매력은 현금흐름, 자본배분, 수익구조를 묶어 지속 가능성을 본다.
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-02"
---

## 가능한 분석

- analysis는 “무슨 숫자인가”보다 “왜 그렇게 변했는가”에 쓰는 엔진이다.
- 수익성, 현금흐름, 안정성, 자본배분, 가치평가를 조합하면 엔진에 단일 축으로 정의되지 않은 투자 논제도 만들 수 있다.

## 절차

- `basic.analysis`, `analysis`, `Company.analysis` capability를 먼저 확인한다.
- 질문을 재무 축으로 분해한다: 수익성/성장성/안정성/현금흐름/자본배분/가치평가/전망.
- target과 period를 고정하고 실제 축 결과를 실행해 표 evidence를 남긴다.
- 축 하나가 부족하면 보완 축을 추가한다. 예: 수익성은 비용구조, 현금흐름은 자본배분, 안정성은 credit.
- 최종 답변은 숫자, 기간, 단위, 인과 가정, 데이터 한계를 함께 남긴다.
