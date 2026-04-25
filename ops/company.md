# Company

> 상위 사상: [philosophy.md](philosophy.md) · 자가개선 루프: [coreloop.md](coreloop.md)

**주체**: Company facade (`dartlab.Company(stockCode)`).
**현재**: 편의성 3 원칙 (접근성·속도·신뢰성) 확립 · DART / EDGAR 이중 provider · show/select/topics + analysis/credit/review/quant/macro/gather 위임 · lazy load + BoundedCache.
**방향**: cache freshness 자동 갱신 · 첫 호출 지연 단축 · EDGAR property parity 확대.

Company 는 dartlab 의 facade. 종목코드 하나로 모든 데이터에 접근한다. 각 섹션은 **"이렇게 한다"** 명제로 열고, 반복된 실수는 섹션 하단 **"반복 실패"** 에 정리한다.

---

## 1. 호출 계약 — 종목코드 하나로 끝낸다

```python
import dartlab
c = dartlab.Company("005930")    # 종목코드 하나면 끝
c.topics                          # 사용 가능한 topic 목록
c.show("IS")                      # topic 데이터
c.select("IS", ["매출액"])         # 행/열 필터
```

### facade 고유 메서드 전수 목록

엔진 호출(`analysis/credit/review/quant/macro/gather`)을 제외한 Company facade 고유 메서드.

#### 데이터 조회 (핵심)
| 메서드 | 시그니처 | 설명 |
|--------|----------|------|
| `show` | `show(topic, *, period=None, freq=None, ...)` | topic 데이터 조회 (부분 빌드) |
| `select` | `select(topic, rows, *, period=None, ...)` | 행/열 필터 + `.chart()` |
| `table` | `table(topic, *, period=None, ...)` | 테이블 형태 접근 |
| `trace` | `trace(topic, period=None)` | 출처 추적 (docs/finance/report 중 어디서) |
| `diff` | `diff(*, topics=None, periods=None, ...)` | 기간간 텍스트 변화 감지 |
| `topicSummaries` | `topicSummaries()` | 토픽 목록 + 200자 요약 (경량) |

#### 탐색 메타 (property)
| property | 반환 | 설명 |
|----------|------|------|
| `sections` | `pl.DataFrame` | 통합 sections (docs+finance+report) — 무거움 |
| `topics` | `pl.DataFrame` | topic 목록 |
| `sources` | `pl.DataFrame` | 소스(docs/finance/report) 별 topic 현황 |
| `index` | `pl.DataFrame` | 전체 주제 메타 목록 |
| `facts` | `pl.DataFrame` | 통합 facts DataFrame |
| `market` | `str` | 시장 (KOSPI/KOSDAQ/NYSE 등) |
| `currency` | `str` | 통화 (KRW/USD) |
| `fiscalYearEnd` | `str` | 결산월 |
| `retrievalBlocks` | `pl.DataFrame` | RAG/벡터검색용 원문 마크다운 블록 |
| `contextSlices` | `pl.DataFrame` | LLM 컨텍스트 윈도우에 맞춘 슬라이스 |

#### raw 데이터 접근 (property)
| property | 반환 | 설명 |
|----------|------|------|
| `rawDocs` | `pl.DataFrame` | 원본 docs parquet |
| `rawFinance` | `pl.DataFrame` | 원본 finance parquet |
| `rawReport` | `pl.DataFrame` | 원본 report parquet |

#### 공시
| 메서드 | 시그니처 | 설명 |
|--------|----------|------|
| `filings` | `filings()` | 공시 목록 |
| `liveFilings` | `liveFilings(*, bgn=None, end=None, ...)` | 실시간 공시 목록 (OpenDART API) |
| `readFiling` | `readFiling(rceptNo, ...)` | 공시 원문 읽기 |
| `disclosure` | `disclosure(category, ...)` | 카테고리별 공시 조회 |
| `update` | `update(*, categories=None)` | 로컬 데이터 갱신 |
| `news` | `news(*, days=30)` | 뉴스 조회 |
| `watch` | `watch(*, interval=None, ...)` | 공시 감시 |

#### 구조화 뷰 (하위 데이터 접근)
| 메서드 | 시그니처 | 설명 |
|--------|----------|------|
| `governance` | `governance(view=None)` | 지배구조 (최대주주/이사회/감사의견) |
| `workforce` | `workforce(view=None)` | 임직원 (인원/보수) |
| `capital` | `capital(view=None)` | 자본 변동 |
| `debt` | `debt(view=None)` | 차입금/사채 상세 |
| `network` | `network(view=None, *, hops=1)` | 기업 네트워크 (관계사/출자) |
| `audit` | `audit()` | 감사 리스크 종합 분석 |
| `keywordTrend` | `keywordTrend(keyword, ...)` | 공시 키워드 추세 |

#### 섹터/순위 (property)
| property | 반환 | 설명 |
|----------|------|------|
| `sector` | - | 업종 정보 |
| `sectorParams` | - | 업종별 파라미터 |
| `rank` | - | 시장 내 순위 |
| `industry` | `dict` | 산업 밸류체인 내 위치 |

#### 스토리/인과 분석
| 메서드 | 시그니처 | 설명 |
|--------|----------|------|
| `validateStory` | `validateStory(overrides=None)` | Damodaran 3-test 스토리 검증 |
| `causalWeights` | `causalWeights()` | 인과 가중치 |
| `valuationImpact` | `valuationImpact()` | 밸류에이션 임팩트 |
| `storyTree` | `storyTree(*, basePeriod=None)` | 스토리 트리 |
| `narrativeDiff` | `narrativeDiff(*, claims=None)` | 서사 변화 비교 |

#### AI/뷰어
| 메서드 | 시그니처 | 설명 |
|--------|----------|------|
| `ask` | `ask(question, ...)` | AI 질의 |
| `view` | `view(*, port=8400)` | 로컬 Svelte 뷰어 실행 |

#### 클래스 메서드 (Company 클래스 레벨)
| 메서드 | 시그니처 | 설명 |
|--------|----------|------|
| `canHandle` | `canHandle(code)` | 이 provider가 처리 가능한지 |
| `priority` | `priority()` | provider 우선순위 (DART=10, EDGAR=20) |
| `listing` | `listing(*, forceRefresh=False)` | 전종목 목록 |
| `search` | `search(keyword)` | 종목 검색 |
| `resolve` | `resolve(codeOrName)` | 종목코드/회사명 → 종목코드 |
| `codeName` | `codeName(stockCode)` | 종목코드 → 회사명 |
| `status` | `status()` | 데이터 상태 |

### 노트북

[![marimo](https://marimo.io/shield.svg)](https://marimo.app/github.com/eddmpython/codertest123/blob/master/notebooks/marimo/01_company.py)
[![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/01_company.ipynb)

---

## 2. 근본 전제 — 비교 가능성을 근간으로 삼는다

**Company 는 기업 분석의 진입점이지, dartlab 의 전부가 아니다. dartlab 은 경제→섹터→기업→재무→가치의 6막 인과를 추적하는 플랫폼이다.**

**모든 기간은 비교 가능해야 하고, 모든 회사는 비교 가능해야 한다.**

이것이 dartlab 의 근본 전제다. sections 사상(topic × period 수평화)과 계정 표준화(XBRL 정규화)는 이 전제를 현실로 만드는 두 엔진이다. scan 이 가능한 것도, analysis 가 의미 있는 것도, 이 비교 가능성이 확보되어 있기 때문이다.

- 기간 비교 가능 → 같은 회사의 과거와 현재를 나란히 놓는다 (sections, diff).
- 기업 비교 가능 → 다른 회사의 같은 지표를 나란히 놓는다 (scan, analysis).

| 항목 | 내용 |
|------|------|
| 레이어 | L0/L1 facade |
| 진입점 | `dartlab.Company("005930")`, `c.show()`, `c.select()` |
| 소비 | core/(protocols, finance, docs), providers/(dart, edgar) |
| 생산 | scan, analysis, review, ai 모두 Company 를 소비 |
| 핵심 | sections 사상 (topic × period), 단일 진입점 (show/select), canHandle 라우팅 |

핵심 철학:
- 비교 가능성이 모든 분석의 기반.
- 완벽한 축을 세우는 게 모든 방향성.
- Company → Analysis → Review → Scan 순서로 계층이 쌓인다.
- 모든 개선은 **DART/EDGAR 양쪽 동시 반영** (protocol 테스트 강제).

---

## 3. sections 사상 — topic × period 수평화로 지도를 만든다

sections (topic × period 수평화)가 회사의 전체 지도다. Company 엔진의 핵심 사상.

```
sections = { topic: { period: content } }
```

- **finance**: sections 보다 숫자가 강하다 → 해당 topic 을 **대체**한다.
- **report**: DART 에만 있다 → 해당 topic 에 **채운다**.
- **EDGAR**: report 없이 sections + finance 대체만으로 완성.

sections 위에 올라가는 소비 레이어는 두 가지뿐이다:
- **diff**: 기간간 텍스트 변화 감지 → `core/docs/diff.py`.
- **viewer**: sections + index 메타데이터. 렌더러(HTML/Svelte/PDF)가 소비.

source 우선순위: **finance > report > docs** (숫자 → 정형 → 서술).

개별 property(dividend, employee 등)는 sections 사상 이전의 우회로다.
Company 클래스에 직접 연결하지 않고, **show() 경로로만 접근**한다.

**반복 실패** — `c.dividend` / `c.employee` 등 개별 property 로 추가. 이후 show() 경로로 통일.

---

## 4. 단일 진입점 — method/property 만 노출한다

사용자 surface 는 **method/property** 만:

```python
c.show("IS")          # finance topic 데이터 (DataFrame)
c.show("inventory")   # notes topic
c.show("dividend")    # report topic
c.select("IS", ["매출액"])  # 행/열 필터
c.sections            # 통합 sections DataFrame (sections 사상 핵심)
c.facts               # 통합 facts DataFrame
c.diff()              # 기간간 텍스트 변화
c.filings()           # 공시 목록
c.trace(topic)        # 출처 추적
c.review(...)         # 보고서
c.analysis(...)       # 분석
c.credit(...)         # 신용평가
```

`c.docs / c.finance / c.report / c.profile` 4 개 public namespace 는 **모두 제거됨** (Plan v10 P3).
내부 compute 레이어 (review/credit/analysis/valuation) 는 `c._docs / _finance / _report` private 백엔드를 사용한다.

### DART vs EDGAR 데이터 차이 (백엔드)

| 영역 | DART | EDGAR |
|-----------|------|-------|
| docs (private) | 공시 HTML → sections | 10-K/10-Q HTML → sections |
| finance (private) | 로컬 parquet (K-IFRS) | SEC companyfacts API (US-GAAP XBRL) |
| report (private) | 28 apiType (OpenDART API) | 14 apiType (XBRL + 10-K 텍스트 파싱), 13개 공통 |
| profile (private) | sections + finance + report merge | sections + finance merge |

EDGAR report 는 SEC 에 구조화 API 가 없으므로 XBRL facts + 10-K 텍스트 regex 로 추출한다.

**반복 실패** — `c.docs.method()` 같은 namespace 방식 재도입. P3 에서 제거됨.

---

## 5. 공통 인터페이스 — show/select 가 기본 경로

### 핵심 — show/select (경량, 추천 경로)
```python
c.show(topic)                          # 특정 topic 데이터 (부분 빌드, 빠름)
c.show("IS", period="2023")           # 기간 필터
c.show("IS", period=["2022", "2023"]) # 세로 비교
c.select("IS", ["매출액", "영업이익"]) # 행/열 필터
c.select("IS", ["매출액"]).chart()     # 필터 + 시각화
c.topicSummaries()                     # 토픽 목록 + 200자 요약 (경량)
```

show/select 는 **해당 topic 만 부분 빌드** — 전체 sections 를 로드하지 않는다.
AI 가 데이터를 조회할 때는 show/select 를 기본 경로로 사용한다.

### 탐색/추적
```python
c.index           # 전체 주제 목록
c.trace(topic)    # 출처 추적 (docs/finance/report 중 어디서 왔는지)
c.diff()          # 기간간 텍스트 변화
```

### finance topics (Plan v10)
```python
c.show("IS")           # 손익계산서 — 분기 컬럼 (2025Q4, 2025Q3, ...)
c.show("IS", freq="Y") # 연간 합산
c.show("BS") / c.show("CF") / c.show("CIS") / c.show("SCE")
c.show("ratios")       # 재무비율 DataFrame
c.show("ratioSeries")  # 시계열 비율
```

⚠ 기본은 **분기 컬럼만** 노출 — 연간 누적은 `freq="Y"` 명시 또는 calc 함수가 `toDictBySnakeId(c.select(...))` 로 변환할 때 `synthesizeAnnualFromQuarters` 가 자동 합성 (`data["sales"]["2024"]`).

### 메타
```python
c.sections / c.topics             # sections 지도
c.filings()                       # 공시 목록 (= dartlab.listing("filings", corp=...))
c.insights                        # 등급 카드
c.market / c.currency             # 시장 정보
```

---

## 6. sections 접근 — 필요할 때만 전체 로드한다 ⚠️

`c.sections` 는 **전체 docs + finance + report 를 통합 로드**한다. 메모리 소비가 크다.

### 성능 벤치마크 (삼성전자 005930, 2026-03-31 측정)

| 경로 | 시간 | 메모리 peak | 용도 |
|------|------|------------|------|
| `c.show("IS")` | **0.65초** | 92MB | 특정 topic 조회 |
| `c.select("IS", [...])` | **0.01초** | (show 캐시) | 행/열 추출 + 차트 |
| `c.topicSummaries()` | **0.69초** | 경량 | AI 경로 탐색 |
| `c.sections` | **19초** | **409MB** | 전체 지도 필요 시만 |
| `c.review("수익성")` 첫 호출 | **25초** | 411MB | Company 초기화 포함 |
| `c.review()` x3 추가 | **8초** | 367MB | 캐시 재사용 |
| `c.review()` 전체 | **83초** | 424MB | ⚠ 타임아웃 위험 |
| `c.analysis("financial", "수익성")` | **0.03초** | 357MB | review 이후 빠름 |

**규칙**: show/select 로 충분하면 `c.sections` 에 접근하지 않는다. `review()` 전체 호출은 83초 → AI 코드 실행(60초 제한)에서 금지.

**반복 실패** — AI tool 경로에서 `c.sections` 로 전체 로드 → 메모리 409MB + 19초 지연. `c.show(topic)` 로 부분 빌드.

---

## 7. 주석(Notes) — show() 경로로 통합 접근한다

재무제표 주석은 BS/IS 총액 이면의 **항목별 분해** 데이터다. DART(K-IFRS)와 EDGAR(US-GAAP) 모두 동일 인터페이스.

### 접근 경로

| 경로 | 결과 | 용도 | DART | EDGAR |
|------|------|------|------|-------|
| `c.show("inventory")` | 파싱된 DataFrame (항목 × 연도) | AI/코드 분석용 | ✅ HTML 파싱 | ✅ XBRL 수치 태그 |
| `c.show("financialNotes", block, period="2025")` | 원문 마크다운 | 원문 확인용 | ✅ | — |

### notes 지원 항목 (12개)

| 영문 | 한글 | DART | EDGAR | 데이터 내용 |
|------|------|------|-------|------------|
| inventory | 재고자산 | ✅ | ✅ | 상품/제품/원재료 분해 |
| borrowings | 차입금 | ✅ | ✅ | 단기/장기 분해 |
| tangibleAsset | 유형자산 | ✅ | ✅ | PPE gross/net/감가상각 |
| intangibleAsset | 무형자산 | ✅ | ✅ | 영업권/개발비 등 |
| receivables | 매출채권 | ✅ | ✅ | 대손충당금 포함 |
| provisions | 충당부채 | ✅ | ✅ | 보증/소송/구조조정 |
| eps | 주당이익 | ✅ | ✅ | 기본/희석 EPS |
| segments | 부문정보 | ✅ | ✅ | 부문별 매출/이익 |
| costByNature | 비용성격별분류 | ✅ | ✅ | 원재료/급여/감가상각 |
| lease | 리스 | ✅ | ✅ | 사용권자산/리스부채 |
| affiliates | 관계기업 | ✅ | △ | 지분법 투자 (XBRL 태그 제한적) |
| investmentProperty | 투자부동산 | ✅ | △ | 공정가치/장부가 (XBRL 태그 제한적) |

**EDGAR notes 데이터 소스**: XBRL companyfacts 에서 수치 태그 직접 추출.

### analysis enrichment

analysis 축에 notes 데이터가 자동 포함된다:
- `analysis("financial", "자산구조")` → `assetStructure.notesDetail` 에 inventory/tangibleAsset/intangibleAsset.
- `analysis("financial", "비용구조")` → `costBreakdown.costByNature` 에 비용 성격별 분류.

### sections 주석 블록 정렬

financialNotes/consolidatedNotes topic 은 table 블록이 **직전 heading 의 시맨틱 키를 상속**한다.
→ "8. 재고자산" heading 다음의 table 은 모든 기간에서 같은 block 으로 그룹핑됨.
→ period 없이 `show("financialNotes", blockNum)` 호출해도 기간간 섞이지 않음.

---

## 8. 편의성 3 원칙 — 접근성·속도·신뢰성을 동시에 만족한다

Company-bound API 의 설계 원칙. Company-bound API 는 이 3 가지를 동시에 만족해야 한다.
(시장 레벨 엔진 `dartlab.macro()`, `dartlab.scan()` 등은 종목코드 없이 동작하므로 접근성 원칙이 다르다.)

### 접근성
- **종목코드 하나면 끝난다**: 공개 함수는 종목코드(str) 또는 Company 하나만 받는다.
- **2-Tier 접근**: 루트 함수(`dartlab.X("005930")`) + Company 메서드(`c.X()`) 양쪽 모두 제공. 루트 함수가 1차 시민.
- **`import dartlab` 하나로 모든 공개 기능 접근**. 내부 엔진 경로는 사용자에게 노출하지 않는다.

### 속도
- **첫 호출 5초 이내**: Company 생성부터 첫 결과 반환까지 체감 지연 최소화.
- **lazy load 기본**: finance·report·docs 는 접근 시점에 로드.
- **캐시 재사용**: 같은 세션 내 동일 Company 는 BoundedCache 로 재사용.

### 신뢰성
- **숫자는 원본 그대로**: DART/EDGAR 원본 수치 보존.
- **없으면 None**: 데이터가 없을 때 추정값을 만들지 않는다. 사용자가 판단한다.
- **출처 추적 가능**: `trace(topic)` 로 source(docs/finance/report)를 항상 확인 가능.
- **에러는 명시적으로**: 파싱 실패·매핑 누락은 숨기지 않고 드러낸다.

이 원칙은 기존/신규 모든 공개 API 에 소급 적용한다.

**반복 실패** — 추정값으로 None 을 채움 (신뢰성 원칙 위반). 데이터 없으면 None 으로 사용자가 판단.

---

## 9. canHandle 라우팅 — provider 에서 체인으로 분기한다

```
dartlab.Company("005930")
    ↓ canHandle() 체인
    providers/dart/company.py   (priority=10, 한국 종목코드)
    providers/edgar/company.py  (priority=20, 미국 ticker)
```

- `dartlab.Company` 는 facade → 엔진(`providers/dart/`, `providers/edgar/`) 으로 canHandle 라우팅.
- **하위 엔진은 상위 facade 를 import 하지 않는다** (import 방향 CI 검증).
- 새 국가 추가 시 core 수정 0 줄 — provider 패키지만 추가 + canHandle/priority 구현.

### DART vs EDGAR 데이터 소스

| 영역 | DART | EDGAR |
|------|------|-------|
| 회계기준 | K-IFRS | US-GAAP |
| 재무제표 | 로컬 parquet | SEC companyfacts API (on-demand) |
| 공시 문서 | 로컬 parquet (HTML 파싱) | SEC 10-K/10-Q HTML 파싱 |
| 정기보고서 | 28 apiType (OpenDART API) | 9 apiType (XBRL + 텍스트 regex) |
| 계정명 | 한국어 (`계정명` 컬럼) | snakeId (`account` 컬럼) |
| 통화 | KRW (조/억 포맷) | USD ($B/$M 포맷) |
| 주가 | Naver → Yahoo fallback | Yahoo → FMP fallback |
| 계정 브릿지 | `_bridgeKoreanSnakeId()` — 한국어↔snakeId 자동 번역 |
| 통화 분기 | `company.currency` → analysis/review 자동 적용 |

**EDGAR report 14 apiType**: dividend, treasuryStock, stockTotal, employee, auditOpinion, corporateBond, executive, majorHolder, executivePay, capitalChange, outsideDirector, minorityHolder, investedCompany, debtSecurities.

DART 28개 중 13개가 DART/EDGAR 공통. 나머지 15개는 SEC 에 동등 구조가 없는 DART 전용 (개인별 보수, 공모자금 용도 등).

---

## 10. 메모리 안전 ⚠️

> Polars 는 네이티브 Rust 힙. Python gc.collect() 로 회수 불가.
> Company 1 개 ≈ 200~500MB. 3 개 동시 로드 = OOM. (2회 크래시 이력)

- 캐시는 `BoundedCache(pressure_mb=800)` 사용.
- 새 데이터 로드 경로 추가 시 `check_memory_and_gc()` 호출 검토.

---

## 11. 동기화 — 양쪽 provider 에 동시 반영한다

- 개별 property(dividend, employee 등) 는 **show() 경로**로 접근한다.
- 하위 엔진은 상위 facade 를 import 하지 않는다 (import 방향 CI 검증).
- 새 국가 추가 시 core 수정 0 줄 — provider 패키지만 추가.
- Company 기능 변경 시 README (영문+한국어) 동시 반영.
- 노트북 코드는 실행 확인 후에만 커밋.

---

## 12. 관련 코드

| 파일 | 역할 |
|------|------|
| `src/dartlab/company.py` | 루트 facade (canHandle 체인 라우팅) |
| `src/dartlab/core/protocols.py` | CompanyProtocol (@runtime_checkable) |
| `src/dartlab/providers/dart/company.py` | DART 엔진 (canHandle, priority=10) |
| `src/dartlab/providers/edgar/company.py` | EDGAR 엔진 (canHandle, priority=20) |
| `src/dartlab/core/docs/` | diff, viewer, bridge, topicGraph |
| `src/dartlab/core/finance/` | ratios, extract, period, labels |

---

## 요약 — 명제 9 줄

1. 종목코드 하나로 끝낸다 (`dartlab.Company("005930")`), 엔진 (analysis/credit/review/quant/macro/gather) 은 위임.
2. Company 는 dartlab 의 진입점 중 하나. 전체 사상은 6막 인과 (macro→scan/industry→Company→analysis→quant).
3. 모든 기간·모든 회사 비교 가능이 근본 전제. sections (topic × period) 사상 + 계정 표준화가 두 엔진.
4. 사용자 surface 는 method/property 만. `docs/finance/report/profile` namespace 는 제거됨 (Plan v10 P3).
5. 기본 경로는 `show/select` (부분 빌드, 빠름). `c.sections` 는 전체 로드가 필요할 때만.
6. 주석(Notes) 12 종은 `c.show("inventory")` 등 show 로 접근, analysis 축에 자동 enrichment.
7. 편의성 3 원칙 — 접근성 (종목코드 하나 + 2-Tier) · 속도 (첫 호출 5s · lazy) · 신뢰성 (원본 보존 · None).
8. canHandle 라우팅으로 DART(priority=10) / EDGAR(priority=20) 분기. 새 국가는 provider 패키지만 추가.
9. Polars = Rust 힙. Company ≈ 200~500MB, 3 개 동시 = OOM. BoundedCache + check_memory_and_gc.
