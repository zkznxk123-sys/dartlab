---
id: operation.opsAsSkills
title: 운영 문서를 Skills 체계로 흡수
kind: curated
scope: builtin
status: unverified
category: operation
purpose: 과거 운영 문서를 별도 탐색 체계가 아니라 engine, runtime, operation skill로 흡수해 사람과 LLM이 같은 skill resolver에서 운영 규칙을 찾게 하는 전환 규칙이다.
whenToUse:
  - 운영 문서를 스킬 체계로 옮길 때
  - 문서 체계를 단순화할 때
  - 운영 규칙을 외부 LLM도 확인 가능하게 만들 때
  - sourceRefs 기반으로 원문 위치를 보존할 때
inputs:
  - ops 문서
  - 작업 목적
  - 적용할 규칙
outputs:
  - operation skill
  - sourceRef
  - verification gate
sourceRefs:
  - dartlab://skills/start.dartlabSkillOs
  - dartlab://skills/operation.opsAsSkills
requiredEvidence:
  - sourceRef
expectedOutputs:
  - operation category skill
  - 원문 위치가 보존된 규칙
  - 중복 없는 Skills 진입점
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
  - 운영 내용을 SkillSpec에 통째로 복사해 읽기 어려운 문서로 만듦
  - 삭제된 운영 문서 경로와 Skills가 서로 다른 규칙을 말함
  - operation skill에 sourceRefs가 없음
  - 긴 설계 원문을 사람이 읽는 첫 화면에 그대로 노출함
forbidden:
  - 운영 규칙의 SSOT를 삭제된 문서 경로와 SkillSpec 양쪽에 서로 다르게 둔다.
  - API parameters, returns, schema를 operation skill에 복사한다.
  - generated operation skill을 수동으로 직접 수정한다.
examples:
  - 테스트 규칙을 Skills에서 찾기
  - 아키텍처 규칙을 operation skill로 검색하기
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-03"
---

## 절차

- 과거 운영 문서 주제는 `engines.*`, `runtime.*`, `operation.*` curated skill로 흡수한다.
- `/skills`와 `dartlab.skills.search()`를 공식 최초 탐색 표면으로 둔다.
- skill은 원문 전체를 복사하지 않고 제목, 목적, 주요 절차, 검증 게이트, capability handoff를 제공한다.
- 사람이 읽는 첫 화면은 절차와 실행 환경을 보여주고, 세부 API는 capability/docstring으로 내려간다.
- 새 운영 규칙은 먼저 operation skill로 검색 가능해야 하며, 원문 위치가 필요하면 sourceRef를 반드시 둔다.
- 이 전환이 완료되면 삭제된 운영 문서 경로를 공식 진입점으로 안내하지 않는다.
