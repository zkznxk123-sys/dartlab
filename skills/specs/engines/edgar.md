---
id: engines.edgar
title: EDGAR 동기화 규칙
kind: curated
scope: builtin
status: observed
category: engines
purpose: EDGAR 동기화 규칙 엔진의 목적, 경계, 조합 기준을 Skill OS에서 확인하고 실행은 capability/docstring으로 내려간다.
whenToUse:
  - EDGAR 동기화 규칙
  - edgar
  - 1. EDGAR finance primary — SEC 벌크로 간다
  - 2. 한눈에 보기
  - 3. DartCompany ↔ EdgarCompany 동기화 — Public 메서드 양쪽 같게 간다
  - 4. EXEMPT 등록 기준
  - 등록할 수 있는 경우
inputs:
  - 작업 목적
  - 대상 엔진 또는 실행 환경
  - 검증 범위
outputs:
  - selected skill
  - capability/docstring handoff
  - verification gate
capabilityRefs:
  - Company.liveFilings
  - Company.rawDocs
toolRefs:
  - search_reference
  - run_python
knowledgeRefs:
  - start.dartlabSkillOs
sourceRefs:
  - dartlab://skills/engines.edgar
procedure:
  - 1. EDGAR finance primary — SEC 벌크로 간다 기준을 확인한다.
  - 2. 한눈에 보기 기준을 확인한다.
  - 3. DartCompany ↔ EdgarCompany 동기화 — Public 메서드 양쪽 같게 간다 기준을 확인한다.
  - 4. EXEMPT 등록 기준 기준을 확인한다.
  - 등록할 수 있는 경우 기준을 확인한다.
  - 데이터 수집·배포·freshness는 `engines.data`, `engines.gather`, `operation.testing` skill에서 확인한다.
  - Company namespace·notes·데이터 소스 차이는 `engines.company`와 `engines.edgar` skill에서 확인한다.
  - scan EDGAR 11 축·프리빌드는 `engines.scan` skill에서 확인한다.
  - gather market 분기는 `engines.gather` skill에서 확인한다.
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
  - EDGAR 동기화 규칙 규칙 확인
  - edgar 작업을 Skill OS에서 시작
source:
  type: absorbed_skill_os
  absorbedKey: edgar
  format: markdown
lastUpdated: '2026-05-03'
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- API 세부 인자와 반환 구조는 capability/docstring을 확인한다.
- 분석이나 변경 결과는 ref, 실행 로그, 테스트 결과로 검증한다.

## 실행 순서

- 1. EDGAR finance primary — SEC 벌크로 간다 기준을 확인한다.
- 2. 한눈에 보기 기준을 확인한다.
- 3. DartCompany ↔ EdgarCompany 동기화 — Public 메서드 양쪽 같게 간다 기준을 확인한다.
- 4. EXEMPT 등록 기준 기준을 확인한다.
- 등록할 수 있는 경우 기준을 확인한다.
- 데이터 수집·배포·freshness는 `engines.data`, `engines.gather`, `operation.testing` skill에서 확인한다.
- Company namespace·notes·데이터 소스 차이는 `engines.company`와 `engines.edgar` skill에서 확인한다.
- scan EDGAR 11 축·프리빌드는 `engines.scan` skill에서 확인한다.
- gather market 분기는 `engines.gather` skill에서 확인한다.
