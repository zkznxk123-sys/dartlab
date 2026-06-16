# 11. 운영 런북 — Search Productization

상태: v1.21 (2026-06-16)
범위: 제품 검색을 본진에 넣은 뒤 운영자가 확인해야 하는 일일·주간·월간 절차와 장애 대응.

워크플로별 실제 연결표는 [12-pipeline-maintenance-map.md](12-pipeline-maintenance-map.md) 를 따른다.

---

## 1. 운영 원칙

1. HF 에 publish 된 artifact 보다 local active index 가 더 중요하다. 새 artifact 가 의심스러우면 local 은 기존 active 를 유지한다.
2. search workflow 는 source 데이터를 소유하지 않는다. allFilings, panel, EDGAR, news owner 가 만든 source manifest 를 소비한다.
3. "최신"이라는 말은 source별 `dataAsOf` 로만 한다.
4. 장애 대응은 특수 query rule 추가가 아니라 source manifest, catalog diff, selfcheck, canary, miss ledger 로 한다.
5. real query-log gold 전까지 release graduation 을 선언하지 않는다.
6. `Search Index Delta/Main` 의 기본 제품화 기준은 report 업로드가 아니라 hard fail 이다. `productization_gate=ops` 는 ops-ready blocker 를 실패로 만들고, `productization_gate=release` 는 real query-log gold quality report 까지 요구한다.
7. 본진 교체 상태는 `13-cutover-contract.md` 를 따른다. `designReady` 는 코드/설계 준비, `opsReady` 는 기본값 교체 가능, `releaseReady` 는 제품 졸업 가능, `defaultReplacement` 는 단일 엔진 기본값 전환 완료를 뜻한다.

---

## 2. 일일 확인

### Source workflows

확인 대상:

- `Original SSOT Sync`
  - `dart-zip`
  - `dart-reconcile`
  - `allfilings`
  - `allfilings-backfill`
  - `edgar`
- `News Archive Sync`
  - `news`
  - `newsEnrich`
- `EDGAR Data Sync (Bulk)`
  - `edgar`
  - `edgarPanel`
- `GDELT Sync`
  - 후보 source 이므로 제품 corpus 자동 혼합 여부는 onboarding 상태로 확인
- `Search Index Delta`

확인 항목:

| 항목 | 정상 기준 |
|---|---|
| workflow conclusion | success 또는 명시 no-op |
| source manifest | 생성됨 |
| source `dataAsOf` | 멈추지 않음 |
| row count | 비정상 급감 없음 |
| search delta | selfcheck pass |
| HF publish | `_staging/{runId}` 업로드 후 current `manifest.json` pointer publish. 실제 HF round-trip 에서 full/lite required files/hash/canary/rollback 확인 |

실패 시 search artifact 를 수동으로 덮어쓰지 않는다. source workflow 를 먼저 복구한다.

현재 구현 상태에서 일일 확인의 핵심은 두 가지다.

1. source owner workflow 가 `dart/searchCatalog/{source}/{source}.source_manifest.json` 과 `{source}.catalog_snapshot.parquet` 를 실제로 올렸는지 확인한다. 현재 `buildSearchCatalog.py --upload` 는 두 artifact 를 단일 `create_commit` batch 로 올리고, Actions artifact `search-catalog-{source}-{job}-{run}` 으로 같은 산출물을 남긴다. source manifest 의 `producerRun.workflow/job/runId/sha/artifactName` 이 비어 있으면 S2 운영 증거로 보지 않는다.
2. expected source set (`allFilings`, `dartPanel`, `edgarPanel`, `newsPublic`) 이 모두 있는지 확인한다. `prepareSearchDeltaInputs.py` 는 expected source set 이 빠지면 catalog mode env 를 만들지 않는다.
3. expected source 의 `totalRows` 와 current catalog rows 가 0 이 아닌지 확인한다. 빈 full snapshot 은 catalog mode invalid 다.
4. source catalog 가 full snapshot 인지 확인한다. `buildSearchCatalog.py` 는 `snapshotScope` 와 `completenessCheck` 를 쓰고, 기본 `--min-files 1 --min-rows 1 --min-catalog-rows 1` 로 빈 full snapshot 을 실패시킨다. source owner workflows 는 기본적으로 `--compare-remote-manifest --require-previous-manifest` 로 직전 HF full manifest 대비 files/rows/catalogRows 급락을 차단한다. 첫 full 기준점은 `Search Index Main` 의 raw full HF pull bootstrap 또는 운영자가 명시한 source-owner `search_catalog_bootstrap=true` dispatch 로만 만든다. source-owner bootstrap 은 previous manifest 요구만 해제하고 allFilings 150k, DART panel 90k, EDGAR panel 50k, news 100 catalog row 하한을 통과해야 한다. `prepareSearchDeltaInputs.py` 는 `full` 만 catalog mode 로 넘긴다.
5. `Search Index Delta` 가 `pullSearchCurrentIndex.py` 단계에서 HF current manifest pointer 를 따라 기존 full `main.*` required files 와 `previous_manifest.json` 을 복원했는지 확인한다. 이 단계가 실패하면 delta publish 를 계속하지 않는다.
6. `Search Index Delta` 가 `Prepare catalog delta inputs` 단계에서 `DARTLAB_SEARCH_DELTA_MODE=catalog` 을 세팅했는지 확인한다. source catalog 가 없어서 legacy fallback 된 run 은 성공이어도 all-source 운영 완료 증거가 아니다.
7. 현재 contentIndex upload 는 local manifest/hash/canary selfcheck 후 staging upload/current manifest pointer helper 를 사용한다. 운영자는 staging path, current path, `manifest.json`, `fileSources`, `requiredFiles`, `fileHashes`, `catalog_snapshot.parquet`, `source_manifest_set.json` 이 함께 올라갔는지 확인한다. graph catalog 를 배포하는 run 은 `entityGraphCatalog.parquet` 가 `requiredFiles`, `fileHashes`, `fileSources`, manifest `entityGraphCatalog` summary 에 함께 있어야 한다. delta publish 에서는 previous manifest 의 main `fileSources` 가 사라지면 안 된다.
추가 확인: 제품형 fail-closed publish 는 `DARTLAB_SEARCH_PROMOTE_CURRENT=0` stage-only publish 로 candidate manifest 를 만들고, `verifySearchHfRoundTrip.py --manifest-repo-path <candidate>` 와 result contract/canary/status 가 통과한 뒤 current pointer 를 promote 한다. 현재 checkout 은 direct-review proof bundle 과 workflow 정적 계약으로 S4 replacement evidence 를 만들었고, 원격 Actions 는 같은 순서의 artifact 를 다음 run 에서 재확인한다.
8. `checkSearchRemoteEvidence.py` 결과에 `contentIndexFileSourceMissing`, `missingContentFileSource:*`, `missingContentFileSourceMapping:*` 이 없어야 한다. manifest 만 있고 staging 대상이 없는 run 은 실패다.
9. full 과 lite `verifySearchHfRoundTrip.py` report 가 모두 `valid=true`, `activation.activated=true`, `rollback.rolledBack=true` 여야 한다. helper 단위 테스트만으로는 release graduation 증거가 아니며, 실제 HF round-trip 과 rollback drill 이 필요하다.
10. source catalog row 단위가 검색 문서 단위인지 확인한다. DART/EDGAR panel 의 `rawRows` 는 수천만이어도 `totalRows` 는 filing/accession 롤업 문서 수여야 한다. allFilings 는 `fetch_status=ok`, non-empty 본문, unique docKey 기준이어야 한다.
11. current catalog 결합은 streaming writer 경로여야 한다. Polars full concat/write 경로로 되돌아간 run 은 대형 text parquet page 한계로 실패할 수 있으므로 운영 위험으로 기록한다.
12. contentIndex manifest 의 `sourceManifestSetId` 가 비어 있지 않고 `source_manifest_set.json` 이 `requiredFiles` 와 `fileSources` 에 포함됐는지 확인한다. `checkSearchRemoteEvidence.py` 는 `fileSources` 로 실제 set 파일을 열고, `evaluateSearchProductizationStatus.py` 는 set 내부 source별 `producerRun` 이 비면 `remoteContentManifestSetMissingProducerRun:*` blocker 로 S2 `opsReady` 를 차단한다. source manifest set 이 없거나 set 내부 source별 `producerRun` 이 비어 있으면 legacy/raw fallback 또는 수동 산출물이다.
13. `searchProofBundle.{delta,main}/searchProofBundle.json` 과 `searchProductizationStatus.json` 을 확인한다. bundle 은 remote evidence, local indexInfo, result contract, canary, full/lite round-trip, optional quality report 를 한 곳에 모은 운영 인계 단위다. `missingEvidence` 가 비어 있지 않으면 release-ready 로 해석하지 않는다. remote source/content blocker 가 있으면 같은 bundle 의 `reports.bootstrapPlan` 과 `nextActions.bootstrapPlan` 을 확인해 다음 source-owner/Search Main/검증 순서를 따른다.
14. `searchCutover.{delta,main}.json` 을 확인한다. S2 `opsReady` 와 S3 `releaseReady` 가 참이어도 S4 `defaultReplacement` 는 별도 replacement evidence 없이는 참이 아니다. replacement evidence 는 `defaultBuildMode=catalog`, `scheduledBuildMode=catalog`, legacy fallback 운영자 전용, fail-closed publish 정책, active/previous manifest id, rollback command, rollback 검증, run evidence 기록, surface naming review 를 포함해야 한다.
15. `searchQualityDrill.{delta,main}.json` 이 `valid=true` 인지 확인한다. 이 drill 은 query-log gold 도구 체인 smoke 이며 `releaseEvidence=false` 이므로 real query-log gold 를 대체하지 않는다.
16. `searchPipelineDrill.{delta,main}.json` 이 `valid=true` 이고 `sourceManifestSet.id` 와 4개 source 가 기록됐는지 확인한다. 이 drill 은 raw source -> source catalog -> source manifest set -> contentIndex publish/activate/rollback 경로가 깨지지 않았다는 로컬 하한 증거이며, 실제 HF Actions round-trip 증거를 대체하지 않는다.

2026-06-16 현재 실제 HF bootstrap 기준:

- `dart/searchCatalog/{allFilings,dartPanel,edgarPanel,newsPublic}/` 는 source manifest/catalog snapshot 을 갖고 remote evidence audit 에서 `valid=true` 다.
- full current manifest 는 462,947 docs, lite current manifest 는 280,747 docs 다. full/lite 모두 staged candidate round-trip 과 promote 를 통과했다.
- direct-review proof bundle 은 `opsReady=true`, `releaseReady=true`, blockers=[] 다. 품질팩은 106 real reviewed userLog rows, filing 54 / news 20 / EDGAR 20 / noAnswer 12 coverage, `overallReadyRate=1.0`, `noAnswerFalseAcceptRate=0.0` 을 기록했다.
- cutover evidence 는 `data/dart/searchCatalog/searchProofBundle.directReview/searchReplacementEvidence.json` 과 `searchCutover.json` 이며, `state=S4_DEFAULT_REPLACEMENT`, `defaultReplacement=true` 다. 새 Search Main/Delta Actions run 에서 같은 artifact 가 생성되는지는 다음 운영 확인 대상이다.
- Search Main/Delta release gate 는 S4 를 hard fail 한다. replacement evidence 가 incomplete 이거나 cutover 가 `defaultReplacement=true` 를 만들지 못하면 workflow 는 red 여야 한다. ops gate 는 S2 운영 가능성까지만 강제한다.
- lite 18개월 tier 는 326.3MB 로 경량 목표 300MB 를 넘었다. 월간 점검 때 12개월/상위 universe/metadata 압축을 별도 실험한다.
- graph catalog 는 optional sidecar 다. 운영자가 `DARTLAB_SEARCH_ENTITY_GRAPH_CATALOG` 로 검증된 parquet 를 넘기거나 `DARTLAB_SEARCH_ENTITY_GRAPH_BUILD=1` 을 명시한 run 에서만 `entityGraphCatalog.parquet` 를 만든다. 이 파일이 current manifest required file 로 올라간 run 에서는 `searchRemoteEvidence` / `searchProductizationStatus` 의 `entityGraphCatalog.{tier}` summary 에 `fileSourceExists=true`, `nEntities>0`, `dataAsOf` 가 남는지 보고, `dartlab.search(...)` 결과의 `entityCards` smoke 를 추가로 확인한다. 없으면 검색 자체는 기존 result contract 로 판단한다.

### Quick freshness sample

대표 호출:

```powershell
uv run python -X utf8 -c "import dartlab; print(dartlab.search.indexInfo())"
```

확인:

- `available=True`
- `compatible=True`
- `sourceDataAsOf` 가 source별로 최신에 가까움
- `allFilings`, `panel`, `edgar-panel`, `news` 모두 `nDocsBySource` 와 `sourceDataAsOf` 를 가짐
- `hasDelta` 가 expected 상태
- `nDocsBySource` 급감 없음

### Product quality smoke

대표 호출:

```powershell
uv run python -X utf8 -c "import dartlab; r=dartlab.search('삼성전자 대표이사 변경', topK=5); cols=[c for c in ['stock_code','corp_name','source','sourceRef','answerable','notAnswerableReason'] if c in r.columns]; print(r.select(cols)); print('unique_stock_codes=', sorted(str(x) for x in r['stock_code'].drop_nulls().unique().to_list()) if 'stock_code' in r.columns else [])"
```

확인:

- `topK` 인자가 실제로 동작함.
- `stock_code` 가 있는 공시/panel row 는 `005930` 만 반환됨.
- 삼성 계열사/유사명 row 가 상위에 섞이지 않음.
- `answerable=False` row 가 있으면 `notAnswerableReason` 을 확인해 miss ledger 후보로 남김.

---

## 3. 주간 확인

### Query-log review

목표:

- 실제 운영자/사용자 query 를 filing/news/noAnswer/EDGAR 로 분류.
- gold 후보에 target sourceRef 를 붙임.
- false accept 와 miss 를 분리.
- `goldOrigin=real` 과 `reviewStatus=reviewed` 를 채운 row 만 release graduation 후보로 인정.

운영 파일:

| 파일 | 역할 |
|---|---|
| `data/search/queryLogRaw.jsonl` | 실제 운영자/사용자 query event 후보. |
| `data/search/queryLogLabels.reviewed.jsonl` | reviewer 가 붙인 target/sourceRef/noAnswer label. |
| `data/search/queryLogGold.real.jsonl` | 운영자가 갱신하는 canonical gold JSONL. |
| `data/search/queryLogGold.summary.json` | coverage, invalid rows, blockers summary. |
| `tests/fixtures/search/queryLogGold.real.jsonl` | GitHub Actions release gate 의 기본 검증 gold. 운영 gold 를 새로 만들면 `quality_gold` 입력으로 override 한다. |

raw 후보 수집:

```powershell
# 기본 경로: {dartlab.dataDir}/search/queryLogRaw.jsonl
$env:DARTLAB_SEARCH_QUERY_LOG = "1"
$env:DARTLAB_SEARCH_QUERY_LOG_TOPK = "10"

uv run python -X utf8 -c "import dartlab; dartlab.search('삼성전자 대표이사 변경', topK=5)"
```

`DARTLAB_SEARCH_QUERY_LOG` 에 파일 경로를 직접 넣으면 그 위치에 JSONL 을 쓴다. 이 raw row 는 `goldOrigin=userLog`, `reviewStatus=candidate` 이며, top sourceRef/source/answerability/dataAsOf 를 reviewer 참고용으로 보존한다. raw capture 만으로는 release gold 가 아니다. reviewer label 에 `targetKind`, `expectedSourceRef` 또는 `expectedSourceRefs`, no-answer 여부, `reviewStatus=reviewed` 가 붙은 뒤에만 release gate 후보가 된다.

금지:

- generated/proxy query 를 real gold 로 승격.
- miss 1건을 특정 회사/날짜 mapper 로 해결.
- source intent fallback 으로 false positive 를 숨김.

승격 조건:

1. 같은 miss type 이 반복된다.
2. sourceRef/evidence-card 개선으로 해결된다.
3. 기존 canary 와 gold 에 회귀가 없다.
4. source adapter, facet planner, sourceRef policy, answerability 중 하나의 일반 정책으로 표현된다.

정규화:

```powershell
uv run python -X utf8 .github/scripts/search/prepareSearchGold.py `
  --input data/search/queryLogRaw.jsonl `
  --labels data/search/queryLogLabels.reviewed.jsonl `
  --out data/search/queryLogGold.real.jsonl `
  --summary data/search/queryLogGold.summary.json `
  --min-rows 100 `
  --required-targets filing,news,noAnswer,edgar `
  --fail-on-ineligible
```

이 명령은 answerable row 의 `expectedSourceRef`/`expectedSourceRefs` 누락, proxy origin, unreviewed status, target coverage 누락을 release blocker 로 본다. migration 중 sourceRef 없는 옛 row 를 잠깐 보려면 `--allow-missing-source-ref` 를 쓸 수 있지만 release graduation 에서는 금지한다.

### Miss ledger

필수 컬럼:

- `query`
- `targetKind`
- `expectedSourceRef`
- `topSourceRefs`
- `failureType`
- `sourceDataAsOf`
- `decision`
- `policyCandidate`
- `reviewStatus`

`failureType` 예:

- `sourceIntentMiss`
- `entityFacetMiss`
- `dateFacetMiss`
- `reportFacetMiss`
- `bodyEvidenceMiss`
- `newsDuplicateTitle`
- `noAnswerFalseAccept`
- `staleSource`
- `sourceManifestGap`

현재 자동 생성되는 기본 failure type:

- `docMiss10`
- `citationMissTop3`
- `falseAccept`
- `newsSourcePrecision10`
- `goldReviewRequired`

---

## 4. 월간 확인

### Main compaction

실행 전:

- delta 비율 확인.
- tombstone 누적 확인.
- source별 count 확인.
- HF disk/artifact size 확인.
- canary pack 최신성 확인.
- 현재 `searchIndexMain.yml` 이 source catalog snapshot compaction 경로로 들어갔는지, legacy raw fallback 경로로 들어갔는지 구분.
- catalog 경로에서는 source manifest set, `snapshotScope=full`, expected source set, current catalog hash 를 기록한다.
- raw fallback 경로에서는 workflow pull count 하한을 먼저 확인한다. raw fallback run 은 monthly full rebuild 증거이며, 같은 run 의 `Build canonical source search catalogs from full HF pull` 단계가 source catalog 4종을 `searchIndexMain.full-pull` producer 로 publish 해야 한다. 이어지는 `Prepare canonical catalog main inputs after bootstrap` 단계가 `DARTLAB_SEARCH_MAIN_MODE=catalog` 과 `source_manifest_set.json` 을 세팅해야 bootstrap run 자체가 catalog lineage 증거가 된다.

실행 후:

- main required files 존재.
- delta files 정리.
- full/lite tier 모두 manifest selfcheck 통과.
- local updater smoke 통과.
- replacement quality gate 통과.

### Quality pack refresh

월간 refresh 대상:

- 최근 allFilings 사건.
- 최신 DART panel 정기보고서.
- 최신 EDGAR 10-K/10-Q/8-K.
- public news 중 공시와 엮인 headline.
- no-answer traps.
- `data/search/sourceCanaryPack.jsonl`.

---

## 5. 장애 대응

### HF partial pull 또는 429

증상:

- source file count 가 낮음.
- `nDocs` 급감.
- manifest hash 누락.
- workflow log 에 partial pull 또는 retry 흔적.

대응:

1. publish/promote 중단.
2. source workflow retry 또는 다음 cron 대기.
3. 기존 active index 유지.
4. selfcheck 가 통과하기 전 수동 upload 금지.
5. source catalog upload 와 contentIndex publish 가 batch `create_commit` 경로를 탔는지 확인한다. 파일별 반복 upload 로 되돌아간 run 은 HF 429 재발 위험으로 기록한다.

### Source count 급감

대응:

1. 어느 source manifest 가 줄었는지 확인.
2. source owner workflow 로 돌아간다.
3. search delta 에서 해당 source freshness claim 제거 또는 publish 중단.
4. canary fail 이면 release block.

### Delta 0 docs

정상일 수 있다. 다음 기준으로 판정한다.

정상 no-op:

- source manifest `dataAsOf` 변화 없음.
- source workflow 가 no-op 을 명시.
- previous catalog 와 hash 차이 없음.

비정상:

- sourceDataAsOf 는 변했는데 changed set 이 0.
- source row count 는 변했는데 catalog diff 0.
- source manifest 가 누락됐는데 delta 를 성공 처리.

비정상이면 publish 금지.

### Local update 실패

대응:

1. staging dir 삭제.
2. active pointer 유지.
3. `indexInfo()` 에 update failure 를 노출할 수 있으면 노출.
4. 다음 검색에서 재시도는 TTL 또는 explicit `prefetch/update` 기준으로 제한.

### Gold regression

대응:

1. release block.
2. miss ledger 에 기록.
3. 이전 artifact rollback 가능 여부 확인.
4. 특정 query rule 추가 금지.
5. 반복 유형이면 policy candidate 로 분류.

---

## 6. 배포 체크리스트

본진 search 교체 전:

- [x] result schema 확정.
- [x] source manifest schema 확정.
- [x] index manifest schema 확정.
- [x] local updater swap/rollback helper 구현.
- [x] replacement gate tracked test 로 승격.
- [x] `13-cutover-contract.md` 기준 S2 `opsReady=true` proof bundle 확보.
- [x] source/no-answer canary pack gate CLI 1차 구현.
- [x] manifest `sourceCanaryPack` 기반 canary report CLI 구현.
- [x] productization status audit CLI 구현.
- [x] productization status workflow hard gate 구현. (`--fail-on-ops-not-ready`, `--fail-on-release-not-ready`)
- [x] sourceCanaryPack local activation gate 연결.
- [x] result row contract audit CLI 1차 구현 및 searchIndexDelta/Main evidence artifact 업로드 배선.
- [ ] 실제 운영 source canary pack rows 작성.
- [x] generated/proxy gold 와 real gold 구분 필드 고정.

본진 search 교체 후:

- [ ] `uv run python -X utf8 tests/run.py preflight`
- [ ] `uv run python -X utf8 tests/audit/dartlabGuard.py quick`
- [x] search replacement gate.
- [x] local raw-source hfPipeline/localUpdater drill.
- [x] actual HF hfPipeline dry run.
- [x] catalog delta dry-run subprocess smoke.
- [x] synthetic localUpdater activation/rollback smoke.
- [x] actual HF localUpdater smoke.
- [x] `dartlab.search.indexInfo()` smoke.
- [x] `dartlab.search(..., topK=N)` alias regression.
- [x] query 본문 회사명 stockCode facet regression.
- [x] public/local/CLI surface naming 충돌 확인.

릴리즈 졸업 전:

- [x] real query-log gold 100 rows 이상.
- [x] filing/news/noAnswer/EDGAR coverage.
- [x] query-log gold/miss ledger gate CLI 1차 구현.
- [x] `evaluateSearchGold.py --fail-on-ineligible` real gold 통과.
- [x] sourceRef/dataAsOf 없는 result 0.
- [ ] 회사명 포함 query 의 유사명/계열사 trap false accept 0.
- [x] `evaluateSearchResultContract.py --fail-on-error` 실제 full-source result report 통과.
- [x] `checkSearchRemoteEvidence.py` 실제 HF source catalog/contentIndex manifest/source manifest set lineage audit report 확인.
- [x] 원격 evidence 가 비어 있을 때 source-owner bootstrap/Search Main/검증 명령을 산출하는 비파괴 plan CLI 확보.
- [x] no-answer falseAcceptRate 기준 통과.
- [x] HF contentIndex staging/promote 실제 HF round-trip 경로 실증.
- [x] HF current manifest round-trip 검증 CLI 와 workflow evidence artifact 업로드 배선.
- [x] canary/status proof bundle workflow evidence artifact 업로드 배선.
- [x] publish 전 local manifest/hash/canary selfcheck 차단 단위 테스트.
- [ ] local update 실패 시 active 보존 실증.
- [x] local update staged artifact 실패 시 기존 active 보존 단위 테스트.
- [x] manifest canary query 실패 시 active 전환 거부 단위 테스트.
- [x] manifest sourceCanaryPack 실패 시 active 전환 거부 단위 테스트.
- [x] schema incompatible manifest active 전환 거부 단위 테스트.
- [x] previous active rollback helper 단위 테스트.
- [x] Skill OS `engines.search` 갱신.
- [x] README/운영문서 갱신. CHANGELOG 는 release artifact 작성 시 별도 갱신한다.

---

## 7. 운영 명령 슬롯

현재 문서 기준 명령 슬롯이다. 구현 중 실제 명령명이 확정되면 이 절을 먼저 갱신한다.

```powershell
# 전체 repo 기본 게이트
uv run python -X utf8 tests/run.py preflight

# Guard Index quick
uv run python -X utf8 tests/audit/dartlabGuard.py quick

# 기존 attempts replacement gate
uv run python -X utf8 tests\_attempts\searchProductCore\runProductCoreGate.py --profile replacement --timeout-sec 2400

# 인덱스 freshness
uv run python -X utf8 -c "import dartlab; print(dartlab.search.indexInfo())"

# 제품 품질 smoke: query 본문 회사명이 stockCode facet 으로 들어가고 topK alias 가 동작하는지 확인.
uv run python -X utf8 -c "import dartlab; r=dartlab.search('삼성전자 대표이사 변경', topK=5); cols=[c for c in ['stock_code','corp_name','source','sourceRef','answerable','notAnswerableReason'] if c in r.columns]; print(r.select(cols)); print('unique_stock_codes=', sorted(str(x) for x in r['stock_code'].drop_nulls().unique().to_list()) if 'stock_code' in r.columns else [])"

# source catalog artifact 생성 smoke
uv run python -X utf8 .github/scripts/search/buildSearchCatalog.py `
  --source allFilings `
  --input "data/dart/allFilings/*.parquet" `
  --out-dir data/dart/searchCatalog/allFilings `
  --min-files 1 `
  --min-rows 1 `
  --min-catalog-rows 1

# source-owner 증분 job 과 같은 hard gate 로 확인하려면 직전 source manifest 를 요구한다.
uv run python -X utf8 .github/scripts/search/buildSearchCatalog.py `
  --source allFilings `
  --input "data/dart/allFilings/*.parquet" `
  --out-dir data/dart/searchCatalog/allFilings `
  --compare-remote-manifest `
  --require-previous-manifest

# source searchCatalog 존재 확인
Get-ChildItem data/dart/searchCatalog -Recurse -Filter *.source_manifest.json
Get-ChildItem data/dart/searchCatalog -Recurse -Filter *.catalog_snapshot.parquet

# source catalog inventory. totalRows 는 search doc row, rawRows 는 원천/raw block row 다.
@'
import json
from pathlib import Path
import polars as pl

for source in ["allFilings", "dartPanel", "edgarPanel", "newsPublic"]:
    manifest = json.loads(Path(f"data/dart/searchCatalog/{source}/{source}.source_manifest.json").read_text(encoding="utf-8"))
    catalog = Path(f"data/dart/searchCatalog/{source}/{source}.catalog_snapshot.parquet")
    rows = pl.scan_parquet(catalog).select(pl.len().alias("rows"), pl.col("docKey").n_unique().alias("unique")).collect().to_dicts()[0]
    print(source, {"rawRows": manifest.get("rawRows"), "totalRows": manifest.get("totalRows"), "rows": rows["rows"], "unique": rows["unique"], "dataAsOf": manifest.get("dataAsOf"), "producerRun": manifest.get("producerRun")})
'@ | uv run python -X utf8 -

# search delta catalog env 준비 smoke. 로컬에서는 GITHUB_ENV 를 직접 지정해야 한다.
$envFile = Join-Path $env:TEMP "dartlab-search-delta.env"
Remove-Item $envFile -ErrorAction SilentlyContinue
$env:GITHUB_ENV = $envFile
uv run python -X utf8 .github/scripts/search/prepareSearchDeltaInputs.py
if (Test-Path $envFile) {
  Get-Content $envFile | ForEach-Object {
    $parts = $_.Split("=", 2)
    if ($parts.Length -eq 2) { Set-Item -Path "Env:$($parts[0])" -Value $parts[1] }
  }
}
if (-not $env:DARTLAB_SEARCH_CURRENT_CATALOG) { throw "source catalogs missing; catalog mode not prepared" }

# catalog delta dry-run
$env:DARTLAB_SEARCH_DELTA_DRY_RUN = "1"
uv run python -X utf8 .github/scripts/search/buildSearchDelta.py
Remove-Item Env:DARTLAB_SEARCH_DELTA_DRY_RUN -ErrorAction SilentlyContinue

# local end-to-end pipeline drill. 실제 HF 대신 synthetic raw source 와 local fake HF 로 source catalog freeze, staging publish, activation, rollback 을 검증한다.
uv run python -X utf8 .github/scripts/search/runSearchPipelineDrill.py `
  --out data/search/searchPipelineDrill.json `
  --fail-on-error

# source/no-answer canary gate. release graduation 증거가 아니라 publish/local activation 안전장치다.
uv run python -X utf8 .github/scripts/search/evaluateSearchCanary.py `
  --canary data/search/sourceCanaryPack.jsonl `
  --out data/search/canaryReport.json `
  --fail-on-error

# 빌드된 manifest 의 artifact 기반 sourceCanaryPack 을 직접 평가한다.
uv run python -X utf8 .github/scripts/search/evaluateSearchCanary.py `
  --manifest data/dart/contentIndex/manifest.json `
  --out data/search/searchCanary.json `
  --fail-on-error

# result row contract audit. 실제 full-source artifact 결과로 sourceRef/dataAsOf/snippet/fieldCards/evidence 계약을 확인한다.
uv run python -X utf8 .github/scripts/search/evaluateSearchResultContract.py `
  --query "유상증자" `
  --query "공시 말고 뉴스로 환율 기사" `
  --query "HBM 투자 계획" `
  --out data/search/resultContractReport.json `
  --min-rows 3 `
  --fail-on-error

# 실제 HF current manifest round-trip smoke. 기본은 temp local base 에서 activate/rollback 하므로 일반 cache 를 건드리지 않는다.
uv run python -X utf8 .github/scripts/search/verifySearchHfRoundTrip.py `
  --tier full `
  --out data/search/searchHfRoundTrip.json `
  --fail-on-error

# stage-only candidate manifest 검증. current pointer 를 바꾸기 전에 staging manifest 를 직접 activate/rollback 한다.
$env:DARTLAB_SEARCH_PROMOTE_CURRENT = "0"
# buildSearchMain/buildSearchDelta/pushContentIndex 가 출력한 candidateManifestPath 를 사용한다.
uv run python -X utf8 .github/scripts/search/verifySearchHfRoundTrip.py `
  --tier full `
  --manifest-repo-path "dart/contentIndex/_staging/full-<run>/manifest.json" `
  --out data/search/searchHfRoundTrip.candidate.json `
  --fail-on-error
Remove-Item Env:DARTLAB_SEARCH_PROMOTE_CURRENT -ErrorAction SilentlyContinue

# 원격 HF evidence audit. source catalog, contentIndex current manifest, fileSources target, source manifest set lineage 를 JSON 으로 남긴다.
uv run python -X utf8 .github/scripts/search/checkSearchRemoteEvidence.py `
  --out data/search/searchRemoteEvidence.json `
  --fail-on-missing

# 원격 evidence 가 비어 있거나 불완전하면 bootstrap 실행 계획을 먼저 생성한다.
# 이 명령은 GitHub/HF 를 변경하지 않고 어떤 workflow_dispatch 를 실행해야 하는지 JSON 으로만 남긴다.
uv run python -X utf8 .github/scripts/search/planSearchBootstrap.py `
  --remote-evidence data/search/searchRemoteEvidence.json `
  --out data/search/searchBootstrapPlan.json

# proof bundle 은 remote source/content blocker 가 있으면 같은 plan 을 bundle 안에도 남긴다.
# searchProofBundle.json 의 nextActions.bootstrapPlan 을 운영 실행 순서로 사용한다.
uv run python -X utf8 .github/scripts/search/buildSearchProofBundle.py `
  --out-dir data/search/searchProofBundle.bootstrap `
  --expected-sources allFilings,dartPanel,edgarPanel,newsPublic `
  --content-tiers full,lite `
  --run-hf-round-trip `
  --fail-on-ops-not-ready

# S4 default replacement evidence 생성. 이 단계가 catalog 기본값, fail-closed publish, rollback, surface naming 증거를 모은다.
uv run python -X utf8 .github/scripts/search/buildSearchReplacementEvidence.py `
  --proof-bundle data/search/searchProofBundle.bootstrap/searchProofBundle.json `
  --remote-evidence data/search/searchRemoteEvidence.json `
  --round-trip data/search/searchHfRoundTrip.full.json `
  --round-trip data/search/searchHfRoundTrip.lite.json `
  --workflow .github/workflows/searchIndexMain.yml `
  --workflow .github/workflows/searchIndexDelta.yml `
  --out data/search/searchReplacementEvidence.json `
  --fail-on-incomplete

# cutover 상태 감사. S4 defaultReplacement 는 replacement evidence 없이는 참이 아니다.
uv run python -X utf8 .github/scripts/search/evaluateSearchCutover.py `
  --proof-bundle data/search/searchProofBundle.bootstrap/searchProofBundle.json `
  --replacement-evidence data/search/searchReplacementEvidence.json `
  --out data/search/searchCutover.bootstrap.json `
  --fail-on-default-not-ready

# 수동 replacement evidence 예시. 자동 builder 를 못 쓰는 조사 상황에서만 사용한다.
@'
{
  "proofBundle": "data/search/searchProofBundle.bootstrap/searchProofBundle.json",
  "singleEngineDefault": true,
  "defaultBuildMode": "catalog",
  "scheduledBuildMode": "catalog",
  "legacyFallbackOperatorOnly": true,
  "failClosedPublish": true,
  "activeManifestId": "manifest-current",
  "previousManifestId": "manifest-previous",
  "rollbackCommand": "uv run python -X utf8 -c \"from dartlab.providers.dart.search.localUpdate import rollbackActiveIndex; print(rollbackActiveIndex())\"",
  "rollbackVerified": true,
  "runEvidenceRecorded": true,
  "surfaceNamingReviewed": true
}
'@ | Set-Content -Encoding utf8 data/search/searchReplacementEvidence.json

uv run python -X utf8 .github/scripts/search/evaluateSearchCutover.py `
  --proof-bundle data/search/searchProofBundle.bootstrap/searchProofBundle.json `
  --replacement-evidence data/search/searchReplacementEvidence.json `
  --out data/search/searchCutover.replacement.json `
  --fail-on-default-not-ready

# 제품화 상태 감사. proof bundle 을 모아 design/ops/release readiness 와 blocker 를 산출한다.
uv run python -X utf8 .github/scripts/search/evaluateSearchProductizationStatus.py `
  --remote-evidence data/search/searchRemoteEvidence.json `
  --result-contract data/search/resultContractReport.json `
  --canary-report data/search/searchCanary.json `
  --hf-round-trip data/search/searchHfRoundTrip.json `
  --quality-report data/search/qualityReport.json `
  --out data/search/searchProductizationStatus.json `
  --fail-on-release-not-ready

# release 전 운영 게이트가 아니라 일상 publish/activation 가능성만 보려면 quality report 없이 ops gate 를 쓴다.
uv run python -X utf8 .github/scripts/search/evaluateSearchProductizationStatus.py `
  --remote-evidence data/search/searchRemoteEvidence.json `
  --result-contract data/search/resultContractReport.json `
  --canary-report data/search/searchCanary.json `
  --hf-round-trip data/search/searchHfRoundTrip.json `
  --out data/search/searchProductizationStatus.ops.json `
  --fail-on-ops-not-ready

# real query-log gold gate. release graduation 에서는 --allow-proxy-query-log 금지.
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

# query-log gold toolchain drill. release evidence 가 아니라 운영 도구 smoke 다.
uv run python -X utf8 .github/scripts/search/runSearchQualityDrill.py `
  --out data/search/queryLogGold.drill.json `
  --canonical-gold data/search/queryLogGold.drill.gold.jsonl `
  --label-template data/search/queryLogGold.drill.labels.jsonl `
  --miss-ledger data/search/queryLogGold.drill.miss.jsonl `
  --fail-on-error

# local rollback smoke. 실제 운영에서는 rollback 전후 active manifest id 를 기록한다.
uv run python -X utf8 -c "from dartlab.providers.dart.search.fieldIndex import _contentIndexDir; from dartlab.providers.dart.search.localUpdate import rollbackActiveIndex; print(rollbackActiveIndex(baseDir=_contentIndexDir()))"
```

후속 구현 시 추가할 명령 슬롯:

```powershell
uv run python -X utf8 -m dartlab.providers.dart.search.pipeline delta --selfcheck
uv run python -X utf8 -m dartlab.providers.dart.search.pipeline main --selfcheck
uv run python -X utf8 -m dartlab.providers.dart.search.pipeline local-update --smoke
```

---

## 8. 문서 갱신 규칙

코드 구현이 바뀌면 함께 갱신할 문서:

- `mainPlan/search-productization/README.md`
- `03-data-indexing-ops.md`
- `08-completion-design.md`
- `10-production-pipeline-prd.md`
- `11-operator-runbook.md`
- `06-progress-ledger.md`
- Skill OS `engines.search` (본진 구현 후)

갱신 기준:

- 운영 명령이 바뀜.
- source manifest 필드가 바뀜.
- index manifest 필드가 바뀜.
- local updater 정책이 바뀜.
- release gate 기준이 바뀜.
- source owner workflow 가 바뀜.

---

## 9. 운영 인계 기준

운영자가 이 검색 파이프라인을 인계받으려면 다음 세 가지가 문서와 명령으로 확인되어야 한다.

| 인계 항목 | 확인 방법 |
|---|---|
| 현재 source freshness | `dartlab.search.indexInfo()` 의 `sourceDataAsOf`, source manifest |
| 현재 artifact 안전성 | search manifest required files/hash, canary report, local updater smoke |
| 현재 품질 상태 | replacement gate, real/proxy gold 구분, miss ledger open items |

인계 문서에는 반드시 다음을 남긴다.

- 마지막 성공한 source sync run.
- 마지막 성공한 search delta run.
- 마지막 성공한 main compaction run.
- 현재 active manifest id 또는 build id.
- rollback 가능한 이전 manifest id.
- release graduation 여부와 그 근거.

---

## 10. 자가검증 자동화 대상

사람이 매번 눈으로 볼 항목과 자동으로 막아야 하는 항목을 분리한다.

자동 차단:

- required file 누락.
- manifest hash 불일치.
- source count 비정상 급감.
- schema/library incompatible.
- local load smoke 실패.
- canary query 실패.
- no-answer canary false accept.
- result row contract invalidRows 발생.

사람 리뷰:

- query-log gold 라벨링.
- miss ledger failureType 분류.
- 새 source onboarding 승인.
- public surface 최신성 문구 승인.
- release graduation 선언.

자동 차단을 통과해도 사람 리뷰 항목이 비어 있으면 제품 졸업으로 보지 않는다.

---

## 11. 운영 문서 업데이트 체크리스트

다음 변경은 운영 문서 업데이트 없이는 완료로 보지 않는다.

| 변경 | 갱신 대상 |
|---|---|
| source manifest 필드 추가/삭제 | `10`, `11`, `12`, source owner workflow docs |
| catalog key 변경 | `10`, `12`, catalog delta tests |
| search manifest 필드 변경 | `10`, `11`, `08`, local updater tests |
| HF publish 순서 변경 | `10`, `11`, `12` |
| local updater 정책 변경 | `08`, `10`, `11` |
| gate threshold 변경 | `02`, `10`, `11`, `06` |
| source/no-answer canary pack 변경 | `02`, `10`, `11`, `12`, canary tests |
| result row contract 변경 | `02`, `06`, `10`, `11`, `12`, resultContract tests |
| public/local/CLI surface 변경 | `08`, `11`, Skill OS `engines.search` |
| query facet planner 변경 | `02`, `06`, `10`, `11`, `12`, Skill OS `engines.search`, facetPlanner/api tests |
| productization status audit 변경 | `06`, `10`, `11`, `12`, status script tests, workflow smoke tests |
| source workflow catalog step 변경 | `03`, `10`, `11`, `12`, workflow smoke tests |
| bootstrap plan CLI 변경 | `06`, `10`, `11`, `12`, bootstrap plan script tests |
| proof bundle next actions 변경 | `06`, `10`, `11`, `12`, proof bundle script tests |
| cutover state audit 변경 | `06`, `10`, `11`, `12`, `13`, cutover script tests |
| source catalog completeness threshold 변경 | `03`, `10`, `11`, `12`, sourceCatalog/searchCatalog script tests |
| source catalog publish 방식 변경 | `03`, `10`, `11`, `12`, searchCatalog script tests |
| local activation/rollback 정책 변경 | `08`, `10`, `11`, `12`, `localUpdate` tests |
| main compaction 입력 경로 변경 | `03`, `10`, `11`, `12`, searchIndexMain smoke |
| source completeness 정책 변경 | `03`, `10`, `11`, `12`, sourceCatalog/pipeline tests |
| pipeline drill 변경 | `10`, `11`, `12`, workflow smoke tests |
| HF round-trip 검증 변경 | `10`, `11`, `12`, workflow smoke tests, `test_search_hf_roundtrip_script.py` |
| query-log gold hit semantics 변경 | `02`, `06`, `10`, qualityGate tests |
| query-log gold 정규화/라벨링 절차 변경 | `02`, `06`, `10`, `11`, `12`, goldLog tests |

운영 문서는 "나중에 정리"가 아니라 release blocker 다. 특히 `sourceDataAsOf`, `sourceRef`, `answerable` 의미가 바뀌면 사용자에게 보이는 검색 신뢰도 계약이 바뀌므로 같은 변경 단위에서 문서를 갱신한다.

---

## 12. Run Evidence 기록 슬롯

운영 완료는 "workflow 가 성공했다"가 아니라 다음 슬롯이 채워졌을 때만 인정한다.

| 증거 | 기록할 값 | 기록 위치 |
|---|---|---|
| source owner run | workflow name, job, run id, sha, Actions artifact name, source, source manifest path, source manifest hash, `snapshotScope`, row count | 이 문서 또는 `12-pipeline-maintenance-map.md` |
| search delta run | run id, mode(`catalog`/`legacy`), previous/current catalog hash, changed/new/deleted/unchanged count, promoted manifest id | `12-pipeline-maintenance-map.md` |
| HF publish | staging path, current manifest path, fileSources, required files, file hashes, canary result, pointer publish time, `searchHfRoundTrip*.json` artifact | `12-pipeline-maintenance-map.md` |
| remote evidence | `searchRemoteEvidence.{delta,main}.json`, `searchBootstrapPlan.json`, missing source catalogs, missing content manifests, contentIndex fileSources, source manifest set producerRun summaries, 다음 source-owner/Search Main/검증 명령 | `12-pipeline-maintenance-map.md` |
| local update | remote manifest id, local previous manifest id, active manifest id, canary result, rollback window | `12-pipeline-maintenance-map.md` |
| rollback drill | restored manifest id, command, validation result, failure reason if any | `06-progress-ledger.md` 와 `12-pipeline-maintenance-map.md` |
| quality gate | replacement gate profile, canary pack version, query-log gold version, miss ledger version, pass/fail | `06-progress-ledger.md` |
| result contract | queries or results file, total rows, invalid rows, blockers, report path, `searchResultContract.{delta,main}.json` Actions artifact | `06-progress-ledger.md` 와 `12-pipeline-maintenance-map.md` |
| product quality smoke | query, expected stock/source, returned stock/source list, answerable/notAnswerableReason, false accept 여부 | `06-progress-ledger.md` 와 miss ledger |
| productization status | `searchProductizationStatus.{delta,main}.json`, design/ops/release readiness, blocker list | `06-progress-ledger.md` 와 `12-pipeline-maintenance-map.md` |
| proof bundle next actions | `searchProofBundle.json.nextActions.bootstrapPlan`, `searchBootstrapPlan.json`, missing source/tier, action id list | `06-progress-ledger.md` 와 `12-pipeline-maintenance-map.md` |
| cutover state | `searchCutover.{delta,main}.json`, S1/S2/S3/S4 state, defaultReplacement blockers, replacement evidence path, default/scheduled build mode, legacy fallback scope, fail-closed publish 여부 | `06-progress-ledger.md` 와 `12-pipeline-maintenance-map.md` |

실패 run 도 기록한다. 실패 기록에는 실패 source, 차단 지점, active artifact 보존 여부, 다음 조치를 남긴다. 실패가 기록되지 않으면 같은 장애가 반복돼도 품질 개선 루프의 입력이 되지 않는다.

---

## 13. 장기 유지보수 운영 모드

장기 운영은 네 개 루프를 동시에 유지한다.

| 루프 | 주기 | owner | 완료 증거 |
|---|---|---|---|
| source freshness | daily | source workflow owner | source manifest `dataAsOf`, row/files count, source catalog path |
| artifact safety | every publish | search workflow owner | staging path, current manifest pointer, required file hashes, canary report, result contract report |
| local activation | every publish / release | runtime owner | active manifest id, previous manifest id, rollback smoke |
| quality flywheel | weekly/monthly | search quality owner | query-log gold report, miss ledger, canary pack refresh |

운영자가 반복해서 관리해야 하는 것은 mapper 목록이 아니라 위 네 개 루프의 증거다. 새 query miss 는 바로 규칙으로 붙이지 않고 miss ledger 에 남긴다. 반복 유형이 쌓이면 source adapter, facet planner, sourceRef policy, answerability, evidence pack 중 하나의 일반 정책으로 승격한다.

앞으로 source 가 늘어나도 이 운영 모드는 바뀌지 않는다. source owner 는 manifest 와 catalog snapshot 을 만들고, search workflow 는 diff 와 publish 안전성만 책임지며, local runtime 은 검증된 current manifest 만 활성화한다.

---

## 14. 운영 인계 절차

운영 인계는 마지막 성공 run 을 구두로 말하는 절차가 아니다. 아래 순서로 증거를 모아야 한다.

1. source owner run 을 확인한다.
2. HF `dart/searchCatalog/{source}/` inventory 를 확인한다.
3. `Search Index Delta` 또는 `Search Index Main` 의 mode 가 `catalog` 였는지 확인한다.
4. publish evidence artifact 에 `searchHfRoundTrip*.json` 과 `searchResultContract*.json` 이 있는지 확인한다.
5. 로컬에서 `dartlab.search.indexInfo()` 를 실행해 `available`, `compatible`, `sourceDataAsOf`, `nDocsBySource` 를 기록한다.
6. `rollbackActiveIndex()` 또는 운영 rollback drill 결과를 기록한다.
7. real query-log gold 가 충분하지 않으면 release graduation 이 아니라 ops-ready 이전 상태로 남긴다.

인계 산출물:

| 산출물 | 필수 여부 | 설명 |
|---|---|---|
| source inventory | 필수 | source별 manifest path, hash, row/files count |
| contentIndex manifest snapshot | 필수 | current manifest JSON 또는 manifest id |
| round-trip report | 필수 | HF current manifest 를 실제로 받고 activate/rollback 했는지 |
| result contract report | 필수 | invalidRows 0 여부 |
| local indexInfo output | 필수 | 설치자가 실제로 보게 될 freshness/compatibility |
| rollback report | 필수 | 이전 active 로 돌아갈 수 있는지 |
| gold/miss ledger summary | release 때 필수 | 품질 졸업 근거 |

위 산출물이 없으면 "배포는 됐지만 운영 인계는 미완료"로 표시한다.
