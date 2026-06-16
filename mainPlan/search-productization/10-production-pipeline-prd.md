# 10. 제품 파이프라인 PRD — 본진 교체 · HF 증분 · 로컬 자동 업데이트

상태: v0.34 (2026-06-16)
범위: `dartlab.search(...)` 단일 공개계약을 제품 검색으로 교체하기 위한 전체 운영 파이프라인.

실제 workflow 파일명, source owner, artifact, 유지보수 캘린더는 [12-pipeline-maintenance-map.md](12-pipeline-maintenance-map.md) 를 기준으로 한다.

---

## 1. 제품 목표

목표는 새 검색 제품을 옆에 하나 더 세우는 것이 아니다.

`dartlab.search(...)` 안쪽을 단일 제품 검색 엔진으로 교체하고, allFilings, DART panel, EDGAR panel, public news 가 계속 늘어나도 사용자는 같은 호출로 최신에 가까운 공시·뉴스 근거를 찾게 한다.

성공 정의:

1. 본진 검색은 한 엔진이다. legacy/shadow 검색을 운영 기본값으로 병행하지 않는다.
2. 검색 단위는 제목이 아니라 본문이다. 제목·보고서명·section title 은 anchor 이고, filing body, panel rolled body, EDGAR item body, news title/body lane 이 recall 본체다.
3. 새 데이터는 기본적으로 delta 로 흡수한다. full rebuild 는 compaction 또는 schema/tokenizer/normalizer/sourceRef 변경 때만 한다.
4. HF 는 source artifact 와 search artifact 의 SSOT 다. 로컬은 HF manifest 를 보고 필요한 artifact 만 받아 atomic swap 한다.
5. 장애가 나도 이전 인덱스가 계속 살아야 한다. 실패는 publish 중단 또는 local swap 거부로 끝나야지, 빈/부분 인덱스가 active 가 되면 안 된다.

---

## 2. 현재 증거와 갭

가능성은 확인됐다.

| 축 | 현재 증거 |
|---|---:|
| replacement gate | pass |
| staged docs | 24,338 |
| demo-ops readyRate | 1.0 |
| demo-ops latency p95 / max | 59.279ms / 80.955ms |
| larger ceiling docs | 301,579 |
| larger ceiling readyRate | 0.9867 |
| larger ceiling warm p95 / max | 157.9ms / 173.9ms |

남은 제품 갭:

1. daily search delta 는 catalog 를 기본 모드로 쓰고 allFilings/panel/news/EDGAR changed set 을 소비한다. `legacy` 는 운영자 명시 dispatch 예외다. 2026-06-16 local HF bootstrap 으로 source catalog/full/lite contentIndex 원격 evidence 는 확보됐고, scheduled Actions run 으로 catalog-mode delta publish 를 재확인해야 한다.
2. local lazy pull 은 manifest artifact 를 staged download/hash/load/canary smoke/active swap 으로 우선 처리하고 active manifest 비교와 previous active rollback helper 까지 수행한다. HF full/lite current artifact round-trip 은 local bootstrap candidate 로 1회 통과했고, 남은 검증은 같은 순서의 실제 Actions run artifact 확인이다.
3. 실제 query-log gold 가 아직 부족하다. release graduation 은 generated/proxy gold 로 하지 않는다. `qualityGate.py` 와 `evaluateSearchGold.py` 로 real/proxy/review status 를 자동 판정하는 게이트는 1차 구현됐다. `DARTLAB_SEARCH_QUERY_LOG` raw capture hook 은 실제 검색 호출 후보를 남기는 입력 루프일 뿐이며, reviewer label 이 붙기 전에는 release gold 가 아니다.
4. 본진 `api.py/fieldIndex.py/unified.py` 에 source intent, source mask, answerability, evidence card 일부가 들어갔다. `_attempts` replacement gate 는 아직 release graduation 증거가 아니라 회귀 압박 증거다.
5. search publish script 는 `publishIndex.py` 를 통해 local manifest/hash/canary selfcheck 통과 후 `_staging/{runId}` 업로드와 current path `manifest.json` pointer publish 를 수행한다. current manifest 의 `fileSources` 가 staging files 를 가리키므로 current path 에 개별 artifact 를 직접 덮어쓰지 않는다. HF 429 완화를 위해 contentIndex manifest-pointer publish 는 staging files 와 current manifest pointer 를 단일 `create_commit` batch 로 올리고, source catalog publish 도 source manifest 와 catalog snapshot 을 단일 `create_commit` batch 로 올린다. 추가로 `promoteCurrent=False` stage-only publish 와 `verifySearchHfRoundTrip.py --manifest-repo-path` candidate 검증 경로가 생겼다. Search Main/Delta workflow 는 stage -> candidate round-trip/result/canary/optional quality -> promote -> remote evidence/status 순서로 재배치됐다. 남은 publish-safety 증거는 실제 Actions run 에서 이 순서와 rollback drill 을 남기는 것이다.
6. monthly main 은 source catalog snapshot 기준 compaction 우선 경로를 갖는다. `searchIndexMain.yml` 은 HF `dart/searchCatalog/**` 를 먼저 pull 하고, valid full snapshot 이 준비되면 `buildSearchMain.py` 가 `rebuildMainFromCatalog(...)` 로 full main 을 compaction 한다. catalog 가 없으면 legacy raw rebuild 로 fallback 한다. local HF bootstrap 에서 catalog-mode full/lite build 와 promote 는 통과했고, 실제 Actions run 증거는 아직 필요하다.
7. source catalog artifact 는 canonical full snapshot claim 이어야 한다. 1차 구현은 manifest `snapshotScope`, expected source set, source row count drop check, source catalog 생성 시 최소 files/rows/catalogRows 차단으로 partial/empty catalog-mode 전환을 막는다. 추가로 `buildSearchCatalog.py --compare-remote-manifest --require-previous-manifest` 가 직전 HF full manifest 대비 files/rows/catalogRows 급락을 차단하므로, daily/source-owner runner 의 partial tree 가 full 로 승격되지 않는다. 첫 canonical bootstrap 은 `searchIndexMain.yml` raw full HF pull 경로의 `searchIndexMain.full-pull` producer 또는 source-owner workflow 의 명시적 `search_catalog_bootstrap=true` dispatch 로 만든다. 2026-06-16 local bootstrap 은 source별 full snapshot 과 `producerRun.workflow=local-search-bootstrap` 을 원격 manifest 에 기록했다. 일반 source-owner 증분 job 은 이전 full manifest 없이 full claim 을 publish 하지 못한다.
8. 결과 row 계약 감사는 1차 구현됐고 full_lite proof bundle 에서 통과했다. `resultContract.py` 와 `evaluateSearchResultContract.py` 는 `source/sourceRef/dataAsOf/snippet/answerable/fieldCards` 와 card evidence 를 검사한다. `searchIndexDelta.yml` 과 `searchIndexMain.yml` 은 이 report 를 evidence artifact 로 업로드한다. 남은 증거는 scheduled Actions artifact 에서 같은 report 를 확인하는 것이다.
9. 원격 HF evidence audit 도 1차 구현됐다. `checkSearchRemoteEvidence.py` 는 HF `dart/searchCatalog/{source}/` source manifest/catalog snapshot 과 `dart/contentIndex/{tier}/manifest.json` 존재 여부, contentIndex manifest `fileSources` 대상 존재, `source_manifest_set.json` 내부 source별 `producerRun`, manifest summary, blocker 를 JSON 으로 남긴다. workflow 는 `searchRemoteEvidence.{delta,main}.json` 을 evidence artifact 로 업로드한다.
10. bootstrap plan CLI 도 1차 구현됐다. `planSearchBootstrap.py` 는 현재 `searchRemoteEvidence` 또는 live audit 를 읽어 누락된 source catalog/contentIndex tier 를 판정하고, productization status 의 의미적 blocker(`sourceCatalogNotFull:*`, `sourceCatalogMissingProducerRun:*`, `remoteContentManifestSetMissingProducerRun:*`, `remoteContentMissingFileSources:*`) 도 source-owner/Search Main action 으로 변환한다. 결과는 source-owner `search_catalog_bootstrap=true` dispatch, catalog-mode `searchIndexMain.yml`, 이후 remote evidence/proof bundle 검증 명령을 담은 `searchBootstrapPlan.json` 이며 GitHub/HF 를 변경하지 않는 비파괴 계획 단계다. `buildSearchProofBundle.py` 는 remote source/content blocker 가 있으면 같은 bundle 에 `searchBootstrapPlan.json` 과 `nextActions.bootstrapPlan` 을 포함한다.
11. 본진 품질 bugfix 도 들어갔다. `dartlab.search(..., topK=N)` 는 public `limit` alias 로 동작하고, query 본문 안의 회사명은 `ListingResolver` 로 stockCode facet 에 승격해 랭킹 전에 마스크한다. `"삼성전자 대표이사 변경"` 이 삼성 계열사로 새던 문제는 이 일반 정책으로 막는다.
12. 제품화 상태 감사도 1차 구현됐다. `evaluateSearchProductizationStatus.py` 는 remote evidence, local `indexInfo`, HF round-trip, result contract, canary, quality report 를 한 proof bundle 로 묶어 `designReady/opsReady/releaseReady` 와 blocker 를 산출한다. release gate 는 quality report 의 `releaseEligible=true` 를 그대로 믿지 않고 `realReviewedRows`, `goldOriginCounts`, `reviewStatusCounts`, required target coverage 를 다시 검사한다. searchIndexDelta/Main workflow 는 `searchProductizationStatus.{delta,main}.json` 을 evidence artifact 로 업로드하고, 기본 ops gate 에서 `--fail-on-ops-not-ready`, release 후보 gate 에서 `--fail-on-release-not-ready` 로 hard fail 한다. `evaluateSearchCutover.py` 는 proof bundle 을 `S1/S2/S3/S4` 로 다시 판정하고, `searchCutover.{delta,main}.json` 을 evidence artifact 에 남긴다.
13. source/no-answer canary 는 artifact v3 계약으로 승격됐다. 상태 감사는 canary report 가 valid 여도 expected source coverage(allFilings/panel/edgar-panel/news)가 빠지면 ops-ready 로 보지 않는다. artifact 에서 자동 생성된 positive canary 는 `requireAnswerable=true` 이므로 소스 lane 만 맞고 evidence 가 비어 있는 결과는 통과하지 않는다. news canary 는 최신 단일 기사 sourceRef 가 아니라 news lane smoke 로 두고, 특정 기사 sourceRef 품질은 real query-log gold/miss ledger 로 승격한다.
14. query-log gold toolchain drill 은 searchIndexDelta/Main evidence artifact 에 포함한다. `runSearchQualityDrill.py` 는 raw log -> reviewer label -> canonical gold -> quality report -> miss ledger 경로를 검증하지만 `goldOrigin=drillSynthetic`, `reviewStatus=drillReviewed`, `releaseEvidence=false` 이며 release graduation 증거가 아니다.
15. S4 기본 교체는 S2/S3 와 별도다. `evaluateSearchCutover.py` 의 replacement evidence 는 `defaultBuildMode=catalog`, `scheduledBuildMode=catalog`, `legacyFallbackOperatorOnly=true`, `failClosedPublish=true`, active/previous manifest id, rollback command, rollback 검증, run evidence 기록, surface naming review 를 요구한다. `buildSearchReplacementEvidence.py` 가 이 증거를 자동 생성하며, direct-review proof bundle 은 S4 를 통과했다. Search Main/Delta 의 release gate 는 replacement evidence incomplete 또는 cutover default 미달이면 hard fail 한다.
16. graph catalog 는 요청 경로 live traversal 이 아니라 contentIndex sidecar artifact 다. `entityGraphCatalog.py` 가 explicit catalog copy 또는 `DARTLAB_SEARCH_ENTITY_GRAPH_BUILD=1` offline build 로 `entityGraphCatalog.parquet` 를 준비하고, 파일이 있으면 manifest `requiredFiles/fileHashes/entityGraphCatalog` summary 에 들어가며 main/delta publish 와 local pull 후보에 포함된다. remote evidence/status 는 graph catalog presence, fileSource existence, nEntities, dataAsOf 를 operator evidence 로 남긴다. 없으면 `entityCards` 없이 같은 `dartlab.search(...)` 계약으로 degrade 한다.

---

## 3. 파이프라인 지도

### 3.1 Source Sync

| source | 현재 owner | search 가 소비할 단위 | 증분 원칙 |
|---|---|---|---|
| DART allFilings | `originalSync.yml` allfilings, `dartlab.pipeline allFilings` | 일별 parquet row | `rceptNo + sectionOrder + text_hash` |
| DART panel | `originalSync.yml` dart-zip, dart-reconcile | filing rollup 또는 section row | `rceptNo + sectionKey + period + text_hash` |
| EDGAR panel | `originalSync.yml` edgar | accession item/section row | `accession + item + sectionKey + text_hash` |
| public news | `newsArchiveSync.yml`, `dartlab.pipeline news/newsEnrich` | URL 기반 article/headline row | `urlHash + title/query/date + text_hash` |
| private news | `naverNewsSync.yml` | 제품 public index 에 기본 제외 | 별도 private/local index 정책 전까지 혼합 금지 |

Search workflow 는 source 데이터를 다시 소유하지 않는다. source sync 가 HF 에 올린 artifact 와 manifest 를 읽어 catalog diff 를 만든다.

현재 연결 대상 workflow 는 다음이다.

| 영역 | workflow | search 책임 |
|---|---|---|
| DART panel/allFilings | `.github/workflows/originalSync.yml` | source manifest 소비, catalog diff |
| EDGAR panel/docs | `.github/workflows/originalSync.yml`, `.github/workflows/edgarSync.yml` | accession namespace 분리, EDGAR panel delta |
| public news | `.github/workflows/newsArchiveSync.yml` | public news sourceRef 와 freshness 유지 |
| GDELT/news 후보 | `.github/workflows/gdeltSync.yml` | onboarding 조건 충족 전 corpus 자동 혼합 금지 |
| daily search delta | `.github/workflows/searchIndexDelta.yml` | all sources changed set, staging selfcheck, promote |
| monthly search main | `.github/workflows/searchIndexMain.yml` | full/lite compaction, rollback 가능한 publish |

### 3.2 Search Delta

현재 `searchIndexDelta.yml` 은 daily job 이며, 기존 content index 를 pull 한 뒤 delta 를 빌드한다. 제품화 후 역할은 다음으로 바뀐다.

1. HF 에서 source manifests 를 읽는다.
2. 마지막 search catalog manifest 와 비교한다.
3. allFilings, DART panel, EDGAR panel, news 의 changed rows 만 stage 한다.
4. DuckDB 또는 Polars catalog 에서 `new/changed/deleted/unchanged` 를 계산한다.
5. changed set 으로 delta CSR/meta/stems/evidence sidecar 를 만든다.
6. canary query pack 과 manifest selfcheck 를 통과한 경우에만 HF staging 을 promote 한다.

### 3.3 Search Main Compaction

월간 main job 은 계속 필요하다. 하지만 일상 최신성의 수단이 아니라 delta 누적을 정리하는 compaction 이다.

현재 구현:

- `searchIndexMain.yml` 이 HF `dart/searchCatalog/**` 를 먼저 pull 하고 `prepareSearchDeltaInputs.py` 로 full source snapshot current catalog 를 준비한다.
- source catalog 가 valid 하면 `buildSearchMain.py` 가 `rebuildMainFromCatalog(...)` 로 full main 을 빌드한다.
- source catalog 가 없으면 기존 HF raw folders (`dart/allFilings`, `dart/panel`, `edgar/panel`, `news/public/rss`, `news/public/rss_enriched`) pull + `rebuildContent(...)` full/lite rebuild 로 fallback 한다.
- raw full pull fallback 은 같은 run 에서 allFilings, dartPanel, edgarPanel, newsPublic canonical source catalog 를 `searchIndexMain.full-pull` producer 로 publish 하고, `Prepare canonical catalog main inputs after bootstrap` 단계에서 그 source set 을 current catalog/source manifest set 으로 다시 freeze 한다. HF raw pull quota 가 첫 bootstrap 을 막거나 source별로 먼저 닫는 편이 안전한 경우에는 `planSearchBootstrap.py` 로 실행계획을 만든 뒤 source-owner workflows 를 `search_catalog_bootstrap=true` 로 명시 dispatch 해 각 source catalog 를 먼저 만들 수 있다. 이 경우에도 source별 높은 min-files/min-rows/min-catalog-rows 하한과 `producerRun` lineage 가 필요하다.
- staging upload/current manifest pointer publish helper 는 1차 구현됐다. 실제 monthly main HF catalog run 증거는 아직 없다.

목표 구현:

- source manifests 를 먼저 freeze 한다.
- freeze 된 source catalog snapshots 로 full/lite main 을 compaction 한다.
- delta 를 main 에 흡수한 뒤 manifest, source counts, quality report, rollback manifest 를 같이 publish 한다.

트리거:

- 매월 정기 compaction.
- `delta_docs / main_docs > 0.1~0.2`.
- tombstone 또는 backfill 이 많아짐.
- panel reconcile 대량 복구.
- allFilings backfill 이 넓은 과거 구간을 채움.
- tokenizer, normalizer, sourceAdapter, sourceRef, schemaVersion 변경.
- artifact 크기, load time, p95 latency 예산 초과.

### 3.4 Local Update

로컬은 background daemon 을 기본으로 두지 않는다. 사용자가 search 를 호출하거나 `prefetch/update` 를 호출할 때 HF manifest 를 확인한다.

흐름:

```text
search/prefetch
-> read local active manifest
-> read HF current manifest
-> compatible + newer 판단
-> download required files into staging dir
-> hash/schema/nDocs/sourceCounts/canary selfcheck
-> active pointer atomic swap
-> clear search cache
-> old active keep for rollback
```

`DARTLAB_NO_HF_DOWNLOAD=1` 은 이 흐름 전체를 끈다. 이 경우 local cache 만 사용하고, 인덱스가 없으면 빈 결과와 안내를 반환한다.

### 3.5 Public Surface

public landing 은 full corpus search 를 브라우저에 강제하지 않는다.

허용:

- lite artifact 기반 demo.
- curated public sample.
- stale/freshness badge 명시.
- local/library 로 승격하는 안내.

금지:

- public `/search` 와 corpus search 를 같은 의미로 섞기.
- "최신 전체 공시 검색" claim.
- private news 혼합.
- sourceRef/dataAsOf 없는 결과 표시.

### 3.6 End-to-End Control Plane

제품 검색의 전체 제어 흐름은 다음 하나로 고정한다.

```text
source sync
-> source manifest/catalog publish
-> search delta/main consumes source catalogs
-> local selfcheck
-> HF staging upload
-> current manifest pointer publish
-> local staged download
-> active pointer atomic swap
-> query-log/canary/result-contract evidence loop
```

각 단계는 앞 단계의 산출물을 수정하지 않고 소비만 한다. search workflow 가 source parquet 를 임의 보정하거나, local runtime 이 selfcheck 를 건너뛰고 current 파일을 직접 active 로 쓰면 이 PRD 위반이다.

운영 상태는 `13-cutover-contract.md` 의 cutover 상태로 판정한다. 핵심 구분은 다음이다.

| 상태 | 의미 | 다음 행동 |
|---|---|---|
| designReady | 문서, 코드, 로컬 테스트가 파이프라인 계약을 설명함 | 실제 Actions/HF 증거 수집 |
| opsReady | source catalog, full/lite HF round-trip, result contract, canary, rollback evidence 가 있음 | 본진 기본값 전환 판단 |
| releaseReady | opsReady + real query-log gold 와 miss ledger 기준까지 통과 | 제품 검색 졸업 선언 가능 |
| defaultReplacement | `dartlab.search(...)` 기본값을 단일 제품 엔진으로 교체 | 장기 dual/shadow 기본값 금지 |

현재 상태는 defaultReplacement 까지 한 번 닫았다. 2026-06-16 local HF bootstrap 은 EDGAR raw mirror 를 3,398 files 로 맞춘 뒤 allFilings, DART panel, EDGAR panel, newsPublic source catalog 를 만들고, 462,947-doc current catalog, catalog-mode full rebuild, 280,747-doc catalog-mode lite rebuild, HF stage-only candidate, full/lite round-trip, current promote, remote evidence audit, canary, result contract, proof bundle 을 통과했다. direct-review 품질팩은 106 real reviewed userLog rows 로 `releaseReady=true` 를 만들었고, replacement evidence 는 `state=S4_DEFAULT_REPLACEMENT`, `defaultReplacement=true` 를 만들었다. 실제 source/search Actions run 증거는 새 workflow artifact 로 재확인한다.

---

## 4. Artifact 계약

### 4.1 Source Manifest

각 source sync 는 search 가 읽을 수 있는 source manifest 를 남긴다.

필수 필드:

| 필드 | 의미 |
|---|---|
| `source` | `allFilings`, `dartPanel`, `edgarPanel`, `newsPublic` |
| `sourceVersion` | source adapter version |
| `schemaVersion` | source parquet schema version |
| `dataAsOf` | source row 기준 최신 일자 |
| `builtAt` | manifest 생성 시각 |
| `files` | path, size, hash/etag, rowCount, minDate, maxDate |
| `totalRows` | source 전체 row 수 |
| `changedRows` | 이번 sync 변경 row 수 |
| `deletedRows` | tombstone 또는 삭제 추정 row 수 |
| `producer` | pipeline stage 이름 |
| `producerRun` | source owner workflow, job, runId, sha, Actions artifact name |
| `gitSha` | 빌드 코드 sha |
| `snapshotScope` | `full` 또는 `partial` |

source manifest 가 없거나 `producerRun` 이 없으면 search delta 는 해당 source 를 제품 운영 증거로 주장하지 않는다. `evaluateSearchProductizationStatus.py` 는 원격 source manifest 에 `producerRun.workflow/job/runId/sha/artifactName` 이 없거나 contentIndex 의 `source_manifest_set.json` 내부 source별 `producerRun` 이 비면 S2 `opsReady` 를 주지 않는다.

`snapshotScope=full` 이 아닌 source 는 current catalog 의 freshness claim 에 포함하지 않는다. 1차 구현은 manifest validation, expected-source enforcement, source row count drop check, `buildSearchCatalog.py --min-files/--min-rows/--min-catalog-rows` 차단을 갖는다. source owner workflows 는 추가로 `--compare-remote-manifest --require-previous-manifest` 를 사용해 직전 HF full manifest 대비 files/rows/catalogRows 급락을 publish 전에 차단한다. 첫 full manifest 는 `searchIndexMain.yml` 의 full HF pull bootstrap 또는 운영자가 명시 실행한 source-owner `search_catalog_bootstrap=true` dispatch 만 만들 수 있다. 일반 source-owner 증분 job 은 이전 full manifest 없이 full claim 을 publish 하지 못한다.

### 4.2 Catalog Snapshot

Search catalog 는 source manifest 를 통합해 doc 단위로 stage 한 결과다.

중요한 단위 규칙:

- `allFilings` 는 `fetch_status=ok` 이고 non-empty 본문인 row 만 사용하며, 같은 `docKey` 가 여러 shard 에 있으면 최신 정상 row 를 남긴다.
- DART panel 과 EDGAR panel 은 raw block row 를 catalog row 로 쓰지 않는다. 본진 검색과 같은 `rceptNo/accession` filing 롤업 단위로 bounded plain text 를 만든다.
- source manifest 의 `totalRows` 는 search catalog doc row 수다. raw/source row 수가 다르면 `rawRows` 로 보존한다.
- catalog snapshot 은 검색/evidence 용 bounded text 를 갖는다. 전체 원문 복구는 source artifact 와 `sourceRef` 로 돌아가서 처리한다.

필수 컬럼:

- `docKey`
- `source`
- `sourceRef`
- `sourcePriority`
- `rceptNo`
- `accession`
- `urlHash`
- `url`
- `sectionKey`
- `sectionOrder`
- `corpCode`
- `stockCode`
- `ticker`
- `companyName`
- `date`
- `reportName`
- `title`
- `textHash`
- `metadataHash`
- `contentLen`
- `deleted`
- `sourceDataAsOf`
- `sourceAdapterVersion`

중복 정책:

- 같은 DART `rceptNo` 가 allFilings 와 panel 에 있으면 panel rolled body 를 우선한다.
- allFilings 는 panel 이 커버하지 않는 비정기/수시 공시와 최신 delta 에 강하다.
- EDGAR 는 accession namespace 로 분리한다.
- news 는 URL hash namespace 로 분리하고, filing 으로 fallback 하지 않는다.

### 4.3 Search Index Manifest

`indexInfo()` 와 local updater 는 search manifest 만 믿는다.

필수 필드:

- `artifactVersion`
- `schemaVersion`
- `tokenizerVersion`
- `normalizerVersion`
- `sourceRefVersion`
- `builtAt`
- `mainDataAsOf`
- `deltaDataAsOf`
- `sourceDataAsOf`
- `nDocsBySource`
- `nDocsByTier`
- `newDocs`
- `changedDocs`
- `deletedDocs`
- `unchangedDocs`
- `hasDelta`
- `requiredFiles`
- `fileHashes`
- `canaryPackVersion`
- `entityGraphCatalog`
- `qualityReportPath`
- `compatibleMinLibraryVersion`
- `compatibleMaxSchemaVersion`
- `buildCommand`
- `gitSha`

`builtAt` 과 `dataAsOf` 는 다르다. 사용자가 묻는 최신성은 `sourceDataAsOf` 로 답한다.

---

## 5. Selfcheck 계약

HF publish 전 selfcheck:

1. required files 존재.
2. manifest file hash 일치.
3. `main_info/delta_info` 와 manifest 의 `nDocs` 일치.
4. source별 row count 가 이전 대비 비정상 급감하지 않음.
5. router/events 비어있지 않음.
6. source canary query 통과.
7. no-answer canary false accept 0.
8. random pressure quick profile 통과.
9. artifact load smoke 통과.
10. index schema 가 현재 library 와 compatible.
11. result row contract audit 통과.

현재 구현된 selfcheck 는 이 계약의 대부분을 포함한다. manifest required files/hash/load smoke, schema compatibility, local canary query, manifest 내 artifact 기반 source/no-answer canary pack, optional `entityGraphCatalog.parquet` required file/hash/summary, source catalog diff smoke, source catalog batch publish helper, bootstrap plan CLI, publish 전 local selfcheck, staging upload/current manifest pointer publish helper, manifest 기반 source/no-answer canary pack evaluator, result contract evaluator, result contract workflow evidence upload, query 본문 회사명 stockCode facet regression, local end-to-end pipeline drill, HF current manifest round-trip CLI, productization status evaluator, replacement evidence evaluator 는 들어갔다. 2026-06-16 local HF bootstrap 에서 sourceCatalog/currentCatalog/full rebuild/lite rebuild/canary/resultContract/full-lite round-trip/promote 는 통과했고, direct-review 106 row 품질팩과 S4 cutover 도 통과했다. 동일 순서의 Actions 결과 확인과 300 rows 방향 query-log 확대는 계속 필요하다.

Local swap 전 selfcheck:

1. staging dir 에 required files 전부 존재.
2. hash 검증.
3. manifest JSON parse.
4. schema compatible.
5. `loadSegment` smoke.
6. canary 3~5개 query smoke.
7. 실패 시 staging 삭제, active 유지.

---

## 6. 테스트 전략

전체 `pytest tests/ -v` 는 금지한다. 제품 검색의 release gate 는 다음 묶음이다.

### 6.1 코드 변경 전후

```powershell
uv run python -X utf8 tests/run.py preflight
uv run python -X utf8 tests/audit/dartlabGuard.py quick
```

검색 L0~L1.5 경계 또는 provider/data path 변경 시:

```powershell
uv run python -X utf8 tests/audit/dartlabGuard.py strict --scope l0-l15 --providers dart,edgar
```

### 6.2 Search Product Gate

`tests/_attempts/searchProductCore` replacement gate 는 tracked gate 로 승격한다.

필수 프로필:

- quick: 개발 중 회귀 확인.
- full: 큰 slice 품질 확인.
- replacement: 단일 엔진 교체 승인 gate.
- hfPipelineDryRun: source manifest, catalog diff, staging publish selfcheck.
- localUpdaterSmoke: staged download, hash 검증, atomic swap, rollback.
- localPipelineDrill: synthetic raw source parquet 로 source catalog 와 `source_manifest_set.json` 을 만든 뒤 catalog diff, artifact build, staging upload/current manifest pointer publish, local activation, rollback 을 한 번에 검증.
- hfRoundTrip: HF current manifest 를 내려받아 temp/local contentIndex 에 activate 하고 rollback 하는 smoke.
- resultContractAudit: 실제 result rows 가 `source/sourceRef/dataAsOf/snippet/answerable/fieldCards` 와 evidence card 계약을 만족하는지 검증하고 workflow evidence artifact 로 업로드.
- remoteEvidenceAudit: HF source catalog inventory, contentIndex current manifest, fileSources target, contentIndex `source_manifest_set.json` 내부 source별 `producerRun` 을 감사하고 `searchRemoteEvidence.{delta,main}.json` 으로 proof bundle 에 남김.
- qualityToolchainDrill: synthetic reviewed rows 로 query-log gold/miss-ledger 도구 체인을 검사하고 `searchQualityDrill.{delta,main}.json` 으로 남김. release 증거는 아님.
- productizationStatusAudit: remote evidence, local indexInfo, HF round-trip, result contract, canary, real quality report 를 모아 `searchProductizationStatus.{delta,main}.json` 으로 `designReady/opsReady/releaseReady` 를 판정.

ops-ready 최소 조건:

- remote source catalog 는 expected source 4종의 manifest/catalog 파일, `snapshotScope=full`, `dataAsOf`, row/file count 를 가진다.
- remote contentIndex full/lite manifest 는 expected source별 `nDocsBySource` 와 `sourceDataAsOf`, `fileSources` 를 가진다.
- remote contentIndex full/lite manifest 는 `sourceManifestSetId` 를 갖고, `fileSources` 로 열리는 `source_manifest_set.json` 내부 4개 source 모두 `producerRun.workflow/job/runId/sha/artifactName` 을 가진다.
- local `indexInfo()` 는 available/compatible/manifestValid 이고 expected source별 count/freshness 를 가진다.
- HF round-trip, result contract, source/no-answer canary report 가 valid 이다.

release-ready 는 위 조건에 real query-log gold quality report 가 붙어야 한다.

### 6.3 Release Graduation

제품 졸업은 다음을 모두 만족해야 한다.

| 항목 | 기준 |
|---|---:|
| real query-log gold | 100 rows 이상, 권장 300 |
| coverage | filing/news/noAnswer/EDGAR 포함 |
| overall readyRate | 0.9 이상 |
| filing docHit10 | 0.9 이상 |
| filing memoryCitationTop3Exact | 0.9 이상 |
| news sourcePrecision10 | 0.9 이상 |
| noAnswer falseAcceptRate | 0.1 이하 |
| result contract invalidRows | 0 |
| warm latency p95 | 제품 체감 가능 범위 |
| local update failure | active index 보존 |

proxy/generated gold 는 release graduation 증거가 아니다. regression pressure 로만 쓴다.

실행 계약:

```powershell
uv run python -X utf8 .github/scripts/search/prepareSearchGold.py `
  --input data/search/queryLogRaw.jsonl `
  --labels data/search/queryLogLabels.reviewed.jsonl `
  --out data/search/queryLogGold.real.jsonl `
  --summary data/search/queryLogGold.summary.json `
  --min-rows 100 `
  --required-targets filing,news,noAnswer,edgar `
  --fail-on-ineligible

uv run python -X utf8 .github/scripts/search/evaluateSearchGold.py `
  --gold data/search/queryLogGold.real.jsonl `
  --out data/search/qualityReport.json `
  --miss-ledger data/search/missLedger.jsonl `
  --min-rows 100 `
  --required-targets filing,news,noAnswer,edgar `
  --fail-on-ineligible

uv run python -X utf8 .github/scripts/search/evaluateSearchResultContract.py `
  --queries-json data/search/queryLogGold.real.jsonl `
  --out data/search/resultContractReport.json `
  --min-rows 100 `
  --fail-on-error
```

`--allow-proxy-query-log` 는 실험/회귀 압박에서만 쓴다. release graduation 에서는 금지한다.

---

## 7. 운영 유지보수

### 매일

- source workflows 성공 여부 확인.
- search delta selfcheck 결과 확인.
- source별 `dataAsOf` 가 멈췄는지 확인.
- failure issue 또는 monitor pipeline 을 본다.

### 매주

- miss ledger 를 분류한다.
- 반복 miss 만 policy backlog 로 승격한다.
- query-log gold candidate 를 리뷰한다.
- `indexInfo()` freshness sample 을 기록한다.

### 매월

- main compaction 실행.
- delta tombstone 비율과 artifact size 확인.
- full/lite tier 크기 확인.
- canary pack 을 최신 사건으로 갱신한다.
- 실제 query-log gold gate 를 다시 실행한다.

### Schema 변경 때

- sourceAdapter/tokenizer/normalizer/sourceRefVersion bump.
- full rebuild 필수 여부 판단.
- compatible library version 명시.
- old local cache rejection 또는 graceful fallback 확인.

---

## 8. 장애 대응 원칙

| 장애 | 대응 |
|---|---|
| HF 429 또는 partial pull | publish 금지. staging 보존 또는 retry. active 유지. |
| source manifest 누락 | 해당 source freshness claim 금지. delta 에 포함하지 않음. |
| source count 급감 | upload 중단. source owner workflow 조사. |
| delta 빌드 0 docs | 정상 no-op 인지 sourceDataAsOf 로 판정. 불명확하면 publish 금지. |
| local download 실패 | staging 삭제. 기존 active 사용. |
| schema incompatible | 사용자에게 update 안내. 기존 compatible cache 사용. |
| canary fail | publish 금지. miss ledger 에 기록. |
| real gold regression | release block. 단일 query 특수 mapper 금지. |

---

## 9. 구현 단계

### Phase 0. 계약 고정

- 이 문서를 PRD 기준으로 채택.
- result schema, source manifest, index manifest, selfcheck schema 확정.
- `06-progress-ledger.md` NEXT 와 연결.

현재 상태: result schema, result contract audit, result contract evidence upload, remote evidence audit, bootstrap plan CLI, proof bundle next actions, cutover state audit, productization status audit, proof bundle 생성, source manifest, source catalog generation, catalog diff/dry-run/delta export, expected source empty snapshot 차단, manifest-aware current index pull, delta publish 의 previous `fileSources` 보존, index manifest 생성/업로드, publish 전 local selfcheck, remote `requiredFiles`/`fileSources` 대상 검증, full/lite HF round-trip gate, local staged download/selfcheck/active pointer, previous active rollback helper, active manifest 비교, source intent hard isolation, query 회사명 stockCode facet, missing-evidence/facet/stale-source answerability, row/bounded-chunk evidence, memory card, query-log raw capture, query-log gold/miss-ledger gate 는 1차 구현됐다. 실제 GitHub Actions source owner/search delta run 확인, full-source evidence/result contract report 확인, reviewer-labeled real query-log gold row 확보는 남아 있다.

### Phase 1. 본진 single-engine migration

- `_attempts` runtime 을 `src/dartlab/providers/dart/search` 책임 단위로 분해.
- `dartlab.search(...)` 공개 시그니처 유지.
- source intent, facet planner, answerability, evidence pack, memory card 를 내부 모듈로 붙임.
- replacement gate 를 acceptance 로 둠.

현재 1차 완료:

- source intent hard isolation.
- content/unified source pre-rank mask.
- source mismatch / missing evidence answerability.
- row-level evidence card / memory-card set.
- receipt/date/report/company facet mismatch.
- query-focused bounded `evidenceText` chunk card.
- local active manifest comparison.
- searchIndexDelta catalog mode entrypoint.
- source owner searchCatalog artifact generation.
- searchIndexDelta HF searchCatalog pull and catalog env preparation.
- local pipeline drill preflight for searchIndexDelta/SearchIndexMain, including raw source parquet -> source catalog -> `source_manifest_set.json` freeze -> contentIndex publish/activate/rollback.
- manifest-aware current index pull for delta publish.
- full/lite HF round-trip evidence gate.
- remote evidence fileSources target existence gate.
- remote blocker 를 source-owner bootstrap/Search Main/검증 순서로 바꾸는 bootstrap plan CLI.
- proof bundle 실패 시 `searchBootstrapPlan.json` 과 `nextActions.bootstrapPlan` 포함.
- `evaluateSearchCutover.py` 로 proof bundle 을 S1/S2/S3/S4 cutover state 로 판정하고 `searchCutover.{delta,main}.json` evidence artifact 생성.
- proof bundle artifact generation for searchIndexDelta/Main.

남은 항목:

- actual workflow run evidence for source owner manifests and scheduled catalog delta publish.
- staging upload/current manifest pointer publish path 는 1차 구현 완료. delta publish 는 previous manifest `fileSources` 를 보존한다. 실제 HF round-trip 과 rollback drill evidence artifact 확인 필요.
- local raw-source pipeline drill 은 source parquet 에서 source catalog/source manifest set/contentIndex/local activation/rollback 까지 1차 완료. HF current manifest round-trip CLI 와 workflow 배선도 완료. full/lite 양쪽 실제 Actions evidence artifact 확인 필요.
- 실제 full-source artifact 기반 evidence 품질 검증.

### Phase 2. HF catalog delta

- source manifests 를 읽는 catalog builder 작성.
- allFilings/panel/news/EDGAR changed set 계산.
- search delta workflow 를 source sync 이후 selfcheck 기반으로 재구성.

현재 1차 완료:

- source owner workflow 에 `buildSearchCatalog.py` step 추가.
- `buildSearchCatalog.py` 기본 full snapshot completeness threshold 와 직전 full manifest 대비 drop guard 추가.
- HF `dart/searchCatalog/{source}/` upload path 추가. source manifest 와 catalog snapshot 은 단일 `create_commit` batch 로 publish 한다.
- `searchIndexDelta.yml` 이 HF `dart/searchCatalog/**` 와 기존 `catalog_snapshot.parquet` 를 pull.
- `searchIndexDelta.yml` 이 `pullSearchCurrentIndex.py` 로 current manifest pointer 를 따라 기존 full main required files 와 `previous_manifest.json` 을 복원.
- `prepareSearchDeltaInputs.py` 가 source catalogs 를 current catalog 로 합치고 catalog mode env 를 준비.
- `searchIndexDelta.yml` 은 prepared catalog env 를 build step 의 빈 manual input env 로 덮지 않는다.
- `buildSearchDelta.py` 가 catalog mode 에서 changed set 을 `buildContentSegment` 입력으로 사용.

남은 항목:

- 실제 Actions run 에서 source catalog artifacts 생성 확인.
- 실제 scheduled/dispatch run 에서 catalog mode publish 확인.
- catalog mode 를 기본 운영 경로로 선언하기 전 rollback drill 1회.
- staging upload/current manifest pointer publish helper 와 publish 전 local selfcheck 를 실제 HF scheduled run 에서 검증.
- remote evidence 가 manifest 존재뿐 아니라 `fileSources` 대상 파일 존재와 `source_manifest_set.json` 내부 source별 `producerRun` 까지 검증한다. 실제 HF scheduled run 에서 `contentIndexFileSourceMissing` 과 `remoteContentManifestSetMissingProducerRun:*` 이 없는지 확인.
- expected source set 과 `snapshotScope=full` enforcement. (1차 구현 완료, 실제 Actions run 확인 필요)
- expected source empty full snapshot 차단. (source catalog 생성 CLI + catalog mode selfcheck 1차 구현 완료, 실제 source owner pull completeness 확인 필요)

### Phase 3. Local auto update

- manifest compare.
- staged download.
- hash/schema/canary selfcheck.
- active pointer swap.
- rollback.

현재 1차 완료:

- manifest 기반 staged download.
- required files/hash/load smoke/canary selfcheck.
- schema compatibility check.
- source/no-answer canary pack activation check.
- active manifest 비교와 same/older remote skip.
- active pointer atomic swap.
- previous active pointer 보존과 rollback helper.
- 실패 artifact 활성화 거부 단위 테스트.

남은 항목:

- 실제 HF current artifact round-trip smoke evidence artifact 확인.
- 운영자 rollback drill 문서 증거.

### Phase 4. Release graduation

- real query-log gold 100~300 rows 확보.
- replacement + hfPipeline + localUpdater + preflight gate 통과.
- Skill OS `engines.search` 와 운영 문서 갱신.

현재 1차 완료:

- `goldLog.py` 와 `prepareSearchGold.py` 가 raw query log + reviewer label 을 canonical real gold JSONL 로 정규화하고, release coverage/sourceRef/review status 를 요약한다.
- `dartlab.search(...)` 는 `DARTLAB_SEARCH_QUERY_LOG` 가 켜졌을 때 raw candidate JSONL 을 남긴다. 이 row 는 `reviewStatus=candidate` 이므로 reviewer label 전까지 release-eligible 이 아니다.
- `qualityGate.py` 가 query-log gold 를 real/proxy/reviewed 로 분리하고 readyRate/docHit10/memoryCitationTop3Exact/newsSourcePrecision10/noAnswer falseAcceptRate 를 산출한다.
- `evaluateSearchGold.py` 가 실제 `dartlab.search(...)` 또는 precomputed results JSON 으로 quality report 와 miss ledger 를 생성한다.
- `resultContract.py` 와 `evaluateSearchResultContract.py` 가 실제 `dartlab.search(...)` 또는 precomputed results JSON 으로 제품 결과 row 계약 report 를 생성하고 searchIndexDelta/Main evidence artifact 로 업로드한다.
- miss ledger 는 `docMiss10`, `citationMissTop3`, `falseAccept`, `newsSourcePrecision10`, `goldReviewRequired` 를 policy candidate 로 연결한다.
- `canaryPack.py` 와 `evaluateSearchCanary.py` 가 source/no-answer canary pack 을 평가한다. 실제 운영 rows 와 artifact 기반 실행 증거는 남아 있다.
- query-log gold doc/citation hit 는 answerable result 에서만 인정한다.

남은 항목:

- 실제 운영자/사용자 raw query 후보를 수집하고 reviewer label 을 붙인 real query-log gold 100~300 rows 확보.
- raw log 와 reviewer label 을 `prepareSearchGold.py --fail-on-ineligible` 로 canonical `data/search/queryLogGold.real.jsonl` 에 고정.
- artifact 기반 source/no-answer canary pack 자동 생성과 artifact publish/local activation path 연결. (1차 완료)
- 운영자가 큐레이션한 최신 사건 source/no-answer canary rows 확보.
- filing/news/noAnswer/EDGAR coverage 를 채운 뒤 `--fail-on-ineligible` 로 통과.
- 실제 full-source artifact 결과로 `evaluateSearchResultContract.py --fail-on-error` 통과 report 확보.
- miss ledger 반복 유형을 일반 정책 backlog 로 승격.

### Phase 5. Main compaction catalogization

- `searchIndexMain.yml` raw HF pull 기반 full rebuild 를 source manifest snapshot 기반 compaction 우선 경로로 전환. (1차 완료)
- compaction 입력 source set 을 manifest 로 freeze. (1차 완료, actual run evidence 필요)
- full/lite tier 모두 같은 source snapshot lineage 를 기록.
- staging upload/current manifest pointer publish helper 를 유지하고 source manifest snapshot lineage 를 연결.
- rollback 가능한 previous main manifest 를 보존.

---

## 10. 명시적 비목표

- 새 public search API 추가.
- legacy 검색과 product 검색을 장기 이중 운영.
- 사람이 계속 관리해야 하는 prebuild intent dictionary.
- dense vector DB 를 전역 1차 검색으로 채택.
- public landing 에 full corpus 최신 검색 claim.
- private news 를 public contentIndex 에 혼합.
- full rebuild 를 매일 운영 전제로 두기.

---

## 11. 제품 요구사항

### P0

| 요구사항 | 수락 기준 |
|---|---|
| 단일 공개계약 | `dartlab.search(...)` 시그니처 유지. 새 sibling API 없이 내부 엔진 교체. |
| 본문 검색 기본값 | `scope="auto"` 와 `scope="content"` 가 filing/news body lane 을 검색. 제목은 anchor 로만 사용. |
| source hard isolation | `공시 말고 뉴스`, `뉴스 말고 공시` 류 질의에서 다른 source fallback 금지. |
| source manifest | allFilings, DART panel, EDGAR panel, public news 가 `dataAsOf`, files, row counts, hash/etag 를 제공. |
| source lineage | 각 source manifest 가 `producerRun.workflow/job/runId/sha/artifactName` 을 제공하고 `source_manifest_set.json` 이 이를 보존. |
| source completeness | canonical source catalog 는 full snapshot 임을 manifest, file-count gate, 직전 full manifest 대비 drop guard 로 증명. source-owner 증분 job 은 이전 full manifest 없이는 full claim publish 금지. 단 명시적 `search_catalog_bootstrap=true` 초기 dispatch 는 previous manifest 요구만 해제하고 높은 completeness 하한으로 검증한다. partial snapshot 은 freshness claim 금지. |
| empty source guard | expected source 가 0 row full snapshot 이면 catalog mode 금지. |
| catalog delta | `docKey/textHash/metadataHash/deleted` 로 new/changed/deleted/unchanged 계산. |
| HF publish safety | staging upload, hash/load/canary selfcheck, current manifest pointer publish 순서 준수. |
| local active safety | 새 artifact 실패 시 기존 active index 보존. |
| 결과 계약 | 모든 결과 row 가 `source/sourceRef/dataAsOf/snippet/answerable/notAnswerableReason/fieldCards` 를 가지고 `evaluateSearchResultContract.py --fail-on-error` 를 통과한다. |
| 졸업 차단 | real query-log gold 전에는 release graduation 금지. |

### P1

| 요구사항 | 수락 기준 |
|---|---|
| evidence card | top sourceRef 에 대해 field/value/snippet 근거를 LLM/UI 가 바로 소비 가능. |
| memory card | 반복 질의에서 LLM 이 sourceRef set 을 세션 지식처럼 재사용 가능. |
| HF current pointer | local updater 가 current manifest 와 local manifest 를 비교하고 `fileSources` 에 지정된 staging files 만 갱신. |
| rollback drill | 이전 current artifact 로 되돌리는 절차와 검증 명령 존재. |
| source/no-answer canary pack | artifact 기반 pack 이 manifest 에 자동 포함되고, publish/local activation 전에 source isolation, sourceRef hit, no-answer false accept 를 자동 차단. |
| public lite demo | public surface 는 lite/curated artifact 만 사용하고 full corpus 최신 claim 금지. |

### P2

| 요구사항 | 수락 기준 |
|---|---|
| dense sidecar | sparse topK 안에서 chunk/evidence rerank 용으로만 사용. 전역 1차 검색 대체 금지. |
| GDELT onboarding | source manifest, sourceRef, license, canary, failure type 충족 후 corpus 혼합. |
| private/local news | public index 와 분리된 local/private artifact 정책 수립 후만 사용. |

---

## 12. 이관 승인 매트릭스

| 단계 | 통과 의미 | 필수 증거 |
|---|---|---|
| 본진 코드 이식 가능 | 실험 개념을 `src/dartlab/providers/dart/search` 로 옮길 가치가 있음 | S1 `designReady=true`, replacement/random pressure 기준선, result schema, manifest schema |
| 운영 artifact publish 가능 | HF current manifest pointer 를 올려도 local 이 나쁜 artifact 를 active 하지 않음 | source catalog 4종, source manifest set id, full/lite manifest, staging selfcheck, required file/hash 검증, canary pass, rollback path |
| 본진 기본값 전환 가능 | legacy/search 이중선 없이 단일 엔진으로 교체 가능 | S2 `opsReady=true`, proof bundle `missingEvidence=[]`, result contract/canary/HF round-trip/local indexInfo pass |
| release graduation 가능 | 제품 검색이라고 말할 수 있음 | S3 `releaseReady=true`, real query-log gold 100~300 rows, filing/news/noAnswer/EDGAR coverage, 품질 기준 통과 |

현재 상태는 "본진 기본값 전환 가능"까지 넘겼고 direct-review 기준 S4 defaultReplacement 다. runtime 구현, catalog/local updater/result contract audit, full-source evidence, real reviewed quality report, replacement evidence 가 모두 통과했다. 남은 것은 새 Search Main/Delta Actions artifact 로 같은 순서를 재현하고, query-log gold 를 300 rows 방향으로 늘리는 운영 루프다.

---

## 13. 장기 유지보수 모델

### 책임 분리

| 책임 | owner | search 가 직접 하면 안 되는 일 |
|---|---|---|
| 원천 수집 | source workflow | source row 를 임의 보정하거나 누락을 숨김 |
| source manifest | source workflow | manifest 없는 source 를 최신이라고 주장 |
| catalog diff | search workflow | source별 stable key 없이 row 를 합침 |
| ranking/index | search workflow | public/private source 를 sourceRef 없이 혼합 |
| local activation | runtime updater | selfcheck 실패 artifact 로 active pointer 변경 |
| 품질 개선 | query-log/miss ledger owner | query별 특수 mapper 누적 |

### 유지보수 비용을 낮추는 규칙

1. 새 source 는 manifest/sourceRef/canary/failureType 없이 corpus 에 넣지 않는다.
2. 새 품질 개선은 source adapter, facet planner, sourceRef policy, answerability, evidence pack 중 하나의 일반 정책이어야 한다.
3. daily delta 는 최신성 수단이고 monthly main 은 compaction 수단이다. 둘을 섞지 않는다.
4. `builtAt` 최신성과 `sourceDataAsOf` 최신성을 혼동하지 않는다.
5. local update 는 실패해도 조용히 이전 active 를 유지해야 한다.
6. 모든 운영 문서는 구현 변경과 같은 PR 에서 갱신한다.

### 재색인 기준

정상 증분:

- 새 filing/news/EDGAR row 추가.
- 기존 row 본문 또는 metadata 일부 변경.
- backfill 구간이 stable docKey 로 들어옴.
- source별 deleted/tombstone 이 제한적으로 발생.

full rebuild:

- tokenizer/normalizer/schema/sourceRefVersion 변경.
- docKey 의미 변경.
- source adapter 가 본문 chunk 의미를 바꿈.
- delta 비율, tombstone, artifact size, load time 이 예산 초과.
- 월간 compaction window.

---

## 14. PRD 완료 조건

문서 기준 완료:

- allFilings, DART panel, EDGAR panel, public news, GDELT 후보, private news 경계가 모두 명시됨.
- source manifest, catalog snapshot, search manifest, HF staging upload/current manifest pointer publish, local active swap 이 모두 계약화됨.
- daily/weekly/monthly/release 유지보수 루프가 운영 런북과 연결됨.
- 본진 이식 가능, 기본값 전환 가능, release graduation 가능 조건이 분리됨.

구현 기준 완료:

- `searchIndexDelta.yml` 기본 경로가 all-source catalog delta 를 사용하고 legacy fallback 이 운영자 명시 예외로만 남음.
- publish workflow 가 current pointer 를 gate 전에 바꾸지 않고, staged candidate manifest 를 검증한 뒤 promote 함. (helper/round-trip/워크플로 배선 완료, direct-review proof 통과, 실제 Actions run 재확인 필요)
- source owner workflows 가 source manifest 를 실제 생성하고 HF `dart/searchCatalog/{source}/` 에 publish 함.
- source catalog expected set, full snapshot completeness, 이전 full manifest 대비 급락을 자동 차단함. (1차 구현 완료, 실제 Actions run 확인 필요)
- expected source 0 row full snapshot 을 source catalog 생성과 catalog mode selfcheck 양쪽에서 자동 차단함. (1차 구현 완료, 실제 Actions run 확인 필요)
- `searchIndexMain.yml` 이 source manifest snapshot 기반 main compaction 우선 경로로 전환됨. (1차 구현 완료, 실제 Actions run 확인 필요)
- source intent hard isolation, answerability, evidence card 가 본진 모듈로 들어감.
- local updater 가 HF current pointer 비교까지 수행함.
- source/no-answer canary pack gate 가 publish/local activation 전에 실행 가능함. artifact 기반 pack 자동 생성과 manifest 주입은 1차 완료됐고, 운영자가 큐레이션한 rows 와 실제 Actions artifact run 증거가 남아 있다.
- productization status audit 가 proof bundle 을 판정함. 현재 direct-review 상태는 `opsReady=true`, `releaseReady=true`, blockers=[] 이며, workflow 기본 ops gate/release gate 에서 blocker 를 hard fail 한다.
- cutover state audit 가 S2/S3/S4 를 분리하고, S4 는 catalog 단일 기본값과 fail-closed publish replacement evidence 가 없으면 차단함. direct-review cutover 는 `S4_DEFAULT_REPLACEMENT` 다. workflow release gate 는 `--fail-on-default-not-ready` 로 같은 조건을 강제한다.
- real query-log gold gate 를 통과함. 게이트 구현과 direct-review 106 rows 는 통과했고, 장기 운영 품질을 위해 300 rows 방향으로 계속 늘린다.

운영 증거 기준:

- source owner run id, produced source catalog path, source manifest hash 가 `11` 또는 `12` 에 기록됨.
- search delta run id, catalog mode 여부, promoted manifest id, required file hash 검증 결과가 기록됨.
- local staged download smoke 에서 active manifest id 와 previous manifest id 가 기록됨.
- rollback drill 에서 되돌린 manifest id, 검증 명령, 결과가 기록됨.
- query-log gold/miss ledger 의 review status 가 `06-progress-ledger.md` 에 반영됨.

---

## 15. 운영 문서 동기화 요구사항

제품 검색은 코드만으로 완료되지 않는다. 다음 변경은 같은 변경 단위에서 mainPlan 과 Skill OS 를 함께 갱신해야 운영 완료로 인정한다.

| 변경 | 반드시 갱신할 문서 |
|---|---|
| source 추가 또는 source owner 변경 | `03`, `10`, `11`, `12`, Skill OS `engines.search` |
| source manifest/catalog 필드 변경 | `03`, `10`, `11`, `12` |
| delta/main workflow 순서 변경 | `10`, `11`, `12`, `06` |
| HF publish 방식 변경 | `10`, `11`, `12` |
| local activation/rollback 정책 변경 | `08`, `10`, `11`, `12` |
| quality/canary/gold threshold 변경 | `02`, `06`, `10`, `11` |
| public/local/library 검색 표면 변경 | `08`, `10`, `11`, Skill OS `engines.search` |

운영 문서 업데이트는 사후 정리가 아니라 release blocker 다. 문서가 실제 workflow, manifest, rollback, gold gate 와 어긋나면 제품 검색은 "운영 가능" 상태가 아니다.

## 16. 운영 Proof Bundle

본진 교체 또는 운영 인계 시 다음 proof bundle 이 있어야 한다.

| proof | 최소 내용 | 누락 시 상태 |
|---|---|---|
| source catalog inventory | source별 workflow run id, Actions artifact name, manifest path, snapshotScope, row/files count, hash | catalog delta 운영 증거 부족 |
| search publish evidence | staging path, current manifest pointer, requiredFiles, fileHashes, `fileSources` | artifact publish 가능 판단 보류 |
| remote evidence audit | `searchRemoteEvidence.{delta,main}.json`, source catalog missing list, contentIndex manifest missing list | HF 원격 상태 판단 보류 |
| bootstrap plan | `searchBootstrapPlan.json`, source-owner bootstrap argv, Search Main argv, verification argv | 다음 실행을 사람 기억에 의존 |
| proof bundle next actions | `searchProofBundle.json.nextActions.bootstrapPlan`, missing source/tier, action id list | 실패 proof 와 다음 실행 계획 분리 |
| cutover state | `searchCutover.{delta,main}.json`, S1/S2/S3/S4, defaultReplacement blockers | S2/S3 와 S4 기본값 교체 혼동 |
| HF round-trip report | `searchHfRoundTrip.{delta,main}.json`, activate/rollback 결과 | local 자동 업데이트 실증 부족 |
| result contract report | `searchResultContract.{delta,main}.json`, totalRows, invalidRows | 제품 row 계약 실증 부족 |
| canary report | `searchCanary.{delta,main}.json`, passRate, false accept, source/sourceRef failures | publish/local activation 안전성 판단 보류 |
| local runtime smoke | `dartlab.search.indexInfo()` output, active manifest id, compatible flag | 사용 환경 안전성 판단 보류 |
| rollback evidence | previous manifest id, rollback command, validation result | 장애 복구 인계 불가 |
| quality evidence | real/proxy gold 구분, query-log summary, miss ledger status | release graduation 금지 |
| productization status | `searchProductizationStatus.{delta,main}.json`, `designReady/opsReady/releaseReady`, blocker list | 증거 조합을 사람 기억에 의존 |

Proof bundle 은 `12-pipeline-maintenance-map.md` 의 운영 증거 원장과 `06-progress-ledger.md` 의 결정/NEXT 에 연결한다. 증거 파일이 Actions artifact 로만 남는 경우에도 run id 와 artifact name 을 문서에 남겨야 한다.
