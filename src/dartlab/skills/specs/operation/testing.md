---
id: operation.testing
title: dartlab 테스트 · CI 운영 규칙
kind: curated
scope: builtin
status: observed
category: operation
purpose: dartlab 테스트 · CI 운영 규칙 운영 규칙을 Skill OS에서 확인하고 변경 전후 검증 게이트로 사용한다.
whenToUse:
  - dartlab 테스트 · CI 운영 규칙
  - testing
  - 1. 핵심 원칙 — 4 개로 간다
  - 2. 3-Tier CI 구조
  - Tier 1 — `ci-fast.yml` (PR + master push, 목표 ≤ 3 분)
  - Tier 2 — `ci-full.yml` (master push only, 목표 ≤ 10 분)
  - Tier 3 — `ci-nightly.yml` (cron 15:00 UTC = KST 00:00, 목표 ≤ 45 분)
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
  - dartlab://skills/operation.testing
procedure:
  - 1. 핵심 원칙 — 4 개로 간다 기준을 확인한다.
  - 2. 3-Tier CI 구조 기준을 확인한다.
  - Tier 1 — `ci-fast.yml` (PR + master push, 목표 ≤ 3 분) 기준을 확인한다.
  - Tier 2 — `ci-full.yml` (master push only, 목표 ≤ 10 분) 기준을 확인한다.
  - Tier 3 — `ci-nightly.yml` (cron 15:00 UTC = KST 00:00, 목표 ≤ 45 분) 기준을 확인한다.
  - '**module scope 권장** — 파일 단위 로드·해제.'
  - '**session scope 지양** — Company 여러 개 로드 누적 시 OOM.'
  - '**function scope** — 필요하면 사용, `gc.collect()` 권장.'
  - root `dartlab` logger 에 stderr `StreamHandler` 자동 부착 (최초 1 회).
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
  - dartlab 테스트 · CI 운영 규칙 규칙 확인
  - testing 작업을 Skill OS에서 시작
source:
  type: absorbed_skills
  absorbedKey: testing
  format: markdown
lastUpdated: '2026-05-03'
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- 공개 호출 방식과 대표 반환 형태는 skill에서 확인하고, 세부 필드는 capability/docstring으로 검산한다.
- 분석이나 변경 결과는 ref, 실행 로그, 테스트 결과로 검증한다.

## 실행 순서

- 1. 핵심 원칙 — 4 개로 간다 기준을 확인한다.
- 2. 3-Tier CI 구조 기준을 확인한다.
- Tier 1 — `ci-fast.yml` (PR + master push, 목표 ≤ 3 분) 기준을 확인한다.
- Tier 2 — `ci-full.yml` (master push only, 목표 ≤ 10 분) 기준을 확인한다.
- Tier 3 — `ci-nightly.yml` (cron 15:00 UTC = KST 00:00, 목표 ≤ 45 분) 기준을 확인한다.
- **module scope 권장** — 파일 단위 로드·해제.
- **session scope 지양** — Company 여러 개 로드 누적 시 OOM.
- **function scope** — 필요하면 사용, `gc.collect()` 권장.
- root `dartlab` logger 에 stderr `StreamHandler` 자동 부착 (최초 1 회).

