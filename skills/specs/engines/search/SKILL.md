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
  - 공개 호출 방식, 대표 반환 형태, 오류/제한 동작을 skill과 불일치한 채 방치하지 않는다.
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
- 공개 호출 방식과 대표 반환 형태는 skill에서 확인하고, 세부 필드는 capability/docstring으로 검산한다.
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

## 공개 호출 방식

- `dartlab.search("삼성전자 공시")`
- `dartlab.Company("005930").disclosure()`

## 호출 동작

- 공시/문서/참조 텍스트를 검색한다. 인덱스 신선도가 부족하면 beta 한계를 명시하고 단일 종목 공시는 Company 경유를 우선한다.
- 실행 전에 target, period/date, metric, source 또는 universe를 확인한다.
- 데이터가 없거나 runtime 제한이 있으면 값을 추정하지 않고 한계와 필요한 다음 수집 경로를 말한다.

## 대표 반환 형태

- search result list/DataFrame을 반환한다. 핵심 컬럼은 title, snippet, source, date, score, url/ref다.
- 전체 세부 필드는 공개 docstring/capability와 동기화한다. 코드/API 변경으로 이 설명이 오래되면 skill 갱신 누락으로 본다.

## 기본 검증

- 실행 결과는 tableRef, valueRef, dateRef, executionRef 중 필요한 근거로 남긴다.
- 최종 판단의 숫자 claim은 해당 table/value ref에 직접 묶는다.
- 스킬과 실제 공개 API의 호출 방식, 대표 반환 형태, 오류/제한 동작이 다르면 같은 변경에서 스킬을 갱신한다.


