---
id: operation.issues
title: 이슈 관리
kind: curated
scope: builtin
status: observed
category: operation
purpose: 이슈 관리 운영 규칙을 Skill OS에서 확인하고 변경 전후 검증 게이트로 사용한다.
whenToUse:
  - 이슈 관리
  - issues
  - 1. 별도 이슈 폴더 없이 기존 인프라 3 개로 분담한다
  - 2. 연결 구조 — 테스트 docstring → 커밋 메시지 → Issue 로 역추적한다
  - 3. 이슈 수정 — 6 단계로 진행한다
  - 4. 테스트는 기능별 파일에 통합한다
  - 요약 — 명제 4 줄
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
  - dartlab://skills/operation.issues
procedure:
  - 1. 별도 이슈 폴더 없이 기존 인프라 3 개로 분담한다 기준을 확인한다.
  - 2. 연결 구조 — 테스트 docstring → 커밋 메시지 → Issue 로 역추적한다 기준을 확인한다.
  - 3. 이슈 수정 — 6 단계로 진행한다 기준을 확인한다.
  - 4. 테스트는 기능별 파일에 통합한다 기준을 확인한다.
  - 요약 — 명제 4 줄 기준을 확인한다.
  - 'docstring 에 `Regression for #N` 표기.'
  - 수정 전 FAIL 확인.
  - 수정 후 PASS 확인.
  - GitHub 이 자동으로 Issue 에 커밋 링크 연결.
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
  - 이슈 관리 규칙 확인
  - issues 작업을 Skill OS에서 시작
source:
  type: absorbed_skills
  absorbedKey: issues
  format: markdown
lastUpdated: '2026-05-03'
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- 공개 호출 방식과 대표 반환 형태는 skill에서 확인하고, 세부 필드는 capability/docstring으로 검산한다.
- 분석이나 변경 결과는 ref, 실행 로그, 테스트 결과로 검증한다.

## 실행 순서

- 1. 별도 이슈 폴더 없이 기존 인프라 3 개로 분담한다 기준을 확인한다.
- 2. 연결 구조 — 테스트 docstring → 커밋 메시지 → Issue 로 역추적한다 기준을 확인한다.
- 3. 이슈 수정 — 6 단계로 진행한다 기준을 확인한다.
- 4. 테스트는 기능별 파일에 통합한다 기준을 확인한다.
- 요약 — 명제 4 줄 기준을 확인한다.
- docstring 에 `Regression for #N` 표기.
- 수정 전 FAIL 확인.
- 수정 후 PASS 확인.
- GitHub 이 자동으로 Issue 에 커밋 링크 연결.

