---
id: operation.apiContract
title: API Contract — dartlab 호출 규칙 단일 진실의 원천
kind: curated
scope: builtin
status: observed
category: operation
purpose: API Contract — dartlab 호출 규칙 단일 진실의 원천 운영 규칙을 Skill OS에서 확인하고 변경 전후 검증 게이트로 사용한다.
whenToUse:
  - API Contract — dartlab 호출 규칙 단일 진실의 원천
  - api contract
  - 1. 단일 진입점 — Dual Access (call form + attr form) 로 간다
  - 구현
  - 좋은 예
  - 내부 series-tuple 빌더
  - 검증 방법
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
  - dartlab://skills/operation.apiContract
procedure:
  - 1. 단일 진입점 — Dual Access (call form + attr form) 로 간다 기준을 확인한다.
  - 구현 기준을 확인한다.
  - 좋은 예 기준을 확인한다.
  - 내부 series-tuple 빌더 기준을 확인한다.
  - 검증 방법 기준을 확인한다.
  - '**IS · CIS · CF (flow)** — 4 분기 모두 있을 때만 단순 합 (3 분기 이하 → None).'
  - '**BS (stock)** — Q4 (= 연말잔액). 없으면 그 해 가장 최근 분기.'
  - 공개 함수는 종목코드 (str) 또는 Company 만 받는다.
  - 추가 import 금지 — `import dartlab` 하나로 모든 기능 접근.
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
  - API Contract — dartlab 호출 규칙 단일 진실의 원천 규칙 확인
  - api-contract 작업을 Skill OS에서 시작
source:
  type: absorbed_skills
  absorbedKey: api-contract
  format: markdown
lastUpdated: '2026-05-03'
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- 공개 호출 방식과 대표 반환 형태는 skill에서 확인하고, 세부 필드는 capability/docstring으로 검산한다.
- 분석이나 변경 결과는 ref, 실행 로그, 테스트 결과로 검증한다.

## 실행 순서

- 1. 단일 진입점 — Dual Access (call form + attr form) 로 간다 기준을 확인한다.
- 구현 기준을 확인한다.
- 좋은 예 기준을 확인한다.
- 내부 series-tuple 빌더 기준을 확인한다.
- 검증 방법 기준을 확인한다.
- **IS · CIS · CF (flow)** — 4 분기 모두 있을 때만 단순 합 (3 분기 이하 → None).
- **BS (stock)** — Q4 (= 연말잔액). 없으면 그 해 가장 최근 분기.
- 공개 함수는 종목코드 (str) 또는 Company 만 받는다.
- 추가 import 금지 — `import dartlab` 하나로 모든 기능 접근.

