# 03. 데이터·인덱싱 운영 — 계속 늘어나는 문서를 재색인 없이 흡수

상태: v1.3 (2026-06-16)
범위: allFilings, panel parquet, news 를 제품 검색 인덱스로 운영하는 방식.

---

## 1. 입력 데이터

| 입력 | 역할 |
|---|---|
| allFilings | 비정기/전체 공시 원문. 빠른 최신성의 핵심. |
| panel parquet | 정기공시 섹션·재무 표와 연결되는 깊은 원문. |
| news | 공시와 구분되는 외부 기사 source. |

제품 검색은 세 데이터와 향후 EDGAR panel/allFilings 계열을 한 catalog 에 stage 하되, source 를 잃으면 안 된다. 전체 운영 계약은 [10-production-pipeline-prd.md](10-production-pipeline-prd.md) 와 [11-operator-runbook.md](11-operator-runbook.md) 를 따른다. 실제 workflow/산출물 연결은 [12-pipeline-maintenance-map.md](12-pipeline-maintenance-map.md) 를 기준으로 한다.

---

## 2. 증분 원칙

추가 데이터만 들어오면 전체 재색인이 아니다.

1. catalog 에 stage.
2. `doc_key + text_hash` 로 unchanged/new/changed 판정.
3. unchanged 는 skip.
4. new/changed 만 delta CSR 로 빌드.
5. chunk embedding/evidence cache 도 new/changed 만 갱신.
6. 월간 또는 임계치 초과 시 main compaction.

전체 rebuild 가 필요한 경우:

- tokenizer 변경.
- normalizer 변경.
- embedding model 또는 chunk rule 변경.
- index schemaVersion 변경.
- sourceRef 정책 변경으로 기존 metadata 의미가 바뀜.

증분 catalog 는 source 별 manifest 를 소비한다. search index workflow 는 allFilings, DART panel, EDGAR panel, public news row 를 DuckDB catalog 에 stage 하고 `doc_key/text_hash/metadata_hash/deleted` 로 changed set 을 만든다. daily delta 는 allFilings 만이 아니라 panel changed rcept, EDGAR changed accession, news changed row 도 포함해야 한다.

source manifest 가 없거나 row count 가 비정상 급감하면 해당 source 를 최신으로 주장하지 않는다. selfcheck 를 통과하지 못한 delta 는 HF 에 promote 하지 않는다.

---

## 2.1 Source catalog artifact 흐름

source owner workflow 는 원천 parquet 를 만든 직후 search 용 artifact 도 같이 만든다.

| source | 생성 workflow | 생성 script | HF path |
|---|---|---|---|
| allFilings | `originalSync.yml` allfilings/backfill | `.github/scripts/search/buildSearchCatalog.py` | `dart/searchCatalog/allFilings/` |
| DART panel | `originalSync.yml` dart-zip/reconcile | `.github/scripts/search/buildSearchCatalog.py` | `dart/searchCatalog/dartPanel/` |
| EDGAR panel | `originalSync.yml`, `edgarSync.yml` | `.github/scripts/search/buildSearchCatalog.py` | `dart/searchCatalog/edgarPanel/` |
| public news | `newsArchiveSync.yml` newsEnrich | `.github/scripts/search/buildSearchCatalog.py` | `dart/searchCatalog/newsPublic/` |

`searchIndexDelta.yml` 은 먼저 `.github/scripts/search/pullSearchCurrentIndex.py` 로 HF current manifest pointer 를 따라 기존 full `main.*` 파일을 flat `data/dart/contentIndex/` 로 복원한다. 이 단계는 `previous_manifest.json` 을 보존하고, 가능하면 `catalog_snapshot.parquet` 도 함께 받는다. 그 다음 HF `dart/searchCatalog/**` 를 받고 `.github/scripts/search/prepareSearchDeltaInputs.py` 가 source catalog 들을 `current.catalog_snapshot.parquet` 로 합쳐 다음 환경변수를 쓴다.

- `DARTLAB_SEARCH_DELTA_MODE=catalog`
- `DARTLAB_SEARCH_PREVIOUS_CATALOG`
- `DARTLAB_SEARCH_CURRENT_CATALOG`
- `DARTLAB_SEARCH_SOURCE_MANIFESTS`
- `DARTLAB_SEARCH_SOURCE_MANIFEST_SET`

catalog artifact 가 없으면 `auto` 모드는 legacy allFilings delta 로 fallback 한다. 운영 목표는 source artifacts 가 정상 생성된 뒤 scheduled run 이 catalog mode 로 동작하는 것이다.

중요한 운영 계약:

- `{source}.catalog_snapshot.parquet` 는 그 source 의 search 대상 전체 snapshot 이어야 한다.
- changed subset 만 들어간 catalog 를 같은 HF path 에 올리면 이전 row 가 삭제된 것으로 오해될 수 있다.
- partial snapshot 이 필요하면 manifest 에 `snapshotScope=partial` 을 명시하고, search delta 는 해당 source 를 최신 claim 에 포함하지 않아야 한다.
- 1차 구현은 `snapshotScope=full|partial`, expected source set, catalog row count drop check, source catalog 생성 시 `--min-files/--min-rows/--min-catalog-rows` 차단을 갖는다. `buildSearchCatalog.py` 는 full snapshot 기본값에서 빈 파일/빈 row/빈 normalized catalog 를 실패시킨다.
- canonical source catalog bootstrap 은 두 경로다. 기본 경로는 `searchIndexMain.yml` 의 raw full HF pull 이며, source catalog 가 없거나 catalog mode 가 준비되지 않은 monthly main 은 `dart/allFilings`, `dart/panel`, `edgar/panel`, `news/public/rss_enriched` 를 full pull 한 뒤 source catalog 4종을 `searchIndexMain.full-pull` producer 로 publish 한다. 보조 경로는 source-owner workflow 의 명시적 `search_catalog_bootstrap=true` dispatch 이며, 이전 manifest 없이도 source별 높은 `--min-files/--min-rows/--min-catalog-rows` 하한을 통과해야 한다. 두 경로 모두 그 직후 `prepareSearchDeltaInputs.py` 를 실행해 `DARTLAB_SEARCH_MAIN_MODE=catalog`, current catalog, source manifest set 을 main/delta build 입력으로 고정한다.
- source owner daily/incremental workflows 는 기본적으로 canonical bootstrap 경로가 아니다. 이 workflow 들은 `--compare-remote-manifest --require-previous-manifest` 로 HF 직전 source manifest 를 읽고, 이전 full 대비 files/rows/catalogRows 가 허용치 이상 급락하면 publish 를 실패시킨다. 이전 full manifest 가 없으면 source owner 단계의 full claim 도 실패한다. 단, 운영자가 `workflow_dispatch` 로 `search_catalog_bootstrap=true` 를 명시한 1회 bootstrap 에서는 previous manifest 요구만 해제하고 source별 높은 하한으로 partial runner tree 승격을 막는다.
- source owner workflow 는 source catalog HF publish 와 별개로 `search-catalog-{source}-{job}-{run}` Actions artifact 를 남긴다. 같은 run lineage 는 source manifest 의 `producerRun.workflow/job/runId/sha/artifactName` 에도 들어간다.
- `prepareSearchDeltaInputs.py` 는 합쳐진 source set 의 `source_manifest_set.json` 을 만들고, catalog-mode main/delta/lite contentIndex 는 이 파일을 `requiredFiles`/`fileHashes` 에 포함한다. 이 파일은 각 source 의 `producerRun` 도 보존한다. remote evidence 는 contentIndex manifest 의 `fileSources` 를 따라 이 파일을 실제로 열고, 파일이 없거나 내부 source별 `producerRun` 이 비면 legacy/raw fallback 또는 수동 산출물로 보고 S2 opsReady 를 주지 않는다.
- delta publish 는 새 `delta.*` 만 current manifest 에 넣지 않는다. `previous_manifest.json` 의 `fileSources` 를 보존한 뒤 새 delta 파일 경로만 덮어써야 하며, main required file 경로가 사라지면 제품화 ops gate 실패다.
- `planSearchBootstrap.py` 는 누락 목록뿐 아니라 `sourceCatalogNotFull:*`, `sourceCatalogMissingProducerRun:*`, `remoteContentManifestSetMissingProducerRun:*`, `remoteContentMissingFileSources:*` 같은 productization status blocker 를 source-owner bootstrap/Search Main/검증 명령으로 변환한다. 운영자는 실패한 proof bundle 의 `nextActions.bootstrapPlan` 을 따라야 하며, 수동 추측으로 source set 을 조합하지 않는다.

---

## 2.2 앞으로 추가될 데이터의 증분 정책

향후 데이터가 늘어나는 방향은 전부 같은 규칙으로 흡수한다. 새 source 를 붙일 때마다 검색 workflow 에 특수 분기를 추가하는 것이 아니라, source owner 가 아래 계약을 채우고 search workflow 는 catalog diff 만 수행한다.

| 데이터 증가 | 기본 처리 | full rebuild 조건 |
|---|---|---|
| allFilings 월별/과거 backfill | backfill slab 을 source full snapshot 에 반영하고 `docKey/textHash` changed set 만 delta 로 publish | docKey 정책 변경, 대량 tombstone, delta/main 비율 초과 |
| DART panel reconcile | 복구된 rcept/section 을 `dartPanel` snapshot 에 반영하고 panel 우선순위로 delta publish | panel rollup/chunk 의미 변경 |
| EDGAR panel 확대 | accession/item/section namespace 로 `edgarPanel` snapshot 에 반영 | EDGAR sourceRefVersion 또는 section adapter 변경 |
| public news 확대 | `newsPublic` sourceRef 를 URL hash 로 유지하고 public headline/body lane 만 delta publish | canonical URL 정책 또는 public/private 경계 변경 |
| GDELT 후보 | manifest/sourceRef/license/canary/failureType 충족 전에는 제품 corpus 에 혼합하지 않음 | onboarding 승인 후 첫 full/lite compaction |
| private/local news | public contentIndex 와 분리. local/private artifact 정책 확정 전까지 제품 corpus 에 혼합 금지 | 별도 tier 또는 private artifact 계약 신설 |

재색인 판단은 "데이터가 많아졌는가"가 아니라 "기존 docKey/textHash 로 같은 의미를 보존할 수 있는가"로 한다. 의미가 보존되면 delta, 의미가 바뀌면 full rebuild 다.

### 2.3 자동 업데이트 생명주기

데이터가 계속 늘어나는 운영에서는 "누가 언제 전체 재색인 버튼을 누르는가"를 운영 모델로 두지 않는다. source owner 가 자기 source 의 full snapshot manifest 를 유지하고, search 는 그 snapshot 들의 diff 만 본다.

| 이벤트 | source owner 책임 | search workflow 책임 | local/runtime 책임 | full rebuild 여부 |
|---|---|---|---|---|
| allFilings daily forward | 신규 일별 parquet 와 source manifest 갱신 | previous/current catalog diff 로 delta build | 새 manifest 가 compatible 하면 staged activation | 불필요 |
| allFilings backfill | 과거 slab 을 full snapshot 에 merge 하고 date range 기록 | changed/new rows 만 delta 로 흡수 | 기존 active 유지 후 새 delta 확인 | delta 비율 초과 시 월간 compaction |
| DART panel reconcile | 복구 rcept/section 을 panel snapshot 에 반영 | panel 우선순위 유지해 changed set export | sourceDataAsOf 와 sourceRef 보존 확인 | rollup 의미 변경 때만 |
| EDGAR panel 확대 | accession/item namespace 와 filing date 보존 | EDGAR sourceRef 로 DART 와 분리해 delta build | incompatible schema 는 activate 거부 | sourceRefVersion 변경 때만 |
| public news 증가 | canonical URL hash 와 public/private 경계 보존 | newsPublic lane 만 delta build, filing fallback 금지 | source intent hard isolation 확인 | URL policy 변경 때만 |

유지보수자가 장기적으로 관리할 대상은 query mapper 가 아니라 다음 네 상태다.

1. source manifest freshness.
2. catalog diff health.
3. contentIndex manifest/publish safety.
4. query-log gold 와 miss ledger.

이 네 상태가 정상이라면 문서량이 늘어나도 다음 검색은 delta 로 따라간다. 네 상태 중 하나가 깨지면 새 artifact 를 publish/activate 하지 않고, 마지막 정상 active index 를 보존한다.

---

## 3. main + delta 운영

제품 런타임은 main 과 delta 를 합쳐 검색한다.

- main: 안정 세그먼트, 월간 compaction.
- delta: 일간 또는 수집 직후 증분.
- 같은 `(rceptNo, sectionOrder)` 는 delta 우선.
- `indexInfo()` 는 `dataAsOf`, `nDocs`, `hasDelta`, `schemaVersion`, `compatible` 을 반환.

사용자에게 "최신"이라고 말하려면 source별 `sourceDataAsOf` 가 필요하다. 오래된 인덱스면 답변 가능 결과와 stale 안내를 분리하고, 필요하면 `Company.liveFilings()` 같은 라이브 경로를 병행한다.

---

## 4. news 운영

뉴스는 공시와 같은 검색 표면에 들어오지만 같은 source 가 아니다.

- `source=news` 를 metadata 에 보존.
- news URL 또는 `news:` id 를 sourceRef 로 보존.
- article text 는 untrusted external content 로 취급.
- 뉴스 저작권·공개/비공개 경계 때문에 제품 노출은 headline/link 중심으로 시작한다.

제품화 초기에는 "공시 원문 찾기"가 주목표이고, 뉴스는 source intent isolation 과 cross-source answer 에서 보조한다.

---

## 5. 운영 산출물

필수 산출물:

- source manifest: source별 dataAsOf, file hash/etag, row count, changed/deleted count.
- catalog snapshot: staged docs, source counts, changed/new/unchanged.
- source manifest set: 이번 contentIndex 에 사용된 source manifest/catalog snapshot set id, source별 hash/dataAsOf/row count, source owner run lineage.
- index manifest: artifactVersion, schemaVersion, builtAt, mainDataAsOf, deltaDataAsOf, sourceDataAsOf, source counts, tier, changed/new/deleted/unchanged counts, build command.
- quality report: readiness, query-log gold, random pressure.
- canary report: source isolation, expected sourceRef, no-answer false accept.
- miss ledger: miss query, target, topDocs, 판단.

목표 publish 순서:

1. `_staging/{runId}` 에 required files 업로드.
2. manifest hash 와 canary query selfcheck.
3. `current/manifest.json` 만 publish 해서 `fileSources` 로 staging 파일을 가리키게 한다.
4. remote evidence 는 manifest 존재뿐 아니라 `requiredFiles` 의 `fileSources` 대상이 실제 HF 에 있는지 확인하고, contentIndex 의 `source_manifest_set.json` 내부 source별 `producerRun` 을 검증한다.
5. full/lite tier 모두 HF round-trip activate + rollback 을 통과해야 opsReady 다.
6. 실패 시 active artifact 유지.

현재 search publish script 는 `publishIndex.py` 를 통해 local manifest/hash/canary selfcheck 를 먼저 수행하고, 통과한 artifact 파일은 `_staging/{runId}` 에 올린 뒤 current path 에는 pointer manifest 만 publish 한다. source catalog publish 도 manifest 와 catalog snapshot 을 단일 `create_commit` batch 로 올린다. source catalog, contentIndex `source_manifest_set.json` lineage, manifest, catalog-mode delta 검증 뒤 운영 졸업 전에는 실제 HF round-trip, staging hash 재검증, rollback drill 증거가 필요하다. remote source/content blocker 가 있으면 `planSearchBootstrap.py` 와 `buildSearchProofBundle.py` 가 `searchBootstrapPlan.json` 을 남기고, proof bundle 의 `nextActions.bootstrapPlan` 을 다음 source-owner/Search Main/검증 실행 순서로 사용한다.

local pipeline drill 은 실제 HF 대신 synthetic raw source parquet 와 local fake HF 로 운영 bootstrap 을 재현한다. `runSearchPipelineDrill.py` 는 raw source 에서 source catalog 4종을 만들고 `prepareSearchDeltaInputs.py` 로 `source_manifest_set.json` 과 catalog-mode current catalog 를 freeze 한 뒤 staging upload/current manifest pointer publish, local activation, rollback 까지 검증한다. searchIndexDelta/Main preflight 에서 실행되며, 실제 원격 run 전 코드 회귀를 막는 하한 게이트다.

실제 HF round-trip 은 `verifySearchHfRoundTrip.py` 로 검증한다. 이 스크립트는 HF current manifest 를 temp/local contentIndex 에 내려받아 required files/hash/load/canary/sourceCanary selfcheck 후 activate 하고 rollback 한다. searchIndexDelta/Main workflow 는 publish 뒤 full 과 lite report 를 각각 artifact 로 업로드한다.

canary report 는 publish/local activation 전 안전장치다. `evaluateSearchCanary.py` 는 source/no-answer canary pack 실행 결과를 JSON 으로 남기고, 실패 artifact 를 current 또는 active 로 넘기지 않는 근거가 된다.

miss ledger 는 제품 품질 개선의 실제 backlog 다. `evaluateSearchGold.py` 는 query-log gold 실행 결과에서 `docMiss10`, `citationMissTop3`, `falseAccept`, `newsSourcePrecision10`, `goldReviewRequired` 를 JSONL 로 남긴다. 특수 case 를 즉시 붙이지 말고, 반복되는 miss type 만 정책으로 승격한다.

---

## 6. 속도·메모리 목표

제품 목표:

- warm search: 사용자가 체감하는 즉시성.
- sparse index 메모리: 현 large 기준 수십 MB대 유지.
- evidence card: 평균 4KB 이하.
- incremental update: unchanged skip 과 chunk reuse 유지.

LLM 호출 비용은 검색 품질을 올리는 수단이 아니라, 검색 결과를 설명하는 소비자 단계로 둔다.

2026-06-15 ceiling run 기준 현재 상한:

| 항목 | 실측 |
|---|---:|
| docs | 301579 |
| loadSec | 574.2 |
| contextSec / indexBuildSec | 151.5 / 148.1 |
| warm query p50 / p95 / max | 123.1ms / 157.9ms / 173.9ms |
| content CSR memory | 약 591MB |
| metadata CSR memory | 약 36.9MB |

빌드·로드는 무겁지만 데모 운영에서는 한 번만 수행된다. warm query 는 300k 문서에서도 200ms 안쪽이라 제품 데모에 충분하다. 본진 이식 시 과제는 query latency 가 아니라 초기 load/build 를 prebuilt main+delta artifact 로 넘기는 것이다.
