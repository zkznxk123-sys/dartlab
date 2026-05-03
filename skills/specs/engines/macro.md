---
id: engines.macro
title: Macro
kind: curated
scope: builtin
status: observed
category: engines
purpose: Macro 엔진의 목적, 경계, 조합 기준을 Skill OS에서 확인하고 실행은 capability/docstring으로 내려간다.
whenToUse:
  - Macro
  - macro
  - 1. 6 막 구조 — 경제 외부 인과를 추적한다
  - 2. 호출 계약 — 4 엔진 통일 패턴
  - Company-bound 인터페이스
  - 노트북
  - 3. macro → story 블록 매핑 — `종합` 1 회로 10 블록 채운다
inputs:
  - 작업 목적
  - 대상 엔진 또는 실행 환경
  - 검증 범위
outputs:
  - selected skill
  - capability/docstring handoff
  - verification gate
capabilityRefs:
  - macro
toolRefs:
  - search_reference
  - run_python
knowledgeRefs:
  - start.dartlabSkillOs
sourceRefs:
  - dartlab://skills/engines.macro
procedure:
  - 1. 6 막 구조 — 경제 외부 인과를 추적한다 기준을 확인한다.
  - 2. 호출 계약 — 4 엔진 통일 패턴 기준을 확인한다.
  - Company-bound 인터페이스 기준을 확인한다.
  - 노트북 기준을 확인한다.
  - 3. macro → story 블록 매핑 — `종합` 1 회로 10 블록 채운다 기준을 확인한다.
  - '**Company 불필요** — 종목코드 없이 동작 (macro 자체). 단 story 연동 시 `company.market` 참조.'
  - '**macro ↛ analysis** — 같은 L2 지만 상호 import 금지. 해석 조합은 AI(L3) 의 몫.'
  - '**numpy 만** — Hamilton RS, Kalman DFM, Nelson-Siegel, GaR 분위회귀, CP 팩터 전부 numpy 직접 구현. 외부 통계 라이브러리 0.'
  - '3 계층: L0(core/finance 순수함수) → L1(gather 수집) → L2(macro 분석축).'
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
  - Macro 규칙 확인
  - macro 작업을 Skill OS에서 시작
source:
  type: absorbed_skill_os
  absorbedKey: macro
  format: markdown
lastUpdated: '2026-05-03'
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- API 세부 인자와 반환 구조는 capability/docstring을 확인한다.
- 분석이나 변경 결과는 ref, 실행 로그, 테스트 결과로 검증한다.

## 실행 순서

- 1. 6 막 구조 — 경제 외부 인과를 추적한다 기준을 확인한다.
- 2. 호출 계약 — 4 엔진 통일 패턴 기준을 확인한다.
- Company-bound 인터페이스 기준을 확인한다.
- 노트북 기준을 확인한다.
- 3. macro → story 블록 매핑 — `종합` 1 회로 10 블록 채운다 기준을 확인한다.
- **Company 불필요** — 종목코드 없이 동작 (macro 자체). 단 story 연동 시 `company.market` 참조.
- **macro ↛ analysis** — 같은 L2 지만 상호 import 금지. 해석 조합은 AI(L3) 의 몫.
- **numpy 만** — Hamilton RS, Kalman DFM, Nelson-Siegel, GaR 분위회귀, CP 팩터 전부 numpy 직접 구현. 외부 통계 라이브러리 0.
- 3 계층: L0(core/finance 순수함수) → L1(gather 수집) → L2(macro 분석축).
