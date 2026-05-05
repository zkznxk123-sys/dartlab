---
id: runtime.notebooks
title: notebooks 정책 — Colab vs Marimo
kind: curated
scope: builtin
status: observed
category: runtime
purpose: notebooks 정책 — Colab vs Marimo 실행 환경의 제약, 시작 절차, 검증 기준을 Skill OS에서 확인한다.
whenToUse:
  - notebooks 정책 — Colab vs Marimo
  - notebooks
  - 1. 설명 전략 — Colab 은 마크다운 허용, Marimo 는 주석으로만
  - 2. Colab 마크다운 분량 — 3~4 코드 셀마다 1 마크다운으로 간다
  - 3. Marimo 노트북 — 코드 셀 + 첫 줄 한글 주석으로 간다
  - 4. 공통 — 같은 코드·같은 순서로 동기화한다
  - 5. 파일 매핑
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
  - dartlab://skills/runtime.notebooks
procedure:
  - 1. 설명 전략 — Colab 은 마크다운 허용, Marimo 는 주석으로만 기준을 확인한다.
  - 2. Colab 마크다운 분량 — 3~4 코드 셀마다 1 마크다운으로 간다 기준을 확인한다.
  - 3. Marimo 노트북 — 코드 셀 + 첫 줄 한글 주석으로 간다 기준을 확인한다.
  - 4. 공통 — 같은 코드·같은 순서로 동기화한다 기준을 확인한다.
  - 5. 파일 매핑 기준을 확인한다.
  - '**Colab 은 마크다운 셀로 섹션 설명** — 학습·공유용 독자가 맥락을 빠르게 잡게.'
  - '**Marimo 는 코드만** — 실습·실행용. 설명은 코드 옆 짧은 주석으로.'
  - '노트북 최상단 1 장: 제목 + 한 줄 요약 + "이 노트북에서 다루는 것" 2~3 줄.'
  - 주요 섹션 전환점에만 1 장씩 — **3~4 코드 셀마다 1 마크다운**.
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
  - notebooks 정책 — Colab vs Marimo 규칙 확인
  - notebooks 작업을 Skill OS에서 시작
source:
  type: absorbed_skills
  absorbedKey: notebooks
  format: markdown
lastUpdated: '2026-05-03'
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- 공개 호출 방식과 대표 반환 형태는 skill에서 확인하고, 세부 필드는 capability/docstring으로 검산한다.
- 분석이나 변경 결과는 ref, 실행 로그, 테스트 결과로 검증한다.

## 실행 순서

- 1. 설명 전략 — Colab 은 마크다운 허용, Marimo 는 주석으로만 기준을 확인한다.
- 2. Colab 마크다운 분량 — 3~4 코드 셀마다 1 마크다운으로 간다 기준을 확인한다.
- 3. Marimo 노트북 — 코드 셀 + 첫 줄 한글 주석으로 간다 기준을 확인한다.
- 4. 공통 — 같은 코드·같은 순서로 동기화한다 기준을 확인한다.
- 5. 파일 매핑 기준을 확인한다.
- **Colab 은 마크다운 셀로 섹션 설명** — 학습·공유용 독자가 맥락을 빠르게 잡게.
- **Marimo 는 코드만** — 실습·실행용. 설명은 코드 옆 짧은 주석으로.
- 노트북 최상단 1 장: 제목 + 한 줄 요약 + "이 노트북에서 다루는 것" 2~3 줄.
- 주요 섹션 전환점에만 1 장씩 — **3~4 코드 셀마다 1 마크다운**.

