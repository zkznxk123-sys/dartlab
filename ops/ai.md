# AI

LLM 기반 적극적 분석가.
dartlab 엔진(analysis, scan, gather 등)은 AI가 호출하는 **도구**다.
AI는 이 도구를 조합해 질문에 최적화된 분석 흐름을 스스로 설계하고,
실행 과정(코드 + 결과)을 사용자에게 투명하게 보여줘서
사용자가 분석 방법 자체를 학습할 수 있게 돕는다.

## 호출 계약

```python
import dartlab
dartlab.ask("삼성전자 수익성 분석해줘")    # 자연어 → AI 가 도구 자동 선택
dartlab.chat("005930", "배당 추세는?")     # Company-bound
```

## 노트북

[![marimo](https://marimo.io/shield.svg)](https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo/09_ai.py)
[![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/09_ai.ipynb)

---

| 항목 | 내용 |
|------|------|
| 레이어 | L3 |
| 진입점 | `dartlab.ask()`, `dartlab.chat()`, `c.reviewer()` |
| 소비 | analysis, macro, scan, gather, review, Company 전체 |
| 생산 | 사용자에게 해석 + 재현 가능한 코드 제공 |
| provider | gemini, groq, cerebras, mistral, openai, ollama |

## 설계 원칙

- **AI가 분석의 전 과정을 주도** — 데이터 수집, 계산, 판단, 해석, 보고서까지 AI가 수행
- dartlab 엔진은 AI가 호출하는 도구 — AI가 도구를 조합해서 질문에 최적화된 흐름을 스스로 설계
- **CAPABILITIES-Driven**: 코드블록 자동실행. 데이터는 코드가 가져온다.
- **사용자 학습 지원** — AI가 실행하는 코드와 결과를 투명하게 보여준다. 사용자는 답만 얻는 게 아니라 분석 방법을 배운다.
- **함수 제공** — 사용자가 직접 실행할 수 있는 코드를 적극 제공한다. "이렇게 하면 됩니다"가 아니라 "이 코드를 실행하세요"다.
- **모든 provider에서 기본 기능 동작** — 도구 호출 불가 시 코드 실행으로 보충
- defaultProvider 기본 = 없음

## Provider

**무료 API 키 provider:**

| Provider | 무료 티어 | 모델 |
|----------|-----------|-------|
| `gemini` | Gemini 2.5 Pro/Flash | Gemini 2.5 |
| `groq` | 6K-30K TPM | LLaMA 3.3 70B |
| `cerebras` | 1M tokens/day | LLaMA 3.3 70B |
| `mistral` | 1B tokens/month | Mistral Small |

**유료/기타:**

| Provider | 인증 | Tool Calling |
|----------|------|:---:|
| `openai` | API key | O |
| `ollama` | 로컬 | 모델 의존 |

### Ollama 권장 모델 (AI audit 기반 결정)

| 모델 | VRAM | Tool Calling | Context | dartlab audit | 권장 |
|------|------|:---:|------|------|------|
| Gemma 4 E4B | 6GB | 네이티브 | 128K | ⏳ audit 대기 | ⏳ |
| Gemma 4 31B Dense | 20GB+ | 네이티브 | 256K | ⏳ audit 대기 | ⏳ |
| Qwen 3.5 27B | 16GB+ | O | 128K | ⏳ audit 대기 | ⏳ |
| Llama 4 Scout | 16GB+ | O | 10M | ⏳ audit 대기 | ⏳ |

> **벤치마크 숫자로 기본 모델을 정하지 않는다.**
> 각 모델로 dartlab AI audit 30개 질문 실행 → G/P/C/V 등급 비교 → 충분한 품질이 나오는 모델만 권장.
> 벤치마크 #3 이어도 재무분석 + 6막 서사 + tool calling 이 잘 안 되면 권장 불가.

## API

```python
dartlab.ask("삼성전자 재무건전성 분석해줘")
dartlab.ask("분석", provider="openai", model="gpt-4o")
dartlab.chat("005930", "배당 추세를 분석하고 이상 징후를 찾아줘")
```

## Spec 관리 체계

- 각 엔진 폴더에 `spec.py` — 해당 엔진의 메타데이터 선언
- `ai/spec.py` — 총괄 수집기, 각 엔진 spec 합산
- 코드에서 자동 추출 — 수동 동기화 불필요
- `test_spec_integrity.py` — CI에서 spec-코드 불일치 검증
- `/api/spec` 엔드포인트로 MCP/외부 클라이언트도 사용 가능

## AI 분석 능력

### 도구 선택 (60+ 질문 검증)
- **개별 기업 분석**: review/analysis 축 정확 매칭 (1회 성공)
- **매크로 환경 질문**: `dartlab.macro("축")` — 시장 레벨 매크로 해석 (Company 불필요)
- **시장 비교/순위**: scan 단일 축 + filter
- **데이터 직접 조회**: show/select (배당, 매출 추이, 주석 등)
- **주석 상세**: c.show("inventory" / "borrowings" / "tangibleAsset" 등 12항목)
- **실시간 이슈**: newsSearch + gather("news") 교차 검증
- **웹서치 자발 사용**: 분석 부족 시 자동으로 newsSearch/webSearch 보충

### 데이터 품질
- **마크다운 테이블 출력**: Polars 유니코드 → GFM 마크다운 자동 변환
- **원본 데이터 투명 제공**: 결과를 숨기지 않고 사용자에게 그대로 보여줌
- **analysis notes enrichment**: 자산구조/비용구조에 주석 상세 포함

### 성능
- **calc 캐시 공유**: @memoized_calc 120개 함수. analysis↔review 중복 계산 제거
  - 가치평가: 4초→0.09초 (97%↓), 매출전망: 1.5초→0.07초 (95%↓)
- **review 최대 3개 제한**: 타임아웃(60초) 방지
- **느린 축 회피**: 투자효율/가치평가/매출전망은 필요시만

### 해석 품질
- **축 정확 매칭**: "비용구조" → analysis("financial", "비용구조") (다른 축 조합 금지)
- **scan 결과 AI 판단**: 하드코딩 필터 없이 기저효과/이상치를 해석으로 설명
- **교차 검증**: 재무 + 뉴스, IS + CF + BS, notes + analysis 조합

## KnowledgeDB — 자기성장형 단일 DB

AI가 분석할수록 똑똑해지는 영속성 지식 저장소.

| 항목 | 내용 |
|------|------|
| DB 위치 | `~/.dartlab/dartlab_knowledge.db` (SQLite, WAL) |
| 공유 경로 | `data/ai/knowledge/*.json` → HF `ai/knowledge/` |
| 프라이버시 | executions(개인 질문 이력)는 push/pull 대상 아님 |

### 5테이블 구조

| 테이블 | 용도 | 공유 | 소스 |
|--------|------|:----:|------|
| executions | 모든 AI 실행 기록 (질문, 결과, 등급) | X | 실시간 축적 |
| skills | 성공한 코드 패턴 (few-shot) | O | 코드 실행 성공 시 |
| error_patterns | 에러 패턴 + 복구 코드 | O | 코드 실행 에러 시 |
| insights | 기업별 심층 분석 서사 | O | audit + 실시간 분석 |
| meta | DB 버전, 마이그레이션 상태 | - | 내부 |

### 자기성장 루프

```
분석 질문 →
  1. 인사이트 주입 (get_insight → 이전 분석 경험)
     └→ 없으면 동종업계 교차 학습 (get_sector_insights)
  2. Few-shot 주입 (skills 테이블 → 성공 코드 예시)
  3. LLM + 코드 실행
  4. 에러 시 → error_patterns 검색 → 복구 힌트 피드백
  5. 성공 시 → skills에 코드 패턴 저장
  6. 분석 완료 → insights 갱신 (강점/약점/서사 자동 추출)
```

### 코딩 모드

"코드 짜줘" 감지 시 전용 시스템 프롬프트 적용:
- 분석 모드: 코드 실행 → 결과 해석 → 서사
- 코딩 모드: 완전한 독립 실행 코드 → 실행 검증 → 복사-붙여넣기 코드 제공

### HF 동기화

```python
from dartlab.ai.persistence import KnowledgeDB

db = KnowledgeDB.get()
db.push(token="hf_xxx")  # insights/skills/errors → HF
db.pull()                  # HF → 로컬 DB merge (upsert)
```

- push: `data/ai/knowledge/*.json`에 export → HF upload
- pull: HF → `data/ai/knowledge/` → 로컬 DB merge
- 자동 pull: DB 비어있으면 싱글턴 초기화 시 자동 시도
- 실패 시 무시 (AI 기본 동작에 영향 없음)

### 안전장치

- 모든 KnowledgeDB 접근은 `try/except (ImportError, OSError)` 래핑
- DB 접근 실패 시 AI는 인사이트 없이 정상 동작 (graceful degradation)
- insightHints 최대 500자 (프롬프트 토큰 절약)
- 인사이트 90일 만료 시 경고 태그 부착
- HF pull 실패 시 로컬 JSON fallback → 그것도 없으면 무시

## Audit

- 저장: `data/dart/auditAi/`
- AI audit = dartlab 최종 레이어 품질 검증
- 모든 하위 엔진(Company, sections, notes, analysis, scan, gather) 문제가 여기서 표면화
- 실행 → 분류(P/T/C/V) → 수정 → 재실행 → 기록
- auditAnalysis 마크다운 → KnowledgeDB insights 테이블로 자동 파싱 (마이그레이션 시)

## ContextBuilder + ACE Playbook (2026-04-09 도입)

prompt engineering → **context engineering** 전환. ACE (Agentic Context Engineering, ICLR 2026) 패턴 적용.
arxiv.org/abs/2510.04618 — Generator/Reflector/Curator 폐쇄 루프 + delta merge.

### 활성화

**기본 ON** (2026-04-09 병합). ContextBuilder가 userParts를 조립하고 응답 종료 후 Curator가 playbook을 갱신한다.

A/B 검증: v2 응답 풍부도 **+31.6%** (적정PER +618%, 사업구성 +333%), 10/10 성공, 에러 0.

legacy 강제 복원: `DARTLAB_CONTEXT_V1=1` (디버깅 전용).

### 구조

```
ai/context/
├── intent.py         # 8 Intent 결정론 분류기 (act1~6 + compare + concept)
├── encoder.py        # TOON 인코딩 (큰 표는 ~60% 토큰 절감)
├── budget.py         # 11 provider 토큰 한도 + 우선순위 트리밍
├── bundle.py         # ContextPart + PartPriority + ContextBundle
├── builder.py        # ContextBuilder 메인 진입점
├── playbook.py       # ACE Reflector(extractBullets) + Curator(curate) + retrieveBullets
└── selectors/
    ├── legacy.py     # 기존 5 pre-grounding 헬퍼 래퍼
    └── playbook.py   # bullets → ContextPart HIGH 주입
```

### ACE 폐쇄 루프

```
Question
  → ContextBuilder.build()
       intent 분류 → selectors 호출 → budget 트리밍
       playbook bullets retrieval (intent + sector)
  → Generator (ai/runtime/_streamWithCodeExecution)
  → Reflector (extractBullets — 결정론 regex)
       응답 텍스트 → "결론:", "핵심:", "- bullet" 패턴 추출
  → Curator (curate → KnowledgeDB.upsert_bullet)
       grade(G/P→success, C/V→fail, T→neutral)에 따라 카운트 갱신
       delta merge: 신규는 INSERT, 중복은 카운트만 (UNIQUE intent+sector+bullet)
       quality = Beta posterior 근사 (success+1)/(success+fail+2)
  → 다음 호출 시 retrieveBullets가 quality desc로 top-N 주입
```

### selfai 폐기 학습 적용

- LLM Reflector 사용 X (페이퍼는 LLM 사용) — 결정론 regex만
- 자동 진화 X — 모든 selector는 명시적 코드
- KnowledgeDB와 SQLite 위에 얇은 레이어 — 디버깅 가능, 토큰 비용 0
- bullet 절대 삭제 X (context collapse 방지)

### 검증 (2026-04-09)

- intent 분류: **30/30 (100%)**
- TOON 토큰 절감: 평균 **+59%** (균질 표 데이터에서 +63%까지)
- KnowledgeDB delta merge: 같은 bullet 5회 호출 시 row 1개, success/fail 카운트만 갱신
- ContextBuilder 통합: bullets가 `ace.playbook` key로 HIGH 우선순위 주입
- 회귀: test_ai_runtime 77 + test_ai_context 28 + test_ai_context_playbook 27 = **132 PASS**

### Phase 1.5 완료 (2026-04-09)

- selectors/act1~6.py — 분석 calc 결과를 intent별로 선택 주입 ✅
- A/B 평가: 10질문 × v1/v2, **+31.6%** 응답 풍부도 ✅
- Phase 2 Graph — 인과 질문 9/9 graph 주입 ✅
- **기본 ON으로 병합** — feature flag 제거 ✅

## AIView — 정량 데이터 맥락 보강 (2026-04-10 도입)

엔진 calc 결과(dict/DataFrame)를 AI가 **이해**하기 좋은 형태로 자동 변환하는 공통 레이어.

### 문제

AI에게 `영업이익률 13.07%`만 주면 "숫자"는 보지만 "의미"를 모른다.
- 업종 평균 대비 높은지 낮은지?
- 전기 대비 개선인지 악화인지?
- 5년 평균 대비 어느 위치인지?

### 해법

calc 결과 → **autoEnrich()** → encodeAuto(TOON) → LLM

모든 엔진의 반환값을 **구조 자동 감지**로 보강. 엔진별 수작업 0.

| 패턴 | 감지 기준 | 보강 내용 |
|------|----------|----------|
| dict + `history[]` | `"history" in data` | 비율 필드 우선, 5년 평균, YoY(pp/%), 변화 판단 |
| 중첩 history | `v["history"]` in sub-dict | 각 서브키별 요약 생성 |
| flat dict | 숫자 키 존재 | 필드별 포맷 + 요약 |

### 2단계 판별: 독스트링 확정 → 자동 감지 fallback

1. **독스트링 스키마 (확정)**: `parseReturnsSchema(calc_fn)` → docstring의 Returns 섹션에서 `키 : 타입 — 설명 (단위)` 파싱. `(%)` → 비율, `(원)` → 금액, `(일)` → 일수 확정.
2. **자동 감지 (fallback)**: 독스트링이 없는 함수에서 필드명(`margin`, `roe`) + 값 범위로 추측
3. **비율은 pp 차이, 금액은 변화율(%)**: `영업이익률 +2.2pp` vs `매출 +10.9%`
4. **비율 필드 우선 표시**: AI에게 비율이 금액보다 informative

### 독스트링 → AI 체인

```
calc 함수 docstring (Returns 표준화: 키:타입—설명(단위))
  ↓
parseReturnsSchema(fn) — 런타임 docstring 파싱, LRU 캐시
  ↓  {"operatingMargin": {"type": "float", "unit": "%", "desc": "영업이익률"}}
_calcToContextPart() [selectors/_calc_base.py]
  ↓
autoEnrich(data, company=company, calc_fn=fn) — 스키마 기반 확정 보강
  ↓  _summary: "영업이익률 13.1% · 전기비 +2.2pp(소폭 개선) · 5년평균 위 1.2pp"
encodeAuto(enriched) → TOON
  ↓
ContextPart → LLM
```

**모든 selector(act1~6, compare)가 자동 적용** — _calcToContextPart 한 곳만 수정.
**새 calc 함수를 추가해도**: docstring에 Returns만 쓰면 체인 자동 완성.

### 독스트링 Returns 표준 규칙 (ops/code.md 연동)

```
Returns
-------
dict
    history : list[dict]
        period : str — 기간
        operatingMargin : float — 영업이익률 (%)    ← (%) = 비율 확정
        revenue : float — 매출 (원)                 ← (원) = 금액 확정
        dso : float — 매출채권회수일 (일)            ← (일) = 일수 확정
```

141개 analysis calc + 12개 Company/dartlab 공개 API에 적용 완료.

### 실측 (실험 110, 삼성전자 수익성)

| 항목 | A (raw) | B (enriched) |
|------|---------|-------------|
| 응답 길이 | 3,339자 | **1,141자** |
| 코드 실행 | 2라운드 | **0라운드** |
| 판단 | "좋아지는 중" (모호) | "좋다, 역대 최고는 아닌 회복" (명확) |
| 비교 맥락 | 없음 | 5년 평균 +1.2pp, 상위 79.9% |

### 학술 근거

- Kim et al. (시카고대, 2024): 재무제표 + CoT → 이익 방향 60% (인간 53-57% 초과)
- TAP4LLM (EMNLP 2024): 서브테이블 + 보강 → +7.93%p
- FinSheet-Bench (2026): "결정론적 계산과 LLM 해석을 분리하는 아키텍처 필요"

### 확장성

엔진이 새 축을 추가해도 `history + period + 숫자` 패턴만 유지하면 autoEnrich가 자동 적용.
scan 업종 백분위 조회도 company가 있으면 자동.

## 관련 코드

- `src/dartlab/ai/context/aiview.py` — autoEnrich 공통 변환 레이어
- `src/dartlab/ai/context/` — Phase 1: ContextBuilder + ACE 폐쇄 루프 (intent/encoder/budget/builder/playbook/selectors)
- `src/dartlab/ai/` — providers, tools, runtime, memory, persistence, conversation
- `src/dartlab/ai/runtime/core.py` — 시스템 프롬프트, 코드 실행, 마크다운 변환, 인사이트 주입, preGround 백그라운드 thread
- `src/dartlab/ai/persistence/knowledge_db.py` — 단일 영속 DB (CRUD + 마이그레이션 + HF push/pull). selfai 폐기 후 영속성만 분리 보존
- `src/dartlab/ai/persistence/__init__.py` — KnowledgeDB re-export
- `src/dartlab/ai/memory/store.py` — analyze() 결과 저장 wrapper (KnowledgeDB 위임)
- `src/dartlab/cli/stdio.py` — `_handleWarmup` 으로 KnowledgeDB init 사전 지불
- `src/dartlab/analysis/financial/_memoize.py` — calc 캐시 데코레이터

> selfai 엔진 (few_shot/router/reflexion/output_validator) 은 2026-04-06 폐기됨.
> KnowledgeDB 영속성만 `ai/persistence/` 로 분리하여 보존.
