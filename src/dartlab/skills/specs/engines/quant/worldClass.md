---
id: engines.quant.worldClass
title: dartlab quant 세계 최강 — 사상 정합 + 성능 fix 플랜 (2026-04-25 v3)
kind: curated
scope: builtin
status: observed
category: engines
purpose: dartlab quant 세계 최강 — 사상 정합 + 성능 fix 플랜 (2026-04-25 v3) 엔진의 목적, 경계, 조합 기준을 Skill OS에서 확인하고 실행은 capability/docstring으로 내려간다.
whenToUse:
  - dartlab quant 세계 최강 — 사상 정합 + 성능 fix 플랜 (2026-04-25 v3)
  - quantWorldClass
  - 0. 재조사 결과 — 정확한 사상
  - story 엔진 정확한 사상 (v3 정정)
  - 1. 진짜 사상 위반 + 성능 버그 (v3)
  - ❌ 폐기 진단
  - 2. 8 Step 통합 플랜 — 진행 상태
inputs:
  - 작업 목적
  - 대상 엔진 또는 실행 환경
  - 검증 범위
outputs:
  - selected skill
  - capability/docstring handoff
  - verification gate
capabilityRefs:
  - quant
toolRefs:
  - search_reference
  - RunPython
knowledgeRefs:
  - start.dartlabSkillOs
sourceRefs:
  - dartlab://skills/engines.quantWorldClass
procedure:
  - 0. 재조사 결과 — 정확한 사상 기준을 확인한다.
  - story 엔진 정확한 사상 (v3 정정) 기준을 확인한다.
  - 1. 진짜 사상 위반 + 성능 버그 (v3) 기준을 확인한다.
  - ❌ 폐기 진단 기준을 확인한다.
  - 2. 8 Step 통합 플랜 — 진행 상태 기준을 확인한다.
  - '**V8** (story 6막 조립자 부재) — 완전 잘못. SECTIONS + buildBlocks + narrate 30+ 이미 완성'
  - '**V3** (alphas/ 디렉터리) — architecture 기준상 명확한 위반 아님'
  - ✅ Phase 2b 11/11 통과 (Step 1)
  - ✅ `c.quant("altman", "005930")` 단일 / `c.quant("altman")` 횡단면 / `c.quant.altman("005930")` attr (Step 6/7)
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
  - dartlab quant 세계 최강 — 사상 정합 + 성능 fix 플랜 (2026-04-25 v3) 규칙 확인
  - quantWorldClass 작업을 Skill OS에서 시작
source:
  type: absorbed_skills
  absorbedKey: quantWorldClass
  format: markdown
lastUpdated: '2026-05-03'
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- 공개 호출 방식과 대표 반환 형태는 skill에서 확인하고, 세부 필드는 capability/docstring으로 검산한다.
- 분석이나 변경 결과는 ref, 실행 로그, 테스트 결과로 검증한다.

## 실행 순서

- 0. 재조사 결과 — 정확한 사상 기준을 확인한다.
- story 엔진 정확한 사상 (v3 정정) 기준을 확인한다.
- 1. 진짜 사상 위반 + 성능 버그 (v3) 기준을 확인한다.
- ❌ 폐기 진단 기준을 확인한다.
- 2. 8 Step 통합 플랜 — 진행 상태 기준을 확인한다.
- **V8** (story 6막 조립자 부재) — 완전 잘못. SECTIONS + buildBlocks + narrate 30+ 이미 완성
- **V3** (alphas/ 디렉터리) — architecture 기준상 명확한 위반 아님
- ✅ Phase 2b 11/11 통과 (Step 1)
- ✅ `c.quant("altman", "005930")` 단일 / `c.quant("altman")` 횡단면 / `c.quant.altman("005930")` attr (Step 6/7)

## 공개 호출 방식

- `c = dartlab.Company("005930")`
- `c.quant()`
- `dartlab.quant("005930")`

## 호출 동작

- 가격, 밸류에이션, 모멘텀, 변동성, DCF/민감도 신호를 계산한다.
- 실행 전에 target, period/date, metric, source 또는 universe를 확인한다.
- 데이터가 없거나 runtime 제한이 있으면 값을 추정하지 않고 한계와 필요한 다음 수집 경로를 말한다.

## 대표 반환 형태

- dict 또는 DataFrame을 반환한다. 핵심 키는 valuation, momentum, volatility, assumptions, sensitivity, basis이며 가격은 원/달러, 비율은 %/배다.
- 전체 세부 필드는 공개 docstring/capability와 동기화한다. 코드/API 변경으로 이 설명이 오래되면 skill 갱신 누락으로 본다.

## 기본 검증

- 실행 결과는 tableRef, valueRef, dateRef, executionRef 중 필요한 근거로 남긴다.
- 최종 판단의 숫자 claim은 해당 table/value ref에 직접 묶는다.
- 스킬과 실제 공개 API의 호출 방식, 대표 반환 형태, 오류/제한 동작이 다르면 같은 변경에서 스킬을 갱신한다.


