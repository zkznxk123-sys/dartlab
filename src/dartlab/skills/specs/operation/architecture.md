---
id: operation.architecture
title: dartlab 아키텍처 — 전체 청사진
kind: curated
scope: builtin
status: observed
category: operation
purpose: dartlab 아키텍처 — 전체 청사진 운영 규칙을 Skill OS에서 확인하고 변경 전후 검증 게이트로 사용한다.
whenToUse:
  - dartlab 아키텍처 — 전체 청사진
  - architecture
  - 1. 레이어 — L0→L4 5 층 구조로 간다
  - 2. 6 분석 엔진 — 두 소비자를 최고로 지원한다
  - 소비자별 차이
  - 3. 모듈 제공 패턴 — analysis 기준 (6 엔진 동일)
  - 4. import 방향 — L0 ← L1 ← L2 ← L3 하향만 허용한다
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
  - dartlab://skills/operation.architecture
procedure:
  - 1. 레이어 — L0→L4 5 층 구조로 간다 기준을 확인한다.
  - 2. 6 분석 엔진 — 두 소비자를 최고로 지원한다 기준을 확인한다.
  - 소비자별 차이 기준을 확인한다.
  - 3. 모듈 제공 패턴 — analysis 기준 (6 엔진 동일) 기준을 확인한다.
  - 4. import 방향 — L0 ← L1 ← L2 ← L3 하향만 허용한다 기준을 확인한다.
  - '**story 가 쓸 때** — 엔진의 calc 결과를 블록으로 변환하여 보고서에 배치. 해석 제공 안 함.'
  - '**AI 가 쓸 때** — AI 가 주체. 엔진 결과를 의심하고, 원본 (`c.show`) 으로 검증하고, override 로 재계산.'
  - 엔진은 양쪽 모두에게 최고의 재료를 제공한다. 숫자와 근거를 투명하게 반환하여 story 는 배치하고 AI 는 검증할 수 있게.
  - calc 함수는 **독립 모듈** — 다른 calc 호출 가능하지만 순환 없음.
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
  - dartlab 아키텍처 — 전체 청사진 규칙 확인
  - architecture 작업을 Skill OS에서 시작
source:
  type: absorbed_skills
  absorbedKey: architecture
  format: markdown
lastUpdated: '2026-05-03'
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- 공개 호출 방식과 대표 반환 형태는 skill에서 확인하고, 세부 필드는 capability/docstring으로 검산한다.
- 분석이나 변경 결과는 ref, 실행 로그, 테스트 결과로 검증한다.

## 실행 순서

- 1. 레이어 — L0→L4 5 층 구조로 간다 기준을 확인한다.
- 2. 6 분석 엔진 — 두 소비자를 최고로 지원한다 기준을 확인한다.
- 소비자별 차이 기준을 확인한다.
- 3. 모듈 제공 패턴 — analysis 기준 (6 엔진 동일) 기준을 확인한다.
- 4. import 방향 — L0 ← L1 ← L2 ← L3 하향만 허용한다 기준을 확인한다.
- **story 가 쓸 때** — 엔진의 calc 결과를 블록으로 변환하여 보고서에 배치. 해석 제공 안 함.
- **AI 가 쓸 때** — AI 가 주체. 엔진 결과를 의심하고, 원본 (`c.show`) 으로 검증하고, override 로 재계산.
- 엔진은 양쪽 모두에게 최고의 재료를 제공한다. 숫자와 근거를 투명하게 반환하여 story 는 배치하고 AI 는 검증할 수 있게.
- calc 함수는 **독립 모듈** — 다른 calc 호출 가능하지만 순환 없음.

