# 12. 파이프라인·유지보수 맵 - 실제 운영 연결표

상태: v1.26 (2026-06-18)
범위: search productization 이 실제 GitHub workflow, HF artifact, local updater, 품질 gate 로 어떻게 이어지는지 정의한다.

---

## 1. 문서 목적

이 문서는 설계 문서가 아니라 운영 연결표다.

`10-production-pipeline-prd.md` 가 제품 파이프라인의 계약이고, `11-operator-runbook.md` 가 운영 절차라면, 이 문서는 "어느 workflow 가 어떤 artifact 를 만들고 search 는 무엇을 소비하는가"를 실제 파일명 기준으로 고정한다.

원칙:

1. source workflow 는 원천 데이터를 소유한다.
2. search workflow 는 source manifest 를 소비해 catalog diff 와 index artifact 만 만든다.
3. local runtime 은 HF current manifest 를 보고 staged download 후 active pointer 만 바꾼다.
4. 운영자는 query miss 를 특수 mapper 로 해결하지 않는다. miss ledger, canary, gold gate 로 반복 유형만 정책화한다.
5. 본진 교체 판단은 `13-cutover-contract.md` 의 `designReady/opsReady/releaseReady/defaultReplacement` 상태와 proof bundle 을 기준으로 한다.

---

## 2. 현재 파이프라인 맵

| 단계 | 현재 workflow/script | 현재 산출물 | search 제품화 후 계약 |
|---|---|---|---|
| DART panel/original | `.github/workflows/originalSync.yml` `dart-zip`, `dart-reconcile` | `dart/original`, `dart/panel/**`, `search-catalog-dartPanel-*` Actions artifact | `dartPanel` source manifest 생성. source manifest `producerRun` 으로 workflow/job/run lineage 를 보존. source-owner publish 는 직전 HF full manifest 대비 drop guard 를 통과해야 하며, panel changed rcept/section 만 catalog delta 로 보냄. |
| DART allFilings forward | `.github/workflows/originalSync.yml` `allfilings` | `dart/allFilings/*`, recent 통합 parquet, `search-catalog-allFilings-*` Actions artifact | `allFilings` source manifest 생성. source manifest `producerRun` 으로 workflow/job/run lineage 를 보존. source-owner publish 는 직전 HF full manifest 대비 drop guard 를 통과해야 하며, `rceptNo + sectionOrder + text_hash` 로 delta. |
| DART allFilings backfill | `.github/workflows/originalSync.yml` `allfilings-backfill` | 과거 allFilings slab, recent 통합 parquet | backfill 구간만 catalog diff. 넓은 과거 보강은 delta 로 먼저 흡수하고 월간 compaction 에서 main 으로 합침. |
| EDGAR panel | `.github/workflows/originalSync.yml` `edgar`, `.github/workflows/edgarSync.yml` `Update EDGAR panel` | `edgar/panel/{ticker}.parquet`, `search-catalog-edgarPanel-*` Actions artifact | `edgarPanel` source manifest 생성. source manifest `producerRun` 으로 workflow/job/run lineage 를 보존. source-owner publish 는 직전 HF full manifest 대비 drop guard 를 통과해야 하며, accession/item/section namespace 로 DART 와 분리. |
| EDGAR bulk finance/meta | `.github/workflows/edgarSync.yml` | `edgar/finance`, `edgar/meta`, `edgar/scan` | corpus search 본문 source 가 아니다. EDGAR panel/document sourceRef 보강에만 간접 사용. |
| Public news RSS | `.github/workflows/newsArchiveSync.yml` | `news/public/rss/**`, enriched headline artifact, `search-catalog-newsPublic-*` Actions artifact | `newsPublic` source manifest 생성. source manifest `producerRun` 으로 workflow/job/run lineage 를 보존. source-owner publish 는 직전 HF full manifest 대비 drop guard 를 통과해야 하며, public headline/body lane 만 search index 에 포함. private news 와 혼합 금지. |
| GDELT news | `.github/workflows/gdeltSync.yml` | `newsGdelt` 계열 artifact | source adapter, license, sourceRef 정책 확정 전까지 제품 corpus 에 자동 혼합하지 않는다. 후보 source 로만 둔다. |
| Search daily delta | `.github/workflows/searchIndexDelta.yml`, `.github/scripts/search/pullSearchCurrentIndex.py`, `.github/scripts/search/prepareSearchDeltaInputs.py`, `.github/scripts/search/buildSearchDelta.py`, `.github/scripts/search/runSearchPipelineDrill.py`, `.github/scripts/search/verifySearchHfRoundTrip.py`, `.github/scripts/search/evaluateSearchResultContract.py`, `.github/scripts/search/evaluateSearchCanary.py`, `.github/scripts/search/runSearchQualityDrill.py`, `.github/scripts/search/checkSearchRemoteEvidence.py`, `.github/scripts/search/evaluateSearchGold.py`, `.github/scripts/search/evaluateSearchProductizationStatus.py`, `.github/scripts/search/buildSearchProofBundle.py`, `.github/scripts/search/buildSearchReplacementEvidence.py`, `.github/scripts/search/evaluateSearchCutover.py` | manifest-aware current full pull, `previous_manifest.json`, catalog default delta, explicit `legacy` operator mode, `catalog_snapshot.parquet`, `source_manifest_set.json`, optional `entityGraphCatalog.parquet`, local pipeline drill report, `searchHfRoundTrip.delta.full.json`, `searchHfRoundTrip.delta.lite.json`, `searchResultContract.delta.json`, `searchCanary.delta.json`, `searchQualityDrill.delta.json`, `searchRemoteEvidence.delta.json`, optional release `searchQuality.delta.json`/`searchMissLedger.delta.jsonl`, `searchProductizationStatus.delta.json`, `searchReplacementEvidence.delta.json`, `searchCutover.delta.json`, `searchProofBundle.delta/**` | scheduled/default path 는 all-source catalog diff 로 `delta.*` 를 생성한다. source catalogs 가 없으면 ops gate 에서 막고, legacy allFilings fallback 은 운영자가 명시 dispatch 한 예외 경로로만 남긴다. previous `fileSources` 보존, source manifest set freeze, optional graph sidecar requiredFiles/fileSources/evidence summary, remote target existence, set 내부 source별 `producerRun` 검증이 필수다. 기본 `productization_gate=ops` 는 ops-ready hard fail, release 후보는 real gold와 S4 default replacement hard fail 이다. proof bundle/replacement/cutover report 는 운영 인계 단위다. quality drill 은 release 증거가 아니다. |
| Search monthly main | `.github/workflows/searchIndexMain.yml`, `.github/scripts/search/buildSearchMain.py`, `.github/scripts/search/runSearchPipelineDrill.py`, `.github/scripts/search/verifySearchHfRoundTrip.py`, `.github/scripts/search/evaluateSearchResultContract.py`, `.github/scripts/search/evaluateSearchCanary.py`, `.github/scripts/search/runSearchQualityDrill.py`, `.github/scripts/search/checkSearchRemoteEvidence.py`, `.github/scripts/search/evaluateSearchGold.py`, `.github/scripts/search/evaluateSearchProductizationStatus.py`, `.github/scripts/search/buildSearchProofBundle.py`, `.github/scripts/search/buildSearchReplacementEvidence.py`, `.github/scripts/search/evaluateSearchCutover.py` | source catalog snapshot 우선 compaction + raw rebuild fallback + canonical source catalog bootstrap + post-bootstrap catalog input freeze + `source_manifest_set.json` + optional `entityGraphCatalog.parquet` + local selfcheck + staging upload/current manifest pointer helper + local/HF round-trip drill report, `searchHfRoundTrip.main.full.json`, `searchHfRoundTrip.main.lite.json`, `searchResultContract.main.json`, `searchCanary.main.json`, `searchQualityDrill.main.json`, `searchRemoteEvidence.main.json`, optional release `searchQuality.main.json`/`searchMissLedger.main.jsonl`, `searchProductizationStatus.main.json`, `searchReplacementEvidence.main.json`, `searchCutover.main.json`, `searchProofBundle.main/**` | source manifest snapshot lineage, full/lite manifest, hash, canary, fileSources target 존재, source manifest set 내부 `producerRun`, optional graph sidecar requiredFiles/fileSources, full/lite round-trip 통과 후 publish. source catalog 가 없으면 full HF raw pull 에서 canonical source catalog 4종을 `searchIndexMain.full-pull` producer 로 만들고, 같은 run 에서 `prepareSearchDeltaInputs.py` 를 재실행해 catalog-mode main 을 빌드한다. 기본 `productization_gate=ops` 는 ops-ready hard fail, release 후보는 real gold와 S4 default replacement hard fail 이다. proof bundle/replacement/cutover report 는 운영 인계 단위다. quality drill 은 release 증거가 아니다. |
| Bootstrap planning | `.github/scripts/search/planSearchBootstrap.py` | `searchBootstrapPlan.json`, source-owner `workflow_dispatch` argv, Search Main catalog argv, remote evidence/proof bundle verification argv | remote evidence 가 비어 있거나 source/content manifest 가 부족할 때 운영자가 수동 추측으로 순서를 만들지 않는다. productization status 의 `sourceCatalogNotFull:*`, `sourceCatalogMissingProducerRun:*`, `remoteContentManifestSetMissingProducerRun:*`, `remoteContentMissingFileSources:*` 같은 의미적 blocker 도 source-owner/Search Main action 으로 변환한다. plan CLI 는 비파괴로 실행계획만 생성하고, 실제 실행은 checkout 이 Actions 에 배포된 뒤 운영자가 명시적으로 한다. |
| Proof bundle next actions | `.github/scripts/search/buildSearchProofBundle.py`, `.github/scripts/search/planSearchBootstrap.py` | `searchProofBundle.json`, `searchProductizationStatus.json`, `searchBootstrapPlan.json`, `nextActions.bootstrapPlan` | `opsReady=false` proof 도 다음 실행계획을 포함한다. remote source/content blocker 가 있으면 bundle 안의 bootstrap plan 을 source-owner/Search Main/검증 실행 순서로 사용한다. |
| Local lazy pull | `src/dartlab/providers/dart/search/localUpdate.py`, `fieldIndexRebuild.py`, `fieldIndex.py` | manifest 우선 staged activation, previous active rollback, legacy direct pull fallback | staged download, manifest compare, manifest/hash/load/canary/sourceCanary/schema compatibility smoke, optional `entityGraphCatalog.parquet` download, active pointer atomic swap, rollback target selfcheck. |
| Quality gate | `tests/_attempts/searchProductCore/**`, `src/dartlab/providers/dart/search/artifactCanary.py`, `src/dartlab/providers/dart/search/canaryPack.py`, `src/dartlab/providers/dart/search/facetPlanner.py`, `src/dartlab/providers/dart/search/goldLog.py`, `src/dartlab/providers/dart/search/qualityGate.py`, `src/dartlab/providers/dart/search/resultContract.py`, `.github/scripts/search/evaluateSearchCanary.py`, `.github/scripts/search/prepareSearchGold.py`, `.github/scripts/search/evaluateSearchGold.py`, `.github/scripts/search/evaluateSearchResultContract.py`, `.github/scripts/search/evaluateSearchProductizationStatus.py`, `.github/scripts/search/runSearchQualityDrill.py` | replacement/random pressure report, artifact source/no-answer canary pack/report, query company facet regression, opt-in raw query-log candidate, canonical query-log gold JSONL, quality report, miss ledger, result contract report | quick/full/replacement/hfPipeline/localUpdater profiles. artifact positive canary 는 answerable result 를 요구한다. quality drill 은 `drillSynthetic`/`drillReviewed` 로 표식되고 release evidence 가 아니다. 본문 의미 질문은 title lane mapper 가 아니라 `searchUnified` body semantic rerank 로 처리하고, 전체 후보군 score 가 confidence floor 아래면 `answerable=false(lowConfidence)` 로 no-answer false accept 를 막는다. productization status 는 quality report 의 origin/review counts 와 realReviewedRows 를 다시 검사하므로 spoofed releaseEligible 로 졸업할 수 없다. reviewer-labeled real query-log gold 와 result contract report 전에는 release graduation 금지. |

### 2.1 DART scan prebuild 실행 구조

`Data Prebuild (DART)` 는 검색 source catalog 와 별개로 DART scan parquet 를 유지하지만, 같은 운영 원칙을 따른다. 전량 다운로드를 기본으로 되살리지 않고, manifest/ledger/planner 가 먼저 변경량을 결정한 뒤 builder/publish 가 그 계획만 실행한다.

| 책임 | 파일 | 계약 |
|---|---|---|
| manifest | `.github/scripts/prebuild/planning/prebuildManifest.py` | scan 산출물 known path 와 로컬 category count 를 결정한다. scan seed 는 HF tree listing 없이 fixed artifact path 를 직접 resolve 한다. |
| planner | `.github/scripts/prebuild/planning/prebuildPlan.py` | `BaseSeedPlan`, `PanelDeltaPlan` 순수 로직. Actions cache 가 있는 finance/report 는 HF listing 을 열지 않고, panel bootstrap 은 전량 다운로드 없이 ledger 만 기록한다. cap 에 걸린 panel 변경분은 next ledger 에 반영하지 않아 다음 cycle 에 다시 drain 된다. |
| orchestrator | `.github/scripts/prebuild/prebuildData.py` | offline-only CI entry. HF download/listing, scan build, docsIndex, prune, quality check, HF upload 만 실행한다. full panel seed 는 `PREBUILD_FULL=1` 주간/수동 safety path 전용이다. |
| guard | `tests/pipeline/test_prebuild_plan.py`, `tests/pipeline/test_pipeline_hf_metadata.py` | cache-first seed, HF 429 no-change degrade, bootstrap no-download, capped delta ledger 보존, workflow heartbeat/memory env 를 회귀 차단한다. |

강행 invariant:

1. daily incremental 은 finance/report cache + scan known artifact + panel listing 1회만 연다.
2. daily incremental 은 전 종목 panel seed 를 하지 않는다.
3. HF panel listing 429 는 기존 ledger 가 있을 때 no-change 로 degrade 한다.
4. 부분 scan 산출물이 HF current 로 publish 되지 않도록 finance coverage 를 build 후 검증한다.
5. full rebuild 는 빌더 변경/backfill drift 교정 safety path 이며 daily freshness 수단이 아니다.

---

## 3. 목표 파이프라인 순서

### 3.1 Daily Delta

```text
source workflows complete
-> source manifests uploaded
-> pull current full manifest pointer and required main files
-> preserve previous_manifest fileSources
-> search catalog loads previous catalog manifest
-> stage allFilings + dartPanel + edgarPanel + newsPublic
-> docKey/textHash/metadataHash/deleted diff
-> build delta CSR/meta/stems/evidence sidecar
-> selfcheck required files + hashes + source counts + canary
-> upload to HF staging/{runId}
-> verify remote requiredFiles/fileSources targets on staged candidate
-> verify full/lite HF activate and rollback
-> promote current manifest pointer
-> build proof bundle and productization status
-> local clients keep old active until they verify the new manifest
```

Daily delta 의 성공은 "새 문서가 있었다"가 아니라 "새 source manifest 를 읽었고, no-op 이든 changed-set 이든 정직하게 판정했다"다.

### 3.2 Monthly Main Compaction

```text
freeze source manifest snapshot
-> build full main
-> build lite main
-> absorb valid delta
-> write index manifest with sourceDataAsOf
-> run replacement quality gate
-> upload staging
-> verify full/lite HF activate and rollback
-> promote current manifest pointer
-> build proof bundle and productization status
-> keep previous main for rollback window
```

월간 main 은 최신성 수단이 아니다. delta 누적, tombstone, backfill, artifact size, latency 를 정리하는 compaction 이다.

현재 구현은 source catalog snapshot 을 우선 사용한다. `searchIndexMain.yml` 은 HF `dart/searchCatalog/**` 를 먼저 pull 하고 `prepareSearchDeltaInputs.py` 로 current catalog 를 준비한다. 준비되면 `buildSearchMain.py` 가 `rebuildMainFromCatalog(...)` 로 full main 을 compaction 하고, catalog 가 없으면 raw HF folders pull + `rebuildContent(...)` 로 fallback 한다. 이 raw fallback run 은 같은 full pull 에서 canonical source catalog 4종을 `searchIndexMain.full-pull` producer 로 publish 한 뒤 `prepareSearchDeltaInputs.py` 를 다시 실행해 그 source set 을 main build 입력으로 freeze 한다. publish 순서는 staging upload/current manifest pointer helper 를 사용한다. 현재 checkout 은 catalog default/replacement evidence 까지 닫혔고, 실제 catalog mode Actions run artifact 는 다음 run 에서 재확인한다.

### 3.3 Backfill

Backfill 은 full rebuild 로 바로 가지 않는다.

1. source owner 가 과거 slab 을 수집하고 source manifest 의 `files/minDate/maxDate/changedRows` 를 갱신한다.
2. search catalog 는 과거 구간만 diff 한다.
3. delta 로 먼저 publish 한다.
4. `delta_docs/main_docs`, tombstone, load budget 이 임계치를 넘으면 월간 main 또는 수동 compaction 으로 흡수한다.

### 3.4 Schema 또는 Tokenizer 변경

다음 변경은 full rebuild 후보로 본다.

- `sourceRefVersion`
- `schemaVersion`
- `tokenizerVersion`
- `normalizerVersion`
- source adapter 가 docKey 의미를 바꾸는 경우
- chunk/evidence cache key 의미 변경

처리 순서:

1. PRD와 manifest schema 를 먼저 갱신한다.
2. compatible library range 를 정한다.
3. full/lite main 을 새 schema 로 빌드한다.
4. old local cache rejection 또는 graceful fallback 을 테스트한다.
5. release note 와 운영 런북을 갱신한다.

### 3.5 New Source Onboarding

새 source 는 다음 7개 계약 없이는 corpus 에 넣지 않는다.

1. source manifest.
2. stable `docKey`.
3. stable `sourceRef`.
4. public/private exposure policy.
5. source-specific freshness field.
6. source canary query.
7. miss ledger failure type.

이 기준을 통과하지 못하면 `_attempts` 또는 private/local 실험으로만 둔다.

---

## 4. Source Manifest 책임

각 source workflow 가 남길 최소 manifest:

| source | manifest owner | `dataAsOf` 기준 | required count |
|---|---|---|---|
| `allFilings` | `originalSync.yml` allfilings/backfill | row `rcept_dt` 또는 source date max | parquet rows, files, changedRows, deletedRows |
| `dartPanel` | `originalSync.yml` dart-zip/reconcile | panel filing date 또는 rcept date max | ticker files, rcept count, section rows |
| `edgarPanel` | `originalSync.yml` edgar, `edgarSync.yml` panel | accession filing date max | ticker files, accession count, section rows |
| `newsPublic` | `newsArchiveSync.yml` | captured/article date max | rss rows, enriched rows, duplicate count |
| `newsGdelt` | `gdeltSync.yml` | GDELT event date max | GKG rows, source URL count |

Search 는 source manifest 가 없거나 비정상 급감하면 최신 claim 을 하지 않는다. 해당 source 를 delta 에 포함하지 않거나 publish 를 막는다.

### 4.1 Snapshot Completeness

source catalog 는 "이번에 바뀐 row" 모음이 아니라 source별 canonical full snapshot 이다.

현재 `buildSearchCatalog.py`/`sourceCatalog.py` 는 입력 glob 에 잡힌 parquet 파일의 합계를 manifest 로 쓴다. full snapshot 기본값에서는 빈 파일/빈 row/빈 normalized catalog 를 실패시키고 `completenessCheck` 를 manifest 에 남긴다. `--upload` 는 source manifest 와 catalog snapshot 을 단일 `create_commit` batch 로 올린다. GitHub Actions 안에서 실행되면 source manifest 는 `producerRun.workflow/job/runId/sha/artifactName` 도 보존한다. source-owner incremental workflow 는 기본적으로 `--compare-remote-manifest --require-previous-manifest` 로 HF 직전 full manifest 를 읽고 files/rows/catalogRows 급락을 차단한다. 첫 canonical full source catalog 는 `searchIndexMain.yml` 의 raw full HF pull bootstrap 또는 명시적 source-owner `search_catalog_bootstrap=true` dispatch 가 만든다. bootstrap dispatch 는 previous manifest 요구만 해제하고 source별 높은 min-files/min-rows/min-catalog-rows 하한을 유지한다.

2026-06-17 부터 source-owner incremental workflow 는 `--merge-previous-catalog` 를 함께 사용한다. runner 가 이번 run 에서 바뀐 parquet 일부만 갖고 있어도 HF 직전 `{source}.source_manifest.json` 과 `{source}.catalog_snapshot.parquet` 를 내려받아 변경분을 병합한 뒤 full snapshot 으로 검증한다. 병합 규칙은 source별 소유 경계에 맞춘다: `dartPanel` 은 변경 파일 stem stockCode 파티션 교체, `edgarPanel` 은 ticker 파티션 교체, `newsPublic` 은 변경 date 파티션 교체, `allFilings` 는 docKey upsert 이다. 따라서 부분 runner tree 가 거짓 full 로 승격되는 길은 여전히 막고, 정상 증분은 이전 full catalog 를 보존한 채 흡수한다.

운영 기준:

1. source owner workflow 는 catalog build 전에 source별 pull completeness 를 검증한다.
2. source manifest 는 `snapshotScope=full|partial` 과 `completenessCheck` 를 가진다.
3. `snapshotScope=partial` 또는 expected source 누락은 catalog mode env 생성을 막는다.
4. `pipeline.py` 는 expected source 누락, partial snapshot, expected source 0 row, source row count 급감을 invalid 로 처리한다.
5. `buildSearchCatalog.py` 는 기본 `--min-files 1 --min-rows 1 --min-catalog-rows 1` 로 source owner 단계에서 빈 full snapshot 을 실패시킨다.
6. source-owner workflow 는 이전 full manifest 없이는 canonical `snapshotScope=full` publish 를 하지 않는다.
7. source-owner incremental run 은 이전 HF full manifest/catalog 를 내려받아 병합하지 못하면 실패해야 한다.
8. 아직 필요한 운영 증거는 실제 GitHub Actions run 에서 이 차단과 병합이 의도대로 동작하는지 확인하는 것이다.

---

## 5. Search Artifact 책임

Search workflow 가 책임지는 artifact:

- `catalog_snapshot.parquet`
- `catalog_manifest.json`
- `main.npz`
- `main_stems.json`
- `main_meta.parquet`
- `main_info.json`
- `delta.npz`
- `delta_stems.json`
- `delta_meta.parquet`
- `delta_info.json`
- `manifest.json`
- `entityGraphCatalog.parquet` (optional graph sidecar)
- quality report
- canary report
- result contract report

Source owner workflow 가 책임지는 search catalog artifact:

- `{source}.source_manifest.json`
- `{source}.catalog_snapshot.parquet`

HF 위치:

- `dart/searchCatalog/allFilings/`
- `dart/searchCatalog/dartPanel/`
- `dart/searchCatalog/edgarPanel/`
- `dart/searchCatalog/newsPublic/`

search delta 는 이 source catalog 들을 직접 원천 데이터로 보지 않고, previous/current catalog 비교의 입력으로만 쓴다.

목표 publish 순서:

1. build output 을 local work dir 에 생성.
2. `manifest.json` 에 requiredFiles/fileHashes/sourceDataAsOf 기록.
3. load smoke 와 canary 실행.
4. HF `staging/{runId}` 에 업로드.
5. staging artifact 를 다시 읽어 hash 확인.
6. current `manifest.json` pointer 를 마지막에 publish 하고, `fileSources` 로 staging files 를 가리킨다.

중간 실패는 publish 실패다. partial artifact 를 current 로 올리지 않는다.

현재 구현은 `publishIndex.py` helper 로 local manifest/hash/canary selfcheck 후 staging upload 와 current manifest pointer publish 를 수행한다. manifest-pointer publish 는 파일별 `upload_file` 반복 대신 staging files 와 current manifest pointer 를 단일 `create_commit` batch 로 올린다. source catalog publish 도 source manifest 와 catalog snapshot 을 단일 `create_commit` batch 로 올린다. graph sidecar 는 `entityGraphCatalog.py` 가 explicit copy 또는 opt-in offline build 로 준비한다. `promoteCurrent=False` stage-only publish 는 current pointer 를 바꾸지 않고 staging pointer manifest 만 올리며, `verifySearchHfRoundTrip.py --manifest-repo-path` 로 그 candidate 를 직접 activate/rollback 검증할 수 있다. Search Main/Delta workflow 는 stage-only candidate 검증, result contract/canary/status pass, current pointer promote, remote evidence audit 순서로 배선됐다. 운영 artifact publish 가능 판정 전에는 실제 HF run 에서 이 순서와 rollback drill 을 실증해야 한다.

---

## 6. Local Runtime 책임

로컬은 백그라운드 daemon 을 기본으로 갖지 않는다.

호출 트리거:

- `dartlab.search(...)`
- 명시 `prefetch/update`
- local UI 가 검색 화면 진입 시 호출하는 adapter

동작:

1. local active manifest 읽기.
2. HF current manifest 읽기.
3. schema/library/tier compatibility 확인.
4. 필요한 파일만 staging 에 다운로드.
5. hash, required files, schema compatibility, `loadSegment`, canary/sourceCanary smoke 확인.
6. active pointer atomic swap.
7. old active 는 rollback window 동안 유지하고 active pointer 의 `previousActiveDir` 로 보존한다.

`DARTLAB_NO_HF_DOWNLOAD=1` 이면 HF 확인도 download 도 하지 않는다. cache 가 없으면 빈 결과와 명확한 안내를 반환한다.

---

## 7. 유지보수 캘린더

### Daily

- source workflow success/no-op 확인.
- source manifest `dataAsOf` 멈춤 확인.
- search delta selfcheck 결과 확인.
- current manifest source counts 급감 확인.
- local update smoke 가 active 보존을 지키는지 확인.

### Weekly

- query-log 후보를 filing/news/noAnswer/EDGAR 로 라벨링.
- 필요하면 `DARTLAB_SEARCH_QUERY_LOG=1` 로 실제 `dartlab.search(...)` 호출 후보를 `data/search/queryLogRaw.jsonl` 에 쌓는다.
- `prepareSearchGold.py` 로 raw log + reviewer labels 를 canonical `queryLogGold.real.jsonl` 로 정규화.
- miss ledger 의 반복 유형 분류.
- `evaluateSearchGold.py` 로 real/proxy/review status 와 miss ledger 를 생성.
- `evaluateSearchCanary.py` 로 source/no-answer canary pack 을 실행.
- `evaluateSearchResultContract.py` 로 sample/live result row 계약을 감사.
- canary pack 에 최신 사건 3~5개 추가.
- sourceRef/dataAsOf 없는 result 가 있는지 샘플링.
- public/local/library surface wording 이 최신 claim 을 과장하지 않는지 확인.

### Monthly

- main compaction 실행.
- full/lite tier 크기, load time, p95 latency 확인.
- delta/tombstone 비율 확인.
- real query-log gold gate 재실행.
- PRD, runbook, Skill OS `engines.search` 갱신 필요 여부 확인.

### Release

- replacement gate.
- hfPipeline dry run.
- localUpdater smoke.
- local end-to-end pipeline drill.
- preflight/Guard quick.
- real query-log gold 100 rows 이상.
- source/no-answer canary pack 통과.
- result contract audit 통과.
- rollback drill 1회.
- README/CHANGELOG/운영문서 갱신.

---

## 8. 품질 개선 루프

품질 개선은 mapper 관리가 아니라 evidence contract 개선이다.

루프:

1. query-log 와 canary failure 를 miss ledger 에 기록.
2. failure type 을 분류한다.
3. 반복되는 유형만 policy candidate 로 승격한다.
4. source adapter, facet planner, sourceRef policy, answerability, evidence pack 중 한 계층에서 일반 정책으로 해결한다.
5. replacement gate 와 real gold 에 회귀가 없을 때만 유지한다.

금지:

- 회사/날짜/문구별 특수 mapper 누적.
- generated gold 를 release graduation 증거로 사용.
- public/private news 를 sourceRef 없이 혼합.
- 실패 artifact 를 수동 업로드로 덮어쓰기.

---

## 9. 장애와 보존 정책

| 장애 | search publish | local runtime | 운영자 행동 |
|---|---|---|---|
| source manifest 누락 | publish 금지 또는 source 제외 | 기존 active 유지 | source workflow 복구 |
| source count 급감 | publish 금지 | 기존 active 유지 | count 급감 원인 조사 |
| HF 429/partial pull | staging 보존, promote 금지 | old active 유지 | retry 또는 다음 cron |
| delta 0 docs | no-op 근거 있으면 manifest 기록 | 정상 사용 | dataAsOf/hash 변화 확인 |
| canary fail | promote 금지 | old active 유지 | miss ledger 기록 |
| schema incompatible | 새 current 거부 | compatible cache 사용 | library version 안내 |
| real gold regression | release block | current artifact 는 유지 가능 | 일반 정책으로 수정 |

보존:

- current 이전 main/delta 1세대는 rollback window 동안 유지.
- failed staging 은 원인 분석 후 삭제한다.
- query-log gold 는 sourceRef, dataAsOf, reviewStatus 를 포함해 장기 보존한다.
- miss ledger 는 특정 query mapper 목록이 아니라 `policyCandidate` backlog 로 장기 보존한다.

---

## 10. 완료 기준

이 파이프라인 문서가 완료됐다고 볼 조건:

- 실제 workflow 파일명과 source 책임이 문서에 반영됨.
- allFilings, DART panel, EDGAR panel, public news 가 모두 delta 대상에 포함됨.
- GDELT/private news 는 자동 혼합 금지와 onboarding 조건이 명시됨.
- HF staging upload/current manifest pointer publish, local staged download/active swap, rollback 이 명시됨.
- daily/weekly/monthly/release 유지보수 루프가 명시됨.
- 품질 개선이 miss ledger 와 일반 정책 루프로 정의됨.

현재 문서는 설계 완료 기준을 만족한다. 구현 완료 기준은 `10-production-pipeline-prd.md` Phase 1~4 와 `11-operator-runbook.md` 배포 체크리스트 통과다.

현재 구현 상태:

- source owner workflow catalog build step: 정적 smoke 와 focused tests 통과.
- `searchIndexDelta.yml` HF searchCatalog pull/env prep: 정적 smoke 와 focused tests 통과.
- catalog-mode `buildSearchDelta.py`: subprocess dry-run/build smoke 통과.
- `runSearchPipelineDrill.py`: synthetic raw source parquet → source catalog → source manifest set freeze → artifact → staging upload/current manifest pointer publish → activation → rollback subprocess smoke 통과.
- `verifySearchHfRoundTrip.py`: HF current manifest → local staged activation → rollback smoke CLI 구현, workflow publish 후 evidence artifact 업로드 배선 완료. 실제 Actions artifact 증거 필요.
- `checkSearchRemoteEvidence.py`: HF source catalog inventory, source manifest `producerRun`, contentIndex current manifest, `fileSources` 대상 존재 여부, `source_manifest_set.json` 내부 source별 `producerRun` 을 JSON 으로 감사하고 workflow evidence artifact 에 포함. 실제 원격 상태 report 필요.
- `planSearchBootstrap.py`: 현재 remote evidence 또는 live audit 를 source-owner bootstrap/Search Main/검증 실행계획으로 변환한다. 이 단계는 GitHub/HF 를 변경하지 않고 `searchBootstrapPlan.json` 만 남긴다.
- `buildSearchProofBundle.py`: remote source/content blocker 가 있으면 `searchBootstrapPlan.json` 을 bundle 안에 생성하고 `nextActions.bootstrapPlan` 으로 missing source/tier/action id 를 연결한다.
- `buildSearchReplacementEvidence.py`: proof bundle, remote evidence, full/lite round-trip report, Search Main/Delta workflow YAML 을 읽어 S4 default replacement 증거를 생성한다.
- `evaluateSearchCutover.py`: proof bundle 과 replacement evidence 를 S1/S2/S3/S4 cutover state 로 판정하고 workflow evidence artifact 에 `searchCutover.{delta,main}.json` 으로 남긴다.
- `evaluateSearchCanary.py`: manifest `sourceCanaryPack` 기반 canary report 를 생성하고 workflow evidence artifact 에 포함.
- `evaluateSearchProductizationStatus.py`: proof bundle 을 종합해 `designReady/opsReady/releaseReady` 와 blocker list 를 생성하고 workflow evidence artifact 에 포함. source catalog manifest 의 `producerRun` 이 없으면 `sourceCatalogMissingProducerRun:*`, contentIndex set 내부 lineage 가 비면 `remoteContentManifestSetMissingProducerRun:*` 로 S2 를 차단한다.
- `publishIndex.py`: manifest-pointer publish 를 파일별 `upload_file` 반복이 아니라 단일 `create_commit` batch 로 묶는다. 실제 HF 429 감소 여부는 다음 Actions run 에서 확인해야 한다.
- `buildSearchCatalog.py`: source manifest 와 catalog snapshot 도 단일 `create_commit` batch 로 묶는다. 실제 source owner run 에서 `dart/searchCatalog/{source}/` 생성 여부를 확인해야 한다.
- local staged activation/manifest compare/schema compatibility/sourceCanaryPack/rollback helper: provider tests 통과.
- contentIndex publish: `publishIndex.py` 기반 local selfcheck + 단일 `create_commit` batch staging upload/current manifest pointer publish 1차 구현. 실제 HF round-trip 과 rollback drill 증거 필요.
- searchIndexMain: source catalog snapshot 우선 compaction + raw fallback + staging upload/current manifest pointer helper. workflow 기본값은 catalog 이며, 실제 catalog mode Actions run 증거는 다음 run 에서 확인한다.
- source completeness: `snapshotScope`, expected source set, source row count drop check, source catalog `completenessCheck`, 직전 full manifest 대비 drop guard 1차 구현. 실제 Actions run 확인 필요.
- result contract audit: `resultContract.py` 와 `evaluateSearchResultContract.py` 1차 구현, searchIndexDelta/Main evidence artifact 업로드 배선. 실제 full-source HF artifact 결과 report 필요.
- productization status audit: `evaluateSearchProductizationStatus.py` 1차 구현. 2026-06-16 초기 로컬 catalog-mode proof 는 `opsReady=false` 였지만, local HF bootstrap 이후 full_lite proof bundle 은 sourceCatalog/contentIndex/fileSources/full-lite round-trip/canary/resultContract 를 통과했고, direct-review 품질팩 이후 `opsReady=true`, `releaseReady=true` 로 갱신됐다. live HF proof bundle 의 최신 blocker 는 증거 원장을 기준으로 본다.
- query company facet: `facetPlanner.py` 와 `api.py` 가 query 본문 회사명을 `ListingResolver` 로 stockCode facet 에 승격하고 pre-rank mask 로 적용. `삼성전자 대표이사 변경` 계열사 누수 live smoke 와 provider/search regression 통과.

운영 증거 대기:

- `planSearchBootstrap.py` 로 최신 remote blocker 에 대한 실행계획을 남긴 뒤 GitHub Actions source owner 실제 run 에서 `dart/searchCatalog/{source}/` 생성. 첫 생성은 `search_catalog_bootstrap=true` manual dispatch 또는 `searchIndexMain.full-pull` bootstrap 중 하나여야 한다.
- GitHub Actions `searchIndexDelta.yml` 실제 run 에서 catalog mode publish.
- HF contentIndex staging upload/current manifest pointer publish 실제 HF round-trip evidence artifact 확인.
- HF current artifact 를 실제 로컬에서 staged download 후 active swap.
- expected source set 누락 차단과 source full snapshot completeness enforcement 실제 run 증거.
- expected source 0 row full snapshot 차단 실제 run 증거.
- searchIndexMain source manifest snapshot compaction 실제 Actions run 증거.
- result contract report 의 invalidRows 0 실제 run 증거.
- real query-log gold gate 통과. 게이트 구현은 완료됐고 실제 real rows 와 run 증거가 필요하다.

---

## 11. 본진 이관 작업 목록

| 작업 | 현재 위치 | 목표 위치 | 완료 기준 |
|---|---|---|---|
| product result schema | `src/dartlab/providers/dart/search/resultSchema.py` | 동일 | 모든 검색 surface 가 같은 row 계약 통과 |
| source manifest schema | `sourceManifest.py` | source workflows + search validator | source owner 가 실제 manifest 생성 |
| source completeness | `sourceCatalog.py`, `buildSearchCatalog.py`, source workflows, `searchIndexMain.yml`, `prepareSearchDeltaInputs.py`, `pipeline.py` | source workflow + search delta preflight | expected source set, full snapshot 누락, expected source 0 row, empty full snapshot, 이전 full manifest 대비 급락 자동 차단 1차 구현. 첫 canonical source catalog 는 main full pull bootstrap 또는 명시적 source-owner bootstrap 이 담당. 실제 run 확인 필요 |
| catalog diff | `catalog.py`, `pipeline.py` | search delta workflow 기본 경로 | allFilings/panel/EDGAR/news changed set 반영 |
| index manifest | `manifest.py`, `fieldIndexRebuild.py` | main/delta publish 필수 artifact | `indexInfo()` 가 source별 freshness 반환 |
| local active pointer | `localUpdate.py`, `fieldIndex.py` | runtime lazy update 기본 경로 | 실패 artifact activation 거부 |
| source intent | `sourceIntent.py`, `api.py`, `fieldIndex.py`, `unified.py` | 동일 | 뉴스/공시 hard isolation test 통과, source mask 랭킹 전 적용 |
| answerability | `answerability.py`, `facetPlanner.py` | 동일 | source mismatch/missing evidence/facet mismatch/stale source 구분 1차 구현 |
| query company facet | `facetPlanner.py`, `api.py`, `src/dartlab/__init__.py` | 동일 | query 본문 회사명은 `ListingResolver` 기반 stockCode pre-rank mask 로 적용. `topK` public alias 와 계열사 누수 regression 통과 |
| evidence card | `evidencePack.py`, `memoryCard.py`, `resultSchema.py`, `fieldIndex.py`, `fieldIndexRebuild.py` | 동일 | row-level sourceRef/snippet cards + bounded `evidenceText` chunk card 완료. actual full-source 품질 확인 필요 |
| source catalog artifacts | `sourceCatalog.py`, `buildSearchCatalog.py`, source workflows | HF `dart/searchCatalog/{source}`, Actions `search-catalog-*` | source manifest/catalog snapshot 생성 step, batch `create_commit` upload, evidence artifact 업로드, source manifest `producerRun` lineage 배선 완료. 실제 run 확인 필요 |
| delta workflow mode | `.github/scripts/search/buildSearchDelta.py`, `.github/scripts/search/prepareSearchDeltaInputs.py`, `.github/workflows/searchIndexDelta.yml` | scheduled all-source catalog delta | catalog default mode, HF searchCatalog pull, env prep, `source_manifest_set.json` freeze 완료. `legacy` 는 명시 dispatch 예외. 실제 run 확인 필요 |
| main compaction | `.github/workflows/searchIndexMain.yml`, `buildSearchMain.py` | source manifest snapshot compaction | source catalog 우선 compaction, source manifest set required file 포함 완료. 실제 catalog run 증거 필요 |
| query-log raw capture | `api.py`, `goldLog.py` | opt-in `DARTLAB_SEARCH_QUERY_LOG` -> `queryLogRaw.jsonl` candidate rows | 구현 완료. candidate 는 release gold 아님 |
| query-log gold preparation | `goldLog.py`, `prepareSearchGold.py` | raw log + reviewer label -> canonical release gold | 저장 위치/라벨링 절차/정규화 CLI 완료. 실제 reviewed real gold rows 필요 |
| query-log gold gate | `qualityGate.py`, `evaluateSearchGold.py` | release graduation quality gate | real/proxy/review status, metrics, miss ledger 1차 구현. 실제 real gold rows 필요 |
| result contract audit | `resultContract.py`, `evaluateSearchResultContract.py`, searchIndexDelta/Main workflow | product result surface gate | 필수 result fields, fieldCards, card evidence 감사 구현과 evidence artifact 업로드 배선 완료. 실제 full-source HF artifact report 필요 |
| source/no-answer canary gate | `artifactCanary.py`, `canaryPack.py`, `evaluateSearchCanary.py`, `fieldIndexRebuild.py` | publish/local activation safety gate | artifact v3 pack 자동 생성/manifest 주입/evaluator 구현. news lane smoke 와 source coverage 강제 포함. 실제 Actions artifact report 와 운영 curated rows 필요 |
| HF round-trip drill | `verifySearchHfRoundTrip.py`, searchIndexDelta/Main workflow post-publish step | real current manifest download + local activation/rollback smoke | CLI/local fake HF test 완료. 실제 Actions evidence artifact 필요 |
| local pipeline drill | `runSearchPipelineDrill.py`, searchIndexDelta/Main workflow preflight | raw source -> source catalog -> source manifest set -> hfPipeline/localUpdater smoke | subprocess smoke 1차 구현. 실제 HF round-trip 과 Actions run 증거는 별도 필요 |
| productization status audit | `evaluateSearchProductizationStatus.py`, searchIndexDelta/Main workflow | proof bundle readiness 판정 | CLI/fake HF tests 완료. workflow hard gate 배선 완료. 실제 Actions `searchProductizationStatus.{delta,main}.json` report 필요 |

---

## 12. 유지보수 위험 목록

| 위험 | 조기 신호 | 대응 |
|---|---|---|
| source manifest 형식 드리프트 | validator warning, row count 누락 | source owner workflow 차단, schemaVersion bump |
| allFilings 중심 delta 고착 | panel/news 최신 문서가 검색에 늦게 반영 | source catalog 생성과 `searchIndexDelta.yml` catalog mode 실제 run 을 운영 기준으로 고정 |
| prepared catalog env override | scheduled run 이 catalog mode 대신 legacy 로 떨어짐 | manual inputs 는 별도 `GITHUB_ENV` step 으로만 쓰고 build step 에서 빈 env override 금지 |
| 품질 개선 mapper 누적 | query별 예외 증가, tests fixture 비대화 | miss ledger failureType 기반 일반 정책만 허용 |
| full rebuild 남발 | daily runtime 길어짐, HF publish 실패 증가 | delta threshold 와 monthly compaction 으로 분리 |
| public 최신성 과장 | public UI 가 full/latest claim | lite/curated badge 와 local/library 안내로 제한 |
| local cache 파손 | empty active, partial files | staged download + active pointer swap + `rollbackActiveIndex()` drill |
| result contract drift | sourceRef/dataAsOf/snippet/fieldCards 누락 | `evaluateSearchResultContract.py --fail-on-error`, resultSchema/resultContract tests |
| company facet drift | 회사명이 들어간 질의가 계열사/유사명으로 샘 | `facetPlanner`/`api` regression, query-log gold suffix/near-name trap |
| remote evidence drift | source catalog 또는 current manifest 가 HF 에 없음 | `checkSearchRemoteEvidence.py --fail-on-missing`, Actions `searchRemoteEvidence.*.json` |

---

## 13. 문서-코드 동기화 규칙

검색 파이프라인 구현 변경은 다음 원칙으로 mainPlan 과 같이 움직인다.

1. workflow 책임이 바뀌면 이 문서의 2장과 3장을 먼저 바꾼다.
2. manifest 필드가 바뀌면 `10-production-pipeline-prd.md` 와 `11-operator-runbook.md` 를 같이 바꾼다.
3. 품질 gate 기준이 바뀌면 `02-quality-gates.md` 와 `06-progress-ledger.md` 를 같이 바꾼다.
4. public/local/library surface 의미가 바뀌면 `08-completion-design.md` 를 같이 바꾼다.
5. release graduation 을 선언하려면 real query-log gold 근거를 `06-progress-ledger.md` 에 남긴다.

---

## 14. 운영 증거 원장

이 절은 실제 run 이 생기면 최신 항목을 append 한다. 설계 문서와 달리 추정값을 쓰지 않는다.

### Source Catalog Runs

| date | workflow/run | source | snapshotScope | rows/files | HF path | result |
|---|---|---|---|---:|---|---|
| pending | pending | allFilings/dartPanel/edgarPanel/newsPublic | pending | pending | `dart/searchCatalog/{source}/` + source manifest `producerRun` | source catalog batch `create_commit`, producerRun lineage, source-owner previous-manifest drop guard, main full-pull canonical bootstrap, 명시적 `search_catalog_bootstrap=true` source-owner bootstrap 구현 완료. 실제 Actions run 대기 |
| 2026-06-15 | live HF sourceCatalog check | allFilings/dartPanel/edgarPanel/newsPublic | n/a | n/a | `dart/searchCatalog/{source}/{source}.source_manifest.json`, `{source}.catalog_snapshot.parquet` | 404 EntryNotFound. source owner workflow publish 전 원격 상태 |
| 2026-06-16 | local full-source catalog build | allFilings | full | 191,827 docs / 430 files / rawRows 421,726 | `data/dart/searchCatalog/allFilings/` | pass. `fetch_status=ok`, non-empty, unique docKey, bounded plain text, 121.8MB |
| 2026-06-16 | local full-source catalog build | dartPanel | full | 104,759 docs / 2,929 files / rawRows 85,210,459 | `data/dart/searchCatalog/dartPanel/` | pass. filing rollup, 78.5MB |
| 2026-06-16 | local full-source catalog build | edgarPanel | full | 58,901 docs / 2,557 files / rawRows 16,831,346 | `data/dart/searchCatalog/edgarPanel/` | pass. accession rollup, 47.1MB |
| 2026-06-16 | local full-source catalog build | newsPublic | full | 5,649 docs / 1 file | `data/dart/searchCatalog/newsPublic/` | pass. 1.7MB |
| 2026-06-16 | local HF raw bootstrap after EDGAR mirror reconciliation | allFilings | full | 192,095 docs / 430 files | `dart/searchCatalog/allFilings/` | uploaded to HF. manifest/catalog present, `producerRun.workflow=local-search-bootstrap`, remote evidence valid |
| 2026-06-16 | local HF raw bootstrap after EDGAR mirror reconciliation | dartPanel | full | 104,761 docs / 2,930 files | `dart/searchCatalog/dartPanel/` | uploaded to HF. manifest/catalog present, `producerRun.workflow=local-search-bootstrap`, remote evidence valid |
| 2026-06-16 | local HF raw bootstrap after EDGAR mirror reconciliation | edgarPanel | full | 84,293 docs / 3,398 files | `dart/searchCatalog/edgarPanel/` | EDGAR remote/local panel mirror reconciled to 3,398 files before build. manifest/catalog present, remote evidence valid |
| 2026-06-16 | local HF raw bootstrap after EDGAR mirror reconciliation | newsPublic | full | 81,798 docs / 18 files | `dart/searchCatalog/newsPublic/` | uploaded to HF. manifest/catalog present, `producerRun.workflow=local-search-bootstrap`, remote evidence valid |

### Search Delta Runs

| date | workflow/run | mode | previous catalog | current catalog | changed/new/deleted | manifest id | result |
|---|---|---|---|---|---:|---|---|
| pending | pending | catalog | pending | pending | pending | pending | 실제 scheduled/dispatch run 대기 |
| 2026-06-16 | local prepareSearchDeltaInputs | catalog | none | 361,136-doc current catalog | 361,136 new / 0 changed / 0 deleted | local only | pass. current catalog 174.5MB, unique docKey 100%, dry-run 약 2.1초 |
| 2026-06-18 KST | Search Index Delta scheduled run 27719942258 | catalog | HF current full/lite | lite current 292,568 docs | current publish | `dart/contentIndex/lite/manifest.json` staging `lite-27719942258` | completed/success. full source set allFilings/dartPanel/edgarPanel/newsPublic preserved, source manifest set producerRun complete, remote evidence valid. |
| 2026-06-18 KST | Search Index Delta release dispatch 27734759585 | catalog | HF current full/lite | HF source catalog set | workflow-computed delta/no-change | `searchProofBundle.delta/**`, `searchCutover.delta.json` | completed/success on commit `7bc64b0c6`. Candidate round-trip, current lite no-change round-trip, result contract, canary, real query-log quality, remote evidence, release productization status, proof bundle, replacement evidence, cutover state all passed. |

### GitHub Actions Snapshot

| date checked | workflow | latest relevant run | status | result |
|---|---|---|---|---|
| 2026-06-16 KST | Search Index Delta | 27510846976, scheduled 2026-06-14T20:19Z | completed/failure | HF `preupload/main` 429 after allFilings delta build. No current manifest proof. |
| 2026-06-16 KST | Search Index Main | 27260308153, dispatch 2026-06-10T07:25Z | completed/failure | HF 429 / silent partial pull; later 27261869568 cancelled. No catalog-mode main proof. |
| 2026-06-16 KST | Original SSOT Sync | 27529940941, scheduled 2026-06-15T07:09Z | completed/cancelled | source owner catalog proof not available from latest run. |
| 2026-06-16 KST | News Archive Sync | 27551386208, scheduled 2026-06-15T13:57Z | completed/success | source workflow green, but searchCatalog/newsPublic remote artifact still missing in HF evidence audit. |
| 2026-06-16 KST | EDGAR Data Sync (Bulk) | 27540813725, scheduled 2026-06-15T10:42Z | completed/success | source workflow green, but searchCatalog/edgarPanel remote artifact still missing in HF evidence audit. |
| 2026-06-18 KST | Data Prebuild (DART) | 27701989863, push `ba805190` | completed/success | incremental panel listing 2,931 remote / 2,930 ledger, changed panel 584 downloaded, docsIndex merged to 15,258,204 rows, finance prebuild coverage 100%, 23 scan parquet + ledger uploaded to HF. |
| 2026-06-18 KST | Data Prebuild (DART) | 27717621114, workflow_run `ba805190` | completed/success | post-fix automated run green on same head SHA. Confirms Data Prebuild automation path, not only manual dispatch. |
| 2026-06-18 KST | Search Index Delta | 27719942258, scheduled `ba805190` | completed/success | scheduled catalog delta green. Current lite manifest built at 2026-06-17T21:13:20 with 292,568 docs; full manifest remains valid with delta. |
| 2026-06-18 KST | CI Fast | 27701980261, push `ba805190` | completed/success | typecheck, lint, quality, fast tests, architecture-l0-l15, product smoke quick, wheel smoke passed. |
| 2026-06-18 KST | CI Full | 27701980277, push `ba805190` | completed/success | cross-os smoke, fixture integration, product-smoke-wheel, realdata suites, Python 3.12/3.13 full tests passed. |
| 2026-06-18 KST | CI Fast | 27728624428, push `929942475` | completed/success | Data Prebuild planner split head SHA. format, lint, typecheck, quality, fast tests, architecture, product smoke quick, wheel smoke passed. |
| 2026-06-18 KST | CI Full | 27728624435, push `929942475` | completed/success | Data Prebuild planner split head SHA. cross-os smoke, fixture integration, product-smoke-wheel, Python 3.12/3.13 full gates passed. |
| 2026-06-18 KST | Data Prebuild (DART) | 27729224525, dispatch `929942475` | completed/success | new planning package path proved in Actions. `prebuild-scan` completed; `prebuild-full` skipped by full=false. |
| 2026-06-18 KST | Search Index Delta | 27729224528, dispatch `929942475` | completed/success | release dispatch completed on same head. build-delta job passed with candidate verify/promote/status evidence uploaded by workflow. |
| 2026-06-18 KST | Search Index Delta | 27734759585, dispatch `7bc64b0c6` | completed/success | latest release gate after no-change/canary ranking fix. build-delta passed full candidate round-trip, current lite no-change round-trip, result contract, canary passRate 1.0, real query-log quality, remote evidence, proof bundle, replacement evidence, cutover state. |
| 2026-06-18 KST | Data Prebuild (DART) | 27734759598, dispatch `7bc64b0c6` | completed/success | latest DART scan prebuild dispatch green. `prebuild-scan` completed; `prebuild-full` skipped by full=false. |
| 2026-06-18 KST | CI Fast | 27734740493, push `7bc64b0c6` | completed/success | latest search delta/no-change fix head. format, lint, typecheck, quality, fast tests, architecture, product smoke quick, wheel smoke passed. |
| 2026-06-18 KST | CI Full | 27734740472, push `7bc64b0c6` | completed/success | latest search delta/no-change fix head. cross-os smoke, fixture integration, product-smoke-wheel, realdata suites, Python 3.12/3.13 full gates passed. |
| 2026-06-18 KST | CodeQL | 27734740475, push `7bc64b0c6` | completed/success | latest search delta/no-change fix head security scan green. |

### Publish / Local Activation

| date | artifact | staging path | current manifest path | active manifest | previous manifest | selfcheck | result |
|---|---|---|---|---|---|---|---|
| pending | contentIndex full/delta/lite | pending | `dart/contentIndex/manifest.json` | pending | pending | pending | helper 및 HF round-trip CLI/workflow 배선 완료, manifest-pointer publish 는 단일 `create_commit` batch 로 전환, 실제 Actions evidence artifact 대기 |
| 2026-06-16 | local catalog-mode main | local only | local direct manifest, no `fileSources` | local active full | previous local active overwritten | canary pass, result contract pass | `nDocs=361136`, all expected source counts/freshness present. Not ops-ready because no HF current pointer/round-trip |
| 2026-06-15 | live HF manifest check | n/a | `dart/contentIndex/manifest.json`, `dart/contentIndex/lite/manifest.json` | n/a | n/a | 404 EntryNotFound | manifest-pointer publish 전 원격 상태. 실제 round-trip 은 다음 publish run 대기 |
| 2026-06-16 | initial live HF remote evidence audit | n/a | `dart/contentIndex/manifest.json`, `dart/contentIndex/lite/manifest.json` | n/a | n/a | `checkSearchRemoteEvidence.py` valid=false | fileCount=39225, blockers=`contentIndexManifestMissing`, missing full/lite manifests. Later rows supersede this initial state |
| 2026-06-16 | local pipeline drill | local fake HF | `dart/contentIndex/` | synthetic active manifest | synthetic previous manifest | pass in focused subprocess test, sourceManifestSet 4 sources | 실제 HF 증거는 아니며 preflight smoke 로 인정 |
| 2026-06-16 | full contentIndex candidate promote | `dart/contentIndex/_staging/full-20260616094524/` | `dart/contentIndex/manifest.json` | HF current full | previous current manifest pointer | `verifySearchHfRoundTrip.py --tier full` valid=true, activation/rollback true | 462,947 docs; source counts allFilings 192,095 / panel 104,761 / edgar-panel 84,293 / news 81,798 |
| 2026-06-16 | lite contentIndex candidate promote | `dart/contentIndex/lite/_staging/lite-20260616101609/` | `dart/contentIndex/lite/manifest.json` | HF current lite | previous current lite manifest pointer | `verifySearchHfRoundTrip.py --tier lite` valid=true, activation/rollback true | 280,747 docs, 326.3MB. 18개월 default lite 경량성은 후속 개선 필요 |
| 2026-06-18 KST | scheduled lite contentIndex promote | `dart/contentIndex/lite/_staging/lite-27719942258/` | `dart/contentIndex/lite/manifest.json` | HF current lite | previous current lite manifest pointer | remote evidence valid + empty-local lazy pull smoke | 292,568 docs; source counts allFilings 169,144 / panel 18,037 / edgar-panel 13,347 / news 92,040; source freshness allFilings/news/panel 20260617, edgar-panel 20260630. |

### Quality / Gold

| date | gate | corpus | gold origin | pass metric | result |
|---|---|---:|---|---|---|
| 2026-06-15 | demo-ops ceiling | 301579 docs | seeded/proxy | readyRate 0.9867, p95 157.9ms | pressure pass, release graduation 증거 아님 |
| pending | real query-log gold | pending | real | readyRate/docHit/news/noAnswer/EDGAR 기준 | gate 구현 완료, real rows 와 실행 증거 대기 |
| 2026-06-16 | query-log raw capture tooling | n/a | userLog candidate | `DARTLAB_SEARCH_QUERY_LOG` -> `data/search/queryLogRaw.jsonl` | `goldLog.py`/`api.py` hook 구현. 실제 reviewer label rows 는 대기 |
| 2026-06-15 | query-log gold preparation tooling | n/a | n/a | raw+label -> `data/search/queryLogGold.real.jsonl` | `prepareSearchGold.py` and focused tests pass. 실제 rows 는 대기 |
| 2026-06-16 | query-log quality toolchain drill | synthetic 4-row smoke | userLog reviewed synthetic | quality/miss-ledger toolchain valid | `runSearchQualityDrill.py` 구현 및 searchIndexDelta/Main artifact 배선. `releaseEvidence=false`, real gold 대체 불가 |
| pending | source/no-answer canary | pending | artifact-generated + curated operational canary | source isolation/sourceRef/noAnswer 기준 | artifact 기반 pack 구현 완료, 실제 Actions artifact report 와 운영 curated rows 대기 |
| pending | result contract audit | pending | real or full-source artifact result rows | invalidRows 0, sourceRef/dataAsOf/snippet/fieldCards/evidence present | CLI/workflow artifact 배선 완료, 실제 `searchResultContract.{delta,main}.json` Actions report 대기 |
| pending | productization status audit | pending | proof bundle | designReady/opsReady/releaseReady + blockers | CLI/workflow artifact 배선 완료, 실제 `searchProductizationStatus.{delta,main}.json` Actions report 대기 |
| pending | proof bundle next actions | pending | proof bundle + bootstrap plan | `nextActions.bootstrapPlan` 이 missing source/tier/action id 를 포함 | CLI/focused tests 완료. 실제 Actions proof bundle artifact 에서 확인 대기 |
| pending | cutover state audit | pending | proof bundle + replacement evidence | S1/S2/S3/S4, defaultReplacement blockers | CLI/workflow artifact 배선 완료, 실제 `searchCutover.{delta,main}.json` Actions report 대기 |
| 2026-06-15 | local result contract smoke | local active cache | local runtime result rows | totalRows 30, invalidRows 0, validRate 1.0 | `evaluateSearchResultContract.py` live query smoke 통과. HF/Actions full-source evidence 는 아님 |
| 2026-06-16 | local productization status audit | local catalog-mode active cache + local fake remote inventory | proof bundle partial | historical: `designReady=true`, `opsReady=false`, `releaseReady=false` | sourceCatalog/full content manifest inventory valid, local active cache `nDocs=361136`, source counts allFilings 191827 / panel 104759 / edgar-panel 58901 / news 5649, canary passRate 1.0, result contract invalidRows 0. This partial proof was superseded by direct-review S4 rows below. |
| 2026-06-16 | initial live proof bundle | local active cache + live HF remote evidence | proof bundle | historical: `designReady=true`, `opsReady=false`, `releaseReady=false` | local active cache `nDocs=361136`, source freshness allFilings 20260612 / panel 20260615 / edgar-panel 20260630 / news 20260528, canary 5/5 pass. This initial state was superseded by full_lite and direct-review S4 rows below. |
| pending | remote evidence audit | HF current repo | HF source/search artifact inventory | sourceCatalog missing list 0, contentIndex manifest missing list 0 | `checkSearchRemoteEvidence.py` CLI/workflow artifact 배선 완료, 실제 `searchRemoteEvidence.{delta,main}.json` Actions report 대기 |
| 2026-06-16 | initial live remote evidence audit | HF current repo | HF source/search artifact inventory | valid=false | fileCount=39225, blockers=`sourceCatalogMissing`, `contentIndexManifestMissing`; allFilings/dartPanel/edgarPanel/newsPublic source manifest/catalog and full/lite content manifests missing. Later remote evidence row supersedes this initial state |
| 2026-06-16 | live remote evidence audit after bootstrap | HF current repo | HF source/search artifact inventory | valid=true | sourceCatalog all expected sources present; full/lite contentIndex manifests present; required fileSources resolve; source_manifest_set producerRun complete |
| 2026-06-16 | live full_lite proof bundle after bootstrap | HF current repo + local active cache | proof bundle | quality-omitted: `opsReady=true`, `releaseReady=false` | remote evidence valid, full/lite round-trip valid, canary passRate 1.0, result contract valid. Direct-review quality rows below supersede release status. |
| 2026-06-16 | direct-review quality gate | HF current repo + reviewed userLog pack | userLog reviewed | `releaseEligible=true`, blockers=[] | `data/dart/searchCatalog/searchQualityReviewPack.directReview/qualityCycleDirect/qualityReport.json`: 106 real reviewed rows, coverage filing 54 / news 20 / EDGAR 20 / noAnswer 12, ready/docHit/memory/news precision all 1.0, noAnswer false accept 0.0 |
| 2026-06-16 | direct-review productization status | HF current repo + full/lite round-trip + quality report | proof bundle | `opsReady=true`, `releaseReady=true` | `data/dart/searchCatalog/searchProofBundle.directReview/searchProductizationStatus.json`: remote evidence valid, result contract valid, canary valid, full/lite activation+rollback valid, blockers=[] |
| 2026-06-16 | direct-review replacement evidence | proof bundle + remote evidence + workflow YAML | replacement evidence | `valid=true` | `data/dart/searchCatalog/searchProofBundle.directReview/searchReplacementEvidence.json`: catalog default/scheduled, legacy operator-only, fail-closed publish, active/previous manifest id, rollback command/verified, run evidence and surface naming recorded |
| 2026-06-16 | direct-review cutover state | proof bundle + replacement evidence | cutover | `S4_DEFAULT_REPLACEMENT` | `data/dart/searchCatalog/searchProofBundle.directReview/searchCutover.json`: `releaseReady=true`, `defaultReplacement=true`, blockers=[] |
| 2026-06-18 KST | live remote evidence audit | HF current repo | source/content manifest inventory | `valid=true`, blockers=[] | sourceCatalog allFilings/dartPanel/edgarPanel/newsPublic present with producerRun lineage; full/lite contentIndex manifests present; source_manifest_set producerRun complete. |
| 2026-06-18 KST | empty local dataDir lazy pull smoke | HF current lite | runtime `dartlab.search(...)` | `indexInfo.available=true`, `nDocs=292568` | content query "반도체 HBM 투자" returned allFilings body hits, news query "환율 기사" returned news hits, title/auto query "유상증자" returned allFilings hits. All sampled rows had sourceRef and dataAsOf. |
| 2026-06-18 KST | live body semantic/no-answer smoke | HF current lite + local runtime patch | runtime `dartlab.search(...)` | HBM body answerable, no-answer lowConfidence | `HBM 설비투자와 TC bonder 증설을 언급한 공시 원문` top-5 included HBM-related panel/allFilings rows; `화성 지하도시에 상장사가 얼음광산을 매입했다` returned low-score candidates marked `answerable=false`, `notAnswerableReason=lowConfidence`. |
| 2026-06-18 KST | full query-log gold after body rerank guard | HF current full + local runtime patch | `evaluateSearchGold.py --required-targets filing,news,noAnswer,edgar --fail-on-ineligible` | `releaseEligible=true`, blockers=[] | overallReadyRate 0.9811, docHit10 0.9787, memoryCitationTop3Exact 0.9468, newsSourcePrecision10 1.0, noAnswerFalseAcceptRate 0.0. |

---

## 15. 향후 source 확장 계약

향후 `allFilings`, DART panel, EDGAR panel, public news 가 계속 늘어나고 EDGAR allFilings/GDELT/private news 같은 source 가 추가돼도 search workflow 의 기본 구조는 바꾸지 않는다.

| future source | corpus 편입 조건 | 운영 문서에 남길 증거 |
|---|---|---|
| allFilings 추가 월/백필 | source full snapshot, `snapshotScope=full`, row count drop 없음 | source run id, file range, changed/new/deleted count |
| DART panel 추가/reconcile | panel rcept coverage, filing date freshness, panel priority 유지 | reconcile run id, restored rcept count, sourceDataAsOf |
| EDGAR panel 확대 | accession namespace, filing date 원천 컬럼, sourceRefVersion | accession count, item/section count, EDGAR canary |
| EDGAR allFilings 후보 | stable SEC docKey/sourceRef, license/public exposure, source canary | onboarding decision, first catalog manifest |
| public news 확대 | canonical URL hash, public/private 분리, news-only canary | source URL count, duplicate policy, canary report |
| GDELT 후보 | license, URL sourceRef, false-positive failure type, no-answer traps | onboarding checklist, first quality report |
| private/local news | public index 와 분리된 private/local artifact tier | private policy doc, local-only activation evidence |

새 source 는 이 표의 편입 조건을 채우기 전까지 `tests/_attempts` 또는 source workflow 내부 후보로 둔다. 제품 corpus 에 들어온 뒤에는 `12` 의 운영 증거 원장에 첫 성공 run 을 append 하고, `03`/`10`/`11`/Skill OS `engines.search` 를 같은 변경 단위에서 갱신한다.

---

## 16. 유지보수 Control Points

장기 운영에서 매번 확인해야 하는 control point 는 다음 네 곳이다.

| control point | 소유자 | 실패 시 publish/activate 정책 | 문서 증거 |
|---|---|---|---|
| source freshness | source workflow | 해당 source 최신 claim 금지 또는 search publish 중단 | source catalog runs |
| catalog diff | search delta/main workflow | catalog mode 금지, legacy fallback 은 임시 증거로만 인정 | search delta runs |
| artifact safety | search publish workflow | current manifest pointer publish 금지 | publish/local activation |
| runtime activation | local updater | active pointer swap 거부, previous active 유지 | publish/local activation |
| quality flywheel | search quality owner | release graduation 금지 | quality/gold |

이 control point 들이 정상이라면 데이터가 늘어나도 운영 방식은 바뀌지 않는다. allFilings, panel parquet, EDGAR panel, news 는 source owner 가 full snapshot manifest 를 유지하고, search 는 delta/main artifact 안전성만 책임진다.

### 16.1 증분이 쌓일 때 운영 판단

| 신호 | 판단 | 행동 |
|---|---|---|
| source row 증가, `docKey/textHash` 안정 | 정상 증분 | delta publish |
| source row 증가, delta/main 비율 증가 | compaction 필요 | 월간 main 또는 수동 main dispatch |
| source row 급감 | source 장애 가능 | search publish 중단 |
| `snapshotScope=partial` | freshness claim 불가 | catalog mode 제외 |
| result contract invalidRows 발생 | 제품 표면 계약 깨짐 | current publish/activation 차단 |
| real gold regression | 품질 회귀 | release block, miss ledger 정책화 |

### 16.2 운영 문서 업데이트 완료 판정

운영 문서 업데이트는 다음 세 조건을 만족해야 완료다.

1. 실제 workflow/script 파일명이 `12` 의 맵에 반영됐다.
2. 사용자가 실행할 명령과 운영자가 기록할 증거가 `11` 에 반영됐다.
3. 제품 상태와 남은 blocker 가 `06` 에 반영됐다.

이 셋 중 하나라도 빠지면 코드가 동작해도 search productization 문서 작업은 완료가 아니다.
