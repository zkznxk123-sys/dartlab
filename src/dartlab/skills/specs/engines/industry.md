---
id: engines.industry
title: Industry
kind: curated
scope: builtin
status: observed
category: engines
purpose: Industry 엔진의 목적, 경계, 조합 기준을 Skill OS에서 확인하고 실행은 capability/docstring으로 내려간다.
whenToUse:
  - Industry
  - industry
  - 1. 호출 계약 — 4 진입점으로 간다
  - Company-bound 인터페이스
  - 2. 핵심 원칙 — 분류체계는 데이터로, 코드는 파이프라인만
  - 3. 데이터 구조 — 4 JSON 파일로 간다
  - 3-1. taxonomy.json — 분류체계가 데이터다
inputs:
  - 작업 목적
  - 대상 엔진 또는 실행 환경
  - 검증 범위
outputs:
  - selected skill
  - capability/docstring handoff
  - verification gate
capabilityRefs:
  - industry
  - Company.industry
toolRefs:
  - search_reference
  - run_python
knowledgeRefs:
  - start.dartlabSkillOs
sourceRefs:
  - dartlab://skills/engines.industry
procedure:
  - 1. 호출 계약 — 4 진입점으로 간다 기준을 확인한다.
  - Company-bound 인터페이스 기준을 확인한다.
  - 2. 핵심 원칙 — 분류체계는 데이터로, 코드는 파이프라인만 기준을 확인한다.
  - 3. 데이터 구조 — 4 JSON 파일로 간다 기준을 확인한다.
  - 3-1. taxonomy.json — 분류체계가 데이터다 기준을 확인한다.
  - industries 키 = 산업 ID.
  - stages 키 = 공정 ID.
  - keywords = 빌드 파이프라인이 매칭에 사용.
  - '**AI/사람이 JSON 을 직접 편집하여 산업 추가, 키워드 갱신, 공정 재정의**.'
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
  - Industry 규칙 확인
  - industry 작업을 Skill OS에서 시작
source:
  type: absorbed_skill_os
  absorbedKey: industry
  format: markdown
lastUpdated: '2026-05-03'
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- API 세부 인자와 반환 구조는 capability/docstring을 확인한다.
- 분석이나 변경 결과는 ref, 실행 로그, 테스트 결과로 검증한다.

## 실행 순서

- 1. 호출 계약 — 4 진입점으로 간다 기준을 확인한다.
- Company-bound 인터페이스 기준을 확인한다.
- 2. 핵심 원칙 — 분류체계는 데이터로, 코드는 파이프라인만 기준을 확인한다.
- 3. 데이터 구조 — 4 JSON 파일로 간다 기준을 확인한다.
- 3-1. taxonomy.json — 분류체계가 데이터다 기준을 확인한다.
- industries 키 = 산업 ID.
- stages 키 = 공정 ID.
- keywords = 빌드 파이프라인이 매칭에 사용.
- **AI/사람이 JSON 을 직접 편집하여 산업 추가, 키워드 갱신, 공정 재정의**.
