---
id: runtime.mcp
title: MCP
kind: curated
scope: builtin
status: observed
category: runtime
purpose: MCP 실행 환경의 제약, 시작 절차, 검증 기준을 Skill OS에서 확인한다.
whenToUse:
  - MCP
  - mcp
  - 1. 한눈에 보기
  - 2. 설치 — `.mcp.json` 에 dartlab 서버를 등록한다
  - 자동 설치 (프로젝트 루트에서)
  - 수동 설정 (`.mcp.json`)
  - 3. 실행 경로
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
  - dartlab://skills/runtime.mcp
procedure:
  - 1. 한눈에 보기 기준을 확인한다.
  - 2. 설치 — `.mcp.json` 에 dartlab 서버를 등록한다 기준을 확인한다.
  - 자동 설치 (프로젝트 루트에서) 기준을 확인한다.
  - 수동 설정 (`.mcp.json`) 기준을 확인한다.
  - 3. 실행 경로 기준을 확인한다.
  - 상한 5 인스턴스 · TTL 10 분 (`_CACHE_MAX` · `_CACHE_TTL`).
  - LRU 정책. 새 종목 로드 시 가장 오래된 항목 제거.
  - Company 로딩 자체가 수초 걸리므로 같은 종목 반복 질의에 유효.
  - '`ask` · `Company` · `setup` · `collect` · `config` 등 비분석 API.'
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
  - MCP 규칙 확인
  - mcp 작업을 Skill OS에서 시작
source:
  type: absorbed_skill_os
  absorbedKey: mcp
  format: markdown
lastUpdated: '2026-05-03'
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- API 세부 인자와 반환 구조는 capability/docstring을 확인한다.
- 분석이나 변경 결과는 ref, 실행 로그, 테스트 결과로 검증한다.

## 실행 순서

- 1. 한눈에 보기 기준을 확인한다.
- 2. 설치 — `.mcp.json` 에 dartlab 서버를 등록한다 기준을 확인한다.
- 자동 설치 (프로젝트 루트에서) 기준을 확인한다.
- 수동 설정 (`.mcp.json`) 기준을 확인한다.
- 3. 실행 경로 기준을 확인한다.
- 상한 5 인스턴스 · TTL 10 분 (`_CACHE_MAX` · `_CACHE_TTL`).
- LRU 정책. 새 종목 로드 시 가장 오래된 항목 제거.
- Company 로딩 자체가 수초 걸리므로 같은 종목 반복 질의에 유효.
- `ask` · `Company` · `setup` · `collect` · `config` 등 비분석 API.
