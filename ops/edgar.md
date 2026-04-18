# EDGAR 동기화 규칙

DartCompany ↔ EdgarCompany 인터페이스 동기화의 단일 규칙 문서.
데이터 소스/수집/분석 동작은 각 엔진 문서에 통합되어 있다:
- 데이터 수집/배포/freshness → `ops/data.md`, `ops/edgar.md`
- Company namespace/notes/데이터 소스 차이 → `ops/company.md`
- scan EDGAR 11축/프리빌드 → `ops/scan.md`
- gather market 분기 → `ops/gather.md`
- analysis 통화/브릿지 → `ops/analysis.md`
- review 통화 포맷 → `ops/review.md`

## ⛔ [최상위 원칙] dartlab EDGAR finance = SEC 벌크

**dartlab의 EDGAR finance primary 소스는 SEC 벌크.** 자동 파이프라인·프리빌드·HF 배포는 전부 벌크 경로를 쓴다.

- 매일: `Archives/edgar/daily-index/xbrl/companyfacts.zip` (1.37GB, 매일 04:25 UTC)
- 분기: `files/dera/data/financial-statement-data-sets/{Y}q{Q}.zip` (sub/pre/tag, 분기말 +2~3개월)
- **num.tsv는 받지 않는다** — companyfacts.zip이 같은 값의 더 신선한 번들
- `data.sec.gov/api/xbrl/companyfacts` API는 **사용자 선택 경로** (`c.refreshFromApi()`) 만 사용

상세: `ops/edgar.md`.

## 한눈에 보기

| 항목 | 상태 |
|------|------|
| 안정성 | beta (DART core stable 이후) |
| Provider | `providers/edgar/` — CompanyProtocol 완전 구현 |
| 방어막 | `test_protocol.py::test_edgar_has_all_dart_public_methods` |
| 데이터 | HuggingFace `eddmpython/dartlab-data` — `edgar/finance` (벌크 파생), `edgar/meta` (분기 sub/pre/tag), `edgar/docs` (10-K/10-Q), `edgar/scan` (프리빌드) |
| **수집 주기** | daily: companyfacts.zip (04:30 UTC) + 분기: 새 `{Y}q{Q}.zip` 감지 시 |
| **대상** | 나스닥+NYSE ~7,557종목 |
| **프리빌드** | `edgar/scan/finance.parquet` — 33계정 전종목 연간 (2021~) |
| **sectorKpi** | XBRL segments fallback으로 EDGAR도 4업종 KPI 부분 지원 |
| 안내 | EDGAR 벌크(`downloadCompanyfactsBulk` / `convertBulkToParquets`)는 `edgar:bulk_start/done` 이벤트로 시작·완료를 알린다 |

## 핵심 규칙: DartCompany ↔ EdgarCompany 동기화

1. **DartCompany에 public 메소드를 추가하면 EdgarCompany에도 추가한다.**
2. DART 전용 메소드는 `test_protocol.py`의 `_DART_ONLY_EXEMPT`에 **사유 주석과 함께** 등록한다.
3. `_DART_ONLY_EXEMPT` 등록 없이 DART에만 메소드를 추가하면 테스트가 실패한다.

## EXEMPT 등록 기준

EXEMPT에 등록할 수 있는 경우:
- **데이터 소스 구조 차이**: DART 로컬 parquet vs EDGAR 벌크/API (`rawDocs`, `update` 등)
- **한국 시장 전용**: KRX listing 기반 기능 (`codeName`, `resolve`, `search`, `listing`)
- **DART report 전용 구조화 데이터**: SEC에 동등한 구조가 없는 경우 (`network`)

EXEMPT에 **등록하면 안 되는** 경우:
- 범용 분석 기능 (analysis, review, forecast, valuation)
- CompanyProtocol 필수 메소드
- 사용자 대면 메소드 (ask, chat, review, insights)

## EDGAR 전용 메서드 (DART에 없음)

- `refreshFromApi()` — 사용자가 SEC companyfacts API로 즉시 최신화 (자동 파이프라인 비사용)

## Universal Select Bridge

`show.py::_bridgeKoreanSnakeId()` — 한국어 계정명과 snakeId 간 자동 번역:
- `Company("AAPL").select("IS", ["매출액"])` → `sales` row 반환
- `Company("005930").select("IS", ["sales"])` → `매출액` row 반환

## toDict Bridge

`_helpers.py::toDict()` — EDGAR DataFrame의 snakeId 키를 한국어 키로 자동 변환:
- analysis 함수에서 `data.get("매출액")` 이 DART/EDGAR 양쪽에서 동작

## 통화 포맷

- `review/builders.py`: `_REVIEW_CURRENCY` — review 렌더링 시 KRW/USD 분기
- `analysis/financial/capital.py`: `_ANALYSIS_CURRENCY` — analysis 금액 포맷 분기
- `review/registry.py::buildBlocks()`: `company.currency`에서 자동 설정

## EDGAR alias 확장 (select bridge)

`core/finance/labels.py::SNAKEID_ALIASES` — DART ↔ EDGAR snakeId 통합 alias dict (L0):
- `cash_flows_from_financing` → `cash_flows_from_financing_activities`
- `capex` → `purchase_of_property_plant_and_equipment`
- `revenue` → `sales`, `net_income` → `net_profit` 등 44개
- `show.py::_expandEdgarAliases()` 와 `mapper.py::EDGAR_TO_DART_ALIASES` 모두 이 dict 사용
- analysis calc 함수에서 한국어 계정명 사용 → bridge → alias 확장 → EDGAR 매칭

`_quarterlyCols()` / `quarterlyColsFromPeriods()` — EDGAR 연간 데이터 fallback:
- DART: 2025Q4, 2025Q3... (분기)
- EDGAR: 2024, 2023... (연간)
- `"Q" in c` 매칭 실패 시 4자리 연도 컬럼으로 fallback

### pivot frame 필터 이슈 (2026-04 수정)

`providers/edgar/finance/pivot.py::_selectStandalone` — `frame.is_null()` 필터 제거.
SEC companyfacts는 FY 행에 `CY2025`, Q2 standalone 행에 `CY2025Q2` 같은 frame을 정상 부여하므로,
이 필터를 걸면 FY/Q2/Q3 standalone 값이 전부 날아가서 2025Q4 역산 불가 → 분기 데이터 누락.
downstream `_selectFlowDirect`의 `duration_days` 필터가 이미 standalone/YTD를 구분하므로
frame 필터는 불필요하고 오히려 유해함.

### period 캘린더 앵커링 (2026-04-16 도입)

`core/finance/period.py::buildFiscalToCalendarMap` SSOT — pivot 후 column rename
(`{fy}-{fp}` → `{calYear}-{calQ}`) 으로 비-12월 결산 EDGAR 종목을 캘린더 기준으로 통일.
DART(Dec 결산 99%) 는 identity, EDGAR 의 비-Dec 결산만 실제 변환.

| 회사 | FY 결산 | fiscal 라벨 | 캘린더 라벨 (Capital IQ end-month) |
|---|---|---|---|
| MNST/INTC/CPNG/OKLO | Dec | `2025-Q4` | `2025-Q4` (변화 없음) |
| UAA | Mar | `2026-Q3` (FY26 Q3) | `2025-Q4` (end Dec 2025) |
| AAPL | Sep | `2026-Q1` (FY26 Q1) | `2025-Q4` (end Dec 2025) |
| NKE | May | `2026-Q3` (FY26 Q3) | `2026-Q1` (end Feb 2026, 비-aligned) |

**규칙**:
- end-month 매핑 (Capital IQ): Feb-Apr→Q1, May-Jul→Q2, Aug-Oct→Q3, Nov-Dec-Jan→Q4
- pivot 내부 (`_selectStandalone`/`_pivotTimeseries`/`_computeQ4`) 는 fiscal 라벨로 동작
- `_buildTimeseriesFromFacts` 끝에서 한 번 rename (downstream 무영향)
- noise 필터: FY rows duration ≥ 300일, end month + year offset 정확 매칭, ±45일 윈도우 (52-week 달력 수용)

**근본**: 4 비교 가능성 (회사간 비교) — DART `2025Q4` ↔ EDGAR `2025Q4` 동일 키로 cross-company join 가능.
이전엔 fiscal label 그대로라 UA `2026Q3` 와 Samsung `2025Q4` 가 같은 시점인데 다른 컬럼.

## 구조적 한계 (SEC 데이터 없음 — 허용된 None)

analysis 일부 축에서 DART report 전용 서브키가 None:

| 축 | None 키 | 원인 | SEC 대안 | 상태 |
|---|---|---|---|---|
| 수익구조 | segmentComposition | DART docs `productService` 전용 | **SEC companyfacts API가 XBRL segment axis(dimension/member) 를 제공하지 않음.** 이전 XBRL fallback 시도(`_selectEdgarSegmentRevenue`) 는 기간 재공시를 segment 로 오판하는 구조적 문제로 2026-04-15 제거. 실제 segment 복원은 10-K 본문 파싱 또는 raw XBRL instance 파이프라인 필요 | ⚠ 한계 인정 |
| 비용구조 | rawMaterialBreakdown | DART report `rawMaterial` API 전용 | SEC에 구조화 데이터 없음 | ⚠ 한계 인정 |
| 자본배분 | treasuryStockStatus | DART report `treasuryStock` 상세 API 전용 | **XBRL `purchase_of_treasury_stock` fallback 추가** | ✅ 해결 |
| 투자효율 | investmentInOther | DART report `investedCompany` API 전용 | SEC에 구조화 데이터 없음 | ⚠ 한계 인정 |

**4건 중 1건 해결** (treasuryStockStatus XBRL). 나머지 3건은 SEC 구조적 한계.
DART report는 OpenDART API가 구조화 테이블을 직접 제공하지만, SEC에는 동등한 구조화 API가 없다.
segmentComposition 복원은 별도 프로젝트 — 후보 경로: 10-K Item 1/16 텍스트 블록 파싱, SEC `frames` API + dimension, 또는 외부 소스(FMP segment API 등).

## 테스트

```bash
# 동기화 테스트
bash scripts/dev/test-lock.sh tests/ -k "test_edgar_has_all_dart_public_methods" -v

# Protocol 적합성 전체
bash scripts/dev/test-lock.sh tests/test_protocol.py -v

# EDGAR 전용 테스트
bash scripts/dev/test-lock.sh tests/ -k "edgar" -v --tb=short

# 벌크 다운로더 단위 테스트
bash scripts/dev/test-lock.sh tests/test_edgarBulk.py -v
```
