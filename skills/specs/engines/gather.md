---
id: engines.gather
title: Gather
kind: curated
scope: builtin
status: observed
category: engines
purpose: Gather 엔진의 목적, 경계, 조합 기준을 Skill OS에서 확인하고 실행은 capability/docstring으로 내려간다.
whenToUse:
  - Gather
  - gather
  - 1. 호출 — `gather()` 로 가이드, `gather("axis", "code")` 로 수집한다
  - 노트북
  - 2. API 키 미설정 시 — 3 경로로 안내한다
  - 3. Company-bound — `c.gather` 로 종목코드 자동 전달한다
  - 4. 4 축 — price · flow · macro · news
inputs:
  - 작업 목적
  - 대상 엔진 또는 실행 환경
  - 검증 범위
outputs:
  - selected skill
  - capability/docstring handoff
  - verification gate
capabilityRefs:
  - gather
toolRefs:
  - search_reference
  - run_python
knowledgeRefs:
  - start.dartlabSkillOs
sourceRefs:
  - dartlab://skills/engines.gather
procedure:
  - 1. 호출 — `gather()` 로 가이드, `gather("axis", "code")` 로 수집한다 기준을 확인한다.
  - 노트북 기준을 확인한다.
  - 2. API 키 미설정 시 — 3 경로로 안내한다 기준을 확인한다.
  - 3. Company-bound — `c.gather` 로 종목코드 자동 전달한다 기준을 확인한다.
  - 4. 4 축 — price · flow · macro · news 기준을 확인한다.
  - '**대화형 CLI (TTY)** — `promptAndSave` 가 입력을 받아 `.env` 에 저장하고 계속 실행. 사용자가 건너뛰면 `None` 반환.'
  - '**서버·백그라운드 (TTY 없음)** — `core.env.AuthKeyMissing` 예외를 raise. 예외 본문에 서비스명 · 발급 URL · `.env` 설정법 포함.'
  - '**AI 런타임 경유** — `core.env.AuthKeyMissing` 예외 본문을 상위 ask/runtime 경로가 사용자 안내로 전달한다.'
  - '**macro (L2)** — `dartlab.macro()` — 시장 레벨 매크로 해석 (사이클 · 금리 · 자산 · 심리 · 유동성). Company 불필요. → `src/dartlab/macro/README.md`.'
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
  - Gather 규칙 확인
  - gather 작업을 Skill OS에서 시작
source:
  type: absorbed_skill_os
  absorbedKey: gather
  format: markdown
lastUpdated: '2026-05-03'
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- API 세부 인자와 반환 구조는 capability/docstring을 확인한다.
- 분석이나 변경 결과는 ref, 실행 로그, 테스트 결과로 검증한다.

## 실행 순서

- 1. 호출 — `gather()` 로 가이드, `gather("axis", "code")` 로 수집한다 기준을 확인한다.
- 노트북 기준을 확인한다.
- 2. API 키 미설정 시 — 3 경로로 안내한다 기준을 확인한다.
- 3. Company-bound — `c.gather` 로 종목코드 자동 전달한다 기준을 확인한다.
- 4. 4 축 — price · flow · macro · news 기준을 확인한다.
- **대화형 CLI (TTY)** — `promptAndSave` 가 입력을 받아 `.env` 에 저장하고 계속 실행. 사용자가 건너뛰면 `None` 반환.
- **서버·백그라운드 (TTY 없음)** — `core.env.AuthKeyMissing` 예외를 raise. 예외 본문에 서비스명 · 발급 URL · `.env` 설정법 포함.
- **AI 런타임 경유** — `core.env.AuthKeyMissing` 예외 본문을 상위 ask/runtime 경로가 사용자 안내로 전달한다.
- **macro (L2)** — `dartlab.macro()` — 시장 레벨 매크로 해석 (사이클 · 금리 · 자산 · 심리 · 유동성). Company 불필요. → `src/dartlab/macro/README.md`.
