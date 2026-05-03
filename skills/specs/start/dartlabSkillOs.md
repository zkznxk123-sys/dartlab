---
id: start.dartlabSkillOs
title: DartLab Skill OS 최초 진입
kind: curated
scope: builtin
status: unverified
category: start
purpose: 사람과 LLM이 DartLab을 처음 볼 때 Skills 하나에서 분석, 엔진 능력, 운영 규칙, 확장 절차를 찾는 공식 시작점이다.
whenToUse:
  - DartLab을 처음 볼 때
  - 어떤 문서부터 봐야 하는지 모를 때
  - 외부 LLM이 DartLab 작업을 시작할 때
  - 문서, API 사용법, 분석 절차가 흩어져 보일 때
  - 전체 체계와 확장 규칙을 한 번에 확인할 때
inputs:
  - 사용자 목적
  - 작업 대상
  - 실행 환경
outputs:
  - selectedSkill
  - basic engine skill
  - operation skill
  - sourceRef
  - verification gate
toolRefs:
  - dartlab.skills.search
  - dartlab.skills.get
sourceRefs:
  - dartlab://skills/start.dartlabSkillOs
  - dartlab://skills/operation.opsAsSkills
  - dartlab://skills/operation.code
  - dartlab://skills/operation.apiContract
requiredEvidence:
  - skillRef
  - sourceRef
expectedOutputs:
  - 시작 skill
  - 필요한 원문 위치
  - 다음 실행 절차
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
  - 삭제된 운영 문서 경로를 직접 순회하다가 적용 규칙을 놓침
  - basic engine skill과 operation skill을 구분하지 못함
  - sourceRef 없이 규칙을 요약함
  - API 세부 schema를 SkillSpec에 복사함
forbidden:
  - Skills 검색 없이 임의 문서를 시작점으로 삼지 않는다.
  - 운영 규칙과 엔진 API schema를 같은 skill에 중복하지 않는다.
  - sourceRef 없는 규칙 설명을 공식 절차로 취급하지 않는다.
examples:
  - 처음 온 LLM은 무엇부터 봐야 하나?
  - DartLab 문서와 운영 규칙을 Skills에서 찾는 순서
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-03"
---

## 절차

- 먼저 `start.dartlabSkillOs`를 읽고 현재 작업이 분석, 엔진 능력 확인, 운영 규칙 확인, 확장 중 어디에 속하는지 분류한다.
- 분석 목적이면 `finance`, `screens`, `visuals` curated skill을 먼저 검색한다.
- 엔진이 무엇을 할 수 있는지 확인하려면 `basic.*` generated skill을 읽고, 상세 API는 capability/docstring으로 내려간다.
- 테스트, 릴리즈, 문서, 아키텍처, UI, 데이터, MCP 같은 운영 규칙은 `operation.*` 또는 `runtime.*` skill에서 찾는다.
- 각 skill의 `sourceRefs`는 삭제된 문서 경로가 아니라 `dartlab://skills/{skillId}` 리소스를 가리킨다.
- 새 절차가 반복되면 user skill로 시작하고, audit과 사용자 확인을 거쳐 curated 또는 엔진 docstring으로 승격한다.
