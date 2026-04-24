# AI

**주체**: AI 엔진 (`dartlab.ask` · 서버 `/api/ask` 경유).
**현재**: 4축 사상 (CAPABILITIES tool · 시스템 프롬프트 · 자율 개입 override · 적극적 분석가) 확립. 8 운영 원칙 (P1~P8) 실행 중.
**방향**: 엔진 override 키 자동 생성 · 블로그/경험 tool 활용 확대 · 응답 latency 단축.

**dartlab 을 대표하는 적극적 분석가.** 엔진은 도구, AI 가 주체자.
이 문서가 AI 엔진의 **단일 진실의 원천 (single source of truth)**. 흔들리지 않는다.

각 섹션은 **"이렇게 한다"** 명제로 열고, 반복된 실수는 섹션 하단 **"반복 실패"** 에 정리한다.

---

## 1. 호출 — `dartlab.ask(question)` 단일 진입점으로 간다

```python
import dartlab
dartlab.ask("삼성전자 수익성 분석해줘")                     # 자연어 → AI 가 도구 자율 호출
dartlab.ask("이 회사 어때", stockCode="005930")             # UI/CLI 가 종목코드 힌트
for chunk in dartlab.ask("분석", stream=True):
    print(chunk, end="")
```

진입점 **단일**: `dartlab.ask(question)`. Company-bound 는 `c.ask(query)` — 내부에서 `stockCode=self.stockCode` 힌트 전달. `chat` / `reviewer` / `ask(stock, question)` 은 쓰지 않는다.

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

**반복 실패** — `dartlab.chat` / `c.reviewer` / `ask(stockCode, question)` 다중 진입점 유지. 2026-04-06 단일화 완료.

---

## 2. 아키텍처 — 단일 데이터 흐름으로 간다

```
dartlab.ask(question, *, stockCode?)
  │
  ├─ 시스템 프롬프트 조립 (static[cache_control] + dynamic)
  │     + CAPABILITIES reference 자동 주입 (guide/_generated.py)
  │
  ├─ request scope: beginCompanyCache() — ContextVar 에 {stockCode: Company}
  │     한 요청 내 같은 종목 tool 여러 개가 Company 인스턴스 공유 →
  │     finance 매핑 1회. BoundedCache 공유. 메모리 폭발 완화.
  │
  ├─ streamWithTools (runtime/toolLoop.py, max 10 라운드)
  │     provider.stream_with_tools() — SSE delta 실시간 text + ToolResponse
  │     tool 자동 등록 (__all__ + Company 공개 - 블랙리스트)
  │     인터리빙 강제: 한 라운드에 tool 1개만 (resp.tool_calls[:1]).
  │     tool 실행: runToolWithProgress (worker thread + ContextVar)
  │              → getOrCreateCompany(stockCode)  (request-scoped cache)
  │              → serializeForLlm(autoEnrich) + serializeForUi
  │     이벤트: tool_call / tool_progress (실시간 진행 라인) / tool_result / chunk
  │
  ├─ 이벤트 분기 — server SSE / CLI stdio / notebook generator
  │
  └─ post-response 학습 (자율성 침해 아님)
        saveAnalysis      — executions 테이블
        _updateInsight    — insights (regex 추출)
        curate            — ACE bullet delta merge
```

---

## 3. 정보원천 — 세 개로 간다

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

---

## 4. 사상 — 6 막 인과로 간다

dartlab AI 는 **경제(macro) → 섹터(scan/industry) → 기업(Company) → 재무(analysis) → 가치(quant)** 의 6막 인과를 추적한다.

- 종목 분석 시에도 macro/scan/industry 를 자율 연결하여 인과 맥락 제공.
- 종목 없는 질문도 처리: `dartlab.ask("경제 어때?")` → macro 엔진 직접 호출.
- `dartlab.ask("반도체 업종 비교")` → scan/industry 엔진 직접 호출.
- Company 는 6막 중 하나의 진입점이지, dartlab 의 전부가 아니다.

**반복 실패** — Company 편의성 원칙을 dartlab 전체 사상으로 혼동. Company 는 엔진 편의성, dartlab 은 4 비교 가능성 + 6막 인과.

---

## 5. 4축 사상 — 이 넷이 dartlab AI

| 축 | 재정의 | 코드 |
|---|---|---|
| **CAPABILITIES 기반** | 도구 = AI 근육. `dartlab.__all__` + Company 공개 method **자동 순회 + 블랙리스트**. 수동 dict 금지. | `ai/tools/__init__.py::_autoDiscover` |
| **시스템 프롬프트 주도** | 5원칙 + 질문 유형별 축 조합 + 판단 형식 + override 매커니즘을 static 프롬프트에 (cache_control). | `runtime/core.py::_SYSTEM_PROMPT` |
| **AI 자율 개입** ⭐ | 엔진 결과 **소비자가 아니라 조율자**. tool 선택 + **`overrides=` 로 엔진 계산 가정 직접 교체**. 하한 강제 금지. | `runtime/toolLoop.py` + `core/overrides.py` |
| **적극적 분석가** | 엔진 결과 의심 → `show` 원본 검증 → **overrides 재호출로 엔진 조율** → 판단 형식. | 시스템 프롬프트 + post-response |

---

## 5.5 skill 은 독스트링이다 — 별도 파일 없음

**SSOT = [`ops/skills.md`](skills.md).** 본 섹션은 AI 엔진 관점의 요약 포인터.

핵심 명제 5 줄:

1. **skill = 공개 엔진·함수의 docstring**. 별도 `skills/` 디렉토리나 `SKILL.md` 파일 없음. `help(scanRatio)` 가 곧 skill 본문.
2. **3 층 docstring**: 엔진 `__init__.py` (사상·레시피·질문→조합 매핑) → 공개 함수 docstring (9 섹션: When/How/Parameters/Returns/Raises/Examples/Notes/Guide/See Also) → `ai/runtime` (여러 엔진 엮는 종합 절차). `ops/code.md` SSOT 준수.
3. **AI 노출 = tool schema description** (기존 `ai/tools/__init__.py::_toolDescription` 경로). skill 카탈로그 별도 프롬프트 주입 없음. 필요 시 `Read` tool 로 엔진 docstring · `ops/{engine}.md` 직접 참조.
4. **자가 개선 5 Phase 는 docstring 위에서 돌아간다** — 실험 (audit 로그) → 후보 (반복 패턴 감지) → 승격 (docstring Guide PR) → 자기개선 (반례 · 개선 PR) → 엔진 승격 (반복 조합을 공식 axis 로). audit 로그 축적 훅 `server/streaming.py` 완료.
5. **축 개선·추가 시 독스트링을 skill 급으로 유지** 의무. When/How/Verified/Examples 모두 채우지 않으면 merge 반려. `ops/skills.md §4` 참조.

AI 엔진이 해야 할 일:

- **Phase 1 실행 완료** — `server/streaming.py::stream_ask` audit 로그 훅 · `Read` tool 추가. 남은 것: 테스트 audit 2 회 재실행 + `_buildSkillCatalog` 제거된 프롬프트에서 광역 발굴 응답 품질 재확인.
- **docstring 개선 — scan 엔진 사상 · scanAccount/scanRatio Guide** 를 skill 급으로. `annual` → `freq` 일관화 완료 후 Guide 섹션 최신 유지.
- **prompts 정리 — 기존 `_SYSTEM_PROMPT` 에 박힌 "7 관점 · Reading Notes · 질문→매핑"** 은 docstring 으로 이관·수렴되면 프롬프트에서 점진 제거 (현재는 유지 — docstring 이 충분히 성숙하면 제거).

---

## 6. AI 개입 매커니즘 (override) — 가정을 AI 가 교체한다 ⭐

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
- Level 1 (시스템 디폴트): `overrides=None` → 엔진 자동 계산.
- Level 2 (AI 조율): `overrides={...}` → 지정 가정만 교체, 나머지 자동.

**AI 인지**: 각 tool schema 의 `overrides` 파라미터 description 에 가능한 키 명시 →
`describeOverrides("analysis")` 등이 자동 생성.

---

## 7. 운영 원칙 P1~P8

### P1. 진입점 단일
AI 호출 경로는 `dartlab.ask(question)` 하나. Company-bound 는 `c.ask(query)` — 내부에서 `stockCode=self.stockCode` 힌트 자동 전달. 본 진입점 하나로 통합 운영한다.

### P2. 엔진 결과는 tool 로 조회
AI 는 엔진 결과를 **tool 호출** 로 가져온다 (`show` · `analysis` · `scan` · `credit` · `quant` · `gather` · `macro` 등). 블로그/과거 경험도 `pastInsight` / `sectorInsights` tool 로 AI 자율 선택. 사전 주입 (Pre-grounding / ContextBuilder selectors) 경로는 사용하지 않는다 — AI 의 자율 판단 공간을 보존.

### P3. tool 자동 등록
tool 목록은 `dartlab.__all__` + Company 공개 method 를 **자동 순회** 해 블랙리스트 필터 후 등록. 블랙리스트: setup · collect · collectAll · downloadAll · listing · Company · config · ask · canHandle · priority · status · update · view · 기타 비분석 API. 수동 dict 유지는 중복 SSoT 를 만들기 때문에 자동 경로만 유지.

### P4. tool 호출 수는 질문 복잡도에 따라 자율
AI 는 간단 질문 1회, 복잡 질문 10회까지 tool 호출을 **자율 결정**. 시스템 프롬프트에 "분석당 tool N회" 같은 숫자 하한은 두지 않는다 (Claude Code 방식). "질문 유형별 축 조합" 표는 **참고 가이드** 로만 활용.

### P4.5. AI 의 엔진 개입 (override) ⭐
AI 는 엔진 결과의 **조율자**. 엔진 가정이 비현실적이면 `overrides={...}` 로 계산 과정 자체를 교체해 재호출한다. 4 엔진 (analysis/credit/quant/macro) override 키의 **단일 진실의 원천** 은 [`core/overrides.py`](../src/dartlab/core/overrides.py) 코드 (본 문서는 개념만 설명). tool schema 의 `overrides` description 에 가능한 키가 자동 명시되어 AI 가 인지한다.

### P5. Company 엔진 method 병존
`c.analysis` / `c.credit` / `c.review` / `c.gather` / `c.quant` / `c.show` — 사용자 프로그래밍 경로. 같은 `_Impl` 을 공유하므로 AI tool 과 결과 동일. 노트북 · 스크립트 · publisher 에서 활용.

### P6. 원본 검증은 AI 자율
AI 는 엔진 결과가 의심스러울 때 `show` 원본을 호출해 검증한다. 매 응답마다 의무 호출은 하지 않으며 "매번 원본 검증했다" 같은 문구도 응답에 남기지 않는다 — 답변 간결성 유지.

### P7. 카탈로그 수 대신 기능 설명
축·엔진·tool 개수 ("14축", "10 tool") 는 시간에 따라 늘어나므로 문서·시스템 프롬프트·메모리·블로그·README 모두 **기능 설명 중심**으로 작성한다. 숫자는 CAPABILITIES 자동 생성본에 맡기고 본 문서는 개념만.

### P8. FINANCE 범주는 최소 1회 tool 경유 ⭐
질문 범주를 [ai/context/intent.py::classifyCategory](../src/dartlab/ai/context/intent.py) 가 3 분류:
- **META** (dartlab 자체 안내 — "뭐야", "어떻게 써"): CAPABILITIES + 시스템 프롬프트로 직접 응답. tool 불필요.
- **FINANCE** (기업·시장·매크로·공시·가치·신용 + 애매 주변): **tool 최소 1회 경유**. tool 0회 응답은 dartlab 정체성 훼손 (일반 ChatGPT 와 동일).
- **OUT_OF_SCOPE** (날씨·일반 코딩·사담): 짧게 답 + "dartlab 전문 영역 아님" 안내 + 금융 질문 예시 3개. tool 호출은 범위 밖.

**3중 방어선**:
1. **시스템 프롬프트 블록** (core.py::`_buildCategoryBlock`) — intent 맞춤 필수 tool 조합 명시.
2. **API 레벨 강제** (toolLoop.py::`_resolveToolChoice` · `tool_choice="any"`) — FINANCE 첫 라운드.
3. **런타임 가드** (toolLoop.py::`streamWithTools`) — tool 0회 시 "[VIOLATION] ... 재호출" 자동 재질문 1회.

P4 (자율 결정) 와 충돌 없음 — "n회 하한" 이 아니라 FINANCE 전용 "tool zero 방지". 호출 횟수는 여전히 AI 자율 (1~10회).

**반복 실패** — Pre-grounding 으로 context 떠먹이기 / 수동 tool dict 유지 / FINANCE 질문에 tool 0회 응답. 세 패턴 모두 자율 판단 공간 또는 dartlab 정체성 침해로 제거.

---

## 8. 경험 자산화 — 블로그·응답을 KnowledgeDB 로 순환시킨다

dartlab AI 는 매 대화가 독립이 아니라 **집단 지성**을 축적한다. 사람(블로그) 과 AI(응답) 가 쌓은 서사·bullet·코드 패턴이 KnowledgeDB 에 영구 보존되고, HuggingFace 로 공유된다.

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

---

## 9. 질문 유형별 축 조합 (참고 가이드)

시스템 프롬프트가 AI 에게 참고로 제공 — AI 판단 자율:

| 질문 유형 | 축 조합 예 |
|---|---|
| 수익성 | `analysis("수익성")` + `analysis("비용구조")` + review credit 블록 참고 |
| 가치평가 | `analysis("가치평가")` + `analysis("매출전망")` + `gather("price")` + overrides 조율 |
| 신용/부실 | `credit()` + `analysis("안정성")` + `analysis("현금흐름")` + overrides 시나리오 |
| 사이클 | `macro("사이클")` + `scan("growth")` + `quant("지표")` |
| 비교/스크린 | `scan(axis, ...)` + `analysis` (선택 종목 심층) |
| 공시/이슈 | `search(...)` + `gather("news")` + `show("filings")` |

---

## 10. 분석 결과 해석 — dict 스키마 그대로 쓴다

- **dict 키 추측 금지** — `c.analysis(...)` 결과 dict 는 schema 가 정해져 있음. 독스트링 확인.
- **flags 타입 일관성** — `list[str]` (경고 이름). 문자열 join 금지.
- **autoEnrich 메타 활용** — tool_result dict 에 엔진이 판정한 메타가 주입됨. AI 는 이 값을 **응답에 그대로 인용**하고 재계산하지 않는다.
  * `_summary` : 5년 평균/YoY/추세 한 줄 요약
  * `_yoy` : `{field: "+x.x%"}` dict — history 의 모든 숫자 필드에 대한 직전 기간 대비 변화율 (`core/finance/ratios::yoy_pct` SSOT). 부호 전환 시 필드 생략.
  * `assumptions` : 엔진이 채택한 가정 (override 유도 문구 포함)
- **None 은 "데이터 없음"** — 추정값 만들지 않음. 사용자가 판단.
- **`status="auth_required"` 는 API 키 필요** — tool_result 의 status 가 `auth_required` 이면 `llmText` 본문에 발급 URL + `.env` 설정법이 이미 포함돼 있다. AI 는 그 본문을 사용자 응답에 그대로 포함시켜 키 설정을 안내한다. 데이터 부재로 처리하지 않는다.
- **수치 제시 형식** — 동일 범주 수치 2개 이상 (시계열 · 종목비교 · 재무비율 세트 · grade 묶음) 은 markdown 표로 제시. 글머리 목록 나열 금지. 단일 값은 문장 속 인용. 직렬화 경로(`ai/tools/serialize.py`)는 `_formatNum` (SSOT: `ai/context/aiview.py`) 재사용으로 한국어 단위 포맷 (조/억/원/%/배). Polars DataFrame 은 **수동 GFM 빌드** (Polars ASCII 테이블 줄바꿈 버그 회피).
- **표 뒤 Reading Notes 의무** — 표 제시 후 `"이 표에서 읽을 포인트"` 3개 이하 bullet. 수치 자체 아닌 **변화·대비·의미**. `_yoy` 필드가 있으면 우선 인용. 예: ✗ "매출 14% 감소" ✓ "매출 14% 감소인데 영업이익률은 개선 → 마진 방어 성공".
- **청중 자동 판단** — 질문 어휘로 청중 수준 추정. 초보 신호("뭐야"·"설명")면 전문용어 첫 등장 시 괄호 풀이 필수. 전문가 신호(DCF·WACC·Z-score)면 풀이 생략. LLM 에게 프롬프트로 위임 (별도 분류기 신설 없음).
- **임계값 해석 가이드** — 재무비율 (Debt/EBITDA · 유동비율 · 부채비율 · ICR · PBR · ROE 등) 본문에 나오면 교과서 기준 한 줄 해석 덧붙임. 시스템 프롬프트에 기준 테이블 명시.
- **응답 포맷 ≠ audit 포맷** — `방향=중립/강도=보통/확신도=높음` 4척도 키=값 포맷은 **audit P/T/C/V 내부 평가 기준**이지 사용자 응답 포맷 아님. 응답은 자연스러운 한국어 판단문 1-2 문장. §11 audit 섹션에서만 4척도 사용.
- **인터리빙 서사 강제** — 한 라운드에 tool 1개만 호출. provider 가 parallel 로 여러 개 반환해도 `toolLoop` 과 `oauth_codex` 에서 `[:1]` 로 잘라 낸다. 시스템 프롬프트가 "결과 받으면 1-2 문장 코멘트 후 다음 tool" 을 명시. 사용자가 분석 과정을 따라올 수 있게 하는 게 목적.
- **Request-scoped Company 캐시** — `ai/runtime/companyCache.py` 가 ContextVar 기반 `{stockCode: Company}` dict 를 요청 시작·종료에 묶는다. `_companyHandler` 가 `getOrCreateCompany` 로 재사용 → 같은 종목을 여러 tool 이 조회해도 finance 매핑 1회. notebook / CLI 등 ctx 없는 경로는 기존 동작 유지.
- **scan 단일종목 금지** — `scan` 은 전종목 횡단 비교 전용. 단일 종목이면 `analysis` / `credit` / `show` / `quant` / `debt` / `capital` / `governance` 사용. schema description 과 시스템 프롬프트 양쪽에 명시.

**반복 실패** — dict 키 추측으로 KeyError / 추정값으로 수치 채우기 / 표 없이 bullet 나열 / scan 으로 단일 종목 조회.

---

## 11. AI Audit — 표준 10 질문 + 서버 경유로 간다

AI 응답 품질은 **사람이 실제 응답을 읽고 판단**하는 절차로 검증한다. 자동 메트릭(토큰/길이) 은 보조 지표.

### 표준 질문 세트 (dartlab 사상 전체 커버)

dartlab 은 종목만이 아니라 경제·섹터·시장·공시·메타 전 영역을 다룬다. audit 질문도 전 영역을 커버한다.

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

### 서버 경유 검증

실사용자 진입 경로는 landing/UI → `POST /api/ask`. 직접 `dartlab.ask()` 는 `server/api/ask.py` · `services/ai_analysis.run_plain_chat` · `streaming.stream_ask` · SSE · 요청 직렬화 · 미들웨어 레이어를 건너뛰기 때문에 해당 레이어의 직렬화 실패 · stream 중단 · tool_choice 매핑 · 상태 오염 같은 결함을 드러내지 못한다. 품질 검증은 서버 기동 후 `POST /api/ask` 로 호출한다.

```bash
uv run uvicorn dartlab.server:app --host 127.0.0.1 --port 8400
curl -X POST http://127.0.0.1:8400/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "삼성전자 수익성 분석해줘", "stream": false}'
```

stream 경로(`"stream": true` + SSE 수신)도 함께 검증한다. 서버 콘솔 로그의 tool failed / warning / traceback / import 실패 / provider 에러를 전수 확인한다.

### 결과 저장

질문별 응답 + 서버 로그 snippet + 판정 결과는 `data/audit/ai/{YYYY-MM-DD}/` 에 보존.

**반복 실패** — 직접 `dartlab.ask()` 호출로 audit 결론. 서버 레이어 결함 미탐지.

---

## 12. Provider — oauth-codex 를 audit 표준으로 간다

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

---

## 13. 폐기 히스토리

- **selfai 엔진** (few_shot/router/reflexion/output_validator) 2026-04-06 폐기.
  KnowledgeDB 영속성만 `ai/persistence/` 로 분리 보존.
- **Pre-grounding thread / ContextBuilder selectors** — 떠먹이기. 2026-04-13 완전 제거.
  경험 자산은 `pastInsight` / `sectorInsights` tool 로 AI 자율 조회.
- **dartlab.chat / c.reviewer** — 진입점 단일화 (P1). `dartlab.ask` / `c.ask` 로 통합.

---

## 14. 관련 코드

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

---

## 요약 — 명제 10 줄

1. 진입점은 `dartlab.ask(question)` 단일. Company-bound 는 `c.ask(query)`.
2. dartlab 사상은 6막 인과 (macro → scan/industry → Company → analysis → quant). Company 는 진입점 중 하나.
3. 4축 = CAPABILITIES 기반 · 시스템 프롬프트 주도 · AI 자율 개입(override) · 적극적 분석가.
4. 3 정보원천 = 엔진 tool · pastInsight/sectorInsights · web/news/search. AI 자율 조회.
5. override 로 엔진 가정 교체해 재호출 (FORECAST/VALUATION/ANALYSIS/CREDIT/QUANT/MACRO 키는 `core/overrides.py` SSOT).
6. P1~P8 운영 원칙. 특히 P8 — FINANCE 범주는 tool 최소 1회 경유 (3중 방어선).
7. 경험 자산화 — KnowledgeDB insights/bullets/executions + HF 동기화. 사람(블로그) + AI(응답) 공동 축적.
8. 해석 규칙 — dict 키 추측 금지 / None 존중 / 수치 2개↑ 표 + Reading Notes / scan 단일종목 금지.
9. audit 는 표준 10 질문 + 서버 경유 (`POST /api/ask`) 로 P/T/C/V 판정. 직접 `ask()` 호출 금지.
10. provider 는 oauth-codex 가 audit 표준. 기본 모델 선택은 audit 결과로.
