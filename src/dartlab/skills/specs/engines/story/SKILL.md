---
id: engines.story
title: Story
kind: curated
scope: builtin
status: observed
category: engines
purpose: Story 엔진의 목적, 경계, 조합 기준을 Skill OS에서 확인하고 실행은 capability/docstring으로 내려간다. 트리거 — '보고서', '기업 이야기', 'story', '6 막 인과'.
whenToUse:
  - Story
  - story
  - 1. 사상 — 보고서 빌더로 간다
  - 방향성 메모 — docstring SSOT 와의 교류 (2026-04-24)
  - 2. 2 축 체계 — reportType × template 로 간다
  - 1 축 — reportType (무엇을 집중적으로 볼 것인가)
  - 2 축 — template (이 기업은 어떤 유형인가, 자동 감지)
inputs:
  - 작업 목적
  - 대상 엔진 또는 실행 환경
  - 검증 범위
outputs:
  - selected skill
  - capability/docstring handoff
  - verification gate
capabilityRefs:
  - Story
  - Company.story
toolRefs:
  - search_reference
  - run_python
knowledgeRefs:
  - start.dartlabSkillOs
sourceRefs:
  - dartlab://skills/engines.story
procedure:
  - dartlab.Company(code) 또는 dartlab.story() 로 보고서 빌더 진입.
  - reportType (집중 시점) × template (기업 유형 자동 감지) 2 축 결정.
  - c.story() 또는 dartlab.story(reportType, ...) 호출.
  - 블록별 출력 (scorecard · creditScore · narrative · valuationBand) 검증.
  - capability docstring 의 Guide 섹션과 정합성 확인 후 답변에 묶음.
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
  - 삼성전자 종합 보고서 생성
  - 5 영역 scorecard A~F 평가
  - 20 등급 신용평가 함께 보기
  - reportType 자동 선택
  - 보고서 블록 템플릿 사용법
linkedSkills:
  - engines.company
  - engines.analysis
  - engines.credit
  - engines.macro
source:
  type: absorbed_skills
  absorbedKey: story
  format: markdown
lastUpdated: '2026-05-07'
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- 공개 호출 방식과 대표 반환 형태는 skill에서 확인하고, 세부 필드는 capability/docstring으로 검산한다.
- 분석이나 변경 결과는 ref, 실행 로그, 테스트 결과로 검증한다.

## 실행 순서

- 1. 사상 — 보고서 빌더로 간다 기준을 확인한다.
- 방향성 메모 — docstring SSOT 와의 교류 (2026-04-24) 기준을 확인한다.
- 2. 2 축 체계 — reportType × template 로 간다 기준을 확인한다.
- 1 축 — reportType (무엇을 집중적으로 볼 것인가) 기준을 확인한다.
- 2 축 — template (이 기업은 어떤 유형인가, 자동 감지) 기준을 확인한다.
- **docstring → story**: 엔진 docstring Guide 섹션이 audit 로 충분히 검증되면 story 블록 템플릿에 반영 (같은 해석 규칙 · 같은 임계값).
- **story → docstring**: 기존 story 블록 중 재현 가능 · 해석 규칙 명확한 것은 공개 함수로 추출해 엔진 docstring 에 Guide 로 명시. AI · story 공용 호출.
- `scorecard` — 5 영역 A~F 종합평가.
- `creditScore` — 20 등급 신용평가.

## 공개 호출 방식

- `c = dartlab.Company("005930")`
- `c.story()`
- `dartlab.story(c)`

## 호출 동작

- analysis, credit, macro, scan, quant 결과를 thesis/evidence/risk/limit 구조로 조립한다. 숫자 계산은 하위 엔진 결과 ref에 묶는다.
- 실행 전에 target, period/date, metric, source 또는 universe를 확인한다.
- 데이터가 없거나 runtime 제한이 있으면 값을 추정하지 않고 한계와 필요한 다음 수집 경로를 말한다.

## 대표 반환 형태

- report dict 또는 block list를 반환한다. 핵심 키는 thesis, evidenceBlocks, riskBlocks, limits, sourceRefs다.
- 전체 세부 필드는 공개 docstring/capability와 동기화한다. 코드/API 변경으로 이 설명이 오래되면 skill 갱신 누락으로 본다.

## 기본 검증

- 실행 결과는 tableRef, valueRef, dateRef, executionRef 중 필요한 근거로 남긴다.
- 최종 판단의 숫자 claim은 해당 table/value ref에 직접 묶는다.
- 스킬과 실제 공개 API의 호출 방식, 대표 반환 형태, 오류/제한 동작이 다르면 같은 변경에서 스킬을 갱신한다.


