# Data

HuggingFace 데이터셋 관리, 자동 수집 파이프라인, 프리빌드, 모니터링.

| 항목 | 내용 |
|------|------|
| 레이어 | L0 (core/dataConfig, dataLoader) |
| 진입점 | `Company("005930")` 시 자동 다운로드 |
| 데이터셋 | HuggingFace `eddmpython/dartlab-data` |
| 소비 | Company, providers, scan, analysis 전체 |

## 한눈에 보기 — 자동 파이프라인 (2026-04-06 통합 후)

```
UTC 00:00  kindlist.yml ──────── KRX 종목 리스트 + DART 전체 법인 목록 갱신
UTC 18:00  dataSync.yml (KST 03:00) ─┐
UTC 06:00  dataSync.yml (KST 15:00) ─┴ DART list.json 신규 공시만 수집 (가벼움)
           ↓ workflow_run (completed + success)
           dataPrebuild.yml ──── DART + EDGAR scan 프리빌드 → HF
UTC 20:00  dataPipeline.yml ──── audit 전용 (수집 안 함, Issue 알림만)
일요일 03:00 edgarSync.yml ───── EDGAR 통합 수집 (finance+docs+scan → HF)

비활성화 (코드 유지, 수동 dispatch만):
- dataSyncDaily.yml — dataSync.yml로 통합됨
- dataPipeline.yml full 모드 — workflow_dispatch로 백업 수집 가능

자동 메인 진입점: dataSync.yml (12시간마다 list.json 기반 수집)
```

### 수집 경로 (가벼움 vs 무거움)

| 경로 | 호출 | 동작 | 시간 | 자동 |
|---|---|---|---|---|
| **가벼움 (기본)** | `syncRecent.py` → `batchCollect(targetPeriodsByCode=...)` | list.json 발견 종목·분기만 시도 | 30분 | KST 03/15시 |
| 무거움 (백업) | `syncData.py` → `batchCollectAll(mode="all")` | 전 종목 88분기 차집합 | 5시간 | 수동만 |

**가벼움 경로의 핵심**: `_discoverNewFilings`가 list.json + finance/docs 누락 검사로
정확한 종목·(year, reprt_code) 셋을 만들고, `batchCollect`가 `targetPeriodsByCode`로
받아서 _collectFinance에 전달 → `_buildAllPeriods()` 88분기 우회.

## DATA_RELEASES (중앙 설정)

`src/dartlab/core/dataConfig.py` 한 곳에서 관리:

| 카테고리 | 경로 | 설명 | 자동 수집 |
|----------|------|------|-----------|
| docs | dart/docs | 공시 문서 (~8GB, 2500+종목) | dataSync, dataSyncDaily |
| finance | dart/finance | 재무제표 (~600MB, 2700+종목) | dataSync, dataSyncDaily |
| report | dart/report | 정기보고서 (~320MB, 2700+종목) | dataSync, dataSyncDaily |
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

새 카테고리 추가: `DATA_RELEASES`에 한 줄 + `brand.ts` data 블록 추가.

## 워크플로우 상세

### dataSync.yml — DART 전종목 증분

- **스케줄**: 매일 UTC 17:00 (KST 02:00)
- **Matrix**: finance, report, docs 3병렬
- **흐름**: 캐시 복원 → `syncData.py` (HF clone + batchCollectAll) → 해시 기반 변경 감지 → `uploadData.py` (HF + GH Release)
- **환경변수**: `DART_API_KEYS`, `HF_TOKEN`, `SYNC_CATEGORY`, `SYNC_MODE`
- **타임아웃**: 300분

### dataSyncDaily.yml — 최근 공시 경량

- **스케줄**: 매일 UTC 18:00 (KST 03:00)
- **구조**: 2개 병렬 Job
  - `sync-data`: finance + report (타임아웃 45분)
  - `sync-docs`: docs 전용 — `_collectDocsDirect` 직접 ZIP 수집 (타임아웃 150분)
- **흐름**: DART list.json → 최근 7일 정기공시 → rcept_no 비교 → 새 보고서 종목만 수집 → 카테고리별 changed.txt
- **환경변수**: `DART_API_KEYS`, `SYNC_LOOKBACK_DAYS`, `SYNC_CATEGORIES`
- **API 키 로테이션**: 다중 키 순차 시도, 전체 한도 초과 시 graceful exit
- **concurrency**: `daily-data-sync` 그룹, `cancel-in-progress: true`

### dataPrebuild.yml — DART + EDGAR scan 프리빌드

- **트리거**: `workflow_run` (Data Sync / Daily Data Sync 완료 후 자동)
- **DART 흐름**: 3개 캐시 복원 (finance/report/docs) → `prebuildData.py` → buildScan() → HF upload_folder
- **EDGAR 흐름**: EDGAR finance 캐시 복원 → `buildEdgarFinance()` → `deployEdgarToHF(scan)` → HF
- **DART 출력**: changes.parquet, finance.parquet, report/12개 apiType.parquet
- **EDGAR 출력**: edgar/scan/finance.parquet
- **타임아웃**: 120분

### edgarSync.yml — EDGAR 통합 수집 (벌크 기반)

> ⛔ **dartlab EDGAR finance = SEC 벌크.** `data.sec.gov/api/xbrl/companyfacts` API는 사용자가 명시적으로 요청할 때(`c.finance.refreshFromApi()`)만 호출되는 **선택 경로**다. 자동 CI/프리빌드/HF 배포는 전부 벌크를 쓴다. 상세: `ops/edgar.md`.

- **스케줄**: 매일 UTC 04:30 (companyfacts.zip 갱신 04:25 직후) + 일요일 전체 정산
- **finance (daily 벌크)**:
  - `downloadCompanyfactsBulk()` — `Archives/edgar/daily-index/xbrl/companyfacts.zip` (1.37GB)
  - `convertBulkToParquets()` — 16,601개 {cik}.parquet 일괄 생성
- **meta (분기 벌크)**:
  - `discoverLatestQuarter()` — SEC에 새 `{Y}q{Q}.zip` 있나 체크
  - `downloadQuarterlyDataset(Y, Q)` + `convertQuarterlyToParquets()` — sub/pre/tag parquet
  - `num.tsv는 받지 않음` (companyfacts.zip이 원본)
- **docs (submissions API 경로)**: 10-K/10-Q HTML fetch는 벌크 개념 없음, 기존 경로 유지
- **scan 프리빌드**: `buildEdgarFinance(sinceYear=2021)` → `edgar/scan/finance.parquet`
- **HF 업로드**: `deployEdgarToHF(["finance", "meta", "scan", "docs"])` — 카테고리별 `upload_folder` 단일 커밋
- **유니버스**: `loadEdgarTargetUniverse(tier)` — all=7,557 / nasdaq=4,256 / nyse=3,273 / sp500=500
- **타임아웃**: 180분
- **캐시**: `dartlab-edgar-bulk`, `dartlab-edgar-docs` (run_id 없이 덮어쓰기)

### kindlist.yml — KRX 종목 리스트 + DART 전체 법인 목록

- **스케줄**: 매일 UTC 00:00 (KST 09:00)
- **2가지 수집**:
  - **KindList**: KRX KIND 크롤링 → `metadata/corpList.parquet` (상장사 2,700+)
  - **DartList**: OpenDART CORPCODE.xml → `metadata/dartList.parquet` (전체 법인 115,000+, corp_code 8자리)
- **흐름**: 각각 SHA256 비교 → 변경 시만 GitHub Release + HuggingFace 업로드

### dataPipeline.yml — 마스터 진입점

**단일 진입점으로 전체 파이프라인 실행 + 감사.**

- **스케줄**: 매일 UTC 20:00 (audit 모드)
- **수동 실행**: `full` 모드 = 수집 → 프리빌드 → 감사 순차
- **3개 Job**:
  1. `collect` (full 모드만) — dataSync와 동일한 수집
  2. `prebuild` (full 모드만, collect 완료 후) — scan 프리빌드 + HF 업로드
  3. `audit` (항상) — 전체 워크플로우 상태 감사 + Issue 알림
- **감사 대상**: Data Sync, Daily Data Sync, EDGAR Data Sync, Update KindList, Data Prebuild

## CI 스크립트 역할

| 스크립트 | 호출자 | 역할 |
|----------|--------|------|
| `syncData.py` | dataSync, dataPipeline | HF clone + DART 증분 수집 + changed.txt |
| `syncRecent.py` | dataSyncDaily | 최근 7일 공시 수집 (SYNC_CATEGORIES 분할, docs 직접 ZIP 수집, 키 로테이션) |
| ~~syncEdgarDocs.py~~ | — | 삭제됨 — `dartlab collect --tier` CLI가 대체 |
| `uploadData.py` | dataSync, dataSyncDaily, edgarSync | HF + GH Release 업로드 |
| `prebuildData.py` | dataPrebuild, dataPipeline | scan 프리빌드 + HF 업로드 |
| `monitorPipeline.py` | dataPipeline | 워크플로우 건강 체크 + Issue 알림 |
| `updateKindList.py` | kindlist | KRX 종목 리스트 크롤링 |
| `updateDartList.py` | kindlist | OpenDART CORPCODE.xml → parquet (전체 법인 목록) |

## 로컬 전용 작업

자동 파이프라인에 포함되지 않는 작업:

| 작업 | 명령 | 이유 |
|------|------|------|
| scan snapshot | `buildScanSnapshot()` | 메모리 집약 (scanner 인스턴스화, 전종목 로드) |
| stemIndex 리빌드 | `rebuildIndex()` + `pushStemIndex()` | allFilings 데이터 필요 (~220초) |
| allFilings 수집 | `collectMeta()` + `fillContent()` | 대량 API 호출 |
| 단일 종목 수집 | `dartlab collect 005930` | 개발/디버깅용 |

## 동시 실행 제어

| 워크플로우 | concurrency group | cancel-in-progress |
|-----------|-------------------|-------------------|
| dataSync | `data-sync-{event_name}` | true |
| dataSyncDaily | `daily-data-sync` | **false** (이전 실행 대기, 취소 안 함) |
| edgarSync | `edgar-data-sync` | false |

## 수집 엔진

### DART
- `ZipDocsCollector`: ZIP(document.xml) 기반 (빠름, 권장)
- `batchCollect()` / `batchCollectAll()`: 비동기 멀티키 병렬
- `_collectDocsDirect()`: dataSyncDaily docs 전용 경로

### EDGAR

**finance (벌크 primary):**
- `bulk/companyfactsBulk.py::downloadCompanyfactsBulk()` — daily 1.37GB zip (ETag TTL 24h)
- `bulk/companyfactsBulk.py::convertBulkToParquets()` — {cik}.parquet 일괄 변환
- `bulk/datasetBulk.py::downloadQuarterlyDataset()` — 분기 zip (sub/pre/tag만, num.tsv 제외)
- `bulk/datasetBulk.py::convertQuarterlyToParquets()` — `edgar/meta/{sub|pre|tag}/{Y}Q{Q}.parquet`

**docs (submissions API):**
- `AsyncEdgarClient`: httpx 비동기, 0.12s throttle, `asyncio.Semaphore(8)`
- `batchCollectEdgar()` / `batchCollectEdgarAll()`: 워커 3개, Queue 기반 ticker 분배, Rich Live progress
- `_collectEdgarDocs()`: SEC submissions API → 10-K/10-Q HTML fetch → sections parquet (증분: 파일 존재 스킵)

**HF 배포:**
- `deployEdgarToHF()`: `upload_folder` 단일 커밋 (카테고리별 `finance/meta/scan/docs`)

**사용자 선택 경로 (자동 CI에 없음):**
- `company.py::refreshFromApi()` — companyfacts API per-ticker 호출, 최신성 즉시 반영 원할 때만

## 3-Layer Freshness

`loadData()`나 `Company()` 호출 시 로컬 데이터 최신성을 자동 확인. DART/EDGAR 동일 구조.

### DART Freshness

| Layer | 메커니즘 | TTL | 비용 | 위치 |
|-------|---------|-----|------|------|
| L1 ETag+Size | HTTP HEAD → HF ETag + Content-Length 2단계 검증 | 24시간 | HEAD 1회 | `dataLoader._checkRemoteFreshness` |
| L2 TTL | 네트워크 오류 시 파일 mtime 기반 폴백 | 30일 | 0 | `_utils._checkDartDocsFreshness` |
| L3 API | DART OpenAPI rcept_no 비교 → 누락 공시 감지 | 24시간 | API 1~2회 | `freshness.checkFreshness` |

**P0 수정 (2026-04-06)**:
- 과거 버그: `_checkRemoteFreshness`가 .etag 사이드카가 없으면 현재 HF ETag를 그대로
  저장 + fresh 판정 → parquet은 옛날 그대로인데 .etag만 새로 만들어져 영구 stale 고정.
- 결과: 사용자 finance 캐시 99.2% (2,726/2,747) 가 stale로 굳어진 사례 발견.
- 수정 1: etag 사이드카가 없으면 무조건 stale로 판정, 다운로드 강제.
- 수정 2: ETag뿐만 아니라 Content-Length도 비교 → ETag는 같지만 손상된 케이스 방어.
- 회귀 테스트: `tests/test_dataLoader_freshness.py` (6 케이스).

### EDGAR Freshness

| Layer | 메커니즘 | TTL | 비용 | 위치 |
|-------|---------|-----|------|------|
| L1 TTL | .freshness 사이드카 mtime 기반 | 24시간 | 0 | `edgar/freshness._isFreshnessCheckExpired` |
| L2 Local | 로컬 파일 존재 확인 (docs/finance) | — | 0 | `checkEdgarFreshness` |
| L3 API | SEC submissions API → accession_no 차집합 | 24시간 | API 1~2회 | `edgar/freshness.checkEdgarFreshness` |

**refresh 파라미터** (`loadData` 내부):
- `"auto"` (기본): L1 TTL 경과 시 ETag 체크 → stale이면 HF에서 갱신
- `"force_check"`: TTL 무시, 즉시 ETag 체크
- `"local_only"`: 원격 체크 안 함, 로컬 파일만 사용

**collect 수집 데이터**: etag 파일 없어도 7일 경과 시 HF 최신본 확인 → etag 기반 갱신 경로 합류.

### 캐시 손상 일괄 회복

`dartlab.core.dataLoader.repairLocalCache(category, dryRun=False)` 헬퍼.

CLI 진입점:

```bash
dartlab collect --repair-cache                       # finance/report/docs 전수 회복
dartlab collect --repair-cache -c finance            # finance만
dartlab collect --repair-cache --dry-run             # 통계만 (다운로드 안 함)
```

ETag + Content-Length 2단계 검증으로 모든 로컬 parquet을 검사하고, stale인 것만
HF에서 재다운로드한다. 사용자 측 손상 회복용. 사용자 finance 폴더 1개 검사에 약 1초.

### Collector 처리 순서 (P0 수정)

`_buildAllPeriods` 가 반환하는 (bsns_year, reprt_code) 리스트는 **최신 분기부터 과거 순**.

- 과거: 2016 Q1 → 2026 Q4 (옛날부터)
- 현재: 2026 Q4 → 2016 Q1 (최신부터)

이유: DART API 일일 한도(20,000회) ÷ 종목당 ~32회 ≈ ~600 종목/일. 전체 2,500+ 종목을
매일 수집할 수 없으므로 한도 도달 시 잘림이 발생한다. 옛날부터 처리하면 매번 동일
종목의 최신 분기가 잘려서 신규 데이터(예: 25Q4 사업보고서)가 영구 누락된다. 최신부터
처리하면 한도 잘림이 발생해도 옛날 분기만 잘리고, 신규 분기는 항상 우선 처리된다.

### Collector 실패 추적 (P0 수정)

과거: 모든 예외를 try/except로 흡수, 로그 없음 → 누락 종목 추적 불가.

수정 후:
- 개별 종목 실패 시 `logging.warning("collect.fail stockCode=... category=... err=...")`
- 배치 종료 시 `data/dart/_collect_state/failures.json` 에 종목별 실패 사유 기록
- API 한도 도달 시 큐의 남은 종목을 `data/dart/_collect_state/pending.txt` 에 저장
- 다음 배치 실행 시 (`syncRecent.py`) pending.txt를 우선 처리

### syncRecent 카테고리별 독립 누락 검사 (P0 수정)

과거: docs의 rcept_no만 비교 → docs는 이미 새 보고서가 들어와 있으면 finance/report
누락 회복 메커니즘이 없었음.

수정 후: docs 새 rcept_no **OR** finance에 (year, reprt_code)가 누락된 종목 모두 포함.
`_existingFinanceReprts` + `_reportNmToFinanceKey` 로 finance parquet의 누락 분기를
직접 확인.

## 캐싱 전략 (GitHub Actions)

- `actions/cache@v4` 사용
- **키 패턴**: `dartlab-data-{category}` (저장/복원 동일 키 → 덮어쓰기)
- **run_id 미사용**: 이전 캐시가 항상 재사용됨 (낭비 제거)
- 카테고리별 독립 캐시 → 병렬 matrix 가능
- EDGAR: `dartlab-edgar-finance`, `dartlab-edgar-docs`

## 업로드 전략

| 대상 | 방식 | 배치 |
|------|------|------|
| HF (개별 파일) | `CommitOperationAdd` | 100파일/커밋 |
| HF (디렉토리) | `upload_folder` | scan 전체 |
| GH Release | `gh release upload --clobber` | 50파일/배치 |
| HF-only | edgarDocs, edinetDocs | GH Release 스킵 |

## 모니터링

- **자동**: dataPipeline.yml audit job (매일 UTC 20:00)
- **감사 대상**: 5개 워크플로우 최근 실행 상태
- **알림**: `pipeline-failure` 라벨 GitHub Issue 자동 생성
- **자동 해소**: 전부 성공 시 열린 Issue 자동 닫기
- **Step Summary**: 모든 워크플로우에 `GITHUB_STEP_SUMMARY` 작성

## 메모리/리소스 제약

| 항목 | 한도 |
|------|------|
| GitHub Actions RAM | ~7GB |
| GitHub Actions 디스크 | 14GB |
| scan 프리빌드 배치 | 200종목 단위 중간 파일 |
| 전체 캐시 합계 | ~9.2GB (finance 600MB + report 320MB + docs 8GB + scan 270MB) |
| scan snapshot | CI 부적합 (메모리 집약) |

## 관련 코드

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
| `src/dartlab/scan/edgarBuilder.py` | EDGAR scan 프리빌드 |
| `.github/scripts/` | CI 스크립트 7개 |
| `.github/workflows/` | 워크플로우 6개 (data 관련: dataSync, dataSyncDaily, dataPrebuild, dataPipeline, edgarSync, kindlist) |
