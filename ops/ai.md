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

```bash
DARTLAB_CONTEXT_V2=1 python -m dartlab ask "..."
```

기본은 OFF (legacy 동작). v2 ON 시 ContextBuilder가 userParts를 조립하고 응답 종료 후 Curator가 playbook을 갱신한다.

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

### Phase 1.5 (다음)

- selectors/act1~6.py — 14축 calc 결과를 intent별로 선택 주입
- A/B 평가: audit 30종 재실행, ACE 페이퍼 finance +8.6% 재현 시도
- LLM Reflector 검토 (현재는 결정론 추출만)

## 관련 코드

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
