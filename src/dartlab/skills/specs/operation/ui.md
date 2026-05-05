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
  - operation.aiProductReplatform
sourceRefs:
  - dartlab://skills/operation.ui
  - dartlab://skills/operation.aiProductReplatform
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
  type: absorbed_skills
  absorbedKey: ui
  format: markdown
lastUpdated: '2026-05-03'
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- 공개 호출 방식과 대표 반환 형태는 skill에서 확인하고, 세부 필드는 capability/docstring으로 검산한다.
- 분석이나 변경 결과는 ref, 실행 로그, 테스트 결과로 검증한다.

## AI 채팅 UI 계약

- AI 제품 바탕 교체의 상세 SSOT는 `operation.aiProductReplatform`이다. `operation.ui`는 UI 표현 계층 규칙만 보완한다.
- 공식 제품 경로는 `DartLab App → /api/ask stream → DartLabResearchGraph → Skill OS/Data/Verifier/Evidence`다.
- UI 표면은 LibreChat식 conversation/message parts 모델을 따른다. DartLab 브랜드, workspace, evidence, artifact viewer는 유지하되 채팅 본문은 message parts만 렌더한다.
- UI와 엔진 사이의 공개 stream은 AG-UI compatible event allowlist만 허용한다. 내부 kernel trace는 Agent Gateway에서 public event로 변환하고, raw trace는 Evidence/journal에만 저장한다.
- 허용 public event는 `TEXT_MESSAGE_*`, `TOOL_CALL_*`, `STATE_*`, `ACTIVITY_*`, `RUN_FINISHED`, `RUN_ERROR`다. 이 목록 밖 이벤트가 채팅 UI로 직접 들어오면 계약 위반이다.
- 새 web chat product path도 `/api/ask` stream을 사용한다. 별도 agent transport를 UI 공식 진입점으로 두지 않는다.
- AI 실행 루프의 공식 교체 지점은 `DartLabResearchGraph`다. 현재 호환 구현이 내부 Ask Workbench를 호출하더라도 제품 경계명과 node 계약은 `route_intent → select_skill → plan_evidence → execute_tool → observe_result → verify_claims → compose_answer → repair_or_fail`로 고정한다.
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

