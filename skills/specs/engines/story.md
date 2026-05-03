---
id: engines.story
title: Story
kind: curated
scope: builtin
status: observed
category: engines
purpose: Story 엔진의 목적, 경계, 조합 기준을 Skill OS에서 확인하고 실행은 capability/docstring으로 내려간다.
whenToUse:
  - Story
  - story
  - 1. 사상 — 보고서 빌더로 간다
  - 방향성 메모 — docstring SSOT 와의 교류 (2026-04-24)
  - 2. 2 축 체계 — reportType × template 로 간다
  - 1 축 — reportType (무엇을 집중적으로 볼 것인가)
  - 2 축 — template (이 기업은 어떤 유형인가, 자동 감지)
inputs:
  - 작업 목적
  - 대상 엔진 또는 실행 환경
  - 검증 범위
outputs:
  - selected skill
  - capability/docstring handoff
  - verification gate
capabilityRefs:
  - Story
  - Company.story
toolRefs:
  - search_reference
  - run_python
knowledgeRefs:
  - start.dartlabSkillOs
sourceRefs:
  - dartlab://skills/engines.story
procedure:
  - 1. 사상 — 보고서 빌더로 간다 기준을 확인한다.
  - 방향성 메모 — docstring SSOT 와의 교류 (2026-04-24) 기준을 확인한다.
  - 2. 2 축 체계 — reportType × template 로 간다 기준을 확인한다.
  - 1 축 — reportType (무엇을 집중적으로 볼 것인가) 기준을 확인한다.
  - 2 축 — template (이 기업은 어떤 유형인가, 자동 감지) 기준을 확인한다.
  - '**docstring → story**: 엔진 docstring Guide 섹션이 audit 로 충분히 검증되면 story 블록 템플릿에 반영 (같은 해석 규칙 · 같은 임계값).'
  - '**story → docstring**: 기존 story 블록 중 재현 가능 · 해석 규칙 명확한 것은 공개 함수로 추출해 엔진 docstring 에 Guide 로 명시. AI · story 공용 호출.'
  - '`scorecard` — 5 영역 A~F 종합평가.'
  - '`creditScore` — 20 등급 신용평가.'
requiredEvidence:
  - skillRef
expectedOutputs:
  - 작업 경로
  - 확인한 근거
  - 검증 결과
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
    notes:
      - 실제 실행 가능 여부는 연결된 capability와 데이터 snapshot 범위를 따른다.
failureModes:
  - Skill OS 검색 없이 과거 문서 경로를 직접 찾음
  - API schema를 skill 본문에 중복해 docstring/capability와 어긋남
  - 검증 게이트 없이 변경 또는 답변을 완료 처리함
forbidden:
  - 삭제된 운영 문서 경로를 공식 진입점으로 안내하지 않는다.
  - API parameters/returns를 SkillSpec에 복사하지 않는다.
examples:
  - Story 규칙 확인
  - story 작업을 Skill OS에서 시작
source:
  type: absorbed_skill_os
  absorbedKey: story
  format: markdown
lastUpdated: '2026-05-03'
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- API 세부 인자와 반환 구조는 capability/docstring을 확인한다.
- 분석이나 변경 결과는 ref, 실행 로그, 테스트 결과로 검증한다.

## 실행 순서

- 1. 사상 — 보고서 빌더로 간다 기준을 확인한다.
- 방향성 메모 — docstring SSOT 와의 교류 (2026-04-24) 기준을 확인한다.
- 2. 2 축 체계 — reportType × template 로 간다 기준을 확인한다.
- 1 축 — reportType (무엇을 집중적으로 볼 것인가) 기준을 확인한다.
- 2 축 — template (이 기업은 어떤 유형인가, 자동 감지) 기준을 확인한다.
- **docstring → story**: 엔진 docstring Guide 섹션이 audit 로 충분히 검증되면 story 블록 템플릿에 반영 (같은 해석 규칙 · 같은 임계값).
- **story → docstring**: 기존 story 블록 중 재현 가능 · 해석 규칙 명확한 것은 공개 함수로 추출해 엔진 docstring 에 Guide 로 명시. AI · story 공용 호출.
- `scorecard` — 5 영역 A~F 종합평가.
- `creditScore` — 20 등급 신용평가.
