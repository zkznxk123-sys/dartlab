---
id: engines.scan
title: Scan
kind: curated
scope: builtin
status: observed
category: engines
purpose: Scan 엔진의 목적, 경계, 조합 기준을 Skill OS에서 확인하고 실행은 capability/docstring으로 내려간다.
whenToUse:
  - Scan
  - scan
  - 1. 사상 — `account` · `ratio` 가 primitive, 복합 축은 preset
  - 데이터 경로 — prebuild 우선, fallback per-file
  - 2. 광역 발굴 SSOT — docstring 이 원천
  - 3. 필드 탐색형 스크리닝 — fields → screen spec → 심층 검증
  - 5. 호출 계약
inputs:
  - 작업 목적
  - 대상 엔진 또는 실행 환경
  - 검증 범위
outputs:
  - selected skill
  - capability/docstring handoff
  - verification gate
capabilityRefs:
  - scan
toolRefs:
  - search_reference
  - run_python
knowledgeRefs:
  - start.dartlabSkillOs
sourceRefs:
  - dartlab://skills/engines.scan
procedure:
  - 1. 사상 — `account` · `ratio` 가 primitive, 복합 축은 preset 기준을 확인한다.
  - 데이터 경로 — prebuild 우선, fallback per-file 기준을 확인한다.
  - 2. 광역 발굴 SSOT — docstring 이 원천 기준을 확인한다.
  - 3. 필드 탐색형 스크리닝 — fields → screen spec → 심층 검증 기준을 확인한다.
  - 5. 호출 계약 기준을 확인한다.
  - '**[`scanRatio` docstring Guide](../src/dartlab/providers/dart/finance/scanAccount.py)** — 7 관점 스크리닝 레시피 (가치 · 성장 · 퀄리티 · 모멘텀 · 배당 · 턴어라운드 · 안정), 질문→primitive 매핑, 5 단계 발굴 워크플로, "투자할만한 회사" 기본 레시피 예제.'
  - '**[`scanAccount` docstring Guide](../src/dartlab/providers/dart/finance/scanAccount.py)** — 계정 원자의 4 사용 패턴과 scanRatio 와의 join 예시.'
  - '`dartlab.scan()` 하나로 모든 축에 접근.'
  - '`c.governance()` 등은 scan 내부 view — 별도 전역 함수가 아니다.'
requiredEvidence:
  - skillRef
  - universe
  - datasetAsOf
  - filter
  - formula
  - table
  - executionRef
expectedOutputs:
  - 작업 경로
  - 확인한 근거
  - 검증 결과
  - 입력/유니버스
  - 필터
  - 계산식/지표
  - 후보 evidence table
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
  - 후보·상위·랭킹 결과를 table 없이 회사명과 퍼센트 bullet로만 나열함
forbidden:
  - 삭제된 운영 문서 경로를 공식 진입점으로 안내하지 않는다.
  - API parameters/returns를 SkillSpec에 복사하지 않는다.
  - universe, 필터, 계산식, 기준일, table ref 없이 후보 발굴을 완료했다고 말하지 않는다.
examples:
  - Scan 규칙 확인
  - scan 작업을 Skill OS에서 시작
source:
  type: absorbed_skill_os
  absorbedKey: scan
  format: markdown
lastUpdated: '2026-05-03'
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- API 세부 인자와 반환 구조는 capability/docstring을 확인한다.
- 분석이나 변경 결과는 ref, 실행 로그, 테스트 결과로 검증한다.

## 실행 순서

- 1. 사상 — `account` · `ratio` 가 primitive, 복합 축은 preset 기준을 확인한다.
- 데이터 경로 — prebuild 우선, fallback per-file 기준을 확인한다.
- 2. 광역 발굴 SSOT — docstring 이 원천 기준을 확인한다.
- 3. 필드 탐색형 스크리닝 — fields → screen spec → 심층 검증 기준을 확인한다.
- 5. 호출 계약 기준을 확인한다.
- **[`scanRatio` docstring Guide](../src/dartlab/providers/dart/finance/scanAccount.py)** — 7 관점 스크리닝 레시피 (가치 · 성장 · 퀄리티 · 모멘텀 · 배당 · 턴어라운드 · 안정), 질문→primitive 매핑, 5 단계 발굴 워크플로, "투자할만한 회사" 기본 레시피 예제.
- **[`scanAccount` docstring Guide](../src/dartlab/providers/dart/finance/scanAccount.py)** — 계정 원자의 4 사용 패턴과 scanRatio 와의 join 예시.
- `dartlab.scan()` 하나로 모든 축에 접근.
- `c.governance()` 등은 scan 내부 view — 별도 전역 함수가 아니다.
- 후보·상위·랭킹 답변은 `입력/유니버스`, `필터`, `계산식/지표`, `결과`를 먼저 밝히고, 회사/식별자, 기준 기간, 원값, metric, rank가 들어간 markdown evidence table을 포함한다.
