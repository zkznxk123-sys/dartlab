---
id: operation.code
title: 코드 규칙
kind: curated
scope: builtin
status: observed
category: operation
purpose: 코드 규칙 운영 규칙을 Skill OS에서 확인하고 변경 전후 검증 게이트로 사용한다.
whenToUse:
  - 코드 규칙
  - code
  - 1. 네이밍 — camelCase 로 간다
  - 2. 독스트링 — 9 섹션으로 쓴다
  - AI 역할 — Guide 에 명시한다
  - Returns 작성 규칙 — 키 + 타입 + 단위를 명시한다
  - 3. CAPABILITIES — 단일 진실의 원천으로 간다
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
  - dartlab://skills/operation.code
procedure:
  - 1. 네이밍 — camelCase 로 간다 기준을 확인한다.
  - 2. 독스트링 — 9 섹션으로 쓴다 기준을 확인한다.
  - AI 역할 — Guide 에 명시한다 기준을 확인한다.
  - Returns 작성 규칙 — 키 + 타입 + 단위를 명시한다 기준을 확인한다.
  - 3. CAPABILITIES — 단일 진실의 원천으로 간다 기준을 확인한다.
  - 기존 코드의 네이밍 패턴을 따른다.
  - 이동된 기존 snake_case 는 하위호환 유지 (shim).
  - '**최신 먼저 역순** — 데이터 정렬 기본값.'
  - '`AI role:` 또는 `AI 역할:` 로 시작하는 짧은 문장을 둔다.'
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
  - 코드 규칙 규칙 확인
  - code 작업을 Skill OS에서 시작
source:
  type: absorbed_skill_os
  absorbedKey: code
  format: markdown
lastUpdated: '2026-05-03'
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- 공개 호출 방식과 대표 반환 형태는 skill에서 확인하고, 세부 필드는 capability/docstring으로 검산한다.
- 분석이나 변경 결과는 ref, 실행 로그, 테스트 결과로 검증한다.

## 실행 순서

- 1. 네이밍 — camelCase 로 간다 기준을 확인한다.
- 2. 독스트링 — 9 섹션으로 쓴다 기준을 확인한다.
- AI 역할 — Guide 에 명시한다 기준을 확인한다.
- Returns 작성 규칙 — 키 + 타입 + 단위를 명시한다 기준을 확인한다.
- 3. CAPABILITIES — 단일 진실의 원천으로 간다 기준을 확인한다.
- 기존 코드의 네이밍 패턴을 따른다.
- 이동된 기존 snake_case 는 하위호환 유지 (shim).
- **최신 먼저 역순** — 데이터 정렬 기본값.
- `AI role:` 또는 `AI 역할:` 로 시작하는 짧은 문장을 둔다.

