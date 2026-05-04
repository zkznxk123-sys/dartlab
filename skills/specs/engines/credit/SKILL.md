---
id: engines.credit
title: Credit (dCR)
kind: curated
scope: builtin
status: observed
category: engines
purpose: Credit (dCR) 엔진의 목적, 경계, 조합 기준을 Skill OS에서 확인하고 실행은 capability/docstring으로 내려간다.
whenToUse:
  - Credit (dCR)
  - credit
  - 1. 호출 — `dartlab.credit` · `c.credit` 두 진입점으로 쓴다
  - 2. 7 축 — 이 구조로 평가한다
  - 3. 결과 구조 — 종합·축별·detail 3 형태로 반환한다
  - 종합 등급 (axis 미지정)
  - 축 단일 (axis 지정)
inputs:
  - 작업 목적
  - 대상 엔진 또는 실행 환경
  - 검증 범위
outputs:
  - selected skill
  - capability/docstring handoff
  - verification gate
capabilityRefs:
  - credit
  - Company.credit
toolRefs:
  - search_reference
  - run_python
knowledgeRefs:
  - start.dartlabSkillOs
sourceRefs:
  - dartlab://skills/engines.credit
procedure:
  - 1. 호출 — `dartlab.credit` · `c.credit` 두 진입점으로 쓴다 기준을 확인한다.
  - 2. 7 축 — 이 구조로 평가한다 기준을 확인한다.
  - 3. 결과 구조 — 종합·축별·detail 3 형태로 반환한다 기준을 확인한다.
  - 종합 등급 (axis 미지정) 기준을 확인한다.
  - 축 단일 (axis 지정) 기준을 확인한다.
  - 7 축 `metrics` 에 시계열 (YoY · 5 년 평균) 부착.
  - '`narrative` 키 추가 — 한국어 인과 문장 (story 블록 재료).'
  - '`debtRatio` — 부채비율 (%)'
  - '`interestCoverage` — 이자보상배율 (배)'
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
  - Credit (dCR) 규칙 확인
  - credit 작업을 Skill OS에서 시작
source:
  type: absorbed_skill_os
  absorbedKey: credit
  format: markdown
lastUpdated: '2026-05-03'
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- 공개 호출 방식과 대표 반환 형태는 skill에서 확인하고, 세부 필드는 capability/docstring으로 검산한다.
- 분석이나 변경 결과는 ref, 실행 로그, 테스트 결과로 검증한다.

## 실행 순서

- 1. 호출 — `dartlab.credit` · `c.credit` 두 진입점으로 쓴다 기준을 확인한다.
- 2. 7 축 — 이 구조로 평가한다 기준을 확인한다.
- 3. 결과 구조 — 종합·축별·detail 3 형태로 반환한다 기준을 확인한다.
- 종합 등급 (axis 미지정) 기준을 확인한다.
- 축 단일 (axis 지정) 기준을 확인한다.
- 7 축 `metrics` 에 시계열 (YoY · 5 년 평균) 부착.
- `narrative` 키 추가 — 한국어 인과 문장 (story 블록 재료).
- `debtRatio` — 부채비율 (%)
- `interestCoverage` — 이자보상배율 (배)

## 공개 호출 방식

- `c = dartlab.Company("005930")`
- `c.credit()`
- `dartlab.credit(c)`

## 호출 동작

- Company 재무 snapshot에서 차입, 현금흐름, 이자보상, 유동성 지표를 읽어 신용 위험을 계산한다. analysis와 상호 import하지 않고 필요한 데이터는 Company/core에서 직접 가져온다.
- 실행 전에 target, period/date, metric, source 또는 universe를 확인한다.
- 데이터가 없거나 runtime 제한이 있으면 값을 추정하지 않고 한계와 필요한 다음 수집 경로를 말한다.

## 대표 반환 형태

- dict 또는 DataFrame 형태의 신용 지표를 반환한다. 핵심 키는 grade/score, leverage, interestCoverage, cashflowBuffer, riskFlags, basis이며 비율은 %, 배수는 배 단위다.
- 전체 세부 필드는 공개 docstring/capability와 동기화한다. 코드/API 변경으로 이 설명이 오래되면 skill 갱신 누락으로 본다.

## 기본 검증

- 실행 결과는 tableRef, valueRef, dateRef, executionRef 중 필요한 근거로 남긴다.
- 최종 판단의 숫자 claim은 해당 table/value ref에 직접 묶는다.
- 스킬과 실제 공개 API의 호출 방식, 대표 반환 형태, 오류/제한 동작이 다르면 같은 변경에서 스킬을 갱신한다.


