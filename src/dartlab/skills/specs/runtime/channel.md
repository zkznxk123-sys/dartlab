---
id: runtime.channel
title: Channel
kind: curated
scope: builtin
status: observed
category: runtime
purpose: Channel 실행 환경의 제약, 시작 절차, 검증 기준을 Skill OS에서 확인한다.
whenToUse:
  - Channel
  - channel
  - 1. 한 줄 사용 — `dartlab channel` 로 끝낸다
  - 2. 기술 스택 — Microsoft DevTunnels 하나로 간다
  - 폐기된 백엔드 (왜 안 썼는가)
  - 3. 자동화 파이프라인 — Phase A~G 로 돌린다
  - 4. 보안 모델 — anonymous reader 기본, URL 노출에 주의한다
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
  - dartlab://skills/runtime.channel
procedure:
  - 1. 한 줄 사용 — `dartlab channel` 로 끝낸다 기준을 확인한다.
  - 2. 기술 스택 — Microsoft DevTunnels 하나로 간다 기준을 확인한다.
  - 폐기된 백엔드 (왜 안 썼는가) 기준을 확인한다.
  - 3. 자동화 파이프라인 — Phase A~G 로 돌린다 기준을 확인한다.
  - 4. 보안 모델 — anonymous reader 기본, URL 노출에 주의한다 기준을 확인한다.
  - 데스크탑 Chrome 정상, 모바일 Chrome 에서 화면은 렌더되지만 상호작용 전체가 멎음 (버튼 무반응, 스피너 영원).
  - 서버 로그 상 모든 API 200 응답.
  - '같은 폰에서 다른 SPA (예: 정적 블로그) 는 정상 동작.'
  - 외부 패키지의 deprecated export 가 번들에 남아 런타임 `ReferenceError` 발생 → 모듈 평가 단계 throw → SPA 전체 hydration 실패.
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
  - Channel 규칙 확인
  - channel 작업을 Skill OS에서 시작
source:
  type: absorbed_skills
  absorbedKey: channel
  format: markdown
lastUpdated: '2026-05-03'
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- 공개 호출 방식과 대표 반환 형태는 skill에서 확인하고, 세부 필드는 capability/docstring으로 검산한다.
- 분석이나 변경 결과는 ref, 실행 로그, 테스트 결과로 검증한다.

## 실행 순서

- 1. 한 줄 사용 — `dartlab channel` 로 끝낸다 기준을 확인한다.
- 2. 기술 스택 — Microsoft DevTunnels 하나로 간다 기준을 확인한다.
- 폐기된 백엔드 (왜 안 썼는가) 기준을 확인한다.
- 3. 자동화 파이프라인 — Phase A~G 로 돌린다 기준을 확인한다.
- 4. 보안 모델 — anonymous reader 기본, URL 노출에 주의한다 기준을 확인한다.
- 데스크탑 Chrome 정상, 모바일 Chrome 에서 화면은 렌더되지만 상호작용 전체가 멎음 (버튼 무반응, 스피너 영원).
- 서버 로그 상 모든 API 200 응답.
- 같은 폰에서 다른 SPA (예: 정적 블로그) 는 정상 동작.
- 외부 패키지의 deprecated export 가 번들에 남아 런타임 `ReferenceError` 발생 → 모듈 평가 단계 throw → SPA 전체 hydration 실패.

