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
  - 공개 호출 방식, 대표 반환 형태, 오류/제한 동작을 skill과 불일치한 채 방치하지 않는다.
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
- 공개 호출 방식과 대표 반환 형태는 skill에서 확인하고, 세부 필드는 capability/docstring으로 검산한다.
- 분석이나 변경 결과는 ref, 실행 로그, 테스트 결과로 검증한다.

## AI 채팅 UI 계약

- 채팅 본문은 최종 답변, 짧은 activity 로그, 실제 코드/시각화 실행 카드, 실패 notice, source 요약만 렌더한다.
- raw prompt, raw tool args/result JSON, 내부 trace JSON, `Agent Trace`, `투명성` 박스는 채팅 본문에 렌더하지 않는다.
- Evidence 패널은 source refs, datasets, raw tool input/output, verification, artifact를 분리해서 보관한다.
- 서버 SSE의 `activity` 이벤트가 사용자용 진행 표면의 정규 계약이다. legacy `reference`, `inspect`, `execute`, `verify`, `tool_*` 이벤트는 activity/message parts로 변환만 하고 직접 카드로 노출하지 않는다.
- 내부 tool id는 채팅 본문에 snake_case로 노출하지 않는다. 기본 표시명은 `replaceAll("_", " ")`를 적용하고, activity 문구는 `search reference 실행함`, `read context 실행함`, `inspect dataset 실행함`, `run python 실행함`, `compile visual 실행함`, `verify 실행함` 형식을 사용한다.
- 진행 중에는 최근 6개 activity만 보이고, 완료 후에는 `명령어 N개 실행` 한 줄로 접는다.
- 분석형 질문의 제품 순서는 `plan → search/read → inspect/run → verify → answer`다. 빈 chunk, 검색-only, tool 실패 은폐, 검증 실패는 성공 응답으로 release하지 않는다.

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

