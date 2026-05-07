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
- L2 는 AI 안에 두지 않는다. `dartlab.skills.*` 가 단일 SSOT 인프라 (SkillSpec / searchSkills / compiler). AI 는 *read-only 소비자* — P-revised 후 `propose_skill` 폐기로 AI 가 spec 작성하지 않는다. `kind: generated` 사다리 폐기, `kind: curated` 만 존재.

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

### 3. 도구 6 + 1 고정 (canonical 6 데이터 도구 + 1 meta-tool)

| API name (snake) | Python identifier (camel) | 카테고리 | 책임 |
|---|---|---|---|
| `run_python` | `runPython` | data | dartlab 라이브러리 + Polars 임의 코드 실행, ref 발급 |
| `read_skill` | `readSkill` | data | `dartlab.skills.searchSkills` 호출, frontmatter + 본문 반환 |
| `read_capability` | `readCapability` | data | `dartlab.core.capability.search` 호출, docstring 반환 |
| `web_search` | `webSearch` | data | 외부 최신 정보, webRef |
| `save_artifact` | `saveArtifact` | data | 산출물 저장, artifactRef |
| `compile_visual` | `compileVisual` | data | 차트 spec codegen (line/bar/table/radar/waterfall/heatmap/histogram) → visualRef, agent.py 가 VIEW_SPEC 이벤트로 인라인 |
| `run_workbench` | `runWorkbench` | meta | chat-native LLM 이 깊은 분석을 위해 5 패스 작업대로 elevate. 결과를 tool_result 로 받음 |

- 추가는 SSOT 갱신 PR 의무. registry 는 화이트리스트 강제 — 외 등록 거부 (`registerTool` 은 plugin 도구만 허용, `CANONICAL_TOOL_NAMES` 보호).
- **이름 컨벤션**: API name (registry key, MCP tool name, LLM 에 보이는 이름) = snake_case. Python 식별자·파일명 = camelCase. `toolSpecs(provider)` 가 변환.
- **삭제됨 (P-revised)**: `propose_skill` — `kind: generated` 자기진화 사다리는 0 promoted skill 로 dormant 상태였고, outcome ground truth loop (§6) 이 더 실용적 학습 신호이므로 폐기.

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

### 6. Outcome ground truth 선순환 (P-revised)

```
분석 결정 (chat-native HARVEST bridge OR workbench HARVEST)
   ↓
outcome_log 에 pending entry 작성 (~/.dartlab/decisions/{market}/{stockCode}.md)
   ↓ (다음 같은 종목 호출 시 BRIEF/agent.py 진입부)
resolve_pending(stockCode):
   - dartlab.providers.{dart,edgar}.Company.price(asOf=...) + 벤치마크 비교
   - 가격/공시 부족 시 pending 유지, 다음 호출까지 굴림
   ↓
reflection (2-4 문장 평문, 마크다운 금지):
   1. 방향성 판단이 옳았는가? (alpha 수치 인용)
   2. 분석 thesis 의 어느 부분이 유지/실패했는가?
   3. 다음 비슷한 분석에 적용할 구체적 lesson 1 가지
   ↓
pending → resolved 로 entry atomic 갱신 (temp+replace)
   ↓
다음 분석 BRIEF/agent.py 가 같은 종목 5 + 다른 종목 3 entry 비대칭 주입
   - same-stockCode: tag + DECISION + REFLECTION 전문
   - cross-stockCode: tag + REFLECTION 만 (decision 300자 truncate)
   ↓
환각 가드: past_context 가 빈 문자열일 때 placeholder 섹션 자체 부재
```

- **per-stockCode markdown SSOT**. HTML 주석 `<!-- ENTRY_END -->` separator (LLM prose 면역).
- **idempotency**: 같은 (date, stockCode) pending 중복 거부.
- **atomic write**: temp file + os.replace — 크래시 mid-write 시 원본 보존.
- **rotation**: pending 영구 보존, resolved 만 `outcome_log_max_entries` 임계 초과 시 oldest drop.
- **chat-native + workbench 양 경로 모두 작성**. 종목 명시 (stockCode 추출 가능) 시에 한해.
- 기존 `memory/decisions.py` (BM25 recall) + `memory/stats.py` (skill usage) 와 직교 — outcome_log 는 *outcome ground truth*, decisions.jsonl 은 *recall 컨텍스트*.

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
├── tools/                     ← P-revised — 6 데이터 + 1 meta
│   ├── registry.py            ← toolSpecs(provider), 화이트리스트 강제
│   └── runPython.py / readSkill.py / readCapability.py / webSearch.py / saveArtifact.py / compileVisual.py / runWorkbench.py
├── workbench/                 ← 5 패스 (LLM 자율 elevate 전용)
│   ├── loop.py                ← orchestration
│   ├── state.py / prompts.py
│   └── brief.py / work.py / critique.py / compose.py / gate.py / harvest.py
├── memory/                    ← outcome ground truth + recall + stats
│   └── decisions.py / stats.py / outcome_log.py / outcome_resolver.py / wiring.py
├── lenses/                    ← P5 (옵션)
│   └── fundamental.py / macro.py / technical.py / sentiment.py
└── settings/                  ← 기존 유지
```

### 경계 강제 (테스트로 잠금)

- `ai/workbench/`, `ai/tools/`, `ai/providers/`, `ai/lenses/` 는 `dartlab.{analysis,company,scan,quant,gather,macro,industry,review,credit,viz,...}` 등 core engine 을 **정적 import 하지 않는다**. (현재 코드도 위반 0 — 본 규칙은 신규 강제가 아닌 회귀 가드.)
- `ai/tools/{readSkill,readCapability}.py` 만 `dartlab.skills.*` (메타) 와 `dartlab.core.capability.*` 의 docstring 을 read-only 로 접근. 데이터 호출은 안 한다.
- `ai/` 코드는 `src/dartlab/skills/` 의 컨텐츠를 일체 변경하지 않는다 (P-revised: HARVEST propose_skill 폐기로 AI 가 spec 작성하지 않음).

### 코드 컨벤션

- 한 폴더 한 책임. 파일 하나 = 함수/클래스 그룹 하나.
- Python 식별자·파일명 = camelCase. 외부 노출 API name = snake_case. CLAUDE.md camelCase 규칙은 식별자 한정.
- UTF-8, 코드 주석 최소.

---

## MCP 표면 매핑

P-revised 후 노출 (MCP 서버 instructions 동시 갱신):

| MCP tool | 매핑 |
|---|---|
| `ask` | kernel.ask 진입 |
| `run_python` | runPython (legacy `engine_call` 통합) |
| `read_skill` | readSkill (legacy `skill_search`/`read` 통합) |
| `read_capability` | readCapability (legacy `generated_spec_search` 통합) |
| `web_search` | webSearch |
| `save_artifact` | saveArtifact |
| `compile_visual` | compileVisual |
| `run_workbench` | runWorkbench (meta-tool, 5 패스 elevate) |

**삭제됨**: `propose_skill` (자기진화 사다리 폐기). `verify_answer` (GATE 통합). `read`/`write` (직접 file I/O 비권장).

---

## 정체성 — 외부 단일 / 내부 분업

- **외부 (사용자가 듣는 목소리)**: 단일 분석가 ("DartLab 분석가").
- **내부 (인지 작업)**: 분업 가능. 단일이 default. 질문 난이도가 임계 넘으면 lens 패널 자동 활성 (P5 — fundamental / macro / technical / sentiment).

---

## 회귀 가드 (테스트로 강제)

- `tests/ai/test_no_core_import.py` — 정적 import 금지 (`ai/workbench/`, `ai/providers/`, `ai/lenses/` 가 `dartlab.<engine>` 정적 import 시 실패)
- `tests/ai/test_tool_whitelist.py` — registry 가 canonical 6 데이터 + 1 meta 외 등록 거부. `propose_skill` / `skill_search` / `generated_spec_search` / `engine_call` / `verify_answer` / `read` / `write` 등록 시 실패
- `tests/ai/test_ref_gate.py` — 숫자·날짜·랭킹 답 ref 없으면 GATE 차단. ref token 형식은 `<refKind:id>` 단일
- `tests/ai/test_providers.py` — 어댑터 schema 변환 단위 테스트
- `tests/ai/test_outcome_log.py` — pending↔resolved 전환, idempotency, atomic temp+replace, asymmetric same/cross format, HTML separator 면역
- `tests/ai/test_lookahead_filter.py` — `Company.show(asOf=...)` 가 미래 fiscal period / 가격 컬럼 drop
- `tests/ai/test_runworkbench_dispatch.py` — chat-native LLM 의 `runWorkbench` tool 호출 시 workbench 5 패스 활성. mode != "analyze" AND tool 미호출 시 workbench 활성 0
- `tests/ai/test_chat_native_harvest.py` — agent.py 종료 시 decisions.jsonl + skill_stats.jsonl + (stockCode 추출 시) outcome_log entry 작성
- `tests/ai/test_provider_whitelist_single_source.py` — `_isLLMProvider` 가 `wired_provider_ids()` 만 사용. hardcoded provider set 0 건 (provider_catalog.py 외)
- `tests/ai/test_safe_stockcode.py` — path traversal 시도 (`..`, `/`, all-dot, 길이 초과) 거부

**삭제된 가드**: `test_skill_spec_integrity.py` (kind=generated 폐기), `test_no_external_skill_writes.py` (ai/ 가 spec 작성 안 함). `test_golden_baseline.py` (heuristic 시대 골든 셋, P-revised 후 폐기).

---

## SSOT 갱신 PR 룰 (P6)

본 SSOT 가 lock 된 이후 다음 변경은 SSOT 갱신 PR 의무:

1. 신규 도구 추가/제거 — canonical 6 데이터 + 1 meta 화이트리스트 변경.
2. 신규 패스 추가/순서 변경 — `BRIEF→WORK→CRITIQUE→COMPOSE→GATE→HARVEST` 외.
3. 신규 provider 어댑터 추가 — `provider_catalog.py` `_PROVIDERS` 변경.
4. ref kind 추가 — `Ref.kind` 값 집합 변경 (`valueRef`, `tableRef`, ...).
5. outcome_log entry 형식 변경 — `[date | stockCode | theme | pending|resolved | ...]` 태그 컬럼 추가/제거.
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
- 2026-05-07: P-revised — propose_skill / kind=generated 자기진화 사다리 폐기 (0 promoted skill, dormant). outcome ground truth loop 도입 (TauricResearch/TradingAgents v0.2.4 메커니즘 흡수: deferred resolution, alpha-conditioned reflection, asymmetric same/cross 주입, HTML separator, atomic temp+replace). runWorkbench meta-tool 도입 (chat-native → 5 패스 elevate 명시 경로). intent.py keyword routing 폐기 — kernel 은 `mode==analyze` 또는 LLM tool 호출만 분기. chat-native HARVEST bridge — agent.py 종료 시 memory/wiring.py 공유 helper 가 decisions.jsonl + skill_stats.jsonl + outcome_log 작성. 2-tier provider role routing (deep/quick). Look-ahead bias 가드 — providers/{dart,edgar}/company.py 에 `asOf` 인자. canonical 도구 정합 — `engine_call` 폐기, `compile_visual` SSOT 인정, `save_artifact` chat-native 노출.
