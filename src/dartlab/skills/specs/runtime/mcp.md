---
id: runtime.mcp
title: MCP
kind: curated
scope: builtin
status: observed
category: runtime
purpose: MCP 실행 환경의 제약, 시작 절차, 검증 기준을 Skill OS에서 확인한다.
whenToUse:
  - MCP
  - mcp
  - 1. 한눈에 보기
  - 2. 설치 — `.mcp.json` 에 dartlab 서버를 등록한다
  - 자동 설치 (프로젝트 루트에서)
  - 수동 설정 (`.mcp.json`)
  - 3. 실행 경로
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
  - dartlab://skills/runtime.mcp
procedure:
  - 1. 한눈에 보기 기준을 확인한다.
  - 2. 설치 — `.mcp.json` 에 dartlab 서버를 등록한다 기준을 확인한다.
  - 자동 설치 (프로젝트 루트에서) 기준을 확인한다.
  - 수동 설정 (`.mcp.json`) 기준을 확인한다.
  - 3. 실행 경로 기준을 확인한다.
  - 상한 5 인스턴스 · TTL 10 분 (`_CACHE_MAX` · `_CACHE_TTL`).
  - LRU 정책. 새 종목 로드 시 가장 오래된 항목 제거.
  - Company 로딩 자체가 수초 걸리므로 같은 종목 반복 질의에 유효.
  - '`ask` · `Company` · `setup` · `collect` · `config` 등 비분석 API.'
requiredEvidence:
  - skillRef
  - executionRef
  - sourceRef
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
  - MCP 규칙 확인
  - mcp 작업을 Skill OS에서 시작
source:
  type: absorbed_skills
  absorbedKey: mcp
  format: markdown
lastUpdated: '2026-05-03'
testUniverse:
  market: KR
  stockCodes:
    - "005930"
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- 공개 호출 방식과 대표 반환 형태는 skill에서 확인하고, 세부 필드는 capability/docstring으로 검산한다.
- 분석이나 변경 결과는 ref, 실행 로그, 테스트 결과로 검증한다.

## 실행 순서

- 1. 한눈에 보기 기준을 확인한다.
- 2. 설치 — `.mcp.json` 에 dartlab 서버를 등록한다 기준을 확인한다.
- 자동 설치 (프로젝트 루트에서) 기준을 확인한다.
- 수동 설정 (`.mcp.json`) 기준을 확인한다.
- 3. 실행 경로 기준을 확인한다.
- 상한 5 인스턴스 · TTL 10 분 (`_CACHE_MAX` · `_CACHE_TTL`).
- LRU 정책. 새 종목 로드 시 가장 오래된 항목 제거.
- Company 로딩 자체가 수초 걸리므로 같은 종목 반복 질의에 유효.
- `ask` · `Company` · `setup` · `collect` · `config` 등 비분석 API.

## 엔진 흡수 contract — MCP 표면이 dartlab 엔진을 어떻게 따라가는가

dartlab 엔진/Skill OS 가 진화해도 MCP 표면이 자동으로 따라가도록 설계된 자동 채널과,
사람이 손대야 하는 수동 touchpoint, 그리고 회귀 가드의 위치를 한곳에 정리한다.

### 자동 채널 — 엔진 변경하면 MCP 코드 손대지 않아도 자동 반영

| 채널 | 어떻게 자동인가 |
|---|---|
| `RunPython` | 모든 새 dartlab 공개 API 즉시 호출 가능. 새 엔진/메서드 추가 시 별도 도구 정의 불필요. 가장 보편적 흡수 채널 |
| `ReadCapability` | `reference/capability/_generated.py` 의 capability catalog(docstring 에서 생성) 색인 |
| `ReadSkill` | `skills/specs/**` 의 모든 skill markdown 자동 색인 (process-lifetime 캐시) |
| `prompts/list` & `prompts/get` | Skill OS 의 `kind: recipe` 카테고리를 prompt 로 자동 노출. arguments 는 skill `inputs` frontmatter 에서 derive |
| `dartlab://skills/{id}` resources | Skill OS 에서 런타임 derive |

### 수동 touchpoint — 엔진 surface 변경 시 사람이 손대야 함

| 위치 | 언제 |
|---|---|
| `ai/tools/registry._SPECS` | canonical tool 추가/제거 (현재 15: 메타 3 · 데이터 3 · 외부 2 · 출력 2 · 분석 추론 3 · elicit 1 · elevate 1) |
| `ai/tools/types.ToolSpec` 의 4 hint | 새 도구의 readOnly/destructive/idempotent/openWorld 분류 |
| `mcp/__init__._MCP_WORKSPACE_AGENT_TOOL_NAMES` | MCP 외부 노출 도구 (canonical 의 부분집합) — 현재 11 (canonical 10 + ask) |
| `ai/tools/registry._LEGACY_NAME_MAP` | snake_case alias 추가/제거 |
| `dartlab/__init__._LAZY_ATTRS` (PEP 562) | 새 top-level `dartlab.X` 모듈 추가 시 등록 |
| `ai/tools/runPython_guard._BLOCKED_ATTR_CALLS` | RunPython 의 차단 호출 목록 — 새 dangerous attr 추가 시 |

### Silent drift — 조용히 깨질 수 있는 채널 (가드 1 종)

- **새 Skill OS 카테고리** — `prompts/list` 는 `kind == "recipe"` 로 hardcode 필터. `playbook/`, `scenario/` 같은 새 카테고리 도입 시 prompts 에서 누락되며 외부 LLM 이 알아챌 수 없음.
  - **가드**: `tests/test_mcp.py::test_recipe_skills_all_exposed_as_prompts` invariant. recipe 파일 set ↔ `_recipeSkillsForPrompts()` 반환 set 일치 검증. 이 테스트가 fail 하면 `_recipeSkillsForPrompts()` 의 필터를 새 카테고리 포함하도록 갱신.

### 큰 변화 시 점검 (체크리스트)

엔진 surface 가 큰 폭으로 바뀔 때 (새 엔진 추가 / 기존 엔진 폐기 / 새 Skill OS 카테고리 도입 / `_generated.py` schema 개편) 다음을 확인한다.

1. `bash tests/test-lock.sh tests/test_mcp.py tests/test_mcp_strong.py -v` — 흡수 표면 회귀.
2. 새 카테고리가 들어왔다면 `_recipeSkillsForPrompts()` 의 `kind` 필터 확장 여부 결정.
3. 새 top-level 모듈이라면 `dartlab/__init__._LAZY_ATTRS` 등록 + RunPython 안에서 import 가능한지 확인.
4. capability 추가/변경 시 `src/dartlab/reference/capability/generateSpec.py` 재실행 후 `_generated.py`(+`_generated_analysis_graph.py`) 커밋. 재생성을 잊어도 CI `capability-catalog-sync` 게이트(`generateSpec.py --check`, 재생성-비교)가 소스↔카탈로그 drift 로 fail 시켜 차단한다.
5. canonical tool 추가/제거 시 `ToolSpec` 의 4 hint 채움 + `tests/test_mcp.py::test_mcp_advertised_tools_carry_annotations` 갱신.
6. **도그푸드 verification** — `uv run python -X utf8 tests/ai/runners/mcp_dogfood_probe.py` 실행. 11 항목 OK 출력 확인. 단위 테스트가 dispatch / 거부 경로 위주라 실 호출 happy path 회귀를 못 잡는 발견 (2026-05-09 LookAheadGuard `Company(market=...)` 회귀) — 큰 변화 후엔 도그푸드 필수.

