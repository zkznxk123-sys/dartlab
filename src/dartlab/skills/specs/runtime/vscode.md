---
id: runtime.vscode
title: VSCode Extension
kind: curated
scope: builtin
status: observed
category: runtime
purpose: VSCode Extension 실행 환경의 제약, 시작 절차, 검증 기준을 Skill OS에서 확인한다.
whenToUse:
  - VSCode Extension
  - vscode
  - 1. 버전 — 0.2.x 끝자리만 올린다
  - 2. 배포 — 7 단계로 진행한다
  - 3. 아키텍처 — webview ↔ extension host ↔ Python backend 3 층으로 간다
  - 4. stdio 프로토콜 — 이 메시지 타입으로 주고받는다
  - 5. 프로바이더 연결 — 선택하면 바로 연결까지 끝낸다
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
  - dartlab://skills/runtime.vscode
procedure:
  - 1. 버전 — 0.2.x 끝자리만 올린다 기준을 확인한다.
  - 2. 배포 — 7 단계로 진행한다 기준을 확인한다.
  - 3. 아키텍처 — webview ↔ extension host ↔ Python backend 3 층으로 간다 기준을 확인한다.
  - 4. stdio 프로토콜 — 이 메시지 타입으로 주고받는다 기준을 확인한다.
  - 5. 프로바이더 연결 — 선택하면 바로 연결까지 끝낸다 기준을 확인한다.
  - '**0.2.x** — 끝자리만 올린다 (0.2.0 → 0.2.1 → 0.2.2 → …).'
  - '`ui/vscode/package.json` 의 `version` 필드가 진실의 원천.'
  - '태그: `vsce-{버전}` (예: `vsce-0.2.1`).'
  - 'CHANGELOG: `ui/vscode/CHANGELOG.md`.'
requiredEvidence:
  - skillRef
  - executionRef
  - sourceRef
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
  - VSCode Extension 규칙 확인
  - vscode 작업을 Skill OS에서 시작
source:
  type: absorbed_skills
  absorbedKey: vscode
  format: markdown
lastUpdated: '2026-05-03'
testUniverse:
  market: KR
  stockCodes:
    - "005930"
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- 공개 호출 방식과 대표 반환 형태는 skill에서 확인하고, 세부 필드는 capability/docstring으로 검산한다.
- 분석이나 변경 결과는 ref, 실행 로그, 테스트 결과로 검증한다.

## 실행 순서

- 1. 버전 — 0.2.x 끝자리만 올린다 기준을 확인한다.
- 2. 배포 — 7 단계로 진행한다 기준을 확인한다.
- 3. 아키텍처 — webview ↔ extension host ↔ Python backend 3 층으로 간다 기준을 확인한다.
- 4. stdio 프로토콜 — 이 메시지 타입으로 주고받는다 기준을 확인한다.
- 5. 프로바이더 연결 — 선택하면 바로 연결까지 끝낸다 기준을 확인한다.
- **0.2.x** — 끝자리만 올린다 (0.2.0 → 0.2.1 → 0.2.2 → …).
- `ui/vscode/package.json` 의 `version` 필드가 진실의 원천.
- 태그: `vsce-{버전}` (예: `vsce-0.2.1`).
- CHANGELOG: `ui/vscode/CHANGELOG.md`.

