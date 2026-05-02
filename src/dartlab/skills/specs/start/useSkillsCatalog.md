---
id: start.useSkillsCatalog
title: Skill catalog 기반 작업 시작
kind: curated
scope: builtin
status: unverified
category: start
purpose: DartLab 코드 전체를 읽기 전에 skills catalog만 보고 목적 skill, capability, 근거 요구사항을 찾는 시작 절차다.
whenToUse:
  - dartlab skills 어떻게 써
  - dartlab 뭐 할 수 있어
  - dartlab 기능과 가능한 분석
  - 스킬만 보고 시작
  - 외부 AI가 DartLab 기능을 찾기
  - 목적 기반 capability 검색
  - show 함수 사용법
inputs:
  - 사용자 질문
outputs:
  - selectedSkill
  - capabilityRefs
  - requiredEvidence
  - runtime limits
capabilityRefs:
  - Company
  - Company.show
  - Company.analysis
  - gather
  - scan
  - macro
  - quant
  - ChartResult
  - ask
toolRefs:
  - dartlab.skills.search
  - dartlab.skills.get
  - search_reference
requiredEvidence:
  - skillRef
expectedOutputs:
  - 목적 skill 후보
  - capability ref 목록
  - 실행 전 확인할 evidence 목록
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: supported
  pyodide:
    status: supported
    limitations:
      - 실제 분석 실행 가능 여부는 선택한 skill의 runtimeCompatibility를 따른다.
failureModes:
  - generic basic skill만 보고 분석 시작
  - DartLab 기능 설명 질문을 RuntimeDatasetCatalog만으로 답함
  - capability schema를 SkillSpec 안에서 찾으려 함
  - requiredEvidence 확인 없이 답변 작성
forbidden:
  - SkillSpec에 없는 API schema를 추측
  - capabilityRefs 확인 없이 실행 코드 작성
examples:
  - dartlab skills 어떻게 써?
  - 스킬만 보고 삼성전자 분석을 시작하려면?
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-02"
---

## 절차

- 사용자 질문을 그대로 skill 검색어로 사용해 curated skill을 먼저 찾는다.
- "뭐 할 수 있어", "기능", "사용법", "함수" 질문은 데이터셋보다 skill/capability ref를 먼저 근거로 삼는다.
- 사용법 답변은 코드 예시를 최소화하고, 숫자·날짜가 필요한 실행 claim처럼 보이지 않게 capability ref를 근거로 설명한다.
- 검색 결과가 generic `basic.*`뿐이면 질문의 목적어를 더 좁혀 다시 검색한다.
- 선택한 skill의 `capabilityRefs`, `requiredEvidence`, `runtimeCompatibility`를 읽는다.
- API 인자와 반환 구조는 capability view 또는 docstring에서 확인한다.
- 실행 전에는 어떤 ref를 만들어야 하는지 목록으로 고정한다.
