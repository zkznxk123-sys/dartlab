# 검색 제품화 준비 — 공시·뉴스 의미검색을 제품 계약으로 승격

상태: 제품화 PRD v0.34 (2026-06-18)
범위: `dartlab.search(...)` 공개계약은 유지하고, 내부 검색·RAG evidence·운영 gate 를 제품 수준으로 승격한다.

---

## 한 줄 결론

**제품화 방향은 새 검색 API 를 만드는 것이 아니라, 기존 `dartlab.search(...)` 안쪽을 large corpus · source isolation · evidence card · query-log gold gate 로 교체하는 것이다.**

실험과 운영 증거는 강하지만, 최신 졸업 기준으로는 아직 제품 졸업이 아니다. 2026-06-16 local HF bootstrap 이후 allFilings, DART panel, EDGAR panel, newsPublic source catalog 와 full/lite contentIndex current manifest, full/lite round-trip, remote evidence audit 는 통과했다. direct-review 106 row userLog/reviewed 품질팩과 replacement evidence 는 과거 S4 배선이 작동함을 보였지만, 2026-06-18 hard-negative gate 추가 뒤에는 release proof 로 충분하지 않다. 최신 current-data pack 은 `.tmp/hf-contentIndex/catalog_snapshot.parquet` 475,549 rows 에서 hard-negative 300행 + noAnswer 60행을 만들었고, metric gate 는 통과했다. 현재 최신 판정은 `designReady=true`, `opsReady=true`, `releaseReady=false` 이며, blocker 는 `realReviewedRows=0/300`, `reviewStatus=candidate`, `goldOrigin=currentDataHardNegative` 이다. 즉 본진 교체/운영 배선은 베타급으로 닫혔고, 베타 제거는 reviewer-approved hard-negative/noAnswer gold 승격 전까지 금지한다.

2026-06-15 demo-ops ceiling run 에서는 로컬 최대에 가까운 301579 docs(allFilings 191827 + panel 104752 + news 5000)를 한 번 로드·인덱싱한 뒤 3 seeds × 100 운영형 질의를 처리했다. 결과는 readyRate 0.9867, filing memoryAnswerReady 0.98, news sourcePrecision10 0.9867, noAnswer falseAcceptRate 0.0, warm query p95 157.9ms, max 173.9ms 였다. 즉 본진 이식 착수 기준은 확보됐고, 릴리즈 졸업만 실제 query-log gold 로 남는다.

---

## 제품 계약

공개 표면은 그대로 간다.

```python
import dartlab

dartlab.search("유상증자")
dartlab.search("반도체 HBM 투자", scope="content")
dartlab.search("공시 말고 뉴스로 환율 기사", scope="news")
dartlab.search("대표이사 변경", corp="005930", start="20240101")
```

새 sibling public call 을 만들지 않는다. RAG, sourceRef set, evidence pack, DuckDB catalog, query planner 는 내부 구현이다. 외부 사용자는 검색 결과와 `dataAsOf`, `source`, `sourceRef`, `dartUrl`/article URL 만 본다.

---

## 문서 지도

1. [00-product-vision.md](00-product-vision.md) — 무엇을 제품으로 만들고, 무엇을 졸업 증거로 볼지.
2. [01-architecture-contract.md](01-architecture-contract.md) — DuckDB catalog, CSR main/delta, source isolation, RAG memory-card 의 책임 분리.
3. [02-quality-gates.md](02-quality-gates.md) — 제품화 gate, 실제 query-log gold, multi-seed random 압박 기준.
4. [03-data-indexing-ops.md](03-data-indexing-ops.md) — allFilings, panel parquet, news 수집·증분·재색인 운영.
5. [04-rag-memory-contract.md](04-rag-memory-contract.md) — LLM 이 자기 지식처럼 쓰는 evidence card 계약.
6. [05-scope-phasing-guardrails.md](05-scope-phasing-guardrails.md) — Phase, kill list, 착수·중단 기준.
7. [06-progress-ledger.md](06-progress-ledger.md) — 현재 실측, 결정, NEXT.
8. [07-specialist-review.md](07-specialist-review.md) — runtime, HF 증분, surface, 품질 gate 전문 검토 결론.
9. [08-completion-design.md](08-completion-design.md) — HF 증분과 local/public/library 완성 설계.
10. [09-innovation-roadmap.md](09-innovation-roadmap.md) — 빠른 의미검색, 덕지덕지 방지, 운영 혁신 방향.
11. [10-production-pipeline-prd.md](10-production-pipeline-prd.md) — 본진 교체, HF source/search manifest, delta, local auto update 전체 PRD.
12. [11-operator-runbook.md](11-operator-runbook.md) — 일일·주간·월간 운영, selfcheck, 장애 대응, 배포 체크리스트, 운영 인계 기준.
13. [12-pipeline-maintenance-map.md](12-pipeline-maintenance-map.md) — 실제 GitHub workflow, HF artifact, local updater, 유지보수 캘린더, 본진 이관 작업표.
14. [13-cutover-contract.md](13-cutover-contract.md) — designReady/opsReady/releaseReady/defaultReplacement cutover 계약.

---

## 제품화 척추

- `dartlab.search(...)` 단일 공개계약 유지.
- DuckDB 는 런타임 검색 엔진이 아니라 수집 카탈로그·변경 감지·증분 export 레이어.
- 기본 랭킹은 본문 content R* sparse CSR main+delta. 제목/보고서명/section title 은 보조 anchor 이고, dense embedding 은 전역 랭킹이 아니라 evidence sidecar 후보로만.
- source intent 는 soft preference 가 아니라 hard isolation. `공시 말고 뉴스`, `뉴스 말고 공시`는 fallback 하지 않는다.
- LLM 용 지식화는 전체 본문 주입이 아니라 `sourceRef set + snippet + field card + dataAsOf` memory-card 반복 주입.
- 관계형 의미 컨텍스트는 본문 랭커가 아니라 graph catalog sidecar 로 붙인다. graph catalog 가 있으면 `dartlab.search(...)` 결과 row 에 optional `entityCards` 가 생기며 peer/stage/credit weak-axis 를 LLM memory-card 에 동봉한다. 표준 산출물은 contentIndex 와 동거하는 `entityGraphCatalog.parquet` 이고, catalog 부재 시 search 는 기존처럼 동작한다.
- 제품 졸업은 실제 query-log gold 100~300 rows 와 reviewer-approved hard-negative 300 rows 통과 후에만. curatedDraft, stratifiedSynthetic, current-data candidate 는 압박 실험일 뿐이다. direct-review 106 row userLog/reviewed 품질팩은 운영 배선의 첫 근거지만, 새 hard-negative gate 뒤에는 베타 제거 증거가 아니다.
- 본진 이식 단계를 넘어 현재 checkout 은 default replacement 배선을 한 번 증명했다. 최신 제품 판정은 `opsReady=true`, `releaseReady=false` 이므로 운영 루프는 Actions proof 재확인, query-log gold 확대, hard-negative 300행 review 승격을 계속한다.
- HF 증분은 source별 `doc_key/text_hash` catalog diff 로 처리한다. allFilings, panel, news 정상 갱신은 delta CSR 로 흡수하고, full rebuild 는 schema/tokenizer/normalizer/sourceRef 의미 변경 때만 한다.
- 혁신의 핵심은 typed sourceRef graph, runtime intent kernel, sparse-first hybrid, incremental knowledge fabric, quality flywheel 이다. 새 API, prebuild intent dictionary, 계속 관리해야 하는 특수 mapper 를 늘리는 방식이 아니다.
- 운영 완성의 핵심은 "장애 없음" 이 아니라 "장애가 나도 나쁜 artifact 를 publish/activate 하지 않음" 이다. HF upload 는 local manifest/hash/canary selfcheck 후 staging candidate 를 만들고, candidate 검증이 끝난 뒤 current manifest pointer 를 promote 하는 순서로 간다. current manifest 는 `fileSources` 로 staging 파일을 가리키며, delta publish 는 previous manifest 의 main `fileSources` 를 보존한다. remote evidence 는 `requiredFiles` 의 fileSources 대상 존재와 contentIndex 가 참조하는 `source_manifest_set.json` 내부 source별 `producerRun` 까지 검사하고, local update 는 staged download 후 atomic swap 과 previous active rollback helper 로 간다.
- publish-before-gate 문제를 닫기 위한 코드/워크플로 계약도 들어갔다. `publishContentIndexFiles(..., promoteCurrent=False)` 또는 `DARTLAB_SEARCH_PROMOTE_CURRENT=0` 은 current pointer 를 바꾸지 않고 staging candidate manifest 만 올리고, `verifySearchHfRoundTrip.py --manifest-repo-path` 로 그 candidate 를 직접 activate/rollback 검증한다. Search Main/Delta workflow 는 candidate round-trip, result contract, canary, optional real quality gate 이후에만 `promoteSearchCandidate.py` 로 current pointer 를 바꾼다. release gate 에서는 `buildSearchReplacementEvidence.py --fail-on-incomplete` 와 `evaluateSearchCutover.py --fail-on-default-not-ready` 를 실행하므로 S4 증거가 깨지면 Actions 가 실패한다. direct-review replacement evidence 는 `failClosedPublish=true` 를 충족했고, 새 Actions run 은 같은 artifact 를 재생성해야 한다.
- 본진 교체는 single-engine replacement 로 간다. 장기 shadow/dual search 를 제품 기본값으로 두지 않는다.
- 실제 운영 연결은 `12-pipeline-maintenance-map.md` 를 따른다. `originalSync.yml`, `newsArchiveSync.yml`, `edgarSync.yml`, `searchIndexDelta.yml`, `searchIndexMain.yml` 의 산출물과 search 책임 경계가 그 문서의 기준이다.
- PRD급 판단은 `10-production-pipeline-prd.md` 의 P0/P1/P2 요구사항과 이관 승인 매트릭스를 따른다. 본진 이식 가능, 기본값 전환 가능, release graduation 가능은 서로 다른 단계다.
- 운영 인계와 장기 유지보수는 `11-operator-runbook.md` 와 `12-pipeline-maintenance-map.md` 의 source freshness, active manifest, rollback manifest, miss ledger, 문서-코드 동기화 규칙을 따른다.
- 앞으로의 데이터 증가는 `03-data-indexing-ops.md`, `10-production-pipeline-prd.md`, `11-operator-runbook.md`, `12-pipeline-maintenance-map.md` 를 함께 갱신하는 방식으로 관리한다. allFilings, DART panel, EDGAR panel, public news, GDELT 후보, private/local news 는 같은 검색 표면에 섞일 수 있어도 source manifest/sourceRef/canary/freshness 계약 없이는 제품 corpus 에 들어가지 않는다.
- 본진 1차 구현은 source intent hard isolation, missing/facet/stale answerability, row/bounded-chunk evidence, memory card, local active manifest 비교, source owner searchCatalog 생성, search delta/main catalog mode 준비까지 들어갔다.
- 운영 문서의 SSOT 는 `10/11/12` 다. pipeline, manifest, HF staging upload/current manifest pointer publish, local active swap, rollback, 유지보수 캘린더, 문서 업데이트 규칙은 이 세 문서를 같이 갱신하지 않으면 완료로 보지 않는다.
- 운영 증거는 말로 남기지 않는다. 실제 Actions run, HF artifact path, local active manifest, rollback 가능한 previous manifest, gold/miss ledger 상태는 `11-operator-runbook.md` 의 run evidence slot 과 `12-pipeline-maintenance-map.md` 의 증거 원장에 기록해야 한다.
- 제품 운영 인계는 code merge 가 아니라 proof bundle 이다. source catalog inventory, contentIndex manifest pointer, HF round-trip report, result contract report, local `indexInfo()` smoke, rollback evidence, query-log gold/miss ledger 상태가 함께 남아야 한다. `.github/scripts/search/buildSearchProofBundle.py` 는 이 report 들을 한 디렉터리에 모아 `searchProofBundle.json` 과 `searchProductizationStatus.json` 을 만들며, searchIndexDelta/Main workflow 는 이 bundle 을 evidence artifact 에 포함한다. 원격 source/content blocker 가 있으면 같은 bundle 안에 `searchBootstrapPlan.json` 과 `nextActions.bootstrapPlan` 도 남겨 다음 실행 순서를 사람 기억에 맡기지 않는다.
- 본진 교체 기준은 `13-cutover-contract.md` 의 상태 기계다. `designReady=true` 는 코드/설계가 본진 이식 가능하다는 뜻이고, `opsReady=true` 는 기본값 교체 가능, `releaseReady=true` 는 실제 query-log gold 와 reviewer-approved hard-negative gold 기준 제품 졸업 가능이라는 뜻이다.
- `evaluateSearchCutover.py` 는 proof bundle 을 `S1/S2/S3/S4` 상태로 다시 판정한다. `S4 defaultReplacement` 는 `opsReady=true` 만으로 주지 않고, `defaultBuildMode=catalog`, `scheduledBuildMode=catalog`, legacy fallback 운영자 전용, fail-closed publish 정책, active/previous manifest, rollback command, rollback 검증, run evidence 기록, surface naming review 를 담은 replacement evidence 가 있어야 한다.
- source catalog 는 HF publish 만으로 끝내지 않는다. source owner workflows 는 `search-catalog-{source}-{job}-{run}` Actions artifact 를 남기고, source manifest 는 `producerRun.workflow/job/runId/sha/artifactName` 을 보존한다. search main/delta 는 `source_manifest_set.json` 을 full/lite contentIndex `requiredFiles` 에 포함해 어떤 source snapshot set 과 어떤 source owner run 으로 만든 인덱스인지 증거화한다.
- query-log gold/miss ledger 는 본진 게이트로 들어갔다. `DARTLAB_SEARCH_QUERY_LOG` 를 켠 `dartlab.search(...)` 는 raw 후보 row 를 남기고, `goldLog.py`, `prepareSearchGold.py`, `qualityGate.py`, `evaluateSearchGold.py` 가 raw log + reviewer label 을 canonical real gold JSONL 로 만들며 real/proxy gold 를 분리해 release eligibility 를 자동 판정한다. raw 후보는 release 증거가 아니며, 실제 reviewed real gold rows 확보는 아직 남아 있다.
- `evaluateSearchProductizationStatus.py` 는 quality report 의 `releaseEligible=true` 만 믿지 않는다. `realReviewedRows>=100`, `goldOriginCounts`, `reviewStatusCounts`, filing/news/noAnswer/edgar coverage 를 다시 검사하고 synthetic/proxy drill rows 는 release blocker 로 본다.
- query-log gold toolchain drill 도 workflow evidence 로 남긴다. `runSearchQualityDrill.py` 는 raw log, reviewer label template, canonical gold, quality report, miss ledger 생성 경로가 깨지지 않았는지 확인하지만 `goldOrigin=drillSynthetic`, `reviewStatus=drillReviewed`, `releaseEvidence=false` 이며 real query-log gold 를 대체하지 않는다.
- source/no-answer canary gate 도 본진 게이트로 들어갔다. `artifactCanary.py`, `canaryPack.py`, `evaluateSearchCanary.py` 가 artifact 기반 source canary pack 생성, source isolation, source coverage, answerable positive, no-answer false accept 를 publish/local activation 전에 빠르게 차단한다. news 는 최신 단일 기사 row sourceRef 가 아니라 `news` lane smoke 로 검사하고, 특정 기사 sourceRef 품질은 real query-log gold/miss ledger 에서 다룬다.
- 결과 row 계약 감사도 본진 게이트로 들어갔다. `resultContract.py` 와 `evaluateSearchResultContract.py` 는 실제 검색 결과 또는 precomputed results 에 대해 `source/sourceRef/dataAsOf/snippet/answerable/fieldCards` 와 card evidence 를 검사하고, searchIndexDelta/Main workflow 는 `searchResultContract.{delta,main}.json` 을 evidence artifact 로 업로드한다. 실제 full-source HF artifact 에서 이 report 를 확인하는 것이 다음 운영 증거다.
- graph catalog enrichment 의 1차 본진 연결이 들어갔다. `entityGraph.py` 는 `DARTLAB_SEARCH_ENTITY_GRAPH_CATALOG` 또는 active contentIndex directory 의 `entityGraphCatalog.parquet`/`graph_catalog.parquet` 를 읽어 검색 row 에 `entityCards` 를 붙인다. `entityGraphCatalog.py` 는 explicit catalog copy 또는 `DARTLAB_SEARCH_ENTITY_GRAPH_BUILD=1` offline build 를 제공하고, `entityGraphCatalog.parquet` 는 manifest `requiredFiles/fileHashes/entityGraphCatalog` summary, main/delta publish list, pull list 에 포함되어 기존 contentIndex staging/pointer/local activation 경로를 탄다. 요청 경로에서 live `Company.industry()`/`credit()` traversal 은 하지 않는다.
- 원격 evidence audit 도 들어갔다. `checkSearchRemoteEvidence.py` 는 HF source catalog 와 contentIndex current manifest 존재 여부뿐 아니라 manifest `fileSources` 로 실제 `source_manifest_set.json` 을 열어 source별 `producerRun` 누락까지 JSON 으로 남기고, searchIndexDelta/Main workflow 는 `searchRemoteEvidence.{delta,main}.json` 을 evidence artifact 에 포함한다.
- local end-to-end pipeline drill 도 들어갔다. `runSearchPipelineDrill.py` 가 synthetic raw source parquet 에서 source catalog 4종을 만들고, `prepareSearchDeltaInputs.py` 로 `source_manifest_set.json` 과 catalog-mode current catalog 를 freeze 한 뒤 contentIndex build, staging upload/current manifest pointer publish, local activation, rollback 을 검증한다. searchIndexDelta/Main preflight 에서 실행되며 실제 HF round-trip 증거는 별도다.
- 실제 HF round-trip 증거 수집 경로도 배선했고 local bootstrap 으로 1회 실증했다. `verifySearchHfRoundTrip.py` 는 HF current manifest 또는 explicit staged candidate manifest 를 temp/local contentIndex 에 내려받아 activate/rollback 을 검증하고, searchIndexDelta/Main workflow 는 current promote 전에 full/lite candidate evidence JSON 을 각각 artifact 로 업로드한다. `evaluateSearchProductizationStatus.py` 는 두 tier round-trip report 가 모두 없으면 opsReady 로 보지 않는다.
- local activation 은 schema compatibility 와 `sourceCanaryPack` 까지 차단한다. source/sourceRef/no-answer canary 가 깨지거나 schema 가 현재 라이브러리와 맞지 않으면 active pointer 를 바꾸지 않는다.
- source catalog 생성도 빈 full snapshot 을 통과시키지 않는다. `buildSearchCatalog.py` 기본 completeness threshold 와 manifest `completenessCheck` 가 source owner 단계에서 빈 files/rows/catalogRows 를 차단한다.
- source catalog 는 이제 canonical full 과 source-owner 증분 publish 를 분리한다. `searchIndexMain.yml` raw full pull fallback 은 HF 전체 raw source 에서 canonical source catalog 4종을 부트스트랩한 뒤 같은 run 에서 `prepareSearchDeltaInputs.py` 를 다시 실행해 catalog-mode main input 으로 freeze 한다. HF raw pull quota 가 첫 bootstrap 을 막는 경우에는 source owner workflows 를 `workflow_dispatch` + `search_catalog_bootstrap=true` 로 명시 실행해 source별 높은 하한을 만족하는 첫 catalog 를 만들 수 있다. 평소 source owner workflows 는 직전 HF source manifest 가 있을 때만 `--compare-remote-manifest --require-previous-manifest` 로 이전 full 대비 files/rows/catalogRows 급락이 없는 경우 publish 한다. 즉 partial runner tree 가 `snapshotScope=full` 로 승격되는 길은 제품 계약 위반이자 hard fail 이다.
- source/search 원격 증거가 비어 있으면 운영자는 임의로 순서를 조합하지 않는다. `planSearchBootstrap.py` 가 `searchRemoteEvidence` 또는 live audit 를 읽어 source-owner `search_catalog_bootstrap=true` dispatch, catalog-mode `searchIndexMain.yml`, remote evidence/proof bundle 검증 명령을 `searchBootstrapPlan.json` 으로 산출한다. `buildSearchProofBundle.py` 도 원격 source/content blocker 가 있으면 이 plan 을 bundle 에 포함한다. 이 plan CLI 자체는 GitHub/HF 를 변경하지 않는 비파괴 단계다.
- HF 429 완화를 위해 source catalog publish 와 contentIndex manifest-pointer publish 모두 단일 `create_commit` batch 경로를 쓴다. 실제 효과는 다음 source/search Actions run 의 원격 evidence 로 확인한다.
- delta 운영의 얇은 지점도 차단했다. `pullSearchCurrentIndex.py` 가 current manifest pointer 를 따라 기존 full main required files 와 `previous_manifest.json` 을 복원하고, `buildSearchDelta.py` 는 previous `fileSources` 를 보존한 current pointer manifest 를 publish 한다. 따라서 delta 가 새 파일만 올리며 main 경로를 잃는 배포는 테스트와 ops gate 에서 실패한다.
- 본진 품질 수정도 들어갔다. `dartlab.search(..., topK=N)` 는 `limit` alias 로 동작하고, query 본문 회사명은 `ListingResolver` 기반 stockCode facet 으로 랭킹 전에 마스크한다. `"삼성전자 대표이사 변경"` 이 삼성 계열사로 새던 문제는 regression/live smoke 로 차단했다.
- 제품화 상태 감사도 들어갔다. `evaluateSearchProductizationStatus.py` 는 remote evidence, source owner run lineage, local indexInfo, HF round-trip, result contract, canary, quality report 를 모아 `designReady/opsReady/releaseReady` 와 blocker 를 산출하고, searchIndexDelta/Main workflow 는 기본 `ops` gate 에서 `--fail-on-ops-not-ready`, release 후보 gate 에서 real query-log gold 와 `--fail-on-release-not-ready` 로 hard fail 한다. source catalog manifest 에 `producerRun` 이 없거나 contentIndex `source_manifest_set.json` 내부 source별 `producerRun` 이 비면 S2 opsReady 를 주지 않는다.
- canary gate 는 manifest 기반으로도 돈다. `evaluateSearchCanary.py --manifest data/dart/contentIndex/manifest.json` 이 artifact 에 자동 주입된 `sourceCanaryPack` 을 평가하고 `searchCanary.{delta,main}.json` 으로 남긴다. 상태 감사는 canary 가 valid 여도 allFilings/panel/EDGAR/news source coverage 가 빠지면 ops-ready 로 보지 않는다.
- direct-review 106행 기준 proof bundle 은 historical release-ready 였다. 최신 기준은 hard-negative 300행을 추가하므로 이 증거는 운영 배선/rollback/fail-closed proof 로만 남긴다.
- 최신 hard-negative+noAnswer current-data 360행 실측은 `.tmp/search-hard-negative/qualityReport.hardNegative.withNoAnswer.eventOnly.candidate.json` 기준 `overallReadyRate=0.9806`, `exactDocHit10=0.9667`, `hardNegativeRows=300`, `hardNegativeWinRate=0.9667`, `noAnswerFalseAcceptRate=0.0`, `forbiddenTop3Rate=0.0`, `forbiddenTop10Rate=0.0`, `sourceIntentLeakRate=0.0`, `constraintViolationRate=0.0` 으로 metric gate 는 통과했다. 하지만 `realReviewedRows=0/300`, `proxyGoldRows=360`, `unreviewedGoldRows=360` 이라 `searchProductizationStatus` 는 `releaseReady=false` 다.
- 2026-06-16 HF full-source catalog-mode cycle 은 운영 배선 기준으로 닫혔다. sourceCatalog 4종(allFilings/panel/EDGAR/news), 462,947-doc current catalog, catalog-mode full rebuild, catalog-mode lite rebuild, HF stage/round-trip/promote, canary, result contract, status audit 가 통과했다.
- 남은 핵심은 reviewer-approved hard-negative 300행 + noAnswer gold 승격, 실제 GitHub Actions scheduled run artifact 재확인, lite tier 크기 최적화다. stale source 판정과 bounded chunk evidence 는 1차 runtime 정책으로 들어갔다.
