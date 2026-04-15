# API Contract — dartlab 호출 규칙 단일 진실의 원천

dartlab 의 모든 공개 API 가 따르는 contract 와 사상. 새 함수/엔진/property 를
추가하기 전에 이 문서를 먼저 읽고 contract 위반이 없는지 확인한다.

이 문서가 source of truth — 다른 ops 문서나 코드와 충돌하면 이 문서가 기준이다.

---

## 1. 단일 진입점 + Dual Access (call form + attr form) [최우선]

**원칙**: 모든 사용자 진입점은 같은 함수 하나지만 두 가지 access form 을 모두 허용한다
(pandas 가 ``df["col"]`` 와 ``df.col`` 둘 다 허용하는 것과 같다).

```python
# call form (canonical)
c.show("IS")
c.show("IS", freq="Y")
c.analysis("financial", "수익성")
c.credit("등급")
c.review("수익성")
c.scan("governance")
c.quant("rsi", "005930")

# attr form (sugar)
c.show.IS()                    # → c.show("IS")
c.show.IS(freq="Y")            # → c.show("IS", freq="Y")
c.analysis.financial("수익성")  # → c.analysis("financial", "수익성")
c.credit.등급()                # → c.credit("등급")
c.review.수익성()              # → c.review("수익성")
c.scan.governance()            # → c.scan("governance")
c.quant.rsi("005930")          # → c.quant("rsi", "005930")
```

두 form 의 동작은 **완전히 동일**. 같은 함수를 다른 access syntax 로 부르는 것일 뿐.

### 구현

`core/dualAccess.py::CallableAccessor` SSOT 헬퍼 — `__call__` + `__getattr__` 양쪽
지원. 모든 진입점이 이 클래스를 통해 wrap 된다.

### 금지: 별도 명칭의 새 진입점

같은 함수의 두 form 은 OK 지만, **같은 데이터에 다른 이름의 진입점** 추가는 금지.

### 좋은 예

```python
c.show("IS")                              # 분기 연결 (기본)
c.show("IS", freq="Y")                    # 연간 연결
c.show("IS", freq="YTD")                  # YTD 누적 연결
c.show("IS", scope="separate")            # 분기 별도
c.show("IS", freq="Y", scope="separate")  # 연간 별도
c.show("IS", period="2023")               # 2023 필터
c.show("ratios")                          # 비율
c.show("inventory")                       # 재고자산 주석
c.show("dividend")                        # 배당
c.select("IS", ["매출액"], freq="Y")       # 행 필터 + 연간
```

### 나쁜 예 (금지)

```python
c.IS                            # ✗ 별도 property — c.show("IS") 로 통합
c.BS / c.CF / c.CIS             # ✗ 동일 — c.show(...)
c.timeseries() / c.timeseries   # ✗ 별도 method
c.annual / c.cumulative         # ✗ 별도 property
c.ratios / c.ratioSeries        # ✗ 별도 property — c.show("ratios")
c.SCE / c.sceMatrix             # ✗ 별도 property — c.show("SCE")
c.notes.inventory               # ✗ accessor namespace — c.show("inventory")
c.IS_annual                     # ✗ 새 property
c.financeAnnual.IS              # ✗ 새 namespace
c.show("IS").annual()           # ✗ DataFrame 메서드 추가
```

### 내부 series-tuple 빌더

calc 모듈 (analysis/forecast/valuation/credit/review/excel) 이 ``(series, periods)``
튜플 형태가 필요한 경우 **private 메서드** ``c._buildFinanceSeries(freq=, scope=)``
를 호출한다. 사용자 진입점이 아니다.

### 검증 방법

```bash
# property/메서드 잔존 0
grep -rn "@property\s*$" src/dartlab/providers/dart/company.py | wc -l    # finance topic property 없어야
grep -rn "def timeseries\|def annual\|def cumulative" src/dartlab/        # 0
grep -rn "c\.IS\b\|c\.BS\b\|c\.CF\b\|c\.CIS\b" src/dartlab tests          # 0 (사용자 코드)
grep -rn "c\.timeseries\|c\.annual\|c\.cumulative" src/dartlab tests      # 0
```

---

## 2. 분기 기본 + 누적/연간/별도는 파라미터 [최우선]

**원칙**: 모든 finance topic 의 default = **분기 standalone + 연결재무 (CFS)**.
연간/누적/별도는 ``freq`` / ``scope`` 파라미터로 토글.

| 모드 | 호출 | schema / 의미 |
|---|---|---|
| 분기 연결 (기본) | `c.show("IS")` | `2025Q4 .. 2024Q1` (CFS) |
| 연간 연결 | `c.show("IS", freq="Y")` | `2025, 2024, ...` (4분기 strict 합) |
| YTD 누적 | `c.show("IS", freq="YTD")` | `2025Q4(YTD), 2025Q3(YTD), ...` |
| 분기 별도 | `c.show("IS", scope="separate")` | OFS (모회사) |
| 연간 별도 | `c.show("IS", freq="Y", scope="separate")` | 둘 다 토글 |

### 파라미터 표준 (pandas 관용)

| 파라미터 | 표준값 | 의미 |
|---|---|---|
| `freq` | `"Q"` (default) / `"Y"` / `"YTD"` | pandas 주기 코드 |
| `scope` | `"consolidated"` (default) / `"separate"` | 회계 범위 |

### 합산 규칙 (freq="Y")

- **IS / CIS / CF (flow)**: 4분기 모두 있을 때만 단순 합 (3분기 이하 → None)
- **BS (stock)**: Q4 (= 연말잔액). 없으면 그 해 가장 최근 분기

### 내부 SSOT

분기 → 연간 합성 로직은 `core/finance/flow.py::synthesizeAnnualFromQuarters` 한
함수에만 존재. `toDict`, `toDictBySnakeId`, `_financeToDataFrame` 모두가 위임.

---

## 3. 파라미터 이름 일관성 [최우선]

같은 의미의 옵션은 모든 함수에서 같은 이름을 쓴다. 신규 코드는 이 이름만 허용.

| 표준 | 타입/값 | 의미 | 금지된 변형 |
|---|---|---|---|
| `freq` | `"Q"` (default) / `"Y"` / `"YTD"` | 시계열 주기 (pandas 표준) | `annual`, `cumulative`, `period_type`, `interval` |
| `scope` | `"consolidated"` (default) / `"separate"` | 회계 범위 | `fsDiv`, `fsDivPref`, `consolidated_only` |
| `basePeriod` | `str \| None` | 분석 기준 시점 ("2024Q4") | `as_of`, `asOf`, `cutoff`, `referenceDate` |
| `period` | `str \| list[str] \| None` | 데이터 필터 기간 | `quarter`, `year`, `time`, `dt` |
| `stockCode` | `str` | 종목코드 (6 digit DART, ticker EDGAR) | `code`, `corp`, `ticker`, `symbol` |
| `topic` | `str` | show/select topic 키 | `category`, `block`, `kind` |
| `axis` | `str` | 엔진 축 이름 (analysis/scan/quant/...) | `metric`, `feature`, `name` |
| `target` | `str \| None` | 엔진 호출 대상 (옵션) | `subject`, `entity` |
| `indList` | `str \| list[str]` | select 행 필터 | `rows`, `accounts`, `items` |
| `colList` | `str \| list[str]` | select 열 필터 | `cols`, `columns` |
| `maxYears` | `int` | 시계열 최대 연도 | `years_back`, `nYears`, `lookback` |
| `maxQuarters` | `int` | 시계열 최대 분기 | `quarters_back`, `nQuarters` |
| `withFallback` | `bool` | fallback 활성 | `useFallback`, `enable_fallback` |
| `dryRun` | `bool` | 미리보기 | `simulate`, `preview` |
| `detail` | `bool` | 상세 출력 (credit 등) | `verbose`, `expand` |

### Bool 조합 금지

같은 함수에 의미 충돌하는 bool 2개 이상 금지. enum/Literal 사용:

```python
# 금지
def f(*, annual: bool = False, cumulative: bool = False)  # ❌

# 권장
def f(*, freq: Literal["Q", "Y", "YTD"] = "Q")  # ✓
```

### 한국어 vs 영문

엔진 호출 시 한국어/영문 둘 다 받는 alias 는 허용된다 (양방향).
파라미터 이름 자체는 항상 영문 camelCase.

---

## 4. 엔진 호출 통일 패턴

모든 엔진은 `엔진("그룹", "축")` 또는 `엔진("축")` 형태로 호출.
축을 루트 함수로 직접 노출 금지.

| 엔진 | 진입점 | 예시 |
|---|---|---|
| analysis | `c.analysis()` | `c.analysis("financial", "수익성")` 또는 `c.analysis("수익성")` |
| credit | `c.credit()` | `c.credit("등급")` |
| quant | `c.quant()` / `dartlab.quant()` | `c.quant("rsi")` |
| macro | `dartlab.macro()` | `dartlab.macro("사이클")` |
| scan | `dartlab.scan()` | `dartlab.scan("financial", "수익성")` |
| review | `c.review()` | `c.review("수익성")` |
| gather | `dartlab.gather()` | `dartlab.gather("price", "005930")` |
| ai | `dartlab.ask()` | `dartlab.ask("...")` |
| listing | `dartlab.listing()` | `dartlab.listing("filings", corp="005930")` |
| search | `dartlab.search()` | `dartlab.search("유상증자")` |

**금지**: `c.profitability()`, `c.kr_profitability()`, `c.financialAnalysis.profitability()` 같이
축을 루트로 노출하거나 namespace 중첩.

---

## 5. 종목코드 하나면 끝 (편의성 3원칙)

### 접근성
- 공개 함수는 종목코드 (str) 또는 Company 만 받는다
- 추가 import 금지 — `import dartlab` 하나로 모든 기능 접근
- 2-Tier: 루트 함수 (`dartlab.X("005930")`) + Company 메서드 (`c.X()`) 양쪽

### 속도
- 첫 호출 5초 이내
- lazy load 기본 — finance/report/docs 는 접근 시점에 로드
- BoundedCache 로 같은 세션 내 재사용

### 신뢰성
- 숫자는 원본 그대로 (DART/EDGAR 원본 보존)
- 없으면 None — 추정값 만들지 않는다
- 출처 추적 가능: `c.trace(topic)`
- 에러는 명시적 — 파싱 실패/매핑 누락 숨기지 않음

---

## 6. 숫자는 원본, 없으면 None

- 결손은 None (0 으로 채우지 않음)
- 진짜 0 과 결손을 구분
- `data.get("매출액") or 0` 같은 결과 dict 의 `or 0` 금지 (분모 가드는 예외, `# noqa: zero-guard` 표시)

### Sentinel 차단

`tests/test_ast_calc_patterns.py::test_no_or_zero_in_return_dict` 가 calc 함수의
return dict 에서 `or 0` 사용을 AST 로 감지하여 차단한다.

---

## 7. 엔진 독립 (L2 간 상호 import 금지)

dartlab은 6레이어 구조. L2 엔진 4개(analysis/quant/credit/macro)는 **동등하고 상호 독립**.

### 레이어 구조

```
L0    core/                               ← 순수 유틸 + 공통 타입
L1    providers/ gather/                  ← 데이터 수집
L1.5  scan/                               ← 전종목 사전 빌드 (parquet)
L2    analysis/ quant/ credit/ macro/     ← 4개 분석 엔진 (동등, 상호 import 금지)
L3    review/                             ← 이야기꾼 (보고서 조립)
L4    ai/ + 사람                          ← 소비자 (해석과 판단)
교차 관심사: guide/
```

### 규칙

- **L2 엔진 간 상호 import 금지** (analysis↛quant, macro↛credit 등)
- **L2 → L1.5(scan) 하향 참조 허용** (scan은 순수 데이터 빌더)
- **L3(review)만 L2를 import** — 모든 엔진 결과를 소비해 보고서 조립
- **L4(ai) → L3/L2 import 허용** — AI는 review + 엔진 직접 호출 가능
- **L2 엔진은 L3(review)를 import 금지** — 엔진은 dict/숫자만 반환, 서사 생성 금지
- 공유 데이터는 L0/L1 (core/, providers/, gather/) 에서 직접 가져온다
- 공유 헬퍼는 한 위치에서 import — SSOT 단일 함수 (예: `core/finance/helpers.py::toDictBySnakeId`)
- 해석의 조합은 review (L3) 또는 AI (L4) 의 몫

### import 방향

```
L0 ← L1 ← L1.5 ← L2 ← L3 ← L4
```

CI sentinel `tests/test_imports.py` 가 강제.

### 엔진 출력 규약

각 엔진은 **dict/숫자/DataFrame만 반환.** 다음은 엔진에서 금지:
- 해석 문장 (narrative string)
- Block 객체 (HeadingBlock, TextBlock 등 — review.blocks)
- Section / Review 객체 (review 전용)
- 렌더링 로직 (review/renderer에서만)

---

## 8. 단일 진실의 원천 (SSOT)

같은 로직을 두 곳에서 구현 금지. 핵심 SSOT 헬퍼:

| 헬퍼 | 위치 | 용도 |
|---|---|---|
| `synthesizeAnnualFromQuarters` | `core/finance/flow.py` | 분기→연간 합성 |
| `mergeAliasRows` | `core/finance/labels.py` | SNAKEID_ALIASES 머지 |
| `SNAKEID_ALIASES` | `core/finance/labels.py` | DART↔EDGAR snakeId alias |
| `get_korean_labels` | `core/finance/labels.py` | snakeId → 한국어 라벨 |
| `toDictBySnakeId` | `analysis/financial/_helpers.py` | SelectResult → dict (단일) |
| `annualColsFromPeriods` | `analysis/financial/_helpers.py` | 기간 컬럼 추출 (단일) |
| `sumBorrowingsKorean` | `analysis/financial/_helpers.py` | 차입금 합산 fallback |
| `annualSumFlow` | `core/finance/flow.py` | credit 모드 부분 합산 (legacy) |

규칙 변경 시 SSOT 한 곳만 수정. 호출자는 위임.

---

## 9. DART/EDGAR 동기화 [최우선]

- DartCompany 에 public 메서드를 추가하면 **EdgarCompany 에도 동일 메서드를 추가**한다
- DART 전용은 `tests/test_protocol.py::_DART_ONLY_EXEMPT` 에 **사유 주석과 함께** 등록
- analysis 축, review 블록, CLI 명령 추가 시 EDGAR Company 에서도 실행하여 crash 없음 확인
- 통화 분기는 `company.currency` 참조 (하드코딩 금지)
- 동기화 검증: `bash scripts/dev/test-lock.sh tests/ -k "test_edgar_has_all_dart_public_methods" -v`

---

## 10. 코드 작성 규칙

### 예외 처리
- `except Exception:` 사용 금지 → 구체적 예외 타입 명시
- 사용자 입력 검증은 early return (try-except 아님)
- 에러 swallowing 금지 (specific 예외만 잡고 의미 있게 처리)

### 독스트링
- 공개 API 함수 9 섹션 필수: Capabilities/AIContext/Guide/SeeAlso/Args/Returns/Requires/Example/Raises (해당 시)
- 상세: `ops/code.md`

### CamelCase
- 함수/변수: camelCase
- 클래스: PascalCase
- 상수: UPPER_SNAKE_CASE

### 시그니처
- keyword-only 옵션은 `*,` 뒤에 배치 — `def f(stockCode, *, annual=False)`
- bool flag 는 항상 keyword-only

---

## 11. 사상 (philosophy)

### 근본 전제
**모든 기간은 비교 가능해야 하고, 모든 회사는 비교 가능해야 한다.**

이게 dartlab 의 존재 이유. sections 사상 (topic × period 수평화) 과 계정 표준화
(XBRL 정규화) 는 이 전제를 현실로 만드는 두 엔진.

- 기간 비교 → 같은 회사의 과거와 현재 (sections, diff)
- 기업 비교 → 다른 회사의 같은 지표 (scan, analysis)
- 시장 비교 → 매크로와 기업 (macro, gather)
- 시장 간 비교 → KR/US 매크로 교차

### 4 비교 가능성
1. **회사 내 비교** (sections, diff) — 같은 회사의 과거와 현재
2. **회사 간 비교** (scan, analysis) — 다른 회사의 같은 지표
3. **시장 내 비교** (macro, gather) — 경제 사이클과 기업의 관계
4. **시장 간 비교** (macro, gather) — KR/US 매크로 교차

### period 라벨 = 캘린더 기준 (Capital IQ end-month 규칙)
- 모든 quarterly period 컬럼은 `{calYear}Q{calQ}` — `end_date` 의 캘린더 분기로 통일
- 12월 결산 (DART 99% / EDGAR Dec): fiscal == calendar identity
- 비-12월 결산 (UAA 3월·NKE 5월·AAPL 9월): fy/fp → end-month CY 자동 매핑
- SSOT: `core/finance/period.py::buildFiscalToCalendarMap` (`providers/edgar/finance/pivot.py` 에서 호출)
- 근거: cross-company join 가능성 (`UA 2025Q4` ↔ `Samsung 2025Q4` 동일 시점 데이터)

### 회사는 스토리가 있다
분석은 숫자 나열이 아니라 **6막 인과 구조의 스토리텔링**이다 (review 사상).
analysis = 도구, review = 사람의 보고서, AI = 적극적 분석가.

### sections 사상
sections (topic × period 수평화) 가 회사의 전체 지도. 양대 축 중 하나.

```
sections = { topic: { period: content } }
```

source 우선순위: **finance > report > docs** (숫자 → 정형 → 서술)

---

## 12. EDGAR 수집 경로 — dartlab=벌크, 사용자 API=선택 [최우선]

> ⛔ **dartlab 자체는 SEC 벌크가 primary 소스.** 자동 CI·프리빌드·HF 배포는 전부 벌크(`companyfacts.zip` + 분기 `{Y}q{Q}.zip`) 파이프라인을 쓴다. 상세: `ops/edgar.md`.

### 경로 분리

| 경로 | 트리거 | 소스 | 용도 |
|------|--------|------|------|
| **자동 파이프라인 (벌크)** | edgarSync.yml cron + workflow_run | `Archives/edgar/daily-index/xbrl/companyfacts.zip` + `files/dera/data/financial-statement-data-sets/{Y}q{Q}.zip` | HF 배포, scan 프리빌드, 전 종목 커버 |
| **사용자 선택 (API)** | `c.finance.refreshFromApi()` 명시 호출 | `data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json` | 공시 당일 최신 분기 즉시 반영 원할 때만 |

### 금지

- 자동 파이프라인 어디서도 `data.sec.gov/api/xbrl/companyfacts` 엔드포인트를 호출하지 않는다.
- `_collectEdgarFinance` 같은 per-ticker API 수집 함수는 **사용자 경로**(`refreshFromApi`)에서만 노출.
- `num.tsv`는 받지 않는다 — `companyfacts.zip`이 같은 값의 더 신선한 번들이라 중복.

### 검증 방법

```bash
# CI 워크플로우가 API 엔드포인트 호출하는지 확인 (0건이어야 함)
grep -rn "data.sec.gov/api/xbrl" .github/ scripts/ src/dartlab/core/ src/dartlab/providers/edgar/bulk/

# 자동 파이프라인 함수에서 companyfacts API 호출 안 하는지
grep -n "companyfacts/CIK" src/dartlab/providers/edgar/bulk/
```

---

## 13. ops/ 가 source of truth

- 코드 ↔ ops/ 충돌 시 코드 기준으로 ops 갱신
- `ops/api-contract.md` (이 문서) 가 모든 API 규칙의 진입점
- 엔진별 상세는 `ops/{engine}.md` 참조
- 사상 변경 / 새 규칙 추가 시 이 문서 갱신 필수

---

## 위반 카탈로그

### ✅ 해결됨 (Plan v9 + v10)

**Plan v9:**
- `c.timeseries()` / `c.annual` / `c.cumulative` 제거 → `c.show("IS", freq=, scope=)` 통합
- DART/EDGAR `getTimeseries()` deprecated 제거
- `c.show()` / `c.select()` 에 `freq` / `scope` 파라미터 추가
- `synthesizeAnnualFromQuarters` SSOT (core/finance/flow.py)
- `mergeAliasRows` SSOT (core/finance/labels.py)
- credit/metrics → analysis._helpers 위임

**Plan v10 (1.0.0 전 클린업):**
- **P0** `c.IS / c.BS / c.CF / c.CIS` 별도 property 제거 → `c.show("IS")` (DART + EDGAR)
- **P1** `c.ratios / c.ratioSeries / c.SCE / c.sceMatrix` 별도 property 제거 → `c.show("ratios")` 등
- **P2** `c.notes.X` 12 sub-property 제거 → `c.show("inventory")` 등
- **P3** **4 namespace 전면 제거** — `c.docs / c.finance / c.report / c.profile` (public 접근 0)
  - 사용자 surface = `c.show()` / `c.select()` / `c.sections` / `c.diff()` / `c.filings()` / `c.facts` / `c.review()` / `c.analysis()` / `c.credit()`
  - 내부 compute (review/credit/valuation/analysis) 는 `c._docs / _finance / _report` private 백엔드 사용
- **P4** Plan vN / R26 마커 정리
- **P5** finance DataFrame 컬럼 `계정명` → `항목` 단일화 (sections 사상 정합)
- **P6** snakeId → 한국어 라벨 SSOT 통합 (`core/finance/labels.py::get_korean_labels()`, `AccountMapper.labelMap()` 한 줄 위임)

### ⚠️ 잔존 / 후속

- 데이터 파일 (`accountMappings.json`) 위치 — 현재 `providers/dart/finance/mapperData/`. 진정한 SSOT 면 `core/data/` 로 이동 필요. 후속.
- `_KR_SUPPLEMENTS` 하드코딩 — `accountMappings.json` 에 흡수 필요. 후속.

---

## 관련 문서

- `src/dartlab/README.md` — Company facade (sections 사상, 4 namespace, canHandle 라우팅)
- `src/dartlab/analysis/README.md` — analysis 엔진 + SSOT 헬퍼 위치
- `src/dartlab/analysis/CREDIT.md` — credit 독립 엔진
- `src/dartlab/providers/edgar/README.md` — DART/EDGAR 동기화 규칙
- `ops/code.md` — camelCase, 독스트링 9 섹션, 릴리즈, Git
- `ops/architecture.md` — 전체 청사진
