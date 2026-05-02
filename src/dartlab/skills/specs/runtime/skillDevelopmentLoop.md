---
id: runtime.skillDevelopmentLoop
title: Skill 개발과 엔진 조합 루프
kind: curated
scope: builtin
status: unverified
category: runtime
purpose: 기본 엔진 capability를 조합해 엔진에 직접 정의되지 않은 분석 절차를 만들고 audit 결과를 docstring 또는 SkillSpec 개선으로 되돌리는 체계다.
whenToUse:
  - 스킬 개발 체계
  - 엔진 조합으로 새 분석 만들기
  - 엔진에 없는 분석을 응용
  - audit 결과를 skills에 반영
  - 독스트링 보강 후보 찾기
inputs:
  - 사용자 질문
  - audit 결과
  - selectedSkill
outputs:
  - skill gap
  - composition plan
  - docstring improvement candidate
  - curated SkillSpec candidate
capabilityRefs:
  - Company
  - Company.analysis
  - Company.show
  - Company.credit
  - Company.quant
  - gather
  - scan
  - macro
  - quant
  - ChartResult
toolRefs:
  - search_reference
  - inspect_dataset
  - run_python
  - compile_visual
  - finalize_answer
knowledgeRefs:
  - dartlabCausalSixActs
requiredEvidence:
  - skillRef
  - capabilityRef
  - auditResult
  - failureMode
expectedOutputs:
  - 반복 가능한 절차
  - 필요한 capabilityRefs
  - 승격 여부 판단
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
    status: limited
    limitations:
      - Pyodide에서는 live API가 필요한 조합을 서버 audit 없이 official로 승격하지 않는다.
failureModes:
  - 한 질문에 맞춘 runner를 skill로 고정
  - API 상세를 SkillSpec에 복사
  - 자동 metric만 보고 official 승격
  - 한 번 실패한 사례를 곧바로 docstring 문제로 단정
forbidden:
  - 질문별 실행 코드 저장
  - 답변 템플릿 저장
  - capability schema 중복
  - 사용자 확인 없는 official 승격
examples:
  - 엔진에 없는 분석도 skills만 보고 만들 수 있는지 확인해줘
  - audit에서 실패한 질문을 skill 또는 docstring 개선으로 반영해줘
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-02"
---

## 절차

- 실패 또는 신규 질문을 목적어, 대상, 필요한 근거, runtime 제약으로 나눈다.
- 먼저 `search_reference`로 curated skill을 찾고, 없으면 `basic.company`, `basic.scan`, `basic.macro`, `basic.quant`, `basic.viz` 중 필요한 엔진 조합을 선택한다.
- 조합이 capability의 Guide/AIContract만으로 충분히 설명되면 docstring 보강 후보로 둔다. 여러 capability를 묶는 분석 절차가 필요하면 curated SkillSpec 후보로 둔다.
- 서버 경유 `/api/ask` audit에서 같은 skill이 반복 P를 받으면 `auditP` 후보가 된다. `official`은 구조 lint, 서버 audit P, 사용자 확인을 모두 만족할 때만 허용한다.
- public API 자체가 새 축을 요구할 정도로 반복되면 docstring Guide/AIContract 또는 공식 엔진 axis로 승격하고, 기존 SkillSpec은 새 capability id를 참조하도록 축소한다.
