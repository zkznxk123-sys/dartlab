---
id: runtime.spaces
title: HuggingFace Spaces — API + MCP 서버
kind: curated
scope: builtin
status: observed
category: runtime
purpose: HuggingFace Spaces — API + MCP 서버 실행 환경의 제약, 시작 절차, 검증 기준을 Skill OS에서 확인한다.
whenToUse:
  - HuggingFace Spaces — API + MCP 서버
  - spaces
  - 1. 한눈에 보기
  - 2. 접근 방법 — 3 경로로 쓴다
  - 1) MCP (설치 없이 AI 에서 직접)
  - 2) REST API (curl · 브라우저)
  - 3) dartlab 설치 + 키 없음 (자동 fallback)
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
  - dartlab://skills/runtime.spaces
procedure:
  - 1. 한눈에 보기 기준을 확인한다.
  - 2. 접근 방법 — 3 경로로 쓴다 기준을 확인한다.
  - 1) MCP (설치 없이 AI 에서 직접) 기준을 확인한다.
  - 2) REST API (curl · 브라우저) 기준을 확인한다.
  - 3) dartlab 설치 + 키 없음 (자동 fallback) 기준을 확인한다.
  - 개별 종목 — `companyInsights` · `companyAnalysis` · `companyStory` · `companyValuation` · `companyCredit` · `companyGather` · `companyQuant` …
  - 시장·거시 — `macroAnalysis` · `marketScan` · `gatherData` · `quantAnalysis` · `topdownScreen`.
  - 검색·목록 — `searchCompany` · `dartlabSearch` · `dartlabListing`.
  - '`crtfc_key` 필드 자동 제거 (키 노출 방지).'
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
  - HuggingFace Spaces — API + MCP 서버 규칙 확인
  - spaces 작업을 Skill OS에서 시작
source:
  type: absorbed_skill_os
  absorbedKey: spaces
  format: markdown
lastUpdated: '2026-05-03'
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- API 세부 인자와 반환 구조는 capability/docstring을 확인한다.
- 분석이나 변경 결과는 ref, 실행 로그, 테스트 결과로 검증한다.

## 실행 순서

- 1. 한눈에 보기 기준을 확인한다.
- 2. 접근 방법 — 3 경로로 쓴다 기준을 확인한다.
- 1) MCP (설치 없이 AI 에서 직접) 기준을 확인한다.
- 2) REST API (curl · 브라우저) 기준을 확인한다.
- 3) dartlab 설치 + 키 없음 (자동 fallback) 기준을 확인한다.
- 개별 종목 — `companyInsights` · `companyAnalysis` · `companyStory` · `companyValuation` · `companyCredit` · `companyGather` · `companyQuant` …
- 시장·거시 — `macroAnalysis` · `marketScan` · `gatherData` · `quantAnalysis` · `topdownScreen`.
- 검색·목록 — `searchCompany` · `dartlabSearch` · `dartlabListing`.
- `crtfc_key` 필드 자동 제거 (키 노출 방지).
