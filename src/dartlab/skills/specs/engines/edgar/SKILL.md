---
id: engines.edgar
title: EDGAR 동기화 규칙
kind: curated
scope: builtin
status: observed
category: engines
purpose: EDGAR 동기화 규칙 엔진의 목적, 경계, 조합 기준을 Skill OS에서 확인하고 실행은 capability/docstring으로 내려간다. 트리거 — '미국 공시', '10-K', 'SEC', 'EDGAR'.
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
  - 공개 호출 방식, 대표 반환 형태, 오류/제한 동작을 skill과 불일치한 채 방치하지 않는다.
examples:
  - EDGAR 동기화 규칙 규칙 확인
  - edgar 작업을 Skill OS에서 시작
source:
  type: absorbed_skills
  absorbedKey: edgar
  format: markdown
lastUpdated: '2026-05-07'
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- 공개 호출 방식과 대표 반환 형태는 skill에서 확인하고, 세부 필드는 capability/docstring으로 검산한다.
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

## 공개 호출 방식

- `c = dartlab.Company("AAPL")`
- `c.show("finance")`
- `c.liveFilings()`
- `dartlab.gather("edgar", "AAPL")`

## 호출 동작

- SEC EDGAR snapshot 또는 live filings에서 미국 기업 재무와 공시 목록을 읽는다. DART 전용 경로로 대체하지 않는다.
- 실행 전에 target, period/date, metric, source 또는 universe를 확인한다.
- 데이터가 없거나 runtime 제한이 있으면 값을 추정하지 않고 한계와 필요한 다음 수집 경로를 말한다.

## 대표 반환 형태

- EDGAR finance/docs DataFrame 또는 filing list를 반환한다. 핵심 컬럼은 ticker, cik, accession, form, filedAt, period, concept, value, unit이다.
- 전체 세부 필드는 공개 docstring/capability와 동기화한다. 코드/API 변경으로 이 설명이 오래되면 skill 갱신 누락으로 본다.

## 기본 검증

- 실행 결과는 tableRef, valueRef, dateRef, executionRef 중 필요한 근거로 남긴다.
- 최종 판단의 숫자 claim은 해당 table/value ref에 직접 묶는다.
- 스킬과 실제 공개 API의 호출 방식, 대표 반환 형태, 오류/제한 동작이 다르면 같은 변경에서 스킬을 갱신한다.


