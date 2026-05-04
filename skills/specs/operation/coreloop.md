---
id: operation.coreloop
title: Core Loop — 자가개선 루프 운영 SSOT
kind: curated
scope: builtin
status: observed
category: operation
purpose: Core Loop — 자가개선 루프 운영 SSOT 운영 규칙을 Skill OS에서 확인하고 변경 전후 검증 게이트로 사용한다.
whenToUse:
  - Core Loop — 자가개선 루프 운영 SSOT
  - coreloop
  - 1. Legacy 5 Phase — O · P · R · F · A
  - 2. Phase O — 기록 인프라
  - legacy 구현 위치
  - 출력
  - v2 스키마
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
  - dartlab://skills/operation.coreloop
procedure:
  - 1. Legacy 5 Phase — O · P · R · F · A 기준을 확인한다.
  - 2. Phase O — 기록 인프라 기준을 확인한다.
  - legacy 구현 위치 기준을 확인한다.
  - 출력 기준을 확인한다.
  - v2 스키마 기준을 확인한다.
  - 아래 경로는 old AI runtime 기준이며 새 AI/skills 경로의 production 표준이 아니다.
  - 새 구현 위치는 `src/dartlab/ai` 와 `src/dartlab/skills` 의 trace, verify, provider, MCP 계약을 따른다.
  - compatibility 코드가 필요하면 새 `AuditPacket`/`ImprovementCandidate` 스키마로 어댑트한다.
  - I/O 실패 조용 무시 (응답 경로 보호).
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
  - Core Loop — 자가개선 루프 운영 SSOT 규칙 확인
  - coreloop 작업을 Skill OS에서 시작
source:
  type: absorbed_skill_os
  absorbedKey: coreloop
  format: markdown
lastUpdated: '2026-05-03'
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- 공개 호출 방식과 대표 반환 형태는 skill에서 확인하고, 세부 필드는 capability/docstring으로 검산한다.
- 분석이나 변경 결과는 ref, 실행 로그, 테스트 결과로 검증한다.

## 실행 순서

- 1. Legacy 5 Phase — O · P · R · F · A 기준을 확인한다.
- 2. Phase O — 기록 인프라 기준을 확인한다.
- legacy 구현 위치 기준을 확인한다.
- 출력 기준을 확인한다.
- v2 스키마 기준을 확인한다.
- 아래 경로는 old AI runtime 기준이며 새 AI/skills 경로의 production 표준이 아니다.
- 새 구현 위치는 `src/dartlab/ai` 와 `src/dartlab/skills` 의 trace, verify, provider, MCP 계약을 따른다.
- compatibility 코드가 필요하면 새 `AuditPacket`/`ImprovementCandidate` 스키마로 어댑트한다.
- I/O 실패 조용 무시 (응답 경로 보호).

