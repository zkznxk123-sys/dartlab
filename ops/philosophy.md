# Philosophy — dartlab 사상 SSOT

**주체**: dartlab 전체 라이브러리 — 엔진·블로그·AI·사람 공동 운영 철학.
**현재**: 사상이 `ops/company.md` · `ops/analysis.md` · `ops/skills.md` 에 분산되어 있던 것을 본 문서로 통합.
**방향**: 본 문서를 정점으로 `ops/coreloop.md` · `ops/skills.md` · `ops/story.md` 등 하위 문서는 구현 상세만 담는다.

이 문서는 dartlab 의 단일 진실의 원천 (SSOT) 이다. "왜 이 라이브러리가 존재하는가" 를 외부 기여자가 하나의 문서로 이해할 수 있어야 한다. 각 섹션은 **"이렇게 한다"** 명제로 열고, 반복된 실수는 섹션 하단 **"반복 실패"** 에 정리한다.

---

## §1. 사상 한 줄 — AI ↔ 사람 상호 의존, 엔진이 다리

dartlab 은 **AI 와 사람이 서로 돕는** 라이브러리다.

- 사람은 엔진·블로그·지식으로 자산을 만든다.
- 그 자산은 자동으로 AI 의 skill 이 된다 — 공개 함수 docstring 이 곧 AI tool schema 다.
- AI 가 실행 중 발견한 개선 (반복 패턴·반례·새 조합) 은 엔진 docstring·블로그 frontmatter 로 사람 자산에 환류한다.
- **엔진이 다리다.** 한 파일이 사람의 분석엔진이자 AI 의 skill 본문.

AI 가 사람을 보조하는 라이브러리가 아니다. 사람이 AI 를 쓰는 라이브러리도 아니다. **양쪽이 같은 엔진을 공유하며 서로 개선시킨다.**

**반복 실패** — AI 를 엔진의 소비자로 강등하거나, 사람을 AI 의 관객으로 강등하는 문서 기술. dartlab 은 양 주체 설계.

---

## §2. 존재 이유 — 비교 가능성 (시야 3 × 관점 6 격자)

dartlab 이 존재하는 단 하나의 이유는 **비교 가능성** 이다. 수치 하나를 제공하는 게 아니라, 수치의 **맥락 (격자 위치)** 을 제공한다.

### 시야 3 축 (WHAT — 무엇을 얼마나 넓게 보나)

| 시야 | 범위 | 예 |
|---|---|---|
| **회사** | 한 기업의 시계열 | 삼성전자 Q1~Q4 × 9 년 |
| **시장** | 한 시장 내 횡단 | 한국 전체 · 미국 전체 |
| **세계시장** | 시장 간 비교 | KR vs US vs JP |

시간축 (기간 비교) 은 각 시야에 내재한다.

### 관점 6 축 (HOW — 어떻게 다르게 보나)

| 관점 | 엔진 | 무엇을 보나 |
|---|---|---|
| **재무** | `analysis` | 재무제표 기반 수익성·성장성·현금·안정성 등 |
| **주가** | `quant` | OHLCV + 수급 + 기술적 지표 |
| **거시** | `macro` | 사이클·금리·유동성 |
| **신용** | `credit` | 등급·이력·플래그 |
| **산업** | `industry` | 밸류체인·공급망·산업지도 |
| **횡단면** | `scan` | 전종목 비교·순위 |

### 격자

18 격자 위에서 한 회사를 움직여 보는 것이 dartlab 의 유일 경쟁력이다.

| | 재무 | 주가 | 거시 | 신용 | 산업 | 횡단면 |
|---|---|---|---|---|---|---|
| 회사 | `c.analysis(...)` | `c.quant()` | `c.macro()` | `c.credit()` | `c.industry()` | — |
| 시장 | — | `dartlab.scan("quant")` | `dartlab.macro(market="KR")` | `dartlab.scan("credit")` | `dartlab.industry(sector="반도체")` | `dartlab.scan(axis)` |
| 세계시장 | — | 시장 간 quant 비교 | `dartlab.macro()` 글로벌 | 시장 간 credit 비교 | 글로벌 밸류체인 | 시장 간 scan 비교 |

(`c = dartlab.Company("005930")` — §3 참조)

비교 가능성은 이 격자의 **어느 칸끼리도 비교 가능** 한 것. "삼성전자 재무" 와 "KR 시장 재무 평균" 비교, "삼성전자 quant" 와 "삼성전자 재무" 괴리 비교 등 전부 격자 위의 이동.

**반복 실패** — "분석 자동화"·"재무 API"·"백테스트 엔진" 으로 dartlab 정체성 혼동. 이런 게 부산물일 뿐 존재 이유 아님.

---

## §3. 투톱 진입점 — `ask` 함수와 `Company` 클래스

사상의 핵심 UX. **AI 와 사람이 각자 최상위 진입점 하나만 기억하면 된다.**

```python
import dartlab

# AI 의 입구 — 일회성 질문 → 답 (함수·동사)
dartlab.ask("삼성전자 수익성 어때")

# 사람의 입구 — 회사 파사드 (클래스·명사)
c = dartlab.Company("005930")
c.story()                              # 읽는 분석 스토리 (보고서)
c.analysis("financial", "수익성")      # 재무
c.credit()                             # 신용
c.quant()                              # 주가
c.macro()                              # 매크로 민감도
c.industry()                           # 산업 맥락
c.show("매출액")                       # 원본
c.gather("news")                       # 뉴스
c.ask("자가 진단 해줘")                # 이 종목 AI 대화
```

Python 관례 준수: `ask` 는 동사·일회성·무상태 → **함수**. `Company` 는 명사·상태 보유 (stockCode · 캐시) → **클래스**. 역할과 사용 패턴이 다르므로 문법도 다르다.

### Company 는 사람의 만능 관문

Company 객체 하나로 모든 엔진 접근. 엔진 새로 추가되면 Company 에 메서드 추가만 하면 자동으로 사람 관문에 노출된다. 종목에 묶인 분석은 전부 `c.` 하나로.

### Company-독립 엔진은 module-level 직접 호출

특정 종목이 아닌 대상 (전종목·시장·섹터) 을 다루는 엔진은 module-level 함수로 제공:

```python
dartlab.scan(axis)                         # 전종목 횡단
dartlab.macro("사이클", market="KR")       # 한국 시장 사이클
dartlab.industry(sector="반도체")          # 반도체 섹터 밸류체인
```

이건 alias 가 아니다 — **Company 가 의미 없는 엔진** 과 **Company 가 의미 있는 엔진** 의 역할 분담. 같은 엔진이 두 경로를 동시에 갖지 않는다.

### 엔진 호출계약 일관성 — 같은 대상 = 같은 인자 이름

module-level 엔진의 대상 지정 파라미터 이름은 전수 통일:

| 대상 | 인자 이름 | 엔진 |
|---|---|---|
| 종목 | `stockCode` | `analysis` · `credit` · `quant` · `gather` · `show` |
| 섹터 | `sector` | `industry` |
| 시장 | `market` | `macro` |

종목 받는 엔진은 Company 객체 호환을 위해 `company=` 키워드도 수용 (객체 전달 시 내부에서 `stockCode` 로 변환). 새 코드는 `stockCode` 사용 권장.

### story = 보고서 빌더 (review 리네임)

`c.story()` 는 엔진 calc 를 블록으로 조립한 **사람이 읽는 분석 스토리**. 기존 review 의 이름만 리네임, 역할 유지 (보고서 빌더). `ops/analysis.md` 의 "회사는 스토리가 있다" 사상과 이름 매칭.

### `c.reviewer()` · `c.review()` · `dartlab.review` 폐기

AI 종합의견은 `dartlab.ask()` 일원화. `c.reviewer()` · `c.review()` · `dartlab.review` 모듈 전부 제거 — alias 는 두지 않는다 (일관성 규약, §5 참조).

**반복 실패** — `review` · `story` · `reviewer` · `ask` 난립 · 엔진마다 종목 지정 인자 이름 제각각 (`company=` · `stockCode=` · `code=` 혼재) · Company 와 중복되는 최상위 진입점 신설. 일관성 훼손.

---

## §4. 엔진 이중성 — 사람의 분석엔진 = AI 의 skill, docstring SSOT

**공개 함수 docstring 은 사람의 분석엔진 매뉴얼이면서 AI 의 skill 본문이다.** 한 파일이 두 역할을 하므로 SSOT 가 단일하다.

### 왜 별도 skill 파일이 없나

- **이중 관리 회피**. `scanRatio` 의 docstring 과 별도 `SKILL.md` 가 있으면 파라미터 하나 바꿔도 두 곳 동기화 — SSOT 위반.
- **AI 경로 단일화**. AI 는 tool schema description 을 이미 docstring 에서 자동 수집 (`src/dartlab/ai/tools/__init__.py::_toolDescription`).
- **사람 경로 단일화**. `help(scanRatio)` · IDE hover · Sphinx 문서 모두 같은 docstring 소비.

### docstring 이 skill 역할을 하기 위한 요건

- `ops/code.md` 의 9 섹션 규격: Summary · Description · Parameters · Returns · Raises · Examples · Notes · Guide · See Also.
- Guide 섹션에 다시 4 하위 블록: **When** (질문 트리거 어휘) · **How** (다른 축과 조합) · **Verified** (audit P 승격 이력 append 자리) · **Examples** (Guide 전용 실전).
- Parameters · Returns 는 단위 (%·원·배·일·점) 명시 필수.

상세: [`ops/skills.md`](skills.md) · [`ops/code.md`](code.md).

**반복 실패** — 로컬 에이전트 skill 파일 같은 이중 파일 잔존. docstring 과 별도 skill 문서가 나뉘어 있으면 곧 불일치. dartlab 에서 skill 은 오직 docstring.

---

## §5. 행동규약 — 편의성 + 신뢰성 + 일관성 (3 축)

dartlab 의 모든 설계·코드·문서·응답이 따르는 **3 축**.

### (1) 편의성 — 사용자 편의가 근본

대상: **AI 와 사람 양쪽**. 둘 다 dartlab 을 편리하게 써야 한다. 한쪽만 편해도 사상 위반.

| 규칙 | 내용 |
|---|---|
| ① | 단일 진입점 — AI 는 `ask`, 사람은 `Company` (종목코드 하나로 전 엔진 접근) |
| ② | tool 자동 등록 — 수동 dict 금지. `dartlab.__all__` + 공개 메서드 순회 |
| ③ | docstring 변경이 곧 AI skill 변경 — 별도 등록·재빌드 없음 |
| ④ | `c.story()` 로 보고서, `c.analysis()` · `c.credit()` · `c.quant()` 등으로 개별 엔진 — 전부 `c.` 하나로 |
| ⑤ | 에러 메시지는 해결책 포함 — "데이터 없음" ❌ → "데이터 없음 → `dartlab.gather('price', '005930')` 로 먼저 수집하세요" ✓ |
| ⑥ | API 키 필요 시 발급 URL + `.env` 설정법 함께 안내 |

### (2) 신뢰성 — 데이터 신뢰가 근본

대상: **데이터**. 원본이 거짓이면 모든 분석이 거짓이다.

| 규칙 | 내용 |
|---|---|
| ① | `None` = 데이터 없음 — 추정값·평균·가짜 숫자 금지 |
| ② | 응답 수치는 엔진 결과만 인용 — AI 재계산·반올림 조작 금지 |
| ③ | 원본 검증 권한 AI 에 부여 — `show` 원본 조회 · `overrides` 재호출 |
| ④ | 매핑·임계값·calibrated parameter 는 실험 검증 후만 반영 |
| ⑤ | `dataAsOf = {latestPeriod, retrievedAt}` 자동 주입 — "실시간" 오인 차단 |

### (3) 일관성 — 코드·API·명명 일관이 근본

대상: **코드 · API · 명명**. dartlab 은 alias 를 인정하지 않는다.

| 규칙 | 내용 |
|---|---|
| ① | **alias 금지** — 같은 기능에 두 이름 공존 금지 |
| ② | breaking change 는 일관성 확보를 위해 **수용** — deprecation 덕지덕지 배제 |
| ③ | 파생 심볼 (CLI · contextvar · 문자열 키 · 테이블 이름) 전수 통일 |
| ④ | 코드 · docstring · ops 문서 · 블로그 · SNS 에서 같은 개념은 같은 이름 |
| ⑤ | 새 이름 확정 시 구 이름 즉시 제거 — 과도기 없음 |

**반복 실패** — 편의성·신뢰성만 박고 일관성 축이 빠져 alias 공존 허용 (`c.review` + `c.story`, `c.reviewer` + `ask` 같은 중복), 파생 심볼 불일치 (코드는 영문·문서는 한글 등), breaking change 를 deprecation 으로 무한 미룸.

---

## §6. 양방향 자가개선 루프 5 Phase (dartlab 고유 O/P/R/F/A)

사람과 AI 가 서로 개선하는 매커니즘. **운영 상세는 [`ops/coreloop.md`](coreloop.md) SSOT**. 본 섹션은 명제만.

| Phase | 이름 | 한 줄 명제 |
|---|---|---|
| **O** | Observe (실험) | 실사용 질문·tool 호출·응답·에러를 `data/audit/ai-ask/YYYY-MM-DD.jsonl` 에 기록 |
| **P** | Pattern (후보 감지) | 동일 `(category, tool_sequence)` N 회 성공 → docstring Guide append 초안 생성 |
| **R** | Promote (승격) | 사용자 `--confirm` → `skill/docstring-*` 브랜치 PR → CODEOWNERS 리뷰 merge |
| **F** | Refine (자가 개선) | AI 가 반례·엣지케이스 발견 → docstring "Caveats" 섹션 추가 PR |
| **A** | Axis (엔진 승격) | 반복 조합 M 회·30 일 숙성 → 공식 엔진 axis 신설 (수동 판단) |

### 양방향

- **사람 → AI**: 엔진 작성·docstring 갱신·블로그 frontmatter `ai:` 블록 작성 → 자동으로 AI 자산. docstring 은 tool schema 로, frontmatter 는 `insights(source="blog")` 로.
- **AI → 사람**: 실행 중 발견한 반복 성공 패턴 (Phase P) · 반례 (Phase F) · 승격 가능 조합 (Phase A) → GitHub PR 로 사람 검토 대기. 자동 merge 금지, 사람 승인 필수.

두 방향 모두 **엔진 docstring 파일 하나** 가 다리. SSOT 단일.

### 자동화 로드맵

초기 전부 수동 (사용자가 주 1 회 `dartlab-coreloop pattern` 실행) → 3 개월 안정화 후 nightly cron 으로 candidate 감지만 자동화 → 6 개월 이상 사이클 clean 유지 시 tier 1 (Guide 섹션 append 만) PR 자동 생성 (merge 는 계속 수동).

**반복 실패** — Phase A 를 자동화 (엔진 axis 를 코드 생성). 이건 사상 수준 결정이라 수동 강제.

---

## §7. 3 정보층 구조 — L-public · L-local · L-memory

dartlab 의 정보는 **3 층** 에 배치된다. 중복 금지.

| 층 | 위치 | 공개 | 내용 |
|---|---|---|---|
| **L-public** | `ops/*.md` · `src/` · `README.md` · `blog/` · `landing/` · `notebooks/` · `docs/` · `sns/` | GitHub 공개 | 사상 · 설계 · 계약 · 코드 (재현 가능한 원본) |
| **L-local** | 로컬 agent 규칙 · 세션 계획 · 작업 메모 · agent 전용 디렉토리 | gitignored, 로컬만 | 강행규칙 · 세션 규약 · 환경 (운영자 작업 상태) |
| **L-memory** | 프로젝트 디렉토리 외부 (운영자 홈) | 프로젝트 외부 | 운영자 ↔ AI 약속 · 세션 간 사실 |

### 판정 규칙

- "외부 기여자가 읽을 이유가 있나?" 예 → **L-public**.
- "세션·환경 규약인가?" 예 → **L-local**.
- "운영자와의 약속·판정 기준인가?" 예 → **L-memory**.

### 중복이 발생하면

동일 내용 두 곳 발견 시 **즉시 SSOT 한 곳에만 두고 나머지는 포인터 (한 줄 링크)** 로 교체.

**반복 실패** — L-local 파일을 git 에 섞어 커밋하면 운영자의 작업 메모가 노출됨. L-memory 를 repo 내부로 당김. L-public 문서에 운영자↔AI 인용 ("사용자 원문: > ...") 을 박음 — 이건 L-memory 내용.

---

## §8. 현재 구현 매핑 — 사상 → 코드 파일 경로

사상을 뒷받침하는 **실제 구현 문장** 13 개. 외부 기여자가 사상이 코드 어디에 박혀있는지 찾을 수 있게.

1. **tool 자동 등록** — `src/dartlab/ai/tools/__init__.py::_autoDiscover` 가 `dartlab.__all__` + Company 공개 메서드 순회 후 `_BLACKLIST` 필터로 tool 자동 등록. 수동 dict 금지.

2. **docstring → AI skill 변환** — 공개 함수 docstring 의 Summary + Returns 는 `src/dartlab/ai/tools/__init__.py::_toolDescription` 에서 tool schema description 으로 자동 변환. docstring 변경 시 별도 등록 없이 AI 가 즉시 개선된 skill 사용.

3. **override 표준 — AI ↔ 엔진 다리** — `src/dartlab/core/overrides.py` 의 `FORECAST_KEYS` · `VALUATION_KEYS` · `ANALYSIS_KEYS` · `CREDIT_KEYS` · `QUANT_KEYS` · `MACRO_KEYS` + `describeOverrides()` + `detectExtremeFlags()` 가 AI 의 엔진 가정 교체·재호출 매커니즘.

4. **Phase O audit 로그 (실험)** — `src/dartlab/server/streaming.py::_AuditCollector` (향후 `src/dartlab/ai/runtime/audit.py` 로 이관) 가 `POST /api/ask` 요청마다 `data/audit/ai-ask/YYYY-MM-DD.jsonl` 에 자동 append. 서버 재시작에도 누적.

5. **post-response 3 종 학습** — 매 응답 종료 시 `runPostResponse()` 가 자동 실행: `save_execution()` (질문·응답·tool 호출 기록), `saveInsightFromResponse()` (regex 로 strengths/weaknesses/narrative 추출), `curate()` (ACE bullet Beta posterior delta merge).

6. **HF 동기화 범위** — `src/dartlab/ai/persistence/knowledge_db.py::export_shared()` 는 `insights` · `playbook` 만 `data/ai/knowledge/` 에 JSON export 후 HuggingFace 로 push. `executions` 는 개인 질문 이력이라 제외.

7. **경험 자산 READ 경로** — AI 는 `src/dartlab/ai/insights.py::pastInsight(stockCode)` 와 `sectorInsights(sector)` 를 자동 등록된 tool 로 자율 호출. 블로그 (source="blog") 우선, 없으면 audit/live fallback.

8. **사람 → AI 흡수** — `src/dartlab/ai/persistence/knowledge_db.py::_migrate_audit_analysis` 가 `data/dart/auditAnalysis/*.md` (사람 수동 작성) 를 `insights(source="audit")` 로 1 회 흡수. 이후 `pastInsight()` 가 자동 조회.

9. **AI 진입점 단일화** — `src/dartlab/ai/runtime/standalone.py::ask` 단일. Company-bound 는 `c.ask(query)`. `dartlab.chat` · `c.reviewer` 는 폐기.

10. **신뢰성 규약 — P8 (FINANCE 범주 tool zero 방지)** — 금융 질문에 tool 미호출 응답을 막는 3 중 방어: `src/dartlab/ai/runtime/core.py::_buildCategoryBlock` (프롬프트) · `src/dartlab/ai/runtime/toolLoop.py::_resolveToolChoice` (`tool_choice='any'`) · `streamWithTools` 재질문 가드.

11. **Request-scoped Company 캐시** — `src/dartlab/ai/runtime/companyCache.py` 의 ContextVar 가 `{stockCode: Company}` dict 를 요청 경계에 묶는다. 한 요청 안 같은 종목 tool 이 여러 개여도 finance 매핑 1 회 (메모리 폭발 완화).

12. **병렬 tool 허용 (한 라운드 최대 4 개)** — `src/dartlab/ai/runtime/toolLoop.py` 의 `_MAX_PARALLEL_TOOLS = 4` 가 한 라운드 최대 4 개까지 병렬 호출을 허용. 같은 라운드 내 순차 실행 (threading 병렬 아님) → Company 캐시 공유로 메모리 안전. 복합 분석 (3+ 엔진 조합) 은 `pythonExec` 으로 한 번에 모아 실행도 가능. `maxRounds=10` 유지하되 실효 처리량 10→30~40 tool. (이전: `tool_calls[:1]` 인터리빙 강제 — 2026-04-25 까지)

13. **dataAsOf 주입** — `src/dartlab/ai/context/aiview.py::autoEnrich` 가 tool_result 에 `dataAsOf = {latestPeriod, retrievedAt}` · `_summary` · `_flags` · `assumptions` 를 자동 주입. AI 는 그 값을 응답에 인용.

---

## §9. 운영 규약 요약

### 사상 위반 시 merge 반려

PR 이 §5 의 3 축 (편의성 · 신뢰성 · 일관성) 중 하나라도 위반하면 merge 반려:

- 편의성 위반: alias 인 척 여러 진입점 신설, "데이터 없음" 에러를 해결책 없이 던짐.
- 신뢰성 위반: 추정값으로 `None` 채우기, 엔진 결과를 AI 가 임의 재계산.
- 일관성 위반: 새 이름 도입하며 구 이름 유지, 파생 심볼 (CLI · 문자열 키 · 테이블) 불일치.

### 문서 경계

- 본 문서 (**philosophy.md**) — 사상 SSOT.
- [`ops/coreloop.md`](coreloop.md) — 자가개선 루프 Phase O/P/R/F/A 운영 상세.
- [`ops/skills.md`](skills.md) — AI/MCP 공용 skill resolver · SkillSpec 규약.
- [`ops/story.md`](story.md) — story 보고서 빌더.
- [`ops/architecture.md`](architecture.md) — L0~L4 레이어 · import 방향.
- [`ops/code.md`](code.md) — docstring 9 섹션 규격 · 코드 품질 · 릴리즈.
- [`ops/api-contract.md`](api-contract.md) — 공개 API 추가 규칙 · 폐기 정책.

### 중복 금지

| 내용 | SSOT | 다른 곳에서는 |
|---|---|---|
| 사상 한 줄 | philosophy.md §1 | 요약 1 줄 + 링크 |
| 시야 × 관점 격자 | philosophy.md §2 | 링크만 |
| 3 축 행동규약 | philosophy.md §5 | 링크만 |
| 5 Phase 명제 | philosophy.md §6 + coreloop.md 상세 | 다른 곳은 "coreloop.md 참조" |
| docstring 9 섹션 규격 | code.md | skills.md 는 참조만 |
| override 키 목록 | `src/dartlab/core/overrides.py` | 문서는 참조만 |
| AI/MCP skill 체계 | `ops/skills.md` + `src/dartlab/skills` | 다른 곳은 한 줄 언급만 |
| 3 정보층 경계 | philosophy.md §7 | 다른 곳은 요약 + 링크 |

**반복 실패** — 사상 섹션과 AI 설계서, skills 문서에 같은 내용 중복 기술. 수정 시 여러 곳 동시 갱신 강요. 본 문서를 정점으로 통합.

---

## 부록 A. 관련 문서 트리

```
ops/
├── philosophy.md       [SSOT · 정점]  ← 본 문서
├── coreloop.md         [자가개선 루프 운영 SSOT]
├── ai.md               [AI 엔진 구현]
├── skills.md           [docstring = skill 규약]
├── story.md            [story 보고서 빌더]
├── architecture.md     [레이어 · import]
├── code.md             [9 섹션 · 품질]
├── api-contract.md     [공개 API]
├── analysis.md · credit.md · quant.md · macro.md · industry.md · scan.md · gather.md
│                       [엔진별 상세]
├── edgar.md · mcp.md · search.md
│                       [외부 시스템 연동]
├── data.md · mappers.md · testing.md · experiments.md · issues.md
│                       [데이터 · 테스트 · 이슈]
├── engineAudit.md      [엔진 결과 검증]
└── channel.md · dashboard.md · notebooks.md · pyodide.md · spaces.md · ui.md · viz.md · vscode.md · quantWorldClass.md
                        [인프라 · 콘텐츠]
```

---

## 부록 B. 폐기·흡수 히스토리

- **`dartlab.chat` · `c.reviewer` 폐기** — AI 진입점 단일화 (`dartlab.ask` 로 통합, 2026-04-06).
- **Pre-grounding thread · ContextBuilder selectors 제거** — "떠먹이기" 배제, AI 자율 판단 공간 보존 (2026-04-13). 경험 자산은 `pastInsight` · `sectorInsights` tool 로 AI 자율 조회.
- **`skills/` 디렉토리 · `SKILL.md` 파일 폐지** — docstring SSOT 확정 (2026-04-24). dartlab 에서 skill 은 엔진 docstring 이 담는다.
- **`review` → `story` 전수 리네임, `c.reviewer()` 제거** — 사상 일치 (회사 = 스토리, 6 막 인과) · 일관성 규약 · AI/사람 투톱 대칭 확립.
