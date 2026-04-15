# AI

**dartlab 을 대표하는 적극적 분석가.** 엔진은 도구, AI 가 주체자.
이 문서가 AI 엔진의 **단일 진실의 원천 (single source of truth)**. 흔들리지 않는다.

---

## 1. 호출 계약

```python
import dartlab
dartlab.ask("삼성전자 수익성 분석해줘")                     # 자연어 → AI 가 도구 자율 호출
dartlab.ask("이 회사 어때", stockCode="005930")             # UI/CLI 가 종목코드 힌트
for chunk in dartlab.ask("분석", stream=True):
    print(chunk, end="")
```

진입점 **단일**: `dartlab.ask(question)`. Company-bound 는 `c.ask(query)` — 내부에서
`stockCode=self.stockCode` 힌트 전달. `chat` / `reviewer` / `ask(stock, question)` 없다.

## 2. 아키텍처 데이터 흐름

```
dartlab.ask(question, *, stockCode?)
  │
  ├─ 시스템 프롬프트 조립 (static[cache_control] + dynamic)
  │     + CAPABILITIES reference 자동 주입 (guide/_generated.py)
  │
  ├─ streamWithTools (runtime/toolLoop.py, max 10 라운드)
  │     provider.stream_with_tools() — SSE delta 실시간 text + ToolResponse
  │     tool 자동 등록 (__all__ + Company 공개 - 블랙리스트)
  │     tool 실행: serializeForLlm(autoEnrich) + serializeForUi
  │     이벤트: tool_call / tool_result / chunk
  │
  ├─ 이벤트 분기 — server SSE / CLI stdio / notebook generator
  │
  └─ post-response 학습 (자율성 침해 아님)
        saveAnalysis      — executions 테이블
        _updateInsight    — insights (regex 추출)
        curate            — ACE bullet delta merge
```

## 3. 3 정보원천

| 원천 | 접근 경로 | 특징 |
|---|---|---|
| **CAPABILITIES** (엔진 tool) | `show` · `analysis` · `scan` · `macro` · `credit` · `quant` · `gather` · `review` · `search` · `searchCompany` · `pythonExec` | 엔진은 AI 근육. 자동 등록 |
| **블로그 / 과거 경험** | `pastInsight(stockCode)` · `sectorInsights(sector)` tool | KnowledgeDB `insights(source="blog")` + AI 축적. 떠먹이기 아님 — AI 자율 조회 |
| **웹 / 뉴스** | `gather("news", ...)` · DART `search` · `pythonExec` 내 webSearch | 실시간 정보 보강 |

## 4. 4축 사상

| 축 | 재정의 | 코드 |
|---|---|---|
| **CAPABILITIES 기반** | 도구 = AI 근육. `dartlab.__all__` + Company 공개 method **자동 순회 + 블랙리스트**. 수동 dict 금지. | `ai/tools/__init__.py::_autoDiscover` |
| **시스템 프롬프트 주도** | 5원칙 + 질문 유형별 축 조합 + 판단 형식 + override 매커니즘을 static 프롬프트에 (cache_control). | `runtime/core.py::_SYSTEM_PROMPT` |
| **AI 자율 개입** ⭐ | 엔진 결과 **소비자가 아니라 조율자**. tool 선택 + **`overrides=` 로 엔진 계산 가정 직접 교체**. 하한 강제 금지. | `runtime/toolLoop.py` + `core/overrides.py` |
| **적극적 분석가** | 엔진 결과 의심 → `show` 원본 검증 → **overrides 재호출로 엔진 조율** → 판단 형식. | 시스템 프롬프트 + post-response |

## 5. AI 개입 매커니즘 (override) ⭐

"AI 자율 개입" 은 tool 선택만이 아니다. **엔진의 계산 과정 자체를 AI 가 제어**한다.

**override 표준** — [core/overrides.py](../src/dartlab/core/overrides.py) — 4 엔진 공통:

| 그룹 | 엔진 | 키 |
|---|---|---|
| FORECAST | analysis | baseRevenue / growthRates / opm / capexRatio / depreciationRatio / nwcRatio / taxRate |
| VALUATION | analysis | wacc / terminalGrowth / primaryModel / riskFreeRate / equityRiskPremium / beta |
| ANALYSIS | analysis | peerGroup / periodRange / sectorBench |
| CREDIT | credit | debtRatio / interestCoverage / currentRatio / quickRatio / ocfToDebt / fcfToDebt / scenarioStress |
| QUANT | quant | window / threshold / period / benchmark |
| MACRO | macro | cyclePhase / rateScenario / fxScenario / liquidityScenario |

**흐름 예시**:
```
AI 가 analysis(axis="가치평가") 호출
  → 엔진이 WACC=18% 로 적정주가 계산 (자동)
  → AI 가 "WACC 18% 는 과대" 판단
  → analysis(axis="가치평가", overrides={"wacc": 9.0}) 재호출
  → 엔진이 WACC=9% 로 재계산
  → 두 결과 비교 → "시장 WACC 기준 적정주가는 X" 판단
```

**Level 1 vs Level 2**:
- Level 1 (시스템 디폴트): `overrides=None` → 엔진 자동 계산
- Level 2 (AI 조율): `overrides={...}` → 지정 가정만 교체, 나머지 자동

**AI 인지**: 각 tool schema 의 `overrides` 파라미터 description 에 가능한 키 명시 →
`describeOverrides("analysis")` 등이 자동 생성.

## 6. 절대 원칙 (흔들림 방지)

### P1. 진입점 단일
`dartlab.ask(question)` 하나. Company-bound 는 `c.ask(query)` — 내부 stockCode 힌트.
`chat` / `reviewer` / `ask(stock, question)` 변종 금지.

### P2. 떠먹이기 금지
- 엔진 결과 **사전 주입** 금지 (Pre-grounding thread, ContextBuilder selectors 부활 금지)
- **예외**: 블로그/경험은 **tool 로 접근** (`pastInsight` / `sectorInsights`). AI 자율 선택.

### P3. 수동 등록 금지
- AI tool 목록은 `dartlab.__all__` + Company 공개 method **자동 순회 + 블랙리스트**
- 수동 `_TOOLS = {...}` 금지
- 블랙리스트: setup · collect · collectAll · downloadAll · listing · Company · config · ask ·
  canHandle · priority · status · update · view · 기타 비분석 API

### P4. 강제 하한 금지
- 시스템 프롬프트에 "분석당 tool 4~7회" 같은 **숫자 하한 금지**
- AI 자율 (간단한 질문엔 1회, 복잡한 질문엔 10회) — Claude Code 방식
- "질문 유형별 축 조합" 표는 **참고 가이드** (강제 X)

### P4.5. AI 가 엔진에 **직접 개입** (override) ⭐
- AI 는 엔진 결과 소비자가 아니라 **조율자**
- 엔진 가정이 비현실적이면 `overrides={...}` 로 **계산 과정 자체 교체** 후 재호출
- 4 엔진 (analysis/credit/quant/macro) override 키는 [core/overrides.py](../src/dartlab/core/overrides.py) 에 정의 — 단일 진실의 원천
- tool schema 의 `overrides` description 에 가능한 키 자동 명시 → AI 자율 선택

### P5. Company 엔진 method 유지
- `c.analysis` / `c.credit` / `c.review` / `c.gather` / `c.quant` / `c.show` — 프로그래밍 경로
- AI tool 과 중복 아님 (같은 `_Impl` 공유). 노트북/스크립트/publisher 에서 사용

### P6. 원본 검증은 AI 자율
- 매번 `show` 호출 의무 X
- 엔진 결과가 의심스러울 때 자율 판단
- "매번 원본 검증 표시" 금지 — 답변 장황함 초래

### P7. 숫자 개수 명시 금지
- "14축", "13 엔진", "10종 도구" 같은 카운트 **금지** (축은 늘어남)
- description/문서에 뭘 하는지로 설명
- 메모리 + ops + README + 블로그 + 시스템 프롬프트 **전부** 적용

### P8. Tool Zero 응답 금지 (FINANCE 범주) ⭐
- 질문 범주를 **META / FINANCE / OUT_OF_SCOPE** 3분류 ([ai/context/intent.py::classifyCategory](../src/dartlab/ai/context/intent.py)).
  - **META** (dartlab 자체 안내 — "뭐야", "어떻게 써"): tool 불필요, CAPABILITIES + 시스템 프롬프트로 답
  - **FINANCE** (기업/시장/매크로/공시/가치/신용 — 애매 금융 주변 포함): **tool 최소 1회 필수**
  - **OUT_OF_SCOPE** (날씨/일반 코딩/사담): 짧게 답 + "dartlab 전문 영역 아님" 명시 + 금융 질문 예시 3개 제시 후 종료. tool 호출 금지
- **FINANCE 범주 tool 0회 응답 = dartlab 정체성 훼손**. 일반 ChatGPT 와 동일 → 경유 강제.
- 3중 방어선:
  1. **시스템 프롬프트 블록** (core.py::`_buildCategoryBlock`) — intent 맞춤 필수 tool 조합 명시
  2. **`tool_choice="any"` API 레벨 강제** (toolLoop.py::`_resolveToolChoice`) — FINANCE 첫 라운드
  3. **런타임 가드** (toolLoop.py::`streamWithTools`) — tool 0회면 "[VIOLATION] ... 재호출" 자동 재질문 1회
- P4 (강제 하한 금지) 와 충돌 없음 — "n회 하한" 이 아니라 "tool zero 금지". FINANCE 내 tool 수는 여전히 AI 자율 (1~10회).

## 7. 경험 자산화 순환

dartlab AI 는 매 대화가 독립이 아니라 **집단 지성**을 축적한다. 사람(블로그) 과 AI(응답) 가
쌓은 서사·bullet·코드 패턴이 KnowledgeDB 에 영구 보존되고, HuggingFace 로 공유된다.

**자산 종류** (KnowledgeDB 테이블):

| 테이블 | 저장 주체 | 내용 | 공유 |
|---|---|---|---|
| `insights` | 사람(블로그) + AI (응답) | 회사별 서사 · strengths · weaknesses · keyMetrics | ✓ HF |
| `bullets` (ACE playbook) | AI 응답 자동 추출 | intent+sector 별 검증 bullet (Beta posterior 품질) | ✓ HF |
| `executions` | AI 응답 자동 | 모든 질문·등급·tool 호출 기록 | ✗ 개인 이력 |

**자산화 순환 루프**:

```
     ┌──────────────────────── HuggingFace 동기화 (push/pull)
     │
     ▼
 KnowledgeDB (insights / bullets / executions)
     ▲                                   │
     │                                   │
  [쓰기]                              [읽기]
     │                                   │
  post-response 자동                     ▼
  · _updateInsightFromResponse        AI 가 tool 로 자율 조회
  · curate(bullet delta merge)        · pastInsight(stockCode)
  · saveAnalysis(executions)          · sectorInsights(sector)
     │                                   │
     └───────────────  AI 응답 ──────────┘
     ▲
     │
사람 (블로그 frontmatter ai: 블록)
  → publisher 가 insights(source="blog") 로 변환
```

**읽기 경로** — `ai/tools/_builtin.py::pastInsight` / `sectorInsights`. AI 가 자율 호출.

**블로그 → insights 파생** — `blog/{company}/index.md` frontmatter `ai:` 블록 →
publisher 가 `KnowledgeDB.upsert_insight(source="blog")`. 사람이 쓴 검증된 서사가 곧 AI 자산.

## 8. 질문 유형별 축 조합 (참고 가이드, 강제 X)

시스템 프롬프트가 AI 에게 참고로 제공 — AI 판단 자율:

| 질문 유형 | 축 조합 예 |
|---|---|
| 수익성 | `analysis("수익성")` + `analysis("비용구조")` + review credit 블록 참고 |
| 가치평가 | `analysis("가치평가")` + `analysis("매출전망")` + `gather("price")` + overrides 조율 |
| 신용/부실 | `credit()` + `analysis("안정성")` + `analysis("현금흐름")` + overrides 시나리오 |
| 사이클 | `macro("사이클")` + `scan("growth")` + `quant("지표")` |
| 비교/스크린 | `scan(axis, ...)` + `analysis` (선택 종목 심층) |
| 공시/이슈 | `search(...)` + `gather("news")` + `show("filings")` |

## 9. 분석 결과 해석 규칙

- **dict 키 추측 금지** — `c.analysis(...)` 결과 dict 는 schema 가 정해져 있음. 독스트링 확인.
- **flags 타입 일관성** — `list[str]` (경고 이름). 문자열 join 금지.
- **autoEnrich _summary 활용** — tool_result dict 에 `_summary` 필드 주입됨 (5년 평균/YoY/추세).
- **None 은 "데이터 없음"** — 추정값 만들지 않음. 사용자가 판단.

## 10. AI Audit 체계

> AI 를 실제로 돌려서 응답 품질을 직접 확인 → 문제 발견 → 시스템 프롬프트/코드 수정 → 재실행.

### 핵심 원칙

- **AI audit = 사람이 AI 응답을 읽고 판단.** 자동 메트릭(토큰/길이)만으로 품질 주장 금지.
- **provider = oauth-codex** (GPT OAuth). gemini 아님.
- 모든 하위 엔진(Company, sections, notes, analysis, scan, gather) 문제가 여기서 표면화.

### 등급 (P/T/C/V)

| 등급 | 기준 |
|---|---|
| **P** (Pass) | 수치 정확 + 6막 인과 해석 + override 활용(필요 시) + 판단 형식 |
| **T** (Tolerable) | 수치 정확, 해석 약함 |
| **C** (Critical) | 수치 오류 / "해석 불가" 면피 / tool 실행 실패 |
| **V** (Violation) | 엔진 미사용 / hallucination / 규칙 위반 |

C/V 등급 나오면 즉시 중단 + 원인 분석 + 재실행.

### 표준 질문 세트 (9개, 매 audit 동일)

3 종목 × 3 축 (수익성/현금흐름/안정성): 삼성전자 · 대우건설 · 삼양식품.

### 실행

```bash
uv run python -X utf8 scripts/audit/aiAudit.py               # 9개 전체
uv run python -X utf8 scripts/audit/aiAudit.py --quick       # 3개 (삼성전자 3축)
uv run python -X utf8 scripts/audit/aiAudit.py --provider gemini
```

결과: `data/audit/ai/{YYYY-MM-DD}/` JSON + 요약 md 저장. P 등급 → playbook recipe 자동 저장.

## 11. Provider

**API 키 provider:**

| Provider | 모델 |
|---|---|
| `gemini` | Gemini 2.5 Pro/Flash |
| `groq` | LLaMA 3.3 70B |
| `cerebras` | LLaMA 3.3 70B |
| `mistral` | Mistral Small |
| `oauth-codex` | GPT OAuth (audit 표준) |

**기타:**

| Provider | 인증 | Tool Calling |
|---|---|:---:|
| `openai` | API key | O |
| `ollama` | 로컬 | 모델 의존 |

**벤치마크 숫자로 기본 모델을 정하지 않는다.** 각 모델로 dartlab AI audit 실행 → P/T/C/V 등급 비교.

## 12. [폐기] — 히스토리

- **selfai 엔진** (few_shot/router/reflexion/output_validator) 2026-04-06 폐기.
  KnowledgeDB 영속성만 `ai/persistence/` 로 분리 보존.
- **Pre-grounding thread / ContextBuilder selectors** — 떠먹이기. 2026-04-13 완전 제거.
  경험 자산은 `pastInsight` / `sectorInsights` tool 로 AI 자율 조회.
- **dartlab.chat / c.reviewer** — 진입점 단일화 (P1). `dartlab.ask` / `c.ask` 로 통합.

## 13. 관련 코드

- [src/dartlab/ai/runtime/standalone.py](../src/dartlab/ai/runtime/standalone.py) — `dartlab.ask` 진입점
- [src/dartlab/ai/runtime/core.py](../src/dartlab/ai/runtime/core.py) — 시스템 프롬프트 + category 블록 + analyze 이벤트 생성
- [src/dartlab/ai/runtime/toolLoop.py](../src/dartlab/ai/runtime/toolLoop.py) — streamWithTools 루프 + P8 가드 + tool_choice 매핑
- [src/dartlab/ai/context/intent.py](../src/dartlab/ai/context/intent.py) — `classifyCategory` (META/FINANCE/OUT_OF_SCOPE) + `classifyIntent` (6막/compare/concept)
- [src/dartlab/ai/tools/__init__.py](../src/dartlab/ai/tools/__init__.py) — `_autoDiscover` + schema
- [src/dartlab/ai/tools/_builtin.py](../src/dartlab/ai/tools/_builtin.py) — pastInsight/sectorInsights
- [src/dartlab/core/overrides.py](../src/dartlab/core/overrides.py) — override 키 정의 + `detectExtremeFlags` 자가 의심
- [src/dartlab/ai/context/aiview.py](../src/dartlab/ai/context/aiview.py) — autoEnrich (tool_result enrichment + [엔진가정] 줄 주입)
- [src/dartlab/ai/persistence/knowledge_db.py](../src/dartlab/ai/persistence/knowledge_db.py) — KnowledgeDB (insights/bullets/executions)
- [src/dartlab/ai/providers/](../src/dartlab/ai/providers/) — provider 구현 (`tool_choice` "any"/"none" 매핑 포함)
