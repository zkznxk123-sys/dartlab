---
id: engines.creditUsage
title: credit 엔진 신용위험 사용 지도
kind: curated
scope: builtin
status: unverified
category: engines
purpose: 상환능력, 부채 부담, 유동성, 현금흐름, 공시 리스크를 credit 중심으로 검토하는 절차를 설명한다.
whenToUse:
  - 기업 신용 위험, 부도 위험, 재무 건전성을 평가할 때
  - 안정성 질문을 analysis보다 신용 관점으로 엄격히 보고 싶을 때
  - story credit 또는 crisis 보고서의 핵심 근거가 필요할 때
capabilityRefs:
  - credit
  - Company.credit
  - analysis
  - Company.analysis
  - scan
toolRefs:
  - search_reference
  - run_python
datasetRefs:
  - dart.finance
  - dart.report
requiredEvidence:
  - target
  - period
  - debt
  - cashflow
  - interestCoverage
  - score
expectedOutputs:
  - credit risk evidence
  - axis-level risk drivers
  - analysis cross-check refs
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
      - finance-lite 범위에서는 일부 상세 축이 제한될 수 있다.
  pyodide:
    status: limited
    dataSources:
      - HuggingFace dartlab-data finance-lite
    limitations:
      - full DART report 기반 공시 리스크는 서버 coverage와 다를 수 있다.
failureModes:
  - credit score를 투자등급 공시처럼 표현
  - 현금흐름 없는 부채비율만으로 신용 결론
  - detail 축 없이 종합 등급만 설명
forbidden:
  - API parameters/returns를 SkillSpec에 중복하지 않는다.
  - 공식 신용평가 등급처럼 단정하지 않는다.
examples:
  - 신용 위험은 credit 종합, analysis 안정성, analysis 현금흐름을 같이 보면 상환능력 원인이 보인다.
  - 위기 보고서는 credit과 story crisis를 연결한다.
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-02"
---

## 가능한 분석

- credit은 “재무가 좋아 보이는가”보다 “부채와 현금흐름이 버틸 수 있는가”에 특화된다.
- analysis 안정성/현금흐름과 묶으면 점수의 원인을 설명할 수 있다.

## 절차

- `basic.credit`과 `credit` capability에서 축과 evidence 요구를 확인한다.
- target과 period를 고정하고 종합 위험과 상세 축을 분리해 실행한다.
- 부채, 유동성, 현금흐름, 이자보상, 공시 리스크 중 어느 축이 결론을 이끄는지 찾는다.
- analysis 안정성/현금흐름으로 credit 결론을 교차 검증한다.
- 최종 답변에는 공식 외부 신용등급이 아니라 DartLab 내부 신용위험 평가라고 밝힌다.
