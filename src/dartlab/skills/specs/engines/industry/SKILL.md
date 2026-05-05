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
  - 공개 호출 방식, 대표 반환 형태, 오류/제한 동작을 skill과 불일치한 채 방치하지 않는다.
examples:
  - Industry 규칙 확인
  - industry 작업을 Skill OS에서 시작
source:
  type: absorbed_skills
  absorbedKey: industry
  format: markdown
lastUpdated: '2026-05-03'
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- 공개 호출 방식과 대표 반환 형태는 skill에서 확인하고, 세부 필드는 capability/docstring으로 검산한다.
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

## 공개 호출 방식

- `c = dartlab.Company("005930")`
- `c.industry()`
- `dartlab.industry("semiconductor")`
- `dartlab.scan("industry")`

## 호출 동작

- 기업을 산업/섹터 맥락에 연결하고 peer, 산업 지표, cycle 신호를 확인한다. 개별 재무 계산은 analysis가 담당한다.
- 실행 전에 target, period/date, metric, source 또는 universe를 확인한다.
- 데이터가 없거나 runtime 제한이 있으면 값을 추정하지 않고 한계와 필요한 다음 수집 경로를 말한다.

## 대표 반환 형태

- industry profile dict 또는 peer DataFrame을 반환한다. 핵심 키는 industry, peers, cycle, indicators, rank, basis다.
- 전체 세부 필드는 공개 docstring/capability와 동기화한다. 코드/API 변경으로 이 설명이 오래되면 skill 갱신 누락으로 본다.

## 기본 검증

- 실행 결과는 tableRef, valueRef, dateRef, executionRef 중 필요한 근거로 남긴다.
- 최종 판단의 숫자 claim은 해당 table/value ref에 직접 묶는다.
- 스킬과 실제 공개 API의 호출 방식, 대표 반환 형태, 오류/제한 동작이 다르면 같은 변경에서 스킬을 갱신한다.


