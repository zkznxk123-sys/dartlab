# Data

**주체**: 데이터 파이프라인 (HuggingFace `eddmpython/dartlab-data` + 자동 수집 워크플로우).
**현재**: 핵심 데이터 워크플로우 (DART/EDGAR/KRX 가격/KRX 지수/metadata/신규 종목 bootstrap/감사) · concurrency group 직렬화 · SEC 벌크 primary · 429 Retry-After 대응.
**방향**: realtime freshness 모니터링 대시보드 · 분기 DART 재정산 자동 감지 · cross-source validator.

HuggingFace 데이터셋 관리, 자동 수집 파이프라인, 프리빌드, 모니터링. 각 섹션은 **"이렇게 한다"** 명제로 열고, 반복된 실수는 섹션 하단 **"반복 실패"** 에 정리한다.

| 항목 | 내용 |
|------|------|
| 레이어 | L0 (core/dataConfig, dataLoader) |
| 진입점 | `Company("005930")` 시 자동 다운로드 |
| 데이터셋 | HuggingFace `eddmpython/dartlab-data` |
| 소비 | Company, providers, scan, analysis 전체 |

---

## 1. 자동 파이프라인 — 핵심 데이터 워크플로우로 간다

핵심 데이터 워크플로우는 단일 책임 · concurrency group 직렬화 원칙을 따른다.

```
cron (UTC)  KST       Workflow               역할
──────────  ────────  ─────────────────────  ─────────────────────────────────
00:00       09:00     kindlist.yml           KRX 상장사 + DART 법인 목록
01:00       10:00     dartNewStocks.yml      KindList 신규 종목 DART 기본 parquet bootstrap
04:30       13:30     edgarSync.yml          EDGAR daily 벌크 (companyfacts.zip)
06:00       15:00     dataSync.yml (#1)  ┐
18:00       03:00+1   dataSync.yml (#2)  ┴── DART list.json 신규 공시 (12h 주기)
[workflow_run (completed+success)]
                      dataPrebuild.yml       DART scan 프리빌드 → HF
11:00       20:00     buildKrxData.yml       KRX OpenAPI 일별 전종목 장마감 후 T-0 incremental → HF (krx/prices)
11:20       20:20     buildKrxIndexData.yml  KRX OpenAPI idx 시장군별 지수 장마감 후 T-0 incremental → HF (krx/indices)
20:00       05:00+1   dataAudit.yml          핵심 워크플로우 health check → Issue
일요일 03:00 12:00    edgarSync.yml (full)   EDGAR 주간 정산 (docs 포함)
```

**원칙:**
- **단일 책임**: DART 수집(dataSync) · DART 프리빌드(dataPrebuild) · EDGAR 전체(edgarSync) · 감사(dataAudit) 독립.
- **직렬화**: 모든 HF 업로드는 `concurrency.group: hf-dataset-push` 로 순차 처리 (sliding-window 429 회피).
- **workflow_run 체인**: KindList 완료 → 신규 종목 bootstrap, DART 수집 완료 → 자동 프리빌드 트리거 (EDGAR 는 edgarSync 내부 end-to-end).
- **backup**: `dataSync.yml workflow_dispatch mode=full` 로 88 분기 차집합 수동 실행.

### 수집 경로 (가벼움 vs 무거움)

| 경로 | 호출 | 동작 | 시간 | 자동 |
|---|---|---|---|---|
| **가벼움 (기본)** | dataSync.yml 자동 cron | list.json 발견 종목·분기만 수집 | 30 분 | KST 03/15 시 |
| **신규 종목 bootstrap** | dartNewStocks.yml 자동 cron/workflow_run | KindList와 HF parquet 목록 대조 후 누락 종목만 수집 | 신규 수에 비례 | KST 10 시 + KindList 성공 후 |
| 무거움 (백업) | dataSync.yml workflow_dispatch (mode=full) | 전 종목 88 분기 차집합 | 5 시간 | 수동만 |

**가벼움 경로 핵심**: `_discoverNewFilings`(syncRecent) 이 list.json + finance/docs 누락 검사로 정확한 종목·(year, reprt_code) 셋을 만들고, `batchCollect` 가 `targetPeriodsByCode` 로 받아서 `_buildAllPeriods()` 88 분기 우회.

**신규 종목 경로 핵심**: `syncNewStocks.py` 가 KindList 전체 종목과 HF `dart/{finance,report,docs}` parquet 목록을 대조한다. recent 공시가 없어도 HF에 파일이 없는 신규 종목은 `batchCollect` 로 bootstrap 하고, 변경 파일만 `uploadData.py` 로 업로드한다.

**반복 실패** — 동시 여러 워크플로우가 HF push → sliding-window 429 폭주. `hf-dataset-push` 단일 그룹으로 직렬화 확정.

---

## 2. Flow 1 — DART 수집 (dataSync.yml) 을 12h 주기로 돌린다

```
┌──────────────────────────────────────────────────────────────────────────┐
│ cron: UTC 06:00 / 18:00  (recent 모드 자동)                              │
│ 또는 workflow_dispatch (mode=full)                                       │
└──────┬───────────────────────────────────────────────────────────────────┘
       │
       ▼  [concurrency: hf-dataset-push, cancel-in-progress=false]
┌──────────────────────────────────────────────────────────────────────────┐
│ Job: sync-finance-report  (matrix: finance, report)                      │
│                                                                          │
│ 1. actions/checkout@v5                                                   │
│ 2. uv sync                                                               │
│ 3. cache.restore  ← dartlab-data-{category}-                             │
│ 4. run: .github/scripts/syncRecent.py                                    │
│    env: DART_API_KEYS, SYNC_LOOKBACK_DAYS=60, SYNC_CATEGORIES=$cat       │
│    ├─ list.json 조회 (최근 60일 정기공시)                                 │
│    ├─ _existingFinanceReprts + rcept_no 비교 → 누락 (year, reprt_code)   │
│    ├─ pending.txt 선 회수 (이전 run API 한도 잘림)                       │
│    ├─ batchCollect(targetPeriodsByCode=...) — API 키 로테이션            │
│    ├─ 개별 실패 → warnings + data/dart/_collect_state/failures.json      │
│    └─ changed.txt 기록 (변경 parquet 파일 목록)                          │
│ 5. run: .github/scripts/uploadData.py --target hf                        │
│    env: HF_TOKEN, SYNC_CATEGORY=$cat                                     │
│    └─ changed.txt 읽어 100파일 배치로 HF upload (429 지수 backoff)       │
│ 6. cache.save  → dartlab-data-{category}-{run_id}                        │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│ Job: sync-docs  (동일 구조, but _collectDocsDirect ZIP 경로)             │
│  timeout-minutes: 150  (docs 가 큼)                                      │
└──────────────────────────────────────────────────────────────────────────┘

workflow_run trigger → Data Prebuild (DART) 자동 실행
```

**실패 시나리오:**
- API 한도 도달 → 큐 남은 종목은 `pending.txt` 에 기록, 다음 run 에서 회수.
- 네트워크 오류 → syncRecent 내부 재시도 3 회.
- HF 업로드 429 → `uploadData.py` 가 지수 backoff (30s → 60s → 120s → 240s).
- Job timeout (60 분) → 캐시는 저장됨, 다음 run 에서 이어받음.

---

## 2-1. Flow 1B — KindList 신규 종목은 별도 bootstrap 으로 보장한다

```
┌──────────────────────────────────────────────────────────────────────────┐
│ trigger: workflow_run (Update KindList completed+success)                │
│ 또는 cron: UTC 01:00 (KST 10:00) / workflow_dispatch                     │
└──────┬───────────────────────────────────────────────────────────────────┘
       │
       ▼  [concurrency: hf-dart-push, cancel-in-progress=false]
┌──────────────────────────────────────────────────────────────────────────┐
│ Job: sync-new-stocks                                                     │
│                                                                          │
│ 1. KindList 로 전체 상장 종목 로드 (코넥스 제외)                         │
│ 2. HF repo_info 로 dart/finance, dart/report, dart/docs 파일 목록 조회   │
│ 3. KindList - HF parquet = 신규 bootstrap 대상                           │
│ 4. category 별 batchCollect(codes, categories=[cat])                     │
│ 5. dist/changed_{cat}.txt 기록 → uploadData.py --target hf               │
│ 6. dataAudit 대상에 포함해 실패를 Issue 로 올림                          │
└──────────────────────────────────────────────────────────────────────────┘
```

**불변식:**
- 신규 종목 판정 원천은 KindList 와 HF parquet 목록이다. 별도 수동 종목 dict 를 만들지 않는다.
- recent sync 는 “공시 이벤트 기반”, 신규 종목 bootstrap 은 “상장 목록 기반”이다. 둘을 섞지 않는다.
- 카테고리별 제한(`NEW_STOCK_LIMIT`)은 자동화 파이프라인 보호 장치다. 제한에 걸린 나머지는 다음 실행에서 이어서 처리한다.

---

## 3. Flow 2 — DART scan 프리빌드 (dataPrebuild.yml) 은 workflow_run 으로 이어진다

```
┌──────────────────────────────────────────────────────────────────────────┐
│ trigger: workflow_run (Data Sync completed+success)                      │
│ 또는 workflow_dispatch                                                   │
└──────┬───────────────────────────────────────────────────────────────────┘
       │
       ▼  [concurrency: hf-dataset-push — dataSync 와 직렬]
┌──────────────────────────────────────────────────────────────────────────┐
│ Job: prebuild-scan                                                       │
│                                                                          │
│ 1. actions/checkout@v5                                                   │
│ 2. uv sync                                                               │
│ 3. cache.restore ← finance/report/docs (3개 병렬)                        │
│ 4. run: .github/scripts/prebuildData.py                                  │
│    env: HF_TOKEN                                                         │
│    ├─ buildChanges()  → dart/scan/changes.parquet                        │
│    ├─ buildFinance()  → dart/scan/finance.parquet (~200 배치)            │
│    ├─ buildReport()   → dart/scan/report/{12 apiType}.parquet            │
│    └─ huggingface_hub.upload_folder → HF dart/scan/                      │
│ 5. cache.save → dartlab-data-scan-{run_id}                               │
└──────────────────────────────────────────────────────────────────────────┘
```

**실패 시나리오:**
- workflow_run.conclusion != "success" → Job skip (if 조건).
- prebuild OOM → 배치 크기 200 유지, scan 파일 부분 파일(`_batch_*.parquet`) 잔존 → 다음 run 에서 덮어쓰기.
- HF upload_folder 429 → 재시도 없음, 다음 workflow_run 에서 재시도.

---

## 4. Flow 3 — EDGAR end-to-end (edgarSync.yml) 은 벌크 primary 로 간다

```
┌──────────────────────────────────────────────────────────────────────────┐
│ cron: UTC 04:30 (daily) / 일요일 03:00 (weekly full)                     │
│ 또는 workflow_dispatch (forceCompanyfacts/forceQuarterly/collectDocs)    │
└──────┬───────────────────────────────────────────────────────────────────┘
       │
       ▼  [concurrency: hf-dataset-push]
┌──────────────────────────────────────────────────────────────────────────┐
│ Job: collect                                                             │
│                                                                          │
│ 1. cache.restore ← dartlab-edgar-{bulk|finance|meta|docs}-               │
│ 2. [daily 벌크] downloadCompanyfactsBulk() + convertBulkToParquets()     │
│    ├─ ETag + TTL(24h) 기반 재다운로드 판정                                │
│    ├─ companyfacts.zip (1.37GB) 스트리밍 해제                             │
│    └─ 16,600+ CIK → data/edgar/finance/{cik}.parquet                     │
│ 3. [분기 벌크] discoverLatestQuarter() + downloadQuarterlyDataset()      │
│    ├─ 최근 4 분기 HEAD 체크 → 새 zip 감지 시 다운로드                     │
│    ├─ sub.tsv / pre.tsv / tag.tsv 만 (num.tsv 제외)                      │
│    └─ data/edgar/meta/{sub,pre,tag}/{Y}Q{Q}.parquet                      │
│ 4. [docs, weekly only] dartlab collect --tier all -c docs                │
│    └─ SEC submissions API → 10-K/10-Q HTML fetch → edgar/docs/           │
│ 5. [scan] buildEdgarFinance(sinceYear=2021) → edgar/scan/finance.parquet │
│    (33계정+meta × 전종목 연간, 배치 200)                                 │
│ 6. [HF 배포] deployEdgarToHF(["scan", "docs" if weekly])                 │
│    ├─ finance / meta 는 HF 미러링 안 함 (SEC 벌크가 원본, ops/edgar.md)   │
│    └─ upload_folder 단일 커밋 (rate limit 회피)                           │
│ 7. cache.save → 4개 병렬                                                 │
└──────────────────────────────────────────────────────────────────────────┘
```

**실패 시나리오:**
- SEC 서버 다운 → HEAD 요청 실패 시 다운로드 스킵, 다음 cron 재시도.
- companyfacts.zip 파싱 실패 → skipped/failed 카운터, converted CIK 는 유지.
- HF upload_folder 429 → deploy.py 가 예외 잡아 카테고리별 partial success.

---

## 5. Flow 4 — 일일 감사 (dataAudit.yml) 는 핵심 워크플로우 status 를 본다

```
┌──────────────────────────────────────────────────────────────────────────┐
│ cron: UTC 20:00 (KST 05:00) / workflow_dispatch                          │
└──────┬───────────────────────────────────────────────────────────────────┘
       │
       ▼  [concurrency: data-audit, cancel-in-progress=true]
┌──────────────────────────────────────────────────────────────────────────┐
│ Job: audit  (10min timeout)                                              │
│                                                                          │
│ 1. run: .github/scripts/monitorPipeline.py                               │
│    env: GH_TOKEN                                                         │
│    ├─ gh api repos/.../actions/workflows/{name}/runs (최근 N회)          │
│    ├─ 핵심 워크플로우 last-run status 확인:                              │
│    │  · Data Sync                                                        │
│    │  · DART New Stocks Sync                                             │
│    │  · Data Prebuild (DART)                                             │
│    │  · EDGAR Data Sync (Bulk)                                           │
│    │  · KRX Data Sync (Bulk)                                             │
│    │  · KRX Index Data Sync (Bulk)                                       │
│    │  · Update KindList                                                  │
│    ├─ 실패 발견 → pipeline-failure 라벨 Issue 생성/갱신                   │
│    └─ 전부 success → 열려있는 pipeline-failure Issue 자동 close          │
│ 2. GITHUB_STEP_SUMMARY 기록                                              │
└──────────────────────────────────────────────────────────────────────────┘
```

**실패 시나리오:**
- GH API rate limit → monitorPipeline.py 는 exit 0 (감사 자체는 성공, Issue 는 다음 run).
- 네트워크 장애 → timeout 10min 에서 종료.

---

## 6. Flow 5 — 법인 목록 갱신 (kindlist.yml) 은 KRX + OpenDART 크롤링

```
┌──────────────────────────────────────────────────────────────────────────┐
│ cron: UTC 00:00 (KST 09:00)                                              │
└──────┬───────────────────────────────────────────────────────────────────┘
       │
       ├─► Job: KindList  → updateKindList.py (KRX KIND 크롤링)
       │                     → metadata/corpList.parquet (상장사 전체)
       │                     → SHA256 비교 → 변경 시 HF + GH Release
       │
       └─► Job: DartList  → updateDartList.py (OpenDART CORPCODE.xml)
                             → metadata/dartList.parquet (115,000+ 법인)
                             → 동일 SHA256 비교 로직
```

### 데이터 흐름 시각화

```
┌────────────┐                                       ┌──────────────┐
│  DART API  │──rcept_no──► dataSync (cron 2x/day) ──► dataPrebuild │
│ list.json  │              └─ parquet (dart/*)    │  └─ scan/*    │
└────────────┘                                       └──────┬───────┘
                                                            │
┌────────────┐                                              ▼
│ SEC daily  │──zip(1.37G)──► edgarSync (cron daily)────► HuggingFace
│companyfacts│                └─ parquet (edgar/finance)   eddmpython/
│.zip        │                                             dartlab-data
└────────────┘                                              ▲
                                                            │
┌────────────┐                                              │
│ SEC quarter│──zip(60~130M)─► edgarSync (auto detect) ─────┤
│ {Y}q{Q}.zip│                └─ sub/pre/tag parquet        │
└────────────┘                                              │
                                                            │
┌────────────┐                                              │
│ KRX KIND   │──HTML crawl──► kindlist (cron daily) ────────┘
│ CORPCODE   │                └─ metadata/*.parquet
└────────────┘

                           ▼
                   dataAudit (cron daily)
                   └─ monitorPipeline.py
                      └─ GH Issue (pipeline-failure)
```

---

## 7. DATA_RELEASES — `core/dataConfig.py` 한 곳에서 관리한다

| 카테고리 | 경로 | 설명 | 자동 수집 |
|----------|------|------|-----------|
| docs | dart/docs | 공시 문서 (~8GB) | dataSync |
| finance | dart/finance | 재무제표 (~600MB) | dataSync |
| report | dart/report | 정기보고서 (~320MB) | dataSync |
| scan | dart/scan | 전종목 횡단분석 프리빌드 | dataPrebuild |
| allFilings | dart/allFilings | 전체 공시 원문 | 로컬 전용 |
| stemIndex | dart/stemIndex | Ngram+Synonym 역인덱스 | 로컬 전용 |
| aiKnowledge | ai/knowledge | AI 분석 지식 (인사이트/스킬/에러패턴) | push/pull |
| edgarDocs | edgar/docs | SEC EDGAR 공시 문서 (10-K/10-Q) | edgarSync, edgar-collect |
| edgar | edgar/finance | SEC EDGAR 재무 (**companyfacts.zip 벌크 파생**) | edgarSync (벌크) |
| edgarMeta | edgar/meta | EDGAR 분기 벌크 메타 (sub/pre/tag) | edgarSync (분기) |
| edgarScan | edgar/scan | EDGAR 전종목 scan 프리빌드 | edgar-collect --scan |
| edinetDocs | edinet/docs | EDINET 공시 (일본) | 로컬 전용 |
| edinet | edinet/finance | EDINET 재무 (일본) | 로컬 전용 |
| krxPrices | krx/prices | KRX 일별 전종목 OHLCV+시총+발행주식수 (raw long) | buildKrxData (cron KST 20:00 평일 T-0 incremental, 장중 수동 실행은 T-1) |
| krxIndices | krx/indices | KRX/KOSPI/KOSDAQ 시장군별 지수 OHLCV+거래대금+시가총액 (raw long) | buildKrxIndexData (cron KST 20:20 평일 T-0 incremental, 장중 수동 실행은 T-1) |
| macroFred | macro/fred | FRED 거시경제 시계열 (observations + manifest) | macroData (daily) |
| macroEcos | macro/ecos | ECOS 한국은행 거시경제 시계열 (observations + manifest) | macroData (daily) |

새 카테고리 추가: `DATA_RELEASES` 에 한 줄 + `brand.ts` data 블록 추가.

---

## 8. 워크플로우 상세 — 각 파일별 명세

### dataSync.yml — DART 수집 (메인)

- **스케줄**: 매일 UTC 06:00 (KST 15:00) + 18:00 (KST 03:00) — 12h 주기.
- **구조**: finance/report Job (list.json 경로) + docs Job (ZIP 수집).
- **흐름**: DART list.json → 최근 N 일 정기공시 → rcept_no 비교 → 새 보고서 종목만 수집 → 카테고리별 changed.txt → HF.
- **환경변수**: `DART_API_KEYS`, `HF_TOKEN`, `SYNC_CATEGORY`, `SYNC_MODE`.
- **모드**:
  - `recent` (자동, 기본): list.json 기반 경량 수집, ~30 분.
  - `full` (수동 dispatch): 88 분기 차집합, 5 시간.
- **API 키 로테이션**: 다중 키 순차 시도, 전체 한도 초과 시 graceful exit.
- **concurrency**: `hf-dataset-push` (모든 HF push 워크플로우와 직렬).

### dataPrebuild.yml — DART scan 프리빌드

- **트리거**: `workflow_run` (Data Sync 완료 + success 후 자동).
- **흐름**: 3 개 캐시 복원 (finance/report/docs) → `prebuildData.py` → buildScan() → HF `upload_folder`.
- **출력**: `dart/scan/changes.parquet` · `finance.parquet` · `report/12 개 apiType.parquet`.
- **EDGAR 프리빌드는 edgarSync.yml 이 전담** (여기선 DART 전용).
- **타임아웃**: 120 분.

### edgarSync.yml — EDGAR 통합 수집 (벌크 기반)

> **dartlab EDGAR finance primary 소스는 SEC 벌크.** `data.sec.gov/api/xbrl/companyfacts` API 는 사용자가 명시적으로 요청할 때 (`c.refreshFromApi()`) 만 호출되는 **선택 경로**. 자동 CI·프리빌드·HF 배포는 전부 벌크를 쓴다. 상세: `ops/edgar.md`.

- **스케줄**: 매일 UTC 04:30 (companyfacts.zip 갱신 04:25 직후) + 일요일 전체 정산.
- **finance (daily 벌크)**:
  - `downloadCompanyfactsBulk()` — `Archives/edgar/daily-index/xbrl/companyfacts.zip` (1.37GB).
  - `convertBulkToParquets()` — 16,601 개 {cik}.parquet 일괄 생성.
- **meta (분기 벌크)**:
  - `discoverLatestQuarter()` — SEC 에 새 `{Y}q{Q}.zip` 있나 체크.
  - `downloadQuarterlyDataset(Y, Q)` + `convertQuarterlyToParquets()` — sub/pre/tag parquet.
  - `num.tsv 는 받지 않음` (companyfacts.zip 이 원본).
- **docs (submissions API 경로)**: 10-K/10-Q HTML fetch 는 벌크 개념 없음, 기존 경로 유지.
- **scan 프리빌드**: `buildEdgarFinance(sinceYear=2021)` → `edgar/scan/finance.parquet`.
- **HF 업로드**: `deployEdgarToHF(["finance", "meta", "scan", "docs"])` — 카테고리별 `upload_folder` 단일 커밋.
- **유니버스**: `loadEdgarTargetUniverse(tier)` — all=7,557 / nasdaq=4,256 / nyse=3,273 / sp500=500.
- **타임아웃**: 180 분.
- **캐시**: `dartlab-edgar-bulk`, `dartlab-edgar-docs` (run_id 없이 덮어쓰기).

### kindlist.yml — KRX 종목 리스트 + DART 전체 법인 목록

- **스케줄**: 매일 UTC 00:00 (KST 09:00).
- **2 가지 수집**:
  - **KindList**: KRX KIND 크롤링 → `metadata/corpList.parquet` (상장사 전체).
  - **DartList**: OpenDART CORPCODE.xml → `metadata/dartList.parquet` (전체 법인 115,000+, corp_code 8 자리).
- **흐름**: 각각 SHA256 비교 → 변경 시만 GitHub Release + HuggingFace 업로드.
- **후속**: 성공 시 `DART New Stocks Sync` 가 KindList 기준 신규 종목의 `finance/report/docs` 누락 parquet 을 bootstrap 한다.

### dartNewStocks.yml — KindList 신규 종목 bootstrap

- **스케줄**: 매일 UTC 01:00 (KST 10:00) + `Update KindList` 성공 후 `workflow_run`.
- **흐름**: KindList 전체 종목과 HF `dart/{finance,report,docs}` parquet 목록 대조 → HF에 없는 종목만 `batchCollect` → 변경 파일만 HF 업로드.
- **환경변수**: `DART_API_KEYS`, `HF_TOKEN`, `NEW_STOCK_CATEGORIES`, `NEW_STOCK_LIMIT`.
- **원칙**: 신규 종목 판정은 KindList/HF 파일 목록만 사용한다. 별도 종목 dict 를 만들지 않는다.

### dataAudit.yml — 일일 감사

**audit 전용** — 수집/프리빌드 역할 없음.

- **스케줄**: 매일 UTC 20:00 (KST 05:00).
- **흐름**: `monitorPipeline.py` 실행 → 핵심 워크플로우 상태 확인 → 실패 시 `pipeline-failure` 라벨 Issue 생성/갱신.
- **감사 대상**: `Data Sync` / `DART New Stocks Sync` / `Data Prebuild (DART)` / `EDGAR Data Sync (Bulk)` / `KRX Data Sync (Bulk)` / `KRX Index Data Sync (Bulk)` / `Update KindList`.
- **타임아웃**: 10 분.
- **수동**: `workflow_dispatch` 로 즉시 실행 가능.

> full 모드 수집은 `dataSync.yml workflow_dispatch mode=full` 로 이전 (이전 dataPipeline.yml full 모드 대체).

---

## 9. CI 스크립트 역할

| 스크립트 | 호출자 | 역할 |
|----------|--------|------|
| `syncData.py` | dataSync (full 모드) | HF clone + DART 88 분기 차집합 수집 + changed.txt |
| `syncRecent.py` | dataSync (recent 모드) | 최근 N 일 공시 수집 (list.json 기반, 키 로테이션) |
| `syncNewStocks.py` | dartNewStocks | KindList와 HF parquet 대조 후 신규 종목 docs/finance/report bootstrap |
| `uploadData.py` | dataSync, edgarSync | HF 업로드 (카테고리별 `upload_folder`) |
| `prebuildData.py` | dataPrebuild | DART scan 프리빌드 + HF 업로드 |
| `monitorPipeline.py` | dataAudit | 워크플로우 건강 체크 + Issue 알림 |
| `updateKindList.py` | kindlist | KRX 종목 리스트 크롤링 |
| `updateDartList.py` | kindlist | OpenDART CORPCODE.xml → parquet (전체 법인 목록) |

---

## 10. 로컬 전용 작업 — CI 밖에서만 돌린다

자동 파이프라인에 포함되지 않는 작업:

| 작업 | 명령 | 이유 |
|------|------|------|
| scan snapshot | `buildScanSnapshot()` | 메모리 집약 (scanner 인스턴스화, 전종목 로드) |
| stemIndex 리빌드 | `rebuildIndex()` + `pushStemIndex()` | allFilings 데이터 필요 (~220초) |
| allFilings 수집 | `collectMeta()` + `fillContent()` | 대량 API 호출 |
| 단일 종목 수집 | `dartlab collect 005930` | 개발/디버깅용 |

---

## 11. 동시 실행 제어 — hf-dataset-push 단일 그룹으로 직렬화한다

| 워크플로우 | concurrency group | cancel-in-progress |
|-----------|-------------------|-------------------|
| dataSync | `hf-dataset-push` | false (대기) |
| dartNewStocks | `hf-dart-push` | false (대기) |
| dataPrebuild | `hf-dataset-push` | false (대기) |
| edgarSync | `hf-dataset-push` | false (대기) |
| kindlist | `hf-dataset-push` | false (대기) |
| buildKrxData | `hf-dataset-push` | false (대기) |
| buildKrxIndexData | `hf-dataset-push` | false (대기) |
| dataAudit | `data-audit` | true (새 감사로 대체) |

**설계 근거**: HF push 하는 모든 워크플로우 (dataSync/dataPrebuild/edgarSync/kindlist) 를 단일 `hf-dataset-push` 그룹에 묶어 **직렬 실행** — HF sliding-window rate limit(1000 req/5min) 에서 429 회피. 동시 실행되면 여러 워크플로우의 preupload 요청이 합산되어 한도 터짐.

### Collect state 경로 분기 (pending.txt 경쟁 회피)

dataSync.yml 의 `sync-finance-report` 와 `sync-docs` Job 이 병렬 실행되므로, `_collect_state/` 하위 파일을 scope 별로 분리:

| Job | env `SYNC_STATE_SCOPE` | 경로 | cache key |
|-----|------------------------|------|-----------|
| sync-finance-report | `fr` | `data/dart/_collect_state/fr/` | `dartlab-collect-state-fr-{run_id}` |
| sync-docs | `docs` | `data/dart/_collect_state/docs/` | `dartlab-collect-state-docs-{run_id}` |

- `syncRecent.py::_stateDir()` 및 `batch.py` 내부 state 저장 로직이 env 기반 분기.
- `skipped_docs_rcept.txt` 는 Job 공용이라 base 경로 유지 (읽기만 해서 경쟁 없음).
- `docs_failures.json` 은 scope 별 저장 (docs job 전용), 7 일 이내 자동 재시도.
- `failures.json` (DART batch) 은 syncRecent 시작부에서 pendingCodes 에 merge 되어 재시도.

---

## 12. 수집 엔진 — DART ZIP / EDGAR 벌크 + 비동기 API

### DART
- `ZipDocsCollector`: ZIP(document.xml) 기반 (빠름, 권장).
- `batchCollect()` / `batchCollectAll()`: 비동기 멀티키 병렬.
- `_collectDocsDirect()`: dataSync docs Job 전용 경로 (ZIP 기반).

### EDGAR

**finance (벌크 primary):**
- `bulk/companyfactsBulk.py::downloadCompanyfactsBulk()` — daily 1.37GB zip (ETag TTL 24h).
- `bulk/companyfactsBulk.py::convertBulkToParquets()` — {cik}.parquet 일괄 변환.
- `bulk/datasetBulk.py::downloadQuarterlyDataset()` — 분기 zip (sub/pre/tag 만, num.tsv 제외).
- `bulk/datasetBulk.py::convertQuarterlyToParquets()` — `edgar/meta/{sub|pre|tag}/{Y}Q{Q}.parquet`.

**docs (submissions API):**
- `AsyncEdgarClient`: httpx 비동기, 0.12s throttle, `asyncio.Semaphore(8)`.
- `batchCollectEdgar()` / `batchCollectEdgarAll()`: 워커 3 개, Queue 기반 ticker 분배, Rich Live progress.
- `_collectEdgarDocs()`: SEC submissions API → 10-K/10-Q HTML fetch → sections parquet (증분: 파일 존재 스킵).

**HF 배포:**
- `deployEdgarToHF()`: `upload_folder` 단일 커밋 (카테고리별 `finance/meta/scan/docs`).

**사용자 선택 경로 (자동 CI 에 없음):**
- `company.py::refreshFromApi()` — companyfacts API per-ticker 호출, 최신성 즉시 반영 원할 때만.

---

## 13. 3-Layer Freshness — ETag + TTL + API 차집합으로 최신성 보장

`loadData()` 나 `Company()` 호출 시 로컬 데이터 최신성을 자동 확인. DART/EDGAR 동일 구조.

### DART Freshness

| Layer | 메커니즘 | TTL | 비용 | 위치 |
|-------|---------|-----|------|------|
| L1 ETag+Size | HTTP HEAD → HF ETag + Content-Length 2 단계 검증 | 24 시간 | HEAD 1 회 | `dataLoader._checkRemoteFreshness` |
| L2 TTL | 네트워크 오류 시 파일 mtime 기반 폴백 | 30 일 | 0 | `_utils._checkDartDocsFreshness` |
| L3 API | DART OpenAPI rcept_no 비교 → 누락 공시 감지 | 24 시간 | API 1~2 회 | `freshness.checkFreshness` |

**P0 수정 (2026-04-06)**:
- 과거 버그: `_checkRemoteFreshness` 가 .etag 사이드카가 없으면 현재 HF ETag 를 그대로 저장 + fresh 판정 → parquet 은 옛날 그대로인데 .etag 만 새로 만들어져 영구 stale 고정.
- 결과: 사용자 finance 캐시 99.2% (2,726/2,747) 가 stale 로 굳어진 사례 발견.
- 수정 1: etag 사이드카가 없으면 무조건 stale 로 판정, 다운로드 강제.
- 수정 2: ETag 뿐만 아니라 Content-Length 도 비교 → ETag 는 같지만 손상된 케이스 방어.
- 회귀 테스트: `tests/test_dataLoader_freshness.py` (6 케이스).

### EDGAR Freshness

| Layer | 메커니즘 | TTL | 비용 | 위치 |
|-------|---------|-----|------|------|
| L1 TTL | .freshness 사이드카 mtime 기반 | 24 시간 | 0 | `edgar/freshness._isFreshnessCheckExpired` |
| L2 Local | 로컬 파일 존재 확인 (docs/finance) | — | 0 | `checkEdgarFreshness` |
| L3 API | SEC submissions API → accession_no 차집합 | 24 시간 | API 1~2 회 | `edgar/freshness.checkEdgarFreshness` |

**refresh 파라미터** (`loadData` 내부):
- `"auto"` (기본): L1 TTL 경과 시 ETag 체크 → stale 이면 HF 에서 갱신.
- `"force_check"`: TTL 무시, 즉시 ETag 체크.
- `"local_only"`: 원격 체크 안 함, 로컬 파일만 사용.

**collect 수집 데이터**: etag 파일 없어도 7 일 경과 시 HF 최신본 확인 → etag 기반 갱신 경로 합류.

### 캐시 손상 일괄 회복

`dartlab.core.dataLoader.repairLocalCache(category, dryRun=False)` 헬퍼.

CLI 진입점:

```bash
dartlab collect --repair-cache                       # finance/report/docs 전수 회복
dartlab collect --repair-cache -c finance            # finance 만
dartlab collect --repair-cache --dry-run             # 통계만 (다운로드 안 함)
```

ETag + Content-Length 2 단계 검증으로 모든 로컬 parquet 을 검사하고, stale 인 것만 HF 에서 재다운로드한다. 사용자 측 손상 회복용. 사용자 finance 폴더 1 개 검사에 약 1 초.

### Collector 처리 순서 (P0 수정)

`_buildAllPeriods` 가 반환하는 (bsns_year, reprt_code) 리스트는 **최신 분기부터 과거 순**.

- 과거: 2016 Q1 → 2026 Q4 (옛날부터).
- 현재: 2026 Q4 → 2016 Q1 (최신부터).

이유: DART API 일일 한도(20,000 회) ÷ 종목당 ~32 회 ≈ ~600 종목/일. 전체 2,500+ 종목을 매일 수집할 수 없으므로 한도 도달 시 잘림이 발생한다. 옛날부터 처리하면 매번 동일 종목의 최신 분기가 잘려서 신규 데이터(예: 25Q4 사업보고서)가 영구 누락된다. 최신부터 처리하면 한도 잘림이 발생해도 옛날 분기만 잘리고, 신규 분기는 항상 우선 처리된다.

### Collector 실패 추적 (P0 수정)

과거: 모든 예외를 try/except 로 흡수, 로그 없음 → 누락 종목 추적 불가.

수정 후:
- 개별 종목 실패 시 `logging.warning("collect.fail stockCode=... category=... err=...")`.
- 배치 종료 시 `data/dart/_collect_state/failures.json` 에 종목별 실패 사유 기록.
- API 한도 도달 시 큐의 남은 종목을 `data/dart/_collect_state/pending.txt` 에 저장.
- 다음 배치 실행 시 (`syncRecent.py`) pending.txt 를 우선 처리.

### syncRecent 카테고리별 독립 누락 검사 (P0 수정)

과거: docs 의 rcept_no 만 비교 → docs 는 이미 새 보고서가 들어와 있으면 finance/report 누락 회복 메커니즘이 없었음.

수정 후: docs 새 rcept_no **OR** finance 에 (year, reprt_code) 가 누락된 종목 모두 포함. `_existingFinanceReprts` + `_reportNmToFinanceKey` 로 finance parquet 의 누락 분기를 직접 확인.

**반복 실패** — etag 사이드카만 갱신하고 parquet 은 stale 유지 / 옛날부터 수집해서 최신 분기 영구 누락 / 예외를 try/except 로 흡수해서 실패 추적 불가. 세 패턴 모두 P0 수정 완료.

---

## 14. 캐싱·업로드·모니터링

### 캐싱 전략 (GitHub Actions)

- `actions/cache@v4` 사용.
- **키 패턴**: `dartlab-data-{category}` (저장/복원 동일 키 → 덮어쓰기).
- **run_id 미사용**: 이전 캐시가 항상 재사용됨 (낭비 제거).
- 카테고리별 독립 캐시 → 병렬 matrix 가능.
- EDGAR: `dartlab-edgar-finance`, `dartlab-edgar-docs`.

### 업로드 전략

| 대상 | 방식 | 배치 |
|------|------|------|
| HF (개별 파일) | `CommitOperationAdd` | 100 파일/커밋 |
| HF (디렉토리) | `upload_folder` | scan 전체 |
| GH Release | `gh release upload --clobber` | 50 파일/배치 |
| HF-only | edgarDocs, edinetDocs | GH Release 스킵 |

### 모니터링

- **자동**: dataAudit.yml (매일 UTC 20:00, 4 워크플로우 상태 확인).
- **감사 대상**: 5 개 워크플로우 최근 실행 상태.
- **알림**: `pipeline-failure` 라벨 GitHub Issue 자동 생성.
- **자동 해소**: 전부 성공 시 열린 Issue 자동 닫기.
- **Step Summary**: 모든 워크플로우에 `GITHUB_STEP_SUMMARY` 작성.

### 메모리/리소스 제약

| 항목 | 한도 |
|------|------|
| GitHub Actions RAM | ~7GB |
| GitHub Actions 디스크 | 14GB |
| scan 프리빌드 배치 | 200 종목 단위 중간 파일 |
| 전체 캐시 합계 | ~9.2GB (finance 600MB + report 320MB + docs 8GB + scan 270MB) |
| scan snapshot | CI 부적합 (메모리 집약) |

---

## 15. 관련 코드

| 파일 | 역할 |
|------|------|
| `src/dartlab/core/dataConfig.py` | DATA_RELEASES 중앙 설정 |
| `src/dartlab/core/dataLoader.py` | parquet 캐싱, HF 동기화, ETag, EDGAR 유니버스 |
| `src/dartlab/scan/builder.py` | DART scan 프리빌드 (changes/finance/report) |
| `src/dartlab/scan/edgarBuilder.py` | EDGAR scan 프리빌드 |
| `src/dartlab/scan/snapshot.py` | scan snapshot (로컬 전용) |
| `src/dartlab/core/search/ngramIndex.py` | stemIndex 역인덱스 빌드/검색 |
| `src/dartlab/ai/persistence/knowledge_db.py` | AI 영속 DB (executions/insights/skills/error_patterns) + HF push/pull. selfai 폐기 후 영속성만 분리 보존 |
| `src/dartlab/providers/dart/openapi/batch.py` | DART 배치 수집 엔진 |
| `src/dartlab/providers/dart/openapi/freshness.py` | DART freshness |
| `src/dartlab/providers/edgar/openapi/batch.py` | EDGAR 배치 수집 엔진 |
| `src/dartlab/providers/edgar/openapi/asyncClient.py` | EDGAR 비동기 SEC 클라이언트 |
| `src/dartlab/providers/edgar/openapi/freshness.py` | EDGAR freshness |
| `src/dartlab/providers/edgar/openapi/deploy.py` | EDGAR → HuggingFace 배포 |
| `.github/scripts/` | CI 스크립트 7 개 |
| `.github/workflows/` | 데이터 워크플로우 (dataSync · dataPrebuild · edgarSync · buildKrxData · buildKrxIndexData · dataAudit · kindlist 등) |

---

## 요약 — 명제 10 줄

1. 핵심 데이터 워크플로우 — kindlist(법인) / dataSync(DART recent 12h) / dataPrebuild(scan) / edgarSync(벌크 daily+weekly) / buildKrxData(전종목 가격) / buildKrxIndexData(시장 지수) / dataAudit(5 am).
2. 모든 HF push 는 `hf-dataset-push` 단일 concurrency group 으로 직렬화 (sliding-window 429 회피).
3. DART 수집은 `list.json` 기반 가벼움 recent 모드가 기본, 88 분기 차집합은 수동 full 모드.
4. EDGAR finance primary 는 SEC 벌크 (`companyfacts.zip` 1.37GB). API per-ticker 는 사용자 선택 경로.
5. workflow_run 체인 — dataSync 성공 → dataPrebuild 자동 트리거. EDGAR 는 edgarSync 내 end-to-end.
6. DATA_RELEASES 는 `core/dataConfig.py` SSOT, 새 카테고리는 한 줄 + `brand.ts` 블록.
7. 3-Layer Freshness — L1 ETag+Size / L2 TTL mtime / L3 API 차집합. etag 사이드카 없으면 무조건 stale.
8. 수집 처리 순서는 최신 분기부터 (API 한도 잘려도 옛날 분기만 누락).
9. 실패 추적 — `failures.json` + `pending.txt` 로 다음 run 에서 우선 회수.
10. CI 밖 로컬 전용 — scan snapshot / stemIndex / allFilings / 단일 종목 collect (메모리 또는 API 대량).
