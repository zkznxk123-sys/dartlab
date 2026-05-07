---
id: engines.dashboard
title: 대시보드 — 회사 종합 스냅샷 (v19 · 정보 깊이 확장)
kind: curated
scope: builtin
status: observed
category: engines
purpose: 대시보드 — 회사 종합 스냅샷 (v19 · 정보 깊이 확장) 엔진의 목적, 경계, 조합 기준을 Skill OS에서 확인하고 실행은 capability/docstring으로 내려간다. 트리거 — '회사 스냅샷', '종합 한눈에', 'dashboard'.
whenToUse:
  - 대시보드 — 회사 종합 스냅샷 (v19 · 정보 깊이 확장)
  - dashboard
  - 1. 설계 원칙 — 전 상장사 동시 커버 · 동적 조합 (v16 확정)
  - 2. 5-tier 데이터 구조 (v19)
  - 클라이언트 런타임 계산 (`assembleCompany.ts`)
  - 3. 섹션 → 데이터 매핑
  - 4. 빌드 — 로컬은 OOM 없이, CI matrix 로 큰 산출물을 분산한다
inputs:
  - 작업 목적
  - 대상 엔진 또는 실행 환경
  - 검증 범위
outputs:
  - selected skill
  - capability/docstring handoff
  - verification gate
capabilityRefs:
  - Company.view
toolRefs:
  - search_reference
  - run_python
knowledgeRefs:
  - start.dartlabSkillOs
sourceRefs:
  - dartlab://skills/engines.dashboard
procedure:
  - 1. 설계 원칙 — 전 상장사 동시 커버 · 동적 조합 (v16 확정) 기준을 확인한다.
  - 2. 5-tier 데이터 구조 (v19) 기준을 확인한다.
  - 클라이언트 런타임 계산 (`assembleCompany.ts`) 기준을 확인한다.
  - 3. 섹션 → 데이터 매핑 기준을 확인한다.
  - 4. 빌드 — 로컬은 OOM 없이, CI matrix 로 큰 산출물을 분산한다 기준을 확인한다.
  - 'radar 5 축: grades A-F → 1-5 스케일.'
  - 'Altman Z: `finance.bs.totals` 공식 (1.2A + 1.4B + 3.3C + 0.6D + 1.0E).'
  - 'Beneish M: 5-var simplified (DSRI · GMI · AQI).'
  - 'HHI + Top-N suppliers: `ecosystem.links` 필터.'
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
  - 대시보드 — 회사 종합 스냅샷 (v19 · 정보 깊이 확장) 규칙 확인
  - dashboard 작업을 Skill OS에서 시작
source:
  type: absorbed_skills
  absorbedKey: dashboard
  format: markdown
lastUpdated: '2026-05-07'
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- 공개 호출 방식과 대표 반환 형태는 skill에서 확인하고, 세부 필드는 capability/docstring으로 검산한다.
- 분석이나 변경 결과는 ref, 실행 로그, 테스트 결과로 검증한다.

## 실행 순서

- 1. 설계 원칙 — 전 상장사 동시 커버 · 동적 조합 (v16 확정) 기준을 확인한다.
- 2. 5-tier 데이터 구조 (v19) 기준을 확인한다.
- 클라이언트 런타임 계산 (`assembleCompany.ts`) 기준을 확인한다.
- 3. 섹션 → 데이터 매핑 기준을 확인한다.
- 4. 빌드 — 로컬은 OOM 없이, CI matrix 로 큰 산출물을 분산한다 기준을 확인한다.
- radar 5 축: grades A-F → 1-5 스케일.
- Altman Z: `finance.bs.totals` 공식 (1.2A + 1.4B + 3.3C + 0.6D + 1.0E).
- Beneish M: 5-var simplified (DSRI · GMI · AQI).
- HHI + Top-N suppliers: `ecosystem.links` 필터.

## 공개 호출 방식

- `c = dartlab.Company("005930")`
- `c.dashboard()`
- `c.show("dashboard")`

## 호출 동작

- Company의 주요 재무, 안정성, 수익성, 현금흐름, 이벤트를 한 화면용 snapshot으로 조합한다. 원자료가 없으면 해당 블록만 비워 둔다.
- 실행 전에 target, period/date, metric, source 또는 universe를 확인한다.
- 데이터가 없거나 runtime 제한이 있으면 값을 추정하지 않고 한계와 필요한 다음 수집 경로를 말한다.

## 대표 반환 형태

- dict 또는 table bundle을 반환한다. 핵심 키는 summary, metrics, blocks, warnings, sourceRefs이며 각 숫자는 period, value, unit을 유지한다.
- 전체 세부 필드는 공개 docstring/capability와 동기화한다. 코드/API 변경으로 이 설명이 오래되면 skill 갱신 누락으로 본다.

## 기본 검증

- 실행 결과는 tableRef, valueRef, dateRef, executionRef 중 필요한 근거로 남긴다.
- 최종 판단의 숫자 claim은 해당 table/value ref에 직접 묶는다.
- 스킬과 실제 공개 API의 호출 방식, 대표 반환 형태, 오류/제한 동작이 다르면 같은 변경에서 스킬을 갱신한다.


