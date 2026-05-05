---
id: operation.extendSkills
title: Skill 확장과 공식 승격 규칙
kind: curated
scope: builtin
status: unverified
category: operation
purpose: 새 분석법, 운영 규칙, 외부 LLM 사용법을 Skills 체계에 추가하고 official 수준으로 승격하는 기준을 정한다.
whenToUse:
  - 새 skill을 추가할 때
  - 운영 규칙을 operation skill로 흡수할 때
  - user skill을 curated skill로 승격할 때
  - 반복 audit 결과를 docstring 또는 SkillSpec에 반영할 때
inputs:
  - 새 절차
  - sourceRef
  - audit result
  - 사용자 확인
outputs:
  - user skill
  - curated skill
  - docstring improvement
  - official promotion decision
sourceRefs:
  - dartlab://skills/operation.opsAsSkills
  - dartlab://skills/operation.code
  - dartlab://skills/operation.coreloop
requiredEvidence:
  - sourceRef
  - auditResult
  - userConfirmed
expectedOutputs:
  - 확장 위치 결정
  - 승격 가능 여부
  - 검증 체크리스트
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
failureModes:
  - 한 번 쓴 질문별 runner를 skill로 고정
  - 검증 없이 official 상태 부여
  - docstring에 있어야 할 API 능력을 SkillSpec에 중복
  - sourceRef 없는 운영 규칙 추가
forbidden:
  - final answer template 저장
  - API schema 복사
  - 사용자 확인 없는 official 승격
examples:
  - 새 운영 규칙을 operation skill로 추가하기
  - 반복 분석 절차를 curated skill로 승격하기
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-03"
---

## 절차

- 새 내용이 엔진 API 능력이면 docstring/capability로 보강한다.
- 새 내용이 여러 엔진을 조합하는 분석 절차면 curated skill 후보로 둔다.
- 새 내용이 테스트, 릴리즈, 문서, UI, 데이터 같은 운영 규칙이면 operation skill로 둔다.
- 프로젝트별 실험은 `.dartlab/skills/**/*.md` user skill로 시작한다.
- official 승격은 구조 lint, 서버 audit P, 사용자 확인이 모두 있을 때만 허용한다.
- 승격 후에도 SkillSpec은 schema를 복사하지 않고 capabilityRefs와 sourceRefs로 원천을 연결한다.

