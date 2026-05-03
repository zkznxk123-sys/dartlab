---
id: engines.search
title: Search *(beta — AI 사용 비권장)*
kind: curated
scope: builtin
status: observed
category: engines
purpose: Search *(beta — AI 사용 비권장)* 엔진의 목적, 경계, 조합 기준을 Skill OS에서 확인하고 실행은 capability/docstring으로 내려간다.
whenToUse:
  - Search *(beta — AI 사용 비권장)*
  - search
  - 1. scope — `title` 와 `content` 두 개로 간다
  - 2. 호출 계약 — 네 패턴으로 간다
  - 3. search vs listing — 내용 vs 카탈로그로 나눈다
  - 4. 구조 — core/search/ 3 모듈로 간다
  - 5. content 인덱스 — main + delta 세그먼트로 간다
inputs:
  - 작업 목적
  - 대상 엔진 또는 실행 환경
  - 검증 범위
outputs:
  - selected skill
  - capability/docstring handoff
  - verification gate
capabilityRefs:
  - search
  - Company.search
toolRefs:
  - search_reference
  - run_python
knowledgeRefs:
  - start.dartlabSkillOs
sourceRefs:
  - dartlab://skills/engines.search
procedure:
  - 1. scope — `title` 와 `content` 두 개로 간다 기준을 확인한다.
  - 2. 호출 계약 — 네 패턴으로 간다 기준을 확인한다.
  - 3. search vs listing — 내용 vs 카탈로그로 나눈다 기준을 확인한다.
  - 4. 구조 — core/search/ 3 모듈로 간다 기준을 확인한다.
  - 5. content 인덱스 — main + delta 세그먼트로 간다 기준을 확인한다.
  - '`scope="title"` (기본): report_nm + section_title ngram 검색. 제목형 쿼리 전용 ("유상증자", "대표이사 변경"). 95% precision · 1ms.'
  - '`scope="content"`: section_content 본문 BM25 검색. 개념/내용형 쿼리 전용 ("반도체 HBM 투자", "환율 변동 리스크").'
  - 두 엔진은 독립. **가중치 합산은 쓰지 않는다** — 실험 116 에서 합산 방식은 품질 저하 확인됨.
  - 외부 모델/서버 불필요 — 로컬 numpy 역인덱스만으로 동작.
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
  - Search *(beta — AI 사용 비권장)* 규칙 확인
  - search 작업을 Skill OS에서 시작
source:
  type: absorbed_skill_os
  absorbedKey: search
  format: markdown
lastUpdated: '2026-05-03'
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- API 세부 인자와 반환 구조는 capability/docstring을 확인한다.
- 분석이나 변경 결과는 ref, 실행 로그, 테스트 결과로 검증한다.

## 실행 순서

- 1. scope — `title` 와 `content` 두 개로 간다 기준을 확인한다.
- 2. 호출 계약 — 네 패턴으로 간다 기준을 확인한다.
- 3. search vs listing — 내용 vs 카탈로그로 나눈다 기준을 확인한다.
- 4. 구조 — core/search/ 3 모듈로 간다 기준을 확인한다.
- 5. content 인덱스 — main + delta 세그먼트로 간다 기준을 확인한다.
- `scope="title"` (기본): report_nm + section_title ngram 검색. 제목형 쿼리 전용 ("유상증자", "대표이사 변경"). 95% precision · 1ms.
- `scope="content"`: section_content 본문 BM25 검색. 개념/내용형 쿼리 전용 ("반도체 HBM 투자", "환율 변동 리스크").
- 두 엔진은 독립. **가중치 합산은 쓰지 않는다** — 실험 116 에서 합산 방식은 품질 저하 확인됨.
- 외부 모델/서버 불필요 — 로컬 numpy 역인덱스만으로 동작.
