---
id: operation.refactorChecklist
title: Refactor Checklist — 대규모 rename / API 변경 6 단계
kind: curated
scope: builtin
status: observed
category: operation
purpose: Refactor Checklist — 대규모 rename / API 변경 6 단계 운영 규칙을 Skill OS에서 확인하고 변경 전후 검증 게이트로 사용한다.
whenToUse:
  - Refactor Checklist — 대규모 rename / API 변경 6 단계
  - refactor checklist
  - 자동 게이트 — 사람이 빠뜨려도 막히는 안전망
  - 6 단계 점검
  - 1. src 변경
  - 2. tests 변경
  - 3. Skills/ 문서 변경
inputs:
  - 작업 목적
  - 대상 엔진 또는 실행 환경
  - 검증 범위
outputs:
  - selected skill
  - capability/docstring handoff
  - verification gate
capabilityRefs: []
toolRefs:
  - search_reference
knowledgeRefs:
  - start.dartlabSkillOs
sourceRefs:
  - dartlab://skills/operation.refactorChecklist
procedure:
  - 자동 게이트 — 사람이 빠뜨려도 막히는 안전망 기준을 확인한다.
  - 6 단계 점검 기준을 확인한다.
  - 1. src 변경 기준을 확인한다.
  - 2. tests 변경 기준을 확인한다.
  - 3. Skills/ 문서 변경 기준을 확인한다.
  - '공개 API 메서드/함수/클래스 rename (예: `c.review()` → `c.story()`)'
  - '모듈 경로 이전 (예: `dartlab.engines.X` → `dartlab.providers.X`)'
  - '폐기 (예: `c.docs.X` namespace → `c.show(topic)` 단일 진입)'
  - registry/dataclass 필드 rename, 변수/contextvar rename
requiredEvidence:
  - skillRef
  - executionRef
  - sourceRef
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
    status: supported
    notes: []
failureModes:
  - Skill OS 검색 없이 과거 문서 경로를 직접 찾음
  - API schema를 skill 본문에 중복해 docstring/capability와 어긋남
  - 검증 게이트 없이 변경 또는 답변을 완료 처리함
forbidden:
  - 삭제된 운영 문서 경로를 공식 진입점으로 안내하지 않는다.
  - 공개 호출 방식, 대표 반환 형태, 오류/제한 동작을 skill과 불일치한 채 방치하지 않는다.
examples:
  - Refactor Checklist — 대규모 rename / API 변경 6 단계 규칙 확인
  - refactor-checklist 작업을 Skill OS에서 시작
source:
  type: absorbed_skills
  absorbedKey: refactor-checklist
  format: markdown
lastUpdated: '2026-05-03'
testUniverse:
  market: KR
  stockCodes:
    - "005930"
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- 공개 호출 방식과 대표 반환 형태는 skill에서 확인하고, 세부 필드는 capability/docstring으로 검산한다.
- 분석이나 변경 결과는 ref, 실행 로그, 테스트 결과로 검증한다.

## 실행 순서

- 자동 게이트 — 사람이 빠뜨려도 막히는 안전망 기준을 확인한다.
- 6 단계 점검 기준을 확인한다.
- 1. src 변경 기준을 확인한다.
- 2. tests 변경 기준을 확인한다.
- 3. Skills/ 문서 변경 기준을 확인한다.
- 공개 API 메서드/함수/클래스 rename (예: `c.review()` → `c.story()`)
- 모듈 경로 이전 (예: `dartlab.engines.X` → `dartlab.providers.X`)
- 폐기 (예: `c.docs.X` namespace → `c.show(topic)` 단일 진입)
- registry/dataclass 필드 rename, 변수/contextvar rename

