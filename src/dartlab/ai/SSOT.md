# dartlab.ai SSOT

> **상태**: P1 lock 완료 (2026-05-05). mock provider e2e 통과 (`tests/ai/test_workbench_loop.py`). 이후 변경은 SSOT 갱신 PR 의무.

`src/dartlab/ai/` 의 정점 단일 진실 출처. 코드와 충돌 시 lock 후에는 SSOT 가 정답.

---

## 7 원칙

### 1. 3 층 능력 모델 — 모두 dartlab 전역 자산, AI 는 소비자

| 층 | 위치 | 표현 | 누가 쓰나 |
|---|---|---|---|
| **L1 Capability** | `src/dartlab/<engine>/` | Python 함수·클래스 + docstring | 사람·AI·MCP·UI |
| **L2 Skill** | `src/dartlab/skills/specs/<engine>/<id>.md` | markdown spec + frontmatter | 사람·AI·MCP·UI·audit |
| **L3 Tool** | `src/dartlab/ai/tools/` | 6 종 화이트리스트 (LLM 이 손에 쥠) | AI 전용 |

- L1·L2 는 본 SSOT 의 범위 밖. 본 SSOT 는 L3 와 작업대 (workbench) 만 정의한다.
- L2 는 AI 안에 두지 않는다. `dartlab.skills.*` 가 단일 SSOT 인프라 (SkillSpec / searchSkills / compiler / status 사다리). AI 는 read-only 소비자 + HARVEST 의 신규 spec 작성자.

### 2. 작업대 5 패스

```
BRIEF → WORK → CRITIQUE → COMPOSE → GATE → HARVEST
```

각 패스는 LLM 호출 가능한 별도 단계. system prompt 는 패스별 분리 (`workbench/prompts.py`). 같은 분석가 정체성 (외부 목소리) + 다른 인지 단계 (내부 작업).

- **BRIEF**: 질문 해석, `read_skill`/`read_capability`/`recall(memory)` 로 작업 계획 수립
- **WORK**: `run_python`/`web_search`/`save_artifact` 반복 실행
- **CRITIQUE**: 반대가설 강제, 누락 lens 점검 → 필요 시 WORK 회귀
- **COMPOSE**: 답안 + ref 묶음
- **GATE**: ref 검증 — 미달 시 차단/회귀
- **HARVEST**: trace 보고 `propose_skill` 후보 결정

### 3. 도구 6 종 고정

| API name (snake) | Python identifier (camel) | 책임 |
|---|---|---|
| `run_python` | `runPython` | dartlab 라이브러리 + Polars 임의 코드 실행, ref 발급 |
| `read_skill` | `readSkill` | `dartlab.skills.searchSkills` 호출, frontmatter + 본문 반환 |
| `read_capability` | `readCapability` | `dartlab.core.capability.search` 호출, docstring 반환 |
| `web_search` | `webSearch` | 외부 최신 정보, webRef |
| `save_artifact` | `saveArtifact` | 산출물 저장, artifactRef |
| `propose_skill` | `proposeSkill` | `skills/specs/<engine>/<id>.md` 신규 작성 (kind: generated, status: unverified) |

- 추가는 SSOT 갱신 PR 의무. registry 는 6 종 화이트리스트 강제 — 외 등록 거부 (`registerTool` 은 plugin 도구만 허용, `CANONICAL_TOOL_NAMES` 보호).
- **이름 컨벤션**: API name (registry key, MCP tool name, LLM 에 보이는 이름) = snake_case. Python 식별자·파일명 = camelCase. `toolSpecs(provider)` 가 변환.

### 4. Provider 카탈로그 — `provider_catalog.py` 단일 출처

```python
class WorkbenchProvider(Protocol):
    config: ProviderConfig
    def generate(self, messages: list[dict], tools: list[dict]) -> ProviderTurn: ...
```

dartlab 정식 provider 9 종 (`provider_catalog.py`):
- **oauth-codex** — ChatGPT OAuth (1 순위, API 키 불필요)
- **openai** — OpenAI API key
- **gemini** — Google Gemini API key
- **groq / cerebras / mistral** — 각자 API key (OpenAI 호환)
- **custom** — OpenAI 호환 임의 엔드포인트
- **ollama** — 로컬 (무인증)
- **codex** — Codex CLI (코딩 전용)

**Anthropic 직접 호출 금지** — ToS 위반 우려로 과거 `claude_code.py` 가 [9eb9d088e](commit) 에서 제거됨. 새 anthropic provider 추가 안 함.

`OpenAICompatibleProvider` 가 openai/oauth-codex/groq/cerebras/mistral/custom/ollama 모두 처리. `OAuthCodexProvider` 는 ChatGPT OAuth backend 의 SSE 응답을 별도 처리. tool schema 는 `_responses_tools` (Responses API) / OpenAI chat-completions `tools` 형식 사용.

**이벤트 타입**: `provider.generate()` 는 동기 호출이고 결과는 `ProviderTurn(content, tool_calls, raw)`. `workbench/runner.py` 가 그것을 `TraceEvent` (kind ∈ `{"llm_text", "llm_tool_use", "tool_result", "pass_enter", "pass_exit", "llm_stop", "llm_error"}`) 로 정규화.

### 5. 모든 답은 ref 에 닿는다

`Ref` (contracts.py:15) 의 `kind ∈ {dataRef, executionRef, valueRef, dateRef, visualRef, webRef, artifactRef, docRef}`. GATE 가 ref 없는 숫자·날짜·랭킹 답을 차단.

### 6. 자기진화 선순환

```
세션 trace
   ↓
HARVEST: 새 조합 / 반복 패턴 / 사용자 피드백 시그널 수집
   ↓
propose_skill(id, title, whenToUse, capabilityRefs, requiredEvidence, body)
   ↓
src/dartlab/skills/specs/<engine>/<id>.md 신규 작성 (kind: generated, status: unverified)
   ↓
memory/stats.py 가 usageCount, successRate, avgValueRefs 집계
   ↓
임계값 통과 → unverified→observed (운영자 confirm 필수)
   ↓ (audit 도구 통과)
observed → auditP (자동) → official (audit + 운영자 sign-off)
   ↓
official 안정 skill 의 패턴이 dartlab core capability 승격 후보 (별도 PR 큐)
```

- **`unverified → observed` 까지 운영자 confirm 필수**. 통계 게이밍·잘못된 학습 격리. CLI: `scripts/dartlab-skills review`.
- 기존 `dartlab.skills.compiler/registry/search/models` 인프라 재사용. 신규 인프라 안 만든다.
- `dartlab.skills.registry._validate_status_evidence` (registry.py:515) 는 자동 승격 게이트로 재사용.

### 7. SSOT 우선

- 코드와 SSOT 충돌 시 (lock 이후) SSOT 가 정답. 코드를 SSOT 에 맞춘다.
- 새 기능은 SSOT 갱신이 선행.
- **단, SSOT 자체 작성 순서**: P0 초안 → P1 minimal slice 동작 확인 → lock 커밋. 코드 안 보고 추상만 적힌 SSOT 를 정점으로 잠그지 않는다.

---

## 폴더 규칙

```
src/dartlab/ai/
├── SSOT.md                    ← 본 문서
├── __init__.py                ← ask() re-export only
├── kernel.py                  ← ask() 진입
├── contracts.py               ← Ref, TraceEvent, ToolResult, Msg
├── trace.py
├── providers/                 ← 정식 — provider_catalog.py 카탈로그 9 종
│   ├── __init__.py            ← ProviderConfig, ProviderTurn, ToolCall, WorkbenchProvider, OpenAICompatibleProvider, UnavailableProvider, create_provider, get_config, available_providers
│   ├── oauth_codex.py         ← OAuthCodexProvider (ChatGPT OAuth, 1 순위)
│   ├── codex.py               ← CodexProvider stub (CLI 후속)
│   └── support/
│       ├── __init__.py
│       └── oauth_token.py     ← PKCE/refresh/revoke
├── tools/                     ← P1 — 6 종만
│   ├── registry.py            ← toolSpecs(provider), 6 종 화이트리스트
│   └── runPython.py / readSkill.py / readCapability.py / webSearch.py / saveArtifact.py / proposeSkill.py
├── workbench/                 ← P1 — 5 패스
│   ├── loop.py                ← orchestration
│   ├── state.py / scratchpad.py / prompts.py
│   └── brief.py / work.py / critique.py / compose.py / gate.py / harvest.py
├── memory/                    ← P3·P5
│   └── decisions.py / stats.py
├── lenses/                    ← P5 (옵션)
│   └── fundamental.py / macro.py / technical.py / sentiment.py
└── settings/                  ← 기존 유지
```

### 경계 강제 (테스트로 잠금)

- `ai/workbench/`, `ai/tools/`, `ai/providers/`, `ai/lenses/` 는 `dartlab.{analysis,company,scan,quant,gather,macro,industry,review,credit,viz,...}` 등 core engine 을 **정적 import 하지 않는다**. (현재 코드도 위반 0 — 본 규칙은 신규 강제가 아닌 회귀 가드.)
- `ai/tools/{readSkill,readCapability,proposeSkill}.py` 만 `dartlab.skills.*` (메타) 와 `dartlab.core.capability.*` 의 docstring 을 read-only 로 접근. 데이터 호출은 안 한다.
- `ai/` 코드는 `src/dartlab/skills/` 의 컨텐츠 SSOT 를 변경하지 않는다 (HARVEST 의 신규 spec 작성 제외). 기존 `kind: curated` spec 수정·이동 금지.

### 코드 컨벤션

- 한 폴더 한 책임. 파일 하나 = 함수/클래스 그룹 하나.
- Python 식별자·파일명 = camelCase. 외부 노출 API name = snake_case. CLAUDE.md camelCase 규칙은 식별자 한정.
- UTF-8, 코드 주석 최소.

---

## MCP 표면 매핑

현재 노출: `mcp__dartlab__{ask, engine_call, skill_search, generated_spec_search, run_python, read}` (+ 보조).

P1 완료 시:

| 현재 | 새 매핑 |
|---|---|
| `ask` | 유지 (kernel.ask 진입) |
| `engine_call` | `run_python` 으로 deprecate-rename. run_python 안에서 임의 dartlab 호출 |
| `skill_search` | `read_skill` rename |
| `generated_spec_search` | `read_capability` rename |
| `read` | `read_skill` 으로 통합 (skillId 기반 절차 읽기) |
| (없음) | `web_search`, `save_artifact`, `propose_skill` 신규 노출 |

MCP 서버 instructions 도 동시 갱신.

---

## 정체성 — 외부 단일 / 내부 분업

- **외부 (사용자가 듣는 목소리)**: 단일 분석가 ("DartLab 분석가").
- **내부 (인지 작업)**: 분업 가능. 단일이 default. 질문 난이도가 임계 넘으면 lens 패널 자동 활성 (P5 — fundamental / macro / technical / sentiment).

---

## 회귀 가드 (테스트로 강제)

- `tests/ai/test_no_core_import.py` — 정적 import 금지 (`ai/workbench/`, `ai/providers/`, `ai/lenses/` 가 `dartlab.<engine>` 정적 import 시 실패)
- `tests/ai/test_tool_whitelist.py` — registry 가 6 종 외 등록 거부
- `tests/ai/test_ref_gate.py` — 숫자·날짜·랭킹 답 ref 없으면 GATE 차단
- `tests/ai/test_skill_spec_integrity.py` — HARVEST 가 작성한 spec 의 frontmatter schema (`SkillSpec` dataclass) 통과
- `tests/ai/test_no_external_skill_writes.py` — `ai/` 코드가 기존 `kind: curated` spec 을 수정하지 않음 (생성만 허용)
- `tests/ai/test_providers.py` — 5 어댑터 schema 변환 단위 테스트
- `tests/ai/golden/baseline.json` + `test_golden_baseline.py` — 휴리스틱 시대 골든 셋, P1 회귀 비교용 (P1 갈아끼운 뒤 폐기 가능)

---

## SSOT 갱신 PR 룰 (P6)

본 SSOT 가 lock 된 이후 다음 변경은 SSOT 갱신 PR 의무:

1. 신규 도구 추가/제거 — `CANONICAL_V2` 6 종 화이트리스트 변경.
2. 신규 패스 추가/순서 변경 — `BRIEF→WORK→CRITIQUE→COMPOSE→GATE→HARVEST` 외.
3. 신규 provider 어댑터 추가 — `PROVIDER_CLASSES` 변경.
4. ref kind 추가 — `Ref.kind` 값 집합 변경 (`valueRef`, `tableRef`, ...).
5. status 사다리 임계값 변경 — `memory/promotion.py` 의 `_OBSERVED_MIN_*` / `_AUDITP_MIN_*`.
6. 폴더 경계 변경 — `ai/{workbench,tools,providers,lenses,memory}` import 정책.

PR 체크리스트:
- [ ] SSOT.md 해당 섹션 갱신
- [ ] 회귀 가드 테스트 추가 또는 갱신 (`tests/ai/test_*.py`)
- [ ] 변경 이력 (본 §) 1 줄 추가
- [ ] 코드 ↔ SSOT 정합성 lint (별도 도구 P6.1)

## 변경 이력

- 2026-05-05: P0 초안 작성.
- 2026-05-05: P1 lock — 5 패스 모듈 + 5 어댑터 + dual-surface providers + V2 6 종 도구 + 회귀 가드 5 종. mock provider e2e 통과.
- 2026-05-05: P2~P5 backbone — readSkill 통합 / HARVEST + propose_skill 자기진화 / status 승격 시그널 + 운영자 confirm 게이트 / memory recall + lens 4 종.
- 2026-05-05: P6 부분 — SSOT PR 룰 + tool 실행 timing telemetry. 실 LLM e2e 회귀 셋은 API 키·비용 분리 (별도 트리거).
- 2026-05-06: provider 시스템 정정 — anthropic/xai 어댑터 (잘못 추가) 삭제, google→gemini rename, 옛 dartlab 정식 시스템 (ProviderConfig/ProviderTurn/WorkbenchProvider/OpenAICompatibleProvider/OAuthCodexProvider/support/oauth_token) 복원, runner.py / brief.py / work.py / critique.py / compose.py / harvest.py 를 generate()/ProviderTurn 시스템으로 재작성.
