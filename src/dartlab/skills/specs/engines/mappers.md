---
id: engines.mappers
title: Mappers
kind: curated
scope: builtin
status: observed
category: engines
purpose: Mappers 엔진의 목적, 경계, 조합 기준을 Skill OS에서 확인하고 실행은 capability/docstring으로 내려간다.
whenToUse:
  - Mappers
  - mappers
  - 1. 한눈에 보기
  - 2. 절대 원칙 — 7 개로 간다
  - 3. 아키텍처
  - 4. 6 매퍼
  - 5. 공통 유틸 (`common.py`) — 모든 파서·매퍼가 공유한다
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
  - run_python
knowledgeRefs:
  - start.dartlabSkillOs
sourceRefs:
  - dartlab://skills/engines.mappers
procedure:
  - 1. 한눈에 보기 기준을 확인한다.
  - 2. 절대 원칙 — 7 개로 간다 기준을 확인한다.
  - 3. 아키텍처 기준을 확인한다.
  - 4. 6 매퍼 기준을 확인한다.
  - 5. 공통 유틸 (`common.py`) — 모든 파서·매퍼가 공유한다 기준을 확인한다.
  - '`_metadata.description` — AI 가 이 매핑의 목적을 이해.'
  - key → value — 한국어 → 영문 canonical (일관된 패턴).
  - category·type 분류 — AI 가 새 항목을 자동 분류하는 학습 데이터.
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
  - Mappers 규칙 확인
  - mappers 작업을 Skill OS에서 시작
source:
  type: absorbed_skill_os
  absorbedKey: mappers
  format: markdown
lastUpdated: '2026-05-03'
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- API 세부 인자와 반환 구조는 capability/docstring을 확인한다.
- 분석이나 변경 결과는 ref, 실행 로그, 테스트 결과로 검증한다.

## 실행 순서

- 1. 한눈에 보기 기준을 확인한다.
- 2. 절대 원칙 — 7 개로 간다 기준을 확인한다.
- 3. 아키텍처 기준을 확인한다.
- 4. 6 매퍼 기준을 확인한다.
- 5. 공통 유틸 (`common.py`) — 모든 파서·매퍼가 공유한다 기준을 확인한다.
- `_metadata.description` — AI 가 이 매핑의 목적을 이해.
- key → value — 한국어 → 영문 canonical (일관된 패턴).
- category·type 분류 — AI 가 새 항목을 자동 분류하는 학습 데이터.
