# EDGAR

SEC EDGAR 수집·분석의 단일 진실의 원천. DART와 **동일 인터페이스**를 유지하되 소스/구조가 다르다.

---

## ⛔ [최상위 원칙] dartlab EDGAR finance = SEC 벌크

> **dartlab의 EDGAR finance는 SEC 벌크가 primary 소스다.**
>
> - 매일 벌크: `Archives/edgar/daily-index/xbrl/companyfacts.zip` (1.37GB, 매일 04:25 UTC)
> - 분기 벌크: `files/dera/data/financial-statement-data-sets/{Y}q{Q}.zip` (sub/pre/tag TSV, 분기말 +2~3개월)
> - **num.tsv는 받지 않는다** — companyfacts.zip이 같은 값의 더 신선한 번들
> - dartlab은 벌크 파생 parquet을 **HuggingFace에 미러링**해서 사용자에게 제공
>
> **`data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json` API는 dartlab 내부 파이프라인에서 사용하지 않는다.**
> 사용자가 최신성을 명시적으로 요청할 때(`c.finance.refreshFromApi()`)만 호출되는 **선택 경로**.
> 자동 수집/프리빌드/HF 배포는 전부 벌크 경로를 쓴다.

**근거:**
1. companyfacts API per-ticker 수집은 16,601 CIK 기준 수 시간 소요 + SEC rate limit 10 req/s에 노출
2. 분기 `pre.tsv`의 **plabel** (회사 고유 표시명) 컬럼은 API에 존재하지 않음 → 계정 매핑 학습 파이프라인에 필수
3. `learnedSynonyms.json` 10,680개 + `standardAccounts.json` 206개 원설계가 tag+plabel 조인으로 학습됨
4. 사용자 1인당 수만 건 API 호출 대신 HF에서 한 번 1.3GB 받으면 전 종목 분석 가능

---

## 데이터 소스 매트릭스

| 소스 | URL | 주기 | 크기 | 역할 |
|------|-----|------|------|------|
| **companyfacts.zip** | `Archives/edgar/daily-index/xbrl/companyfacts.zip` | 매일 04:25 UTC | 1.37GB | **num (값) primary** — {cik}.json 전체 회사 번들 |
| **{Y}q{Q}.zip** | `files/dera/data/financial-statement-data-sets/{Y}q{Q}.zip` | 분기별 (분기말 +2~3개월) | 66~128MB | **sub/pre/tag** — plabel, stmt, line, inpth, adsh |
| ~~num.tsv~~ | (분기 zip 안에 있음) | — | — | **받지 않음** (companyfacts가 원본) |
| companyfacts API | `data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json` | on-demand | per-ticker JSON | **사용자 선택** — `c.finance.refreshFromApi()` 만 호출 |
| submissions API | `data.sec.gov/submissions/CIK{cik}.json` | on-demand | per-ticker | docs 수집 경로 (10-K/10-Q filing 목록) |

### 분기 벌크에서 받는 파일

| 파일 | 키 컬럼 | 내용 |
|------|---------|------|
| **sub.txt** | adsh | cik, form, period, fy, fp, filed (accession 메타데이터) |
| **pre.txt** | adsh, tag | **plabel**, stmt, line, inpth (회사 표시명 + 계층) |
| **tag.txt** | tag, version | tlabel, definition, datatype (XBRL tag 정의) |
| ~~num.txt~~ | — | **받지 않음** (companyfacts.zip이 원본) |

---

## 로컬 저장 구조

```
data/edgar/
├── _bulk/                               # 원본 zip (gitignore, HF 미업로드)
│   ├── companyfacts.zip                 # daily 다운로드
│   └── quarterly/
│       ├── 2024q1.zip
│       ├── 2024q2.zip
│       └── ...
├── finance/{cik}.parquet                # companyfacts 파생 (HF 업로드)
├── meta/                                # 분기 메타 (HF 업로드)
│   ├── sub/{Y}Q{Q}.parquet
│   ├── pre/{Y}Q{Q}.parquet
│   └── tag/{Y}Q{Q}.parquet
├── docs/{ticker}.parquet                # 10-K/10-Q HTML 섹션 (HF 업로드)
└── scan/finance.parquet                 # 전종목 프리빌드 (HF 업로드)
```

### HF 배포 정책 — dartlab 파생물만

| 카테고리 | 원본 소스 | HF 미러링 | 이유 |
|---------|----------|:-----:|------|
| `edgar` (finance) | SEC `companyfacts.zip` daily | ❌ | 사용자 PC 자동 다운로드·변환 (원본이 공개 벌크) |
| `edgarMeta` | SEC `{Y}q{Q}.zip` quarterly | ❌ | 사용자 PC 자동 다운로드·변환 (원본이 공개 벌크) |
| `edgarDocs` | SEC submissions API + HTML 파싱 | ✅ | dartlab 파생물 (섹션 추출 결과) |
| `edgarScan` | `buildEdgarFinance()` 프리빌드 | ✅ | dartlab 파생물 (재계산 비용 큼) |

**원칙:**
- SEC 자체 공개 벌크가 있는 데이터(finance, meta)는 **HF 미러링 없음** — dartlab 이 SEC 에서 직접 받아 로컬 변환
- dartlab 계산 파생물(scan, docs)만 HF 업로드 — 사용자가 직접 만들기에 시간 오래 걸림
- HF 정책은 `providers/edgar/openapi/deploy.py::_BULK_ORIGIN_CATEGORIES` 가 finance/meta 를 차단한다

---

## 핵심 규칙: DartCompany ↔ EdgarCompany 동기화

1. **DartCompany에 public 메소드를 추가하면 EdgarCompany에도 추가한다.**
2. DART 전용 메소드는 `test_protocol.py`의 `_DART_ONLY_EXEMPT`에 **사유 주석과 함께** 등록한다.
3. `_DART_ONLY_EXEMPT` 등록 없이 DART에만 메소드를 추가하면 테스트가 실패한다.

### EXEMPT 등록 기준

EXEMPT에 등록할 수 있는 경우:
- **데이터 소스 구조 차이**: DART 로컬 parquet vs EDGAR on-demand API (`rawDocs`, `update` 등)
- **한국 시장 전용**: KRX listing 기반 기능 (`codeName`, `resolve`, `search`, `listing`)
- **DART report 전용 구조화 데이터**: SEC에 동등한 구조가 없는 경우 (`network`)

EXEMPT에 **등록하면 안 되는** 경우:
- 범용 분석 기능 (analysis, review, forecast, valuation)
- CompanyProtocol 필수 메소드
- 사용자 대면 메소드 (ask, chat, review, insights)

---

## 수집 파이프라인

### 자동 경로 (dartlab 내부, 벌크 기반)

```
매일 04:30 UTC (companyfacts.zip 갱신 직후)
  ↓
downloadCompanyfactsBulk()        # 1.37GB zip
  ↓
extractCompanyfactsZip()          # 스트리밍 해제
  ↓
convertBulkToParquets()           # {cik}.parquet 16,601개 생성
  ↓
discoverLatestQuarter()           # 새 분기 있나?
  ↓ (있으면)
downloadQuarterlyDataset(Y, Q)    # {Y}q{Q}.zip
  ↓
convertQuarterlyToParquets()      # sub/pre/tag parquet
  ↓
buildEdgarFinance(sinceYear=2021) # scan 프리빌드
  ↓
deployEdgarToHF(["finance", "meta", "scan", "docs"])
```

### 사용자 선택 경로 (optional)

```python
# 사용자가 공시 당일 최신 분기 즉시 반영 원할 때만
c = Company("AAPL")
c.finance.refreshFromApi()  # companyfacts API → 로컬 parquet 덮어쓰기
```

- API 경로는 rate limit 10 req/s, user-agent 헤더 필수
- 기본 파이프라인·프리빌드·HF 배포 로직은 이 경로를 **사용하지 않음**

### docs 수집 (10-K/10-Q HTML)

docs는 XBRL 벌크에 본문이 포함되지 않으므로 submissions API에서 개별 filing URL 추출 → HTML fetch → section 파싱.
이 경로는 그대로 유지 (벌크 개념 없음).

---

## 2-Tier 계정 매핑 시스템

### Layer 1: STANDARD (고정) — `mapperData/standardAccounts.json`
- 206개 표준계정 (BS 54 / IS 42 / CF 53 / EQ 6 / CI 4 / NT 20+)
- 344개 commonTags (XBRL tag → snakeId 직접 매핑, confidence 1.0)

### Layer 2: LEARNED (동적) — `mapperData/learnedSynonyms.json`
- 10,680개 `tagMappings` (소문자 정규화 tag → snakeId)
- `plabelMappings` (회사별 표시명 → snakeId) — **벌크 pre.tsv 기반 학습**
- Source: 원설계 `_reference/eddmpython/v1/synonymLearner.py` 이식

### 매핑 우선순위 (`mapper.py::EdgarMapper.mapToDart`)

1. `STMT_OVERRIDES` — 같은 tag가 IS/CF에서 다른 의미 (예: NetIncomeLoss + IS → net_profit, NetIncomeLoss + CF → net_income_cf)
2. `commonTags` — standardAccounts의 직접 매칭
3. `tagMappings` — learnedSynonyms 학습 태그
4. `plabelMappings` — learnedSynonyms 학습 plabel (pre.tsv 조인 시 활성)
5. `EDGAR_TO_DART_ALIASES` — snakeId DART 호환 변환

---

## Universal Select Bridge

`show.py::_bridgeKoreanSnakeId()` — 한국어 계정명과 snakeId 간 자동 번역:
- `Company("AAPL").select("IS", ["매출액"])` → `sales` row 반환
- `Company("005930").select("IS", ["sales"])` → `매출액` row 반환

### toDict Bridge

`_helpers.py::toDict()` — EDGAR DataFrame의 snakeId 키를 한국어 키로 자동 변환:
- analysis 함수에서 `data.get("매출액")` 이 DART/EDGAR 양쪽에서 동작

---

## 통화 포맷

- `review/builders.py`: `_REVIEW_CURRENCY` — review 렌더링 시 KRW/USD 분기
- `analysis/financial/capital.py`: `_ANALYSIS_CURRENCY` — analysis 금액 포맷 분기
- `review/registry.py::buildBlocks()`: `company.currency`에서 자동 설정

---

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

---

## 구조적 한계 (SEC 데이터 없음 — 허용된 None)

analysis 일부 축에서 DART report 전용 서브키가 None:

| 축 | None 키 | 원인 | SEC 대안 | 상태 |
|---|---|---|---|---|
| 수익구조 | segmentComposition | DART docs `productService` 전용 | **XBRL segment revenue fallback 동작** (`revenue.py:80-169`) | ✅ 해결 |
| 비용구조 | rawMaterialBreakdown | DART report `rawMaterial` API 전용 | SEC에 구조화 데이터 없음 | ⚠ 한계 인정 |
| 자본배분 | treasuryStockStatus | DART report `treasuryStock` 상세 API 전용 | **XBRL `purchase_of_treasury_stock` fallback 추가** | ✅ 해결 |
| 투자효율 | investmentInOther | DART report `investedCompany` API 전용 | SEC에 구조화 데이터 없음 | ⚠ 한계 인정 |

**4건 중 2건 해결** (segmentComposition XBRL + treasuryStockStatus XBRL). 나머지 2건은 SEC 구조적 한계.
DART report는 OpenDART API가 구조화 테이블을 직접 제공하지만, SEC에는 동등한 구조화 API가 없다.

---

## scan 11 축 (EDGAR)

| 축 | 지표 | 커버리지 |
|---|------|---------|
| profitability | opMargin, netMargin, ROE, ROA | ~6,600 |
| growth | revenueYoY, opYoY, niYoY | ~5,600 |
| quality | cfToNi, accrualRatio | ~8,300 |
| liquidity | currentRatio, quickRatio | ~4,800 |
| efficiency | assetTurnover, CCC | ~6,100 |
| cashflow | OCF/ICF/FCF, 패턴 분류 | ~5,700 |
| dividendTrend | payoutRatio, 패턴 | ~4,000 |
| capital | 배당+자사주, 분류 | ~4,800 |
| debt | debtRatio, ICR, 위험등급 | ~7,300 |
| valuation | EBITDA, equityMultiplier, ROE | ~16,500 |
| audit | AuditFees, NonAuditFees | 가변 |

데이터 소스: `data/edgar/scan/finance.parquet` — `buildEdgarFinance(sinceYear=2021)` 프리빌드.
33개 계정 × 전체 CIK × 연간 (form=10-K) 기준.

---

## 테스트

```bash
# 프로토콜 동기화 (DART ↔ EDGAR method parity)
bash scripts/dev/test-lock.sh tests/ -k "test_edgar_has_all_dart_public_methods" -v

# Protocol 적합성 전체
bash scripts/dev/test-lock.sh tests/test_protocol.py -v

# EDGAR 전용
bash scripts/dev/test-lock.sh tests/ -k "edgar" -v --tb=short

# 벌크 다운로더
bash scripts/dev/test-lock.sh tests/test_edgarBulk.py -v
```

---

## 관련 코드

| 파일 | 역할 |
|------|------|
| `src/dartlab/providers/edgar/bulk/companyfactsBulk.py` | daily 벌크 다운·파싱 |
| `src/dartlab/providers/edgar/bulk/datasetBulk.py` | 분기 벌크 다운·파싱 (num.tsv 제외) |
| `src/dartlab/providers/edgar/bulk/freshness.py` | 벌크 TTL 관리 |
| `src/dartlab/providers/edgar/openapi/facts.py` | companyfacts JSON → rows (재사용) |
| `src/dartlab/providers/edgar/openapi/batch.py` | docs 수집 (10-K/10-Q HTML) |
| `src/dartlab/providers/edgar/openapi/deploy.py` | HF 업로드 (`upload_folder`) |
| `src/dartlab/providers/edgar/finance/mapper.py` | tag/plabel → snakeId 매핑 |
| `src/dartlab/providers/edgar/finance/merge.py` | num + pre + sub 조인 (학습용) |
| `src/dartlab/providers/edgar/finance/learner.py` | plabel 기반 학습 (eddmpython 이식) |
| `src/dartlab/providers/edgar/finance/pivot.py` | XBRL facts → 분기별 시계열 |
| `src/dartlab/providers/edgar/company.py::refreshFromApi` | 사용자 선택 API 경로 |
| `src/dartlab/scan/edgarBuilder.py` | scan 프리빌드 |
| `.github/workflows/edgarSync.yml` | 벌크 기반 CI 수집 |
