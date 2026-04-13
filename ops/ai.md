# AI

**dartlab을 대표하는 적극적 분석가. 엔진은 도구, AI가 주체자.**

엔진 결과를 읽어주는 낭독기가 아니다. **모든 분석에 개입한다.**
- 분석 엔진을 직접 호출하고, 결과를 의심하고, 원본 재무제표(`c.show`)로 직접 계산하여 검증한다.
- 엔진이 문제가 있으면 원본을 보고 직접 비율을 계산한다.
- 가정이 비현실적이면 override로 재계산하여 비교한다.
- audit 시에는 엔진/데이터 개선을 제안한다.
- 실행 과정(코드 + 결과)을 사용자에게 투명하게 보여줘서 사용자가 분석 방법을 배운다.

### review와의 관계

**AI는 `c.review()`를 직접 호출하지 않는다.** 83초 타임아웃 + AI가 review의 낭독기가 되면 안 된다.

대신 **review의 보고서 타입(11종)을 참고**하여 분석 관점을 잡는다:
- "신용 관점에서 봐줘" → review credit 타입의 블록 조합(안정성/현금/자금/등급) 참고
- "성장주로 봐줘" → review growth 타입(CAGR/마진확장/투자효율) 참고
- "위기 진단해줘" → review crisis 타입(부실/레버리지/유동성) 참고
- 참고하되 **AI 자신의 주관으로 판단**한다. review 결과를 그대로 읽지 않는다.

AI가 엔진을 쓸 때는 AI가 주체자:
- `c.analysis("수익성")` → AI가 직접 판단하고 해석
- `c.show("IS", freq="Y")` → AI가 직접 원본 계산하여 검증
- `dartlab.scan("profitability")` → AI가 직접 업종 위치 확인
- `c.analysis("가치평가", overrides={"wacc": 9.0})` → AI가 가정 조정 후 재계산

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

- **AI는 dartlab을 대표하는 적극적 분석가** — 엔진 결과를 읽어주는 게 아니라, 직접 판단하고 검증하고 개입한다.
- **모든 분석에 개입** — 엔진이 계산한 결과를 맹신하지 않는다. 원본 재무제표로 직접 비율을 계산하여 교차 검증한다.
- **이상 시 직접 행동** — 가정이 비현실적이면 override로 재계산. 데이터가 이상하면 원본(`c.show`)을 파고든다.
- **audit 시 개선 제안** — 엔진/데이터의 문제를 발견하면 구체적 개선안을 제시한다.
- dartlab 엔진(analysis, scan, gather, macro, credit, quant)은 AI의 **도구** — AI가 조합해서 질문에 최적화된 흐름을 설계.
- **CAPABILITIES-Driven**: 코드블록 자동실행. 데이터는 코드가 가져온다.
- **사용자 학습 지원** — AI가 실행하는 코드와 결과를 투명하게 보여준다.
- **모든 provider에서 기본 기능 동작** — 도구 호출 불가 시 코드 실행으로 보충
- defaultProvider 기본 = 없음

## Provider

**API 키 provider:**

| Provider | 모델 |
|----------|-------|
| `gemini` | Gemini 2.5 Pro/Flash |
| `groq` | LLaMA 3.3 70B |
| `cerebras` | LLaMA 3.3 70B |
| `mistral` | Mistral Small |

**기타:**

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

## AI Audit 체계

> AI를 실제로 돌려서 응답 품질을 직접 확인 → 문제 발견 → 시스템 프롬프트/코드 수정 → 재실행.
> review audit이 데이터/엔진 품질을 잡는다면, AI audit은 **AI가 그 엔진을 제대로 쓰는지** 잡는다.

### 핵심 원칙

- **AI audit = 사람이 AI 응답을 읽고 판단.** 자동 메트릭(토큰/길이)만으로 품질 주장 금지.
- **provider = oauth-codex** (GPT OAuth). gemini 아님.
- 모든 하위 엔진(Company, sections, notes, analysis, scan, gather) 문제가 여기서 표면화.

### 파이프라인

```
1단계: AI 실행
   dartlab.ask("삼성전자 수익성 분석해줘", provider="oauth-codex")

2단계: 응답 읽고 판단 (P/T/C/V 등급)
   P(Pass) — 정확한 수치 + 인과 해석 + 코드 실행 성공
   T(Tolerable) — 수치 맞지만 해석 부족 또는 코드 비효율
   C(Critical) — 수치 오류, 코드 실행 실패, "해석 불가" 면피
   V(Violation) — 엔진 미사용, hallucination, 규칙 위반

3단계: 문제 분류
   시스템 프롬프트 문제 → core.py _SYSTEM_PROMPT 수정
   코드 실행 문제 → coding.py (preamble, _wrapForCapture) 수정
   context 문제 → context/ (selectors, builder) 수정
   엔진 데이터 문제 → analysis/review 수정 (→ review audit으로 위임)

4단계: 수정 + 재실행 (P 나올 때까지)

5단계: KnowledgeDB에 기록
   executions 테이블: 질문, 등급, 메트릭
   insights 테이블: 기업별 분석 서사
```

### 체크리스트 (응답 읽을 때)

- [ ] 코드를 실행했는가? (변수 저장만 하고 print 안 한 건 아닌가)
- [ ] analysis dict를 마크다운 테이블로 변환했는가?
- [ ] 수치가 코드 실행 결과에서 나온 것인가? (hallucination 아닌가)
- [ ] "해석 불가" 면피를 하지 않았는가?
- [ ] context 데이터를 활용했는가, 코드를 중복 실행했는가?
- [ ] notes enrichment 메시지가 결과에 섞이지 않았는가?
- [ ] 6막 인과 구조로 해석했는가? (숫자 나열이 아닌가)

### 표준 질문 세트 (규격)

기본 세트 — 매 audit마다 동일한 질문을 돌려야 비교 가능.

| 종목 | 축 | 표준 질문 |
|------|------|----------|
| 삼성전자(005930) | 수익성 | "삼성전자 수익성 분석해줘" |
| 삼성전자(005930) | 현금흐름 | "삼성전자 현금흐름 분석해줘" |
| 삼성전자(005930) | 안정성 | "삼성전자 안정성 분석해줘" |
| 대우건설(047040) | 수익성 | "대우건설 수익성 분석해줘" |
| 대우건설(047040) | 현금흐름 | "대우건설 현금흐름 분석해줘" |
| 대우건설(047040) | 안정성 | "대우건설 안정성 분석해줘" |
| 삼양식품(003230) | 수익성 | "삼양식품 수익성 분석해줘" |
| 삼양식품(003230) | 현금흐름 | "삼양식품 현금흐름 분석해줘" |
| 삼양식품(003230) | 안정성 | "삼양식품 안정성 분석해줘" |

확장 세트 (선택): scan 질문, macro 질문, compare 질문, 메타 지식 질문.

### 등급 판정 기준 (상세)

| 등급 | 수치 정확도 | 코드 실행 | 해석 품질 | 응답 길이 | 특징 |
|------|:---:|:---:|:---:|:---:|---|
| **P** (Pass) | 정확 | 0~2라운드, 에러 없음 | 수치 + 인과 + 한 줄 결론 | 1,000~3,500자 | 6막 구조, SuperMaster 활용 확인 |
| **T** (Tolerable) | 정확 | 2~3라운드 또는 비효율 | 수치는 있으나 인과 해석 약함 | 3,500~6,000자 | 코드 선제출 + 가정 프레임, 중복 출력 |
| **C** (Critical) | 오류 또는 "-" 반복 | 3라운드 소진 또는 실행 실패 | "해석 불가" 면피 | 임의 | dict 키 잘못 추측, hallucination |
| **V** (Violation) | - | 엔진 미사용 | 규칙 위반 | 임의 | 메타 질문에 회사 데이터 인용, review() 남용 |

### 자동화 출력 포맷

각 audit 결과는 구조화된 JSON으로 저장한다.

```json
{
  "timestamp": "2026-04-12T13:45:00",
  "provider": "oauth-codex",
  "question": "삼성전자 수익성 분석해줘",
  "stockCode": "005930",
  "axis": "수익성",
  "grade": "P",
  "metrics": {
    "responseLength": 1049,
    "codeRounds": 1,
    "hasError": false,
    "mentionsPlaybook": true,
    "hasTableStructure": true
  },
  "issues": [],
  "response": "..."
}
```

### 실행 주기

| 주기 | 대상 | 목적 |
|------|------|------|
| 시스템 프롬프트 변경 시 | 표준 세트 9개 | 프롬프트 회귀 확인 |
| provider 추가/변경 시 | 표준 세트 3~9개 × 해당 provider | provider별 품질 비교 |
| 릴리즈 전 | 표준 세트 전체 9개 | 전체 회귀 |
| 일상 (주 1회) | 랜덤 샘플 3개 | 장기 품질 드리프트 감지 |

### 실행 방법

```bash
uv run python -X utf8 scripts/audit/aiAudit.py               # 표준 세트 9개 전체
uv run python -X utf8 scripts/audit/aiAudit.py --quick       # 3개만 (삼성전자 3축)
uv run python -X utf8 scripts/audit/aiAudit.py --provider gemini  # provider 지정
uv run python -X utf8 scripts/audit/aiAudit.py --stock 005930     # 단일 종목
```

결과는 `data/audit/ai/{YYYY-MM-DD}/` 에 JSON + 요약 md 저장.

### 발견 시 처리 규칙

- **C/V 등급 나오면 즉시 중단** + 원인 분석
- 문제 분류 → 해당 파일 근본 수정 (feedback_code_quality.md)
- 수정 후 같은 질문으로 재실행 → P 나올 때까지
- T 등급은 용납 (완벽하지 않아도 사용 가능). 3회 연속 T면 개선 대상으로 등록.

### 저장

- 구조화된 결과: `data/audit/ai/{YYYY-MM-DD}/results.json`
- 요약 리포트: `data/audit/ai/{YYYY-MM-DD}/report.md`
- KnowledgeDB `executions` + `insights` 테이블 (기존)
- **P등급 → playbook recipe 자동 저장** (aiAudit.py가 처리)

### 경험 학습 절차 (Recipe)

> AI 품질은 경험 축적에 의존한다. 검증된 코드 패턴을 playbook에 저장 → HF push → 모든 사용자 자동 pull.

**흐름:**
```
audit P등급 → playbook recipe 자동 저장
수동 검증 → learnRecipe.py로 수동 저장
→ KnowledgeDB.push() → HF 업로드 (playbook.json)
→ 새 사용자 dartlab AI 첫 실행 → auto_pull → recipe 자동 다운로드
→ ExperienceIndex가 recipe 검색 → AI 프롬프트에 주입
```

**수동 학습:**
```bash
# 단일
uv run python -X utf8 scripts/audit/learnRecipe.py "매출 증가 회사" "df = dartlab.scan('growth'); print(df.sort('매출CAGR', descending=True).head(20))"

# 배치
uv run python -X utf8 scripts/audit/learnRecipe.py --batch scripts/audit/seed_recipes.json

# 확인
uv run python -X utf8 scripts/audit/learnRecipe.py --list
```

**자동 학습:** aiAudit.py에서 P등급 결과 → 코드 패턴 추출 → playbook recipe 자동 저장.

**HF 공유:**
```python
from dartlab.ai.persistence import KnowledgeDB
db = KnowledgeDB.get()
db.push(token="hf_xxx")   # playbook.json → HF (recipe 포함)
db.pull()                   # HF → 로컬 merge
```

**프라이버시:** 사용자 개인 executions(질문 이력)는 push 대상 아님. recipe(검증된 코드 패턴)만 공유.

**seed:** `scripts/audit/seed_recipes.json` — 10개 초기 패턴 (수익성/현금흐름/안정성/scan/macro).

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

## AI 개입 레이어 — 도구 조율자 (2026-04-13 도입)

AI가 분석 엔진의 "소비자"에서 "조율자"로 진화하는 레이어.
Kim et al. (2024, 시카고대) 참고: 표준화 재무제표 + CoT → 인간 초과 60% 정확도.

### 3 Phase 구조

**Phase 1: CoT 강제 + 구조화 출력** (시스템 프롬프트)

시스템 프롬프트에 4단계 사고 구조를 강제:
1. **추세(Trend)**: 3~5기 시계열 방향/변곡점
2. **��율(Ratio)**: 핵심 비율 + 업종 대비 + 5년 평균 대비
3. **근거(Rationale)**: 6막 인과 추적 + 외부 요인
4. **판단(Prediction)**: Direction(개선/악화/유지) + Magnitude(대폭/소폭/미미) + Confidence(높음/보통/낮음)

**Phase 1.5: 표준화 재무제표 직접 주입** (Kim et al. 핵심)

`ai/context/selectors/financials.py` — BS/IS/CF 핵심 항목을 AI context에 원본 주입.
AI가 엔진 calc 결과만 해석하지 않고, 원본 숫자로 직접 비율 계산 → calc 결과와 교차 검증.
5%p 이상 불일치 시 AI가 원인을 밝히고 자체 판단 사용.

| 주입 항목 | 소스 |
|---|---|
| IS 7행 | 매출액, 매출원가, 매출총이익, 판관비, 영업이익, 세전이익, 순이익 |
| BS 8행 | 자산총계, 유동자산, 현금, 비유동자산, 부채총계, 유동부채, 비유동부채, 자본총계 |
| CF 3행 | 영업CF, 투자CF, 재무CF |

**Phase 2: Assumption Review** (결정론 검증기)

`ai/context/selectors/assumptions.py` — LLM 호출 없이 임계값 기반 가정 경고.
ACT6_OUTLOOK/ACT_ALL intent에서 ContextBuilder가 자동 주입.

| 검증 | 임계값 | 경고 |
|---|---|---|
| WACC 범위 | <3% 또는 >20% | 리스크 ��리미엄 누락/과대 |
| FCF 부호 | 최근 2기 음수 | DCF 부적합 |
| 매출 성장률 | |g| > 30% | 극단적 전망 |
| 적정주가 괴리 | |gap| > 50% | 가정 과대/과소 |

**Phase 3: Override 재실행 경로**

AI가 비현실적 가정 발견 시 코드블록으로 직접 override:
```python
r = c.analysis("가치평가", overrides={"wacc": 9.0})
```

override 흐름: `Analysis.__call__(overrides=)` → `_run(overrides=)` → `_acceptsOverrides(fn)` 체크 → calc에 전달.

override 키 정의: `core/overrides.py` — FORECAST/VALUATION/CREDIT/MACRO 4그룹.

### 설계 원칙

- 기존 코드 실행 루프(`_streamWithCodeExecution` 3라운드) 활용 — 새 agent 루프 불필요
- 결정론 먼저, LLM ��중 — 가정 검증은 임계값 기반 (환각 방지)
- override는 AI가 명시적으로 판단하고 코드로 적용 — 자동 적용 금지

### 학술 근거

- Kim et al. (2024): GPT + 표준화 BS/IS + CoT → 60% (인간 53-57% 초과)
- ACE (ICLR 2026): Generator/Reflector/Curator 폐쇄 루프
- Fernandez: WACC 입력에서 질적 조정 (사후 곱셈 금지)
- Damodaran: "하나의 서사, 하나의 모델" + Triangulation

## AI 경험 생태계

AI의 경험은 세 층으로 쌓인다:

- **KnowledgeDB = 메인.** 모든 `dartlab.ask()` 호출에서 자동 축적. 2,700+ 기업.
  - executions: 질문/등급 기록. insights: 기업별 서사. playbook: intent별 분석 지침.
  - HuggingFace push/pull로 모든 사용자에게 공유.

- **블로그 = 프리미엄 층.** 5에이전트 + 95점 게이트 + 신뢰성 검증.
  - 블로그 마크다운이 source of truth. frontmatter `ai:` 블록에 verdict/strengths/weaknesses/keyMetrics.
  - 자동 파생: ai: 블록 → KnowledgeDB `insights(source="blog")`. 관리 포인트는 블로그 하나.

- **HuggingFace = 공유.** KnowledgeDB push/pull. 다른 사용자가 pull하면 경험 전파.

AI가 기업 분석 시: insights에서 과거 경험 확인 → 참고하되 최신 데이터로 자기 판단. 맹신 금지.

### 블로그 frontmatter ai: 블록

```yaml
ai:
  verdict: "관통선의 결론 한 문장"
  direction: 개선
  confidence: 높음
  archetype: 사이클
  strengths: ["강점1", "강점2"]
  weaknesses: ["약점1", "약점2"]
  keyMetrics: {revenue: 97.15, opm: 48.59, roe: 35.27, fcf: 21.3}
  dataAsOf: "2026-04-08"
```

## 관련 코드

- `src/dartlab/ai/context/aiview.py` — autoEnrich 공통 변환 레이어
- `src/dartlab/ai/context/` — ContextBuilder + ACE 폐쇄 루프 (intent/encoder/budget/builder/playbook/selectors)
- `src/dartlab/ai/` — providers, tools, runtime, memory, persistence, conversation
- `src/dartlab/ai/runtime/core.py` — 시스템 프롬프트, 코드 실행, 마크다운 변환, 인사이트 주입, preGround 백그라운드 thread
- `src/dartlab/ai/persistence/knowledge_db.py` — 단일 영속 DB (CRUD + 마이그레이션 + HF push/pull). selfai 폐기 후 영속성만 분리 보존
- `src/dartlab/ai/persistence/__init__.py` — KnowledgeDB re-export
- `src/dartlab/ai/memory/store.py` — analyze() 결과 저장 wrapper (KnowledgeDB 위임)
- `src/dartlab/cli/stdio.py` — `_handleWarmup` 으로 KnowledgeDB init 사전 지불
- `src/dartlab/analysis/financial/_memoize.py` — calc 캐시 데코레이터

> selfai 엔진 (few_shot/router/reflexion/output_validator) 은 2026-04-06 폐기됨.
> KnowledgeDB 영속성만 `ai/persistence/` 로 분리하여 보존.
