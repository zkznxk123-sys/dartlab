---
id: operation.opsAsSkills
title: 운영 문서를 Skills 체계로 흡수
kind: curated
scope: builtin
status: unverified
category: operation
purpose: skills를 공개 문서이자 사람과 AI가 직접 실행하는 skill resolver로 유지하고, 엔진 기능·운영 방식 변경을 관련 skill에 동기화하는 운영 규칙이다.
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
  - 기능 개선이나 반환 형태 변경 후 관련 skill을 갱신하지 않음
  - 긴 설계 원문을 사람이 읽는 첫 화면에 그대로 노출함
forbidden:
  - 운영 규칙의 SSOT를 삭제된 문서 경로와 SkillSpec 양쪽에 서로 다르게 둔다.
  - 공개 API의 호출 방식, 대표 반환 형태, 오류/제한 동작과 skill 설명의 불일치를 방치한다.
  - capability/docstring에서 skill을 자동 생성해 엔진 기본 skill을 대체한다.
examples:
  - 테스트 규칙을 Skills에서 찾기
  - 아키텍처 규칙을 operation skill로 검색하기
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-17"
---

## 절차

- 과거 운영 문서 주제는 `engines.*`, `runtime.*`, `operation.*` skill로 흡수한다.
- `/skills`와 `dartlab.skills.search()`를 공식 최초 탐색 표면으로 둔다.
- 엔진 skill은 공개 호출 방식, 호출 동작, 대표 반환 형태, 실행 순서, 검증 게이트를 포함한다.
- 엔진 skill은 tool card 다. 엔진이 무엇을 분석할 수 있는지, 어떤 공개 호출을 쓰는지, 어떤 evidence 를 반환하는지까지만 책임진다. 축별 상세 schema 는 capability/docstring 으로 연결하고, 여러 엔진·반증·시각화·후속 모니터링을 묶는 실제 분석 절차는 recipe skill 로 둔다.
- recipe skill은 EngineCall 우선이다. 엔진에 이미 있는 기능을 RunPython 코드로 다시 구현하지 않고, RunPython 은 engine surface 가 아직 없거나 L1/L1.5 helper 결합이 필요한 fallback 경로로만 둔다.
- recipe 의 visualRefs 는 observed 상태의 `engines.viz.*` 만 공식 연결한다. unverified 시각화는 후속 후보로만 남기며, 근거 표 없이 장식 chart 를 만들지 않는다.
- capability/docstring은 세부 필드와 코드 원천 자료이며, skill은 사람이 그대로 실행할 수 있는 공개 사용 문서다.
- 기능 개선, API 변경, 반환 형태 변경, 운영 방식 개선이 있으면 관련 skill을 같은 변경에서 갱신한다.
- 새 운영 규칙은 먼저 operation skill로 검색 가능해야 하며, 원문 위치가 필요하면 sourceRef를 반드시 둔다.
- 이 전환이 완료되면 삭제된 운영 문서 경로를 공식 진입점으로 안내하지 않는다.

