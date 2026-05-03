---
id: operation.ui
title: UI 엔진 (L4 표현 계층)
kind: curated
scope: builtin
status: observed
category: operation
purpose: UI 엔진 (L4 표현 계층) 운영 규칙을 Skill OS에서 확인하고 변경 전후 검증 게이트로 사용한다.
whenToUse:
  - UI 엔진 (L4 표현 계층)
  - ui
  - 1. 한눈에 보기
  - 2. 디렉토리 구조
  - 3. 빌드
  - 4. 서버 연동 — `_ui_path.py::resolve_ui_build_dir()` 단일 함수로 경로 해석한다
  - UI 빌드 경로 해석 우선순위
inputs:
  - 작업 목적
  - 대상 엔진 또는 실행 환경
  - 검증 범위
outputs:
  - selected skill
  - capability/docstring handoff
  - verification gate
capabilityRefs: []
toolRefs:
  - search_reference
knowledgeRefs:
  - start.dartlabSkillOs
sourceRefs:
  - dartlab://skills/operation.ui
procedure:
  - 1. 한눈에 보기 기준을 확인한다.
  - 2. 디렉토리 구조 기준을 확인한다.
  - 3. 빌드 기준을 확인한다.
  - 4. 서버 연동 — `_ui_path.py::resolve_ui_build_dir()` 단일 함수로 경로 해석한다 기준을 확인한다.
  - UI 빌드 경로 해석 우선순위 기준을 확인한다.
  - '`/assets/*` → `{UI_BUILD}/assets/`.'
  - 나머지 → `{UI_BUILD}/index.html` (SPA fallback).
  - '`ensure_ui_build()` — GitHub ZIP 다운로드 제거. wheel 설치 후 `index.html` 존재만 확인, 없으면 `--force-reinstall`.'
  - '`runner.rs` — `DARTLAB_UI_DIR` 환경변수를 서버 프로세스에 주입.'
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
    status: supported
    notes: []
failureModes:
  - Skill OS 검색 없이 과거 문서 경로를 직접 찾음
  - API schema를 skill 본문에 중복해 docstring/capability와 어긋남
  - 검증 게이트 없이 변경 또는 답변을 완료 처리함
forbidden:
  - 삭제된 운영 문서 경로를 공식 진입점으로 안내하지 않는다.
  - API parameters/returns를 SkillSpec에 복사하지 않는다.
examples:
  - UI 엔진 (L4 표현 계층) 규칙 확인
  - ui 작업을 Skill OS에서 시작
source:
  type: absorbed_skill_os
  absorbedKey: ui
  format: markdown
lastUpdated: '2026-05-03'
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- API 세부 인자와 반환 구조는 capability/docstring을 확인한다.
- 분석이나 변경 결과는 ref, 실행 로그, 테스트 결과로 검증한다.

## 실행 순서

- 1. 한눈에 보기 기준을 확인한다.
- 2. 디렉토리 구조 기준을 확인한다.
- 3. 빌드 기준을 확인한다.
- 4. 서버 연동 — `_ui_path.py::resolve_ui_build_dir()` 단일 함수로 경로 해석한다 기준을 확인한다.
- UI 빌드 경로 해석 우선순위 기준을 확인한다.
- `/assets/*` → `{UI_BUILD}/assets/`.
- 나머지 → `{UI_BUILD}/index.html` (SPA fallback).
- `ensure_ui_build()` — GitHub ZIP 다운로드 제거. wheel 설치 후 `index.html` 존재만 확인, 없으면 `--force-reinstall`.
- `runner.rs` — `DARTLAB_UI_DIR` 환경변수를 서버 프로세스에 주입.
