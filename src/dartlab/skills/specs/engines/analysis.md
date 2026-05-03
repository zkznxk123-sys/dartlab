---
id: engines.analysis
title: Analysis
kind: curated
scope: builtin
status: observed
category: engines
purpose: Analysis 엔진의 목적, 경계, 조합 기준을 Skill OS에서 확인하고 실행은 capability/docstring으로 내려간다.
whenToUse:
  - Analysis
  - analysis
  - 1. 호출 계약 — 5 엔진 통일 패턴으로 간다
  - 노트북
  - 2. 엔진 독립 규칙 — L2 상호 import 하지 않는다
  - 3. 6 막 인과 — 스토리 구조로 재무제표를 읽는다
  - 6 막
inputs:
  - 작업 목적
  - 대상 엔진 또는 실행 환경
  - 검증 범위
outputs:
  - selected skill
  - capability/docstring handoff
  - verification gate
capabilityRefs:
  - analysis
  - Company.analysis
toolRefs:
  - search_reference
  - run_python
knowledgeRefs:
  - start.dartlabSkillOs
sourceRefs:
  - dartlab://skills/engines.analysis
procedure:
  - 1. 호출 계약 — 5 엔진 통일 패턴으로 간다 기준을 확인한다.
  - 노트북 기준을 확인한다.
  - 2. 엔진 독립 규칙 — L2 상호 import 하지 않는다 기준을 확인한다.
  - 3. 6 막 인과 — 스토리 구조로 재무제표를 읽는다 기준을 확인한다.
  - 6 막 기준을 확인한다.
  - '**analysis ↛ credit, credit ↛ analysis** — 같은 L2 지만 상호 import 금지.'
  - '**macro ↛ analysis, analysis ↛ macro** — 같은 L2 지만 상호 import 금지. 시장 레벨 매크로 해석은 `dartlab.macro()` 엔진이 담당 (→ `Skill OS).'
  - 각 엔진이 데이터 필요하면 Company/core(L0/L1) 에서 직접 가져온다.
  - '**story 가 조합한다.** story 에서 analysis 블록과 credit 블록을 성격별로 블록식으로 조합하여 보고서를 구성한다.'
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
  - Analysis 규칙 확인
  - analysis 작업을 Skill OS에서 시작
source:
  type: absorbed_skill_os
  absorbedKey: analysis
  format: markdown
lastUpdated: '2026-05-03'
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- API 세부 인자와 반환 구조는 capability/docstring을 확인한다.
- 분석이나 변경 결과는 ref, 실행 로그, 테스트 결과로 검증한다.

## 실행 순서

- 1. 호출 계약 — 5 엔진 통일 패턴으로 간다 기준을 확인한다.
- 노트북 기준을 확인한다.
- 2. 엔진 독립 규칙 — L2 상호 import 하지 않는다 기준을 확인한다.
- 3. 6 막 인과 — 스토리 구조로 재무제표를 읽는다 기준을 확인한다.
- 6 막 기준을 확인한다.
- **analysis ↛ credit, credit ↛ analysis** — 같은 L2 지만 상호 import 금지.
- **macro ↛ analysis, analysis ↛ macro** — 같은 L2 지만 상호 import 금지. 시장 레벨 매크로 해석은 `dartlab.macro()` 엔진이 담당 (→ `Skill OS).
- 각 엔진이 데이터 필요하면 Company/core(L0/L1) 에서 직접 가져온다.
- **story 가 조합한다.** story 에서 analysis 블록과 credit 블록을 성격별로 블록식으로 조합하여 보고서를 구성한다.
