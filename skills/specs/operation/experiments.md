---
id: operation.experiments
title: Experiments
kind: curated
scope: builtin
status: observed
category: operation
purpose: Experiments 운영 규칙을 Skill OS에서 확인하고 변경 전후 검증 게이트로 사용한다.
whenToUse:
  - Experiments
  - experiments
  - 1. 폴더 — `experiments/XXX_camelCaseName/` + `STATUS.md` 로 정리한다
  - 2. 파일 — `XXX_camelCaseFeature.py` 로 독립 실행 가능하게 쓴다
  - 3. 파일 생성 — 만들었으면 같은 턴에 실행하고 결과를 채운다
  - 4. Docstring — 이 구조로 채운다
  - 5. 흡수 — 사용자 승인 후에만 본체에 반영한다
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
  - dartlab://skills/operation.experiments
procedure:
  - 1. 폴더 — `experiments/XXX_camelCaseName/` + `STATUS.md` 로 정리한다 기준을 확인한다.
  - 2. 파일 — `XXX_camelCaseFeature.py` 로 독립 실행 가능하게 쓴다 기준을 확인한다.
  - 3. 파일 생성 — 만들었으면 같은 턴에 실행하고 결과를 채운다 기준을 확인한다.
  - 4. Docstring — 이 구조로 채운다 기준을 확인한다.
  - 5. 흡수 — 사용자 승인 후에만 본체에 반영한다 기준을 확인한다.
  - '`experiments/XXX_camelCaseName/` — 실험별 하위 폴더 분리.'
  - 각 폴더에 `STATUS.md` 로 현황 기록.
  - 실험 코드는 실험 폴더 안에서 관리한다.
  - 네이밍 — `XXX_camelCaseFeature.py` (001 부터).
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
  - Experiments 규칙 확인
  - experiments 작업을 Skill OS에서 시작
source:
  type: absorbed_skill_os
  absorbedKey: experiments
  format: markdown
lastUpdated: '2026-05-03'
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- 공개 호출 방식과 대표 반환 형태는 skill에서 확인하고, 세부 필드는 capability/docstring으로 검산한다.
- 분석이나 변경 결과는 ref, 실행 로그, 테스트 결과로 검증한다.

## 실행 순서

- 1. 폴더 — `experiments/XXX_camelCaseName/` + `STATUS.md` 로 정리한다 기준을 확인한다.
- 2. 파일 — `XXX_camelCaseFeature.py` 로 독립 실행 가능하게 쓴다 기준을 확인한다.
- 3. 파일 생성 — 만들었으면 같은 턴에 실행하고 결과를 채운다 기준을 확인한다.
- 4. Docstring — 이 구조로 채운다 기준을 확인한다.
- 5. 흡수 — 사용자 승인 후에만 본체에 반영한다 기준을 확인한다.
- `experiments/XXX_camelCaseName/` — 실험별 하위 폴더 분리.
- 각 폴더에 `STATUS.md` 로 현황 기록.
- 실험 코드는 실험 폴더 안에서 관리한다.
- 네이밍 — `XXX_camelCaseFeature.py` (001 부터).

