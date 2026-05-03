---
id: engines.company
title: Company
kind: curated
scope: builtin
status: observed
category: engines
purpose: Company 엔진의 목적, 경계, 조합 기준을 Skill OS에서 확인하고 실행은 capability/docstring으로 내려간다.
whenToUse:
  - Company
  - company
  - 1. 호출 계약 — 종목코드 하나로 끝낸다
  - facade 고유 메서드 전수 목록
  - 데이터 조회 (핵심)
  - 탐색 메타 (property)
  - raw 데이터 접근 (property)
inputs:
  - 작업 목적
  - 대상 엔진 또는 실행 환경
  - 검증 범위
outputs:
  - selected skill
  - capability/docstring handoff
  - verification gate
capabilityRefs:
  - Company
  - Company.show
  - Company.select
  - Company.trace
toolRefs:
  - search_reference
  - run_python
knowledgeRefs:
  - start.dartlabSkillOs
sourceRefs:
  - dartlab://skills/engines.company
procedure:
  - 1. 호출 계약 — 종목코드 하나로 끝낸다 기준을 확인한다.
  - facade 고유 메서드 전수 목록 기준을 확인한다.
  - 데이터 조회 (핵심) 기준을 확인한다.
  - 탐색 메타 (property) 기준을 확인한다.
  - raw 데이터 접근 (property) 기준을 확인한다.
  - 기간 비교 가능 → 같은 회사의 과거와 현재를 나란히 놓는다 (sections, diff).
  - 기업 비교 가능 → 다른 회사의 같은 지표를 나란히 놓는다 (scan, analysis).
  - 비교 가능성이 모든 분석의 기반.
  - 완벽한 축을 세우는 게 모든 방향성.
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
  - Company 규칙 확인
  - company 작업을 Skill OS에서 시작
source:
  type: absorbed_skill_os
  absorbedKey: company
  format: markdown
lastUpdated: '2026-05-03'
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- API 세부 인자와 반환 구조는 capability/docstring을 확인한다.
- 분석이나 변경 결과는 ref, 실행 로그, 테스트 결과로 검증한다.

## 실행 순서

- 1. 호출 계약 — 종목코드 하나로 끝낸다 기준을 확인한다.
- facade 고유 메서드 전수 목록 기준을 확인한다.
- 데이터 조회 (핵심) 기준을 확인한다.
- 탐색 메타 (property) 기준을 확인한다.
- raw 데이터 접근 (property) 기준을 확인한다.
- 기간 비교 가능 → 같은 회사의 과거와 현재를 나란히 놓는다 (sections, diff).
- 기업 비교 가능 → 다른 회사의 같은 지표를 나란히 놓는다 (scan, analysis).
- 비교 가능성이 모든 분석의 기반.
- 완벽한 축을 세우는 게 모든 방향성.
