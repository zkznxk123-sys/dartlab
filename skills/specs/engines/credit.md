---
id: engines.credit
title: Credit (dCR)
kind: curated
scope: builtin
status: observed
category: engines
purpose: Credit (dCR) 엔진의 목적, 경계, 조합 기준을 Skill OS에서 확인하고 실행은 capability/docstring으로 내려간다.
whenToUse:
  - Credit (dCR)
  - credit
  - 1. 호출 — `dartlab.credit` · `c.credit` 두 진입점으로 쓴다
  - 2. 7 축 — 이 구조로 평가한다
  - 3. 결과 구조 — 종합·축별·detail 3 형태로 반환한다
  - 종합 등급 (axis 미지정)
  - 축 단일 (axis 지정)
inputs:
  - 작업 목적
  - 대상 엔진 또는 실행 환경
  - 검증 범위
outputs:
  - selected skill
  - capability/docstring handoff
  - verification gate
capabilityRefs:
  - credit
  - Company.credit
toolRefs:
  - search_reference
  - run_python
knowledgeRefs:
  - start.dartlabSkillOs
sourceRefs:
  - dartlab://skills/engines.credit
procedure:
  - 1. 호출 — `dartlab.credit` · `c.credit` 두 진입점으로 쓴다 기준을 확인한다.
  - 2. 7 축 — 이 구조로 평가한다 기준을 확인한다.
  - 3. 결과 구조 — 종합·축별·detail 3 형태로 반환한다 기준을 확인한다.
  - 종합 등급 (axis 미지정) 기준을 확인한다.
  - 축 단일 (axis 지정) 기준을 확인한다.
  - 7 축 `metrics` 에 시계열 (YoY · 5 년 평균) 부착.
  - '`narrative` 키 추가 — 한국어 인과 문장 (story 블록 재료).'
  - '`debtRatio` — 부채비율 (%)'
  - '`interestCoverage` — 이자보상배율 (배)'
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
  - Credit (dCR) 규칙 확인
  - credit 작업을 Skill OS에서 시작
source:
  type: absorbed_skill_os
  absorbedKey: credit
  format: markdown
lastUpdated: '2026-05-03'
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- API 세부 인자와 반환 구조는 capability/docstring을 확인한다.
- 분석이나 변경 결과는 ref, 실행 로그, 테스트 결과로 검증한다.

## 실행 순서

- 1. 호출 — `dartlab.credit` · `c.credit` 두 진입점으로 쓴다 기준을 확인한다.
- 2. 7 축 — 이 구조로 평가한다 기준을 확인한다.
- 3. 결과 구조 — 종합·축별·detail 3 형태로 반환한다 기준을 확인한다.
- 종합 등급 (axis 미지정) 기준을 확인한다.
- 축 단일 (axis 지정) 기준을 확인한다.
- 7 축 `metrics` 에 시계열 (YoY · 5 년 평균) 부착.
- `narrative` 키 추가 — 한국어 인과 문장 (story 블록 재료).
- `debtRatio` — 부채비율 (%)
- `interestCoverage` — 이자보상배율 (배)
