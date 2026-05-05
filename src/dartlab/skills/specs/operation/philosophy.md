---
id: operation.philosophy
title: Philosophy — dartlab 사상 SSOT
kind: curated
scope: builtin
status: observed
category: operation
purpose: Philosophy — dartlab 사상 SSOT 운영 규칙을 Skill OS에서 확인하고 변경 전후 검증 게이트로 사용한다.
whenToUse:
  - Philosophy — dartlab 사상 SSOT
  - philosophy
  - §1. 사상 한 줄 — AI ↔ 사람 상호 의존, 엔진이 다리
  - §2. 존재 이유 — 비교 가능성 (시야 3 × 관점 6 격자)
  - 시야 3 축 (WHAT — 무엇을 얼마나 넓게 보나)
  - 관점 6 축 (HOW — 어떻게 다르게 보나)
  - 격자
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
  - dartlab://skills/operation.philosophy
procedure:
  - §1. 사상 한 줄 — AI ↔ 사람 상호 의존, 엔진이 다리 기준을 확인한다.
  - §2. 존재 이유 — 비교 가능성 (시야 3 × 관점 6 격자) 기준을 확인한다.
  - 시야 3 축 (WHAT — 무엇을 얼마나 넓게 보나) 기준을 확인한다.
  - 관점 6 축 (HOW — 어떻게 다르게 보나) 기준을 확인한다.
  - 격자 기준을 확인한다.
  - 사람은 엔진·블로그·지식으로 자산을 만든다.
  - 그 자산은 자동으로 AI 의 skill 이 된다 — 공개 함수 docstring 이 곧 AI tool schema 다.
  - AI 가 실행 중 발견한 개선 (반복 패턴·반례·새 조합) 은 엔진 docstring·블로그 frontmatter 로 사람 자산에 환류한다.
  - '**엔진이 다리다.** 한 파일이 사람의 분석엔진이자 AI 의 skill 본문.'
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
  - Philosophy — dartlab 사상 SSOT 규칙 확인
  - philosophy 작업을 Skill OS에서 시작
source:
  type: absorbed_skills
  absorbedKey: philosophy
  format: markdown
lastUpdated: '2026-05-03'
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- 공개 호출 방식과 대표 반환 형태는 skill에서 확인하고, 세부 필드는 capability/docstring으로 검산한다.
- 분석이나 변경 결과는 ref, 실행 로그, 테스트 결과로 검증한다.

## 실행 순서

- §1. 사상 한 줄 — AI ↔ 사람 상호 의존, 엔진이 다리 기준을 확인한다.
- §2. 존재 이유 — 비교 가능성 (시야 3 × 관점 6 격자) 기준을 확인한다.
- 시야 3 축 (WHAT — 무엇을 얼마나 넓게 보나) 기준을 확인한다.
- 관점 6 축 (HOW — 어떻게 다르게 보나) 기준을 확인한다.
- 격자 기준을 확인한다.
- 사람은 엔진·블로그·지식으로 자산을 만든다.
- 그 자산은 자동으로 AI 의 skill 이 된다 — 공개 함수 docstring 이 곧 AI tool schema 다.
- AI 가 실행 중 발견한 개선 (반복 패턴·반례·새 조합) 은 엔진 docstring·블로그 frontmatter 로 사람 자산에 환류한다.
- **엔진이 다리다.** 한 파일이 사람의 분석엔진이자 AI 의 skill 본문.

