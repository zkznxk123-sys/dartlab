---
id: engines.quantWorldClass
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
  - run_python
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
  - API parameters/returns를 SkillSpec에 복사하지 않는다.
examples:
  - dartlab quant 세계 최강 — 사상 정합 + 성능 fix 플랜 (2026-04-25 v3) 규칙 확인
  - quantWorldClass 작업을 Skill OS에서 시작
source:
  type: absorbed_skill_os
  absorbedKey: quantWorldClass
  format: markdown
lastUpdated: '2026-05-03'
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- API 세부 인자와 반환 구조는 capability/docstring을 확인한다.
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
