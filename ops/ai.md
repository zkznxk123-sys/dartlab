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

### 설정/상태/템플릿 API

```python
from dartlab import ai

ai.configure(provider="codex", model=None, temperature=0.3)  # 글로벌 AI profile 갱신
ai.get_config()                       # 현재 LLMConfig 반환
ai.status()                           # provider 연결 상태 확인 (available, model 등)

ai.templates()                        # 분석 템플릿 목록 (list[dict])
ai.templates("deep-analysis")         # 특정 템플릿 내용 (str)
ai.saveTemplate("my-tmpl", content="...") # 사용자 템플릿 저장 (~/.dartlab/templates/)
```

### 플러그인 도구 등록

```python
from dartlab.ai import tool, get_plugin_registry

@tool(category="custom")
def my_analysis(metric: str) -> str:
    """사용자 정의 분석."""
    return f"{metric} 분석 완료"

@tool(requires_company=True)
def company_metric(company, metric: str) -> str:
    """회사별 분석."""
    return f"{company.corpName}: {metric}"

get_plugin_registry()                 # 등록된 플러그인 목록
```

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
| **CAPABILITIES** (엔진 tool) | `show` · `analysis` · `scan` · `macro` · `credit` · `quant` · `gather` · `review` · `search` · `searchCompany` · `pythonExec` · `causalWeights` · `valuationImpact` · `storyTree` · `narrativeDiff` · `industry` | 엔진은 AI 근육. docstring→generateSpec.py→_generated.py 자동 등록. axis enum 자동 주입 (추측 금지). |
| **블로그 / 과거 경험** | `pastInsight(stockCode)` · `sectorInsights(sector)` tool | KnowledgeDB `insights(source="blog")` 40건 — narrative 에 `[direction/confidence/archetype] [revenue/opm/roe/fcf]` 병합 (Phase 14 B1). AI 자율 조회, 떠먹이기 금지. |
| **웹 / 뉴스** | `gather("news", ...)` · DART `search`(공시 본문) · `searchCompany`(티커/회사명, KR+US 통합, `인텔→Intel` alias) · `pythonExec` 내 webSearch | 실시간 정보 보강 |

### 데이터 신선도 매트릭스 (Phase 15 B3)

| 데이터 | TTL / 갱신 주기 | 현황 |
|---|---|---|
| DART 공시 | 당일 | 자동 동기화 |
| DART 재무 (분기/연간) | Q+45일 | 11.6M 행, 2,745 종목 |
| EDGAR companyfacts | 24h ETag (daily ~04:25 UTC) | 16,601 종목 |
| 주가 (KR) | 5분 | Naver/Yahoo/FMP fallback |
| 주가 (US) | 15분 | Yahoo/FMP |
| 뉴스 | 30분 | Google News RSS |
| 거시 (ECOS/FRED) | 6h | Parquet 캐시 |

**AI 는 `tool_result.dataAsOf = {latestPeriod, retrievedAt}` 으로 데이터 신선도 즉시 인지** (Phase 15 B2).
"실시간" 착각 방지 — latest period 가 `2025Q4` 인지 `2024` 인지 명시.

## 3.5. dartlab 사상 — 6막 인과

dartlab AI는 **경제(macro) → 섹터(scan/industry) → 기업(Company) → 재무(analysis) → 가치(quant)** 의 6막 인과를 추적한다.

- 종목 분석 시에도 macro/scan/industry를 자율 연결하여 인과 맥락 제공
- 종목 없는 질문도 처리 가능: `dartlab.ask("경제 어때?")` → macro 엔진 직접 호출
- `dartlab.ask("반도체 업종 비교")` → scan/industry 엔진 직접 호출
- Company는 6막 중 하나의 진입점이지, dartlab의 전부가 아니다

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

### 표준 질문 세트 (dartlab 사상 전체 커버)

dartlab = 종목만이 아니다. 경제/섹터/시장/공시/메타 전부 테스트.

| # | 범주 | 질문 | 검증 포인트 |
|---|---|---|---|
| 1 | KR 종목 | "삼성전자 수익성 분석해줘" | 6막 인과 연결, 원본 교차검증 |
| 2 | KR 종목 | "대우건설 안정성 어때?" | credit + analysis 조합 |
| 3 | KR 종목 | "삼양식품 현금흐름 분석" | CF + 이익품질 연결 |
| 4 | US 종목 | "인텔 분석해줘" | EDGAR 데이터, searchCompany |
| 5 | 매크로 | "경제 어때?" | macro 엔진, 종목 없이 동작 |
| 6 | 섹터 | "반도체 업종 비교해줘" | scan + industry |
| 7 | 공시 | "삼성전자 최근 공시 뭐 있어?" | search tool |
| 8 | 종합 | "SK하이닉스 기업이야기 만들어줘" | 6막 전체, pastInsight 활용 |
| 9 | 메타 | "dartlab 뭐 할 수 있어?" | capabilities() 자율 조회, tool 미호출 |
| 10 | capabilities | "show 함수 어떻게 써?" | capabilities("Company.show") 호출 |

### ⛔ 실행 규칙 — 서버 경유 강제. 직접 `dartlab.ask()` 호출 audit 전면 금지

**왜 서버 경유인가**: 실사용자는 landing/UI → `POST /api/ask`로 들어온다. 직접 `dartlab.ask()`는 `server/api/ask.py` · `services/ai_analysis.run_plain_chat` · `streaming.stream_ask` · SSE · 요청 직렬화 · 미들웨어를 전부 건너뛴다. 이 레이어에서 터지는 에러(직렬화 실패, stream 중단, tool_choice 매핑, 상태 오염)는 서버를 띄워야만 드러난다. 인라인 호출은 "로컬 단독 실행에서는 되던데"의 근원.

**프로세스**:

1. 서버 띄우기 (터미널 A, 로그 실시간 감시):
   ```bash
   uv run uvicorn dartlab.server:app --host 127.0.0.1 --port 8400
   ```
2. audit 호출 (터미널 B):
   ```bash
   curl -X POST http://127.0.0.1:8400/api/ask \
     -H "Content-Type: application/json" \
     -d '{"question": "삼성전자 수익성 분석해줘", "stream": false}'
   ```
   또는 stream 경로도 반드시 테스트(`"stream": true` + SSE 수신).
3. **서버 콘솔 로그 전면 확인** — tool failed / warning / traceback / import 실패 / provider 에러 전부.
4. **AI 응답 텍스트 사람이 직접 읽고** P/T/C/V 판정.
5. C/V → 즉시 중단 + 원인 분석 + 수정 + 재audit.

**질문 다양화 = 엔진 전면 점검**: §10 표준 10개 질문(KR/US 종목 · 매크로 · 섹터 · 공시 · 종합 · 메타 · capabilities)을 전부 돌려 엔진별 이상 포인트 수집. 한 질문만 P여도 다른 범주에서 C/V 나오면 엔진 이상. 에러·warning·tool failed 전부 기록.

**금지**:
- `dartlab.ask(...)` / `c.ask(...)` 직접 호출로 audit 결론 내는 것 금지
- `scripts/audit/aiAudit.py` 가 인라인 `dartlab.ask`를 쓰는 한 audit SSOT 아님 — 서버 경유로 마이그레이션되기 전까지 참고용
- 자동 메트릭(토큰/에러 카운트)만으로 "통과" 주장 금지

결과 저장: `data/audit/ai/{YYYY-MM-DD}/` (질문별 응답 + 서버 로그 snippet + P/T/C/V 등급).

## 11. Provider

**API 키 provider:**

| Provider | 모델 |
|---|---|
| `claude` | Claude 4.6 (Opus/Sonnet/Haiku) |
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
| `codex` | ChatGPT CLI | O |

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
- [src/dartlab/ai/insights.py](../src/dartlab/ai/insights.py) — pastInsight/sectorInsights (READ 경로, tool 자동 등록)
- [src/dartlab/ai/tools/coding.py](../src/dartlab/ai/tools/coding.py) — DartlabCodeExecutor (pythonExec tool)
- [src/dartlab/core/overrides.py](../src/dartlab/core/overrides.py) — override 키 정의 + `detectExtremeFlags` 자가 의심
- [src/dartlab/ai/context/aiview.py](../src/dartlab/ai/context/aiview.py) — autoEnrich (tool_result enrichment + [엔진가정] 줄 주입)
- [src/dartlab/ai/context/playbook.py](../src/dartlab/ai/context/playbook.py) — ACE Curator/Reflector (bullet delta merge, 결정론 추출)
- [src/dartlab/ai/persistence/knowledge_db.py](../src/dartlab/ai/persistence/knowledge_db.py) — KnowledgeDB (insights/bullets/executions)
- [src/dartlab/ai/providers/](../src/dartlab/ai/providers/) — provider 구현 (`tool_choice` "any"/"none" 매핑 포함)
