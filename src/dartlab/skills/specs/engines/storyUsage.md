---
id: engines.storyUsage
title: story 엔진 보고서 조합 사용 지도
kind: curated
scope: builtin
status: unverified
category: engines
purpose: 여러 엔진 결과를 story 보고서 타입으로 조합하되 새 claim을 만들지 않는 절차를 설명한다.
whenToUse:
  - 종합 보고서, executive summary, credit, valuation, crisis, governance 보고서가 필요할 때
  - analysis, credit, quant, macro 결과를 섹션별로 묶어야 할 때
  - 엔진 output을 사람이 읽기 좋은 보고서 구조로 바꿀 때
capabilityRefs:
  - Story
  - Company.story
  - analysis
  - credit
  - quant
  - macro
  - industry
toolRefs:
  - search_reference
  - run_python
datasetRefs:
  - dart.finance
  - dart.report
  - macro.raw
requiredEvidence:
  - target
  - reportType
  - sourceEngines
  - period
  - table
expectedOutputs:
  - report section map
  - source engine evidence chain
  - narrative limits
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
      - 보고서 조합은 가능하나 source engine 실행 범위에 좌우된다.
  pyodide:
    status: limited
    limitations:
      - HTML/rich 렌더링과 full source engine 실행은 환경별로 다르다.
failureModes:
  - story를 원자료 분석 엔진처럼 사용
  - source engine evidence 없이 새 narrative claim 생성
  - reportType과 질문 의도가 불일치
forbidden:
  - API parameters/returns를 SkillSpec에 중복하지 않는다.
  - story 출력만 근거로 숫자 검산을 끝내지 않는다.
examples:
  - credit 보고서는 credit, analysis 안정성/현금흐름/자금조달을 source engine으로 둔다.
  - valuation 보고서는 analysis 가치평가와 quant 가격 신호를 분리해 조합한다.
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-02"
---

## 가능한 분석

- story는 실행 결과를 보고서 구조로 묶는 조합기다.
- 엔진별 결과가 이미 있을 때 full, credit, valuation, crisis, governance 같은 보고서를 빠르게 만들 수 있다.

## 절차

- `basic.story`와 `Story` capability에서 report type과 source engine 관계를 확인한다.
- 질문 의도에 맞는 reportType을 고른다.
- source engine 결과가 없으면 먼저 analysis/credit/quant/macro/industry를 실행해 evidence를 만든다.
- story 결과는 narrative 구조로 쓰고, 숫자 검산은 source engine ref로 한다.
- 최종 답변에는 어떤 engine output이 어느 섹션을 뒷받침했는지 남긴다.
