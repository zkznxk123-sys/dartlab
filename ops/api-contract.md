# API Contract — dartlab 호출 규칙 단일 진실의 원천

dartlab 의 모든 공개 API 가 따르는 contract 와 사상. 새 함수/엔진/property 를
추가하기 전에 이 문서를 먼저 읽고 contract 위반이 없는지 확인한다.

이 문서가 source of truth — 다른 ops 문서나 코드와 충돌하면 이 문서가 기준이다.

---

## 1. 단일 진입점 + 파라미터 계약 [최우선]

**원칙**: 같은 엔진은 단일 진입점에서 파라미터로 동작을 토글한다.
새 property/method 명칭을 늘리는 게 아니라 같은 호출에 옵션을 붙인다.

### 좋은 예

```python
c.show("IS")                    # 분기 (기본)
c.show("IS", annual=True)       # 연간
c.show("IS", cumulative=True)   # YTD 누적
c.timeseries                    # 분기 (기본)
c.timeseries(annual=True)       # 연간
```

### 나쁜 예 (금지)

```python
c.IS_annual                     # ✗ 새 property
c.IS_cumulative                 # ✗ 새 property
c.financeAnnual.IS              # ✗ 새 namespace
c.annual                        # ✗ 별도 property (deprecated)
c.cumulative                    # ✗ 별도 property (deprecated)
```

### 검증 방법

`grep -rn "def IS_\|def BS_\|def CF_\|annualDf\|financeAnnual" src/dartlab/` 결과 0 건.

---

## 2. 분기 기본 + 누적/연간은 파라미터 [최우선]

**원칙**: 모든 finance/timeseries 데이터의 schema 는 **분기 개별값** 이 기본이다.
시계열 view 에 분기+연간 동시 노출은 schema noise — 사용자가 어떤 컬럼이 분기인지
연간인지 헷갈린다.

| 모드 | 호출 | schema |
|---|---|---|
| 분기 (기본) | `c.show("IS")` | `2025Q4, 2025Q3, ..., 2024Q1` |
| 연간 | `c.show("IS", annual=True)` | `2025, 2024, 2023, ...` |
| 누적 (YTD) | `c.show("IS", cumulative=True)` | `2025Q4(Y), 2025Q3(YTD), ...` |

### 합산 규칙

- **IS / CIS / CF (flow)**: 4분기 모두 있을 때만 단순 합 (3분기 이하 → None)
- **BS (stock)**: Q4 (= 연말잔액). 없으면 그 해 가장 최근 분기

### 내부 SSOT

분기 → 연간 합성 로직은 `core/finance/flow.py::synthesizeAnnualFromQuarters` 한
함수에만 존재. `toDict`, `toDictBySnakeId`, `_financeToDataFrame` 모두가 위임.

---

## 3. 파라미터 이름 일관성 [최우선]

같은 의미의 옵션은 모든 함수에서 같은 이름을 쓴다. 신규 코드는 이 이름만 허용.

| 표준 | 의미 | 금지된 변형 |
|---|---|---|
| `annual: bool` | 분기→연간 합산 토글 | `includeAnnual`, `withAnnual`, `is_annual`, `yearly` |
| `cumulative: bool` | 분기 누적 (YTD) 토글 | `cum`, `ytd`, `accumulated`, `running_sum` |
| `basePeriod: str \| None` | 분석 기준 시점 | `as_of`, `asOf`, `cutoff`, `referenceDate` |
| `stockCode: str` | 종목코드 | `code`, `corp`, `ticker`, `symbol` |
| `period: str \| list[str] \| None` | 단일/복수 기간 필터 | `quarter`, `year`, `time`, `dt` |
| `topic: str` | docs/finance topic 키 | `category`, `block`, `kind` |
| `maxYears: int` | 시계열 최대 연도 수 | `years_back`, `nYears`, `lookback` |
| `maxQuarters: int` | 시계열 최대 분기 수 | `quarters_back`, `nQuarters` |
| `withFallback: bool` | fallback 경로 활성 | `useFallback`, `enable_fallback` |
| `dryRun: bool` | 실제 실행 없이 미리보기 | `simulate`, `preview` |

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

- `analysis ↛ credit, credit ↛ analysis` — 같은 L2 지만 서로 호출 안 함
- `analysis ↛ macro, macro ↛ analysis` — 같은 L2 지만 서로 호출 안 함
- 공유 데이터는 L0/L1 (core/, providers/, gather/) 에서 직접 가져온다
- 공유 헬퍼 (예: `toDictBySnakeId`, `sumBorrowingsKorean`) 는 한 위치에서 import — SSOT 단일 함수
- 해석의 조합은 review (L2 조립) 또는 AI (L3) 의 몫

### import 방향

```
L0 (core) ← L1 (providers/gather/scan/quant) ← L2 (analysis/macro/credit) ← review ← L3 (ai)
교차 관심사: guide/ (모든 레이어에서 import 가능)
```

CI sentinel `tests/test_imports.py` 가 강제.

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
- 동기화 검증: `bash scripts/test-lock.sh tests/ -k "test_edgar_has_all_dart_public_methods" -v`

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

## 12. ops/ 가 source of truth

- 코드 ↔ ops/ 충돌 시 코드 기준으로 ops 갱신
- `ops/api-contract.md` (이 문서) 가 모든 API 규칙의 진입점
- 엔진별 상세는 `ops/{engine}.md` 참조
- 사상 변경 / 새 규칙 추가 시 이 문서 갱신 필수

---

## 위반 카탈로그 (Plan v9 fix 대상)

| 위반 | 위치 | 조치 |
|---|---|---|
| `c.annual` 별도 property | `providers/dart/company.py:3875` | `c.timeseries(annual=True)` 로 통합 |
| `c.cumulative` 별도 property | `providers/dart/company.py:3909` | `c.timeseries(cumulative=True)` 로 통합 |
| `_FinanceAccessor.annual` | `providers/dart/_finance_accessor.py:47` | 동일 |
| `_FinanceAccessor.cumulative` | `providers/dart/_finance_accessor.py` | 동일 |
| EDGAR `c.annual` | `providers/edgar/company.py:740` | DART 와 동일 동기화 |
| `_financeToDataFrame(includeAnnual=...)` 내부 파라미터명 | `providers/dart/_finance_helpers.py:133` | `annual=...` 로 rename |
| `c.show()` / `c.select()` 에 `annual` 옵션 미노출 | `providers/dart/company.py:2018` | 사용자 진입점에 옵션 추가 |

---

## 관련 문서

- `ops/company.md` — Company facade (sections 사상, 4 namespace, canHandle 라우팅)
- `ops/analysis.md` — analysis 엔진 + SSOT 헬퍼 위치
- `ops/credit.md` — credit 독립 엔진
- `ops/edgar.md` — DART/EDGAR 동기화 규칙
- `ops/code.md` — camelCase, 독스트링 9 섹션, 릴리즈, Git
- `ops/architecture.md` — 전체 청사진
