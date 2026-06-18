# 06. 진행 원장 — 결정 · 실측 · NEXT

상태: v1.29 (2026-06-18)
범위: 검색 제품화 준비 결정과 다음 작업.

---

## 1. 확정 결정

1. 공개계약은 `dartlab.search(...)` 유지. 새 public call 은 만들지 않는다.
2. DuckDB 는 catalog/export/diff 레이어로만 쓴다.
3. 기본 검색은 R* sparse CSR main+delta.
4. dense embedding 은 evidence sidecar 후보로만 둔다.
5. source intent 는 hard isolation.
6. RAG memory 는 전체 문서 주입이 아니라 sourceRef set 기반 memory-card.
7. 제품 졸업은 실제 query-log gold 통과 후에만 한다. 2026-06-16 direct-review 106 row userLog/reviewed 품질팩은 첫 release gate 를 통과했다.
8. 전문 검토 결론: 본진 이식 착수 단계를 넘겨 현재 checkout 은 S4 defaultReplacement 증거까지 확보했다. 실제 Actions 재실행 증거와 품질 flywheel 은 운영 루프로 계속 유지한다.
9. HF 증분은 source별 catalog diff 로 간다. allFilings, panel, news 정상 갱신은 delta CSR 이며, full rebuild 는 schema/tokenizer/normalizer/sourceRef 의미 변경 때만 한다.
10. 혁신 방향은 typed sourceRef graph, runtime intent kernel, sparse-first hybrid, incremental knowledge fabric, quality flywheel 로 묶는다. prebuild intent dictionary, 덕지덕지 mapper, 새 public API 는 금지한다.
11. 제품 파이프라인은 `10-production-pipeline-prd.md` 를 기준으로 한다. source manifest, catalog snapshot, search index manifest, staging promote, local atomic swap 이 운영 계약이다.
12. 운영 런북은 `11-operator-runbook.md` 를 기준으로 한다. 일일 source freshness, 주간 miss ledger, 월간 main compaction 을 유지보수 루프로 둔다.
13. 실제 운영 연결표는 `12-pipeline-maintenance-map.md` 를 기준으로 한다. `originalSync.yml`, `newsArchiveSync.yml`, `edgarSync.yml`, `gdeltSync.yml`, `searchIndexDelta.yml`, `searchIndexMain.yml` 의 책임과 search 소비 경계를 문서화했다.
14. 본진 이식은 1차 착수했다. result schema, source manifest, catalog diff, catalog delta dry-run, index manifest/indexInfo, manifest 기반 local staged download/active pointer, Korean corp ticker guard 는 `src/dartlab/providers/dart/search` 에 들어갔고 focused tests 로 검증했다.
15. PRD급 파이프라인 문서는 `10-production-pipeline-prd.md` v0.27 를 기준으로 한다. P0/P1/P2 요구사항, 이관 승인 매트릭스, 장기 유지보수 모델, 재색인 기준, PRD/구현 완료 조건, 운영 문서 동기화 요구사항, 실제 구현/운영 증거 대기 상태, source owner `producerRun` lineage 계약, previous-manifest drop guard, bootstrap plan/proof bundle next actions 를 추가했다.
16. 운영 문서는 `11-operator-runbook.md` v1.13 와 `12-pipeline-maintenance-map.md` v1.15 를 기준으로 한다. 운영 인계 기준, 자가검증 자동화 대상, 문서 업데이트 체크리스트, 장기 유지보수 운영 모드, 본진 이관 작업 목록, 유지보수 위험 목록, canonical source catalog bootstrap, source-owner guarded update, sourceCatalog/search delta/local updater 실제 연결표, 향후 source 확장 계약을 추가했다.
17. source intent hard isolation 과 answerability 는 1차 본진 모듈로 들어갔다. `sourceIntent.py` 는 뉴스/공시 source family 를 일반 규칙으로 판정하고, `fieldIndex.py` / `unified.py` 는 source mask 를 랭킹 전에 적용한다. `answerability.py` 는 source mismatch, missing sourceRef, missing snippet/dataAsOf 를 `notAnswerableReason` 으로 분리한다.
18. row-level evidence card 와 memory card 도 1차 본진 모듈로 들어갔다. `evidencePack.py` 는 sourceRef, source, company/report/section/date/url/snippet 카드에 짧은 evidence 를 붙이고, `memoryCard.py` 는 answerable row 의 sourceRef set 과 card set 을 LLM turn 에 넘길 수 있는 형태로 만든다.
19. facet no-answer 와 bounded chunk evidence 도 1차 본진 모듈로 들어갔다. `facetPlanner.py` 는 receipt/date/report/company facets 를 추출하고, `answerability.py` 는 facet mismatch 를 `facetMismatch:*` reason 으로 내린다. `fieldIndex.py` 는 `evidenceText` 를 bounded 메타로 보존하고, `evidencePack.py` 는 query-focused chunk card 를 붙인다.
20. local update 는 HF manifest 를 받은 뒤 active manifest 와 비교한다. 같은 manifest 또는 더 오래된 manifest 는 required files 를 다 받기 전에 `skipped=notNewer` 로 전환하지 않는다.
21. `searchIndexDelta.yml` 과 `buildSearchDelta.py` 는 catalog 를 기본 모드로 쓴다. legacy 는 운영자가 명시 dispatch 할 때만 쓰는 예외 경로이며, scheduled/default run 은 all-source catalog delta path 를 타야 한다.
22. source owner workflow 가 search source manifest/catalog snapshot 을 만들 수 있는 1차 배선을 추가했다. `sourceCatalog.py` 와 `buildSearchCatalog.py` 가 parquet 에서 `{source}.source_manifest.json` 과 `{source}.catalog_snapshot.parquet` 를 만들고 HF `dart/searchCatalog/{source}/` 로 업로드한다. `originalSync.yml`, `newsArchiveSync.yml`, `edgarSync.yml` 에 allFilings/dartPanel/edgarPanel/newsPublic 생성 step 이 들어갔다.
23. `searchIndexDelta.yml` scheduled path 는 HF `dart/searchCatalog/**` 와 직전 `dart/contentIndex/catalog_snapshot.parquet` 를 받아 `prepareSearchDeltaInputs.py` 로 catalog mode env 를 준비한다. catalog artifacts 가 없으면 legacy delta mode 를 유지한다. 실제 GitHub Actions run 증거는 아직 없으므로 운영 완성은 다음 run 확인 후 판단한다.
24. `buildSearchMain.py`, `buildSearchDelta.py`, `pushContentIndex()` 는 `publishIndex.py` 를 통해 local manifest/hash/canary selfcheck 통과 후 HF `_staging/{runId}` 업로드와 manifest pointer publish 를 사용한다. Search Main/Delta 운영 경로는 `promoteCurrent=0` staged candidate 를 먼저 만들고, candidate round-trip/result contract/canary/quality gate 통과 후 `promoteSearchCandidate.py` 가 current pointer 를 바꾸는 fail-closed 순서로 고정한다. 운영 증거는 실제 HF Actions run 의 candidate 검증, promote, rollback drill 이 남아 있다.
25. `searchIndexMain.yml` 은 source catalog snapshot 이 준비되면 raw HF pull 을 건너뛰고 `buildSearchMain.py` 의 catalog compaction 경로를 사용한다. catalog 가 없으면 raw HF folders pull + `rebuildContent(...)` full/lite rebuild 로 fallback 하되, 같은 run 에서 allFilings/dartPanel/edgarPanel/newsPublic canonical source catalog 를 `searchIndexMain.full-pull` producer 로 publish 하고 `prepareSearchDeltaInputs.py` 를 다시 실행해 catalog-mode main input 으로 freeze 한다. 실제 Actions run 증거는 아직 필요하다.
26. source catalog 는 목표상 full snapshot 이어야 한다. `buildSearchCatalog.py` 는 `snapshotScope=full|partial` 을 manifest 에 쓰고, `prepareSearchDeltaInputs.py` 는 expected source set 과 full snapshot 을 만족할 때만 catalog mode env 를 쓴다. `pipeline.py` 는 expected source 누락, partial snapshot, source row count 급감을 invalid 로 처리한다. source owner workflows 는 직전 HF full manifest 를 요구하고 files/rows/catalogRows 급락을 차단한다. 실제 Actions run 증거는 아직 필요하다.
27. stale source answerability 는 1차 runtime 정책으로 들어갔다. `facetPlanner.py` 는 최신/최근/current/latest 성격의 질의를 `freshnessRequired` 로 표시하고, `answerability.py` 는 source별 허용 일수를 넘긴 결과를 `staleSource` 로 내린다.
28. 운영 증거 기록 계약을 문서화했다. 실제 source owner run, search delta run, HF publish, local activation, rollback drill, quality gate 증거는 `11-operator-runbook.md` 의 Run Evidence 기록 슬롯과 `12-pipeline-maintenance-map.md` 의 운영 증거 원장에 append 해야 한다.
29. query-log gold/miss ledger 게이트는 1차 본진 모듈로 들어갔다. `qualityGate.py` 는 real/proxy/review status, readyRate, docHit10, memoryCitationTop3Exact, newsSourcePrecision10, noAnswer falseAcceptRate, release blockers 를 산출하고, `evaluateSearchGold.py` 는 quality report 와 miss ledger 를 만든다.
30. publish 전 artifact selfcheck 도 `publishIndex.py` 에 들어갔다. `preflightContentIndexPublish()` 는 `manifest.json` 의 required files/hash 와 optional canary 를 로컬에서 검증하고, 실패하면 HF upload 전에 차단한다.
31. local rollback helper 도 `localUpdate.py` 에 들어갔다. active pointer 는 이전 active dir 를 보존하고, `rollbackActiveIndex()` 는 rollback target selfcheck 통과 시에만 pointer 를 되돌린다.
32. source/no-answer canary gate 도 1차 본진 모듈로 들어갔다. `canaryPack.py` 는 expected source/sourceRef/no-answer trap 을 평가하고, `evaluateSearchCanary.py` 는 실제 search 또는 precomputed result 로 canary report 를 만든다.
33. Skill OS `engines.search` 와 `engines.search.disclosureSearch` 는 본진 product search 계약에 맞춰 갱신했다. 검색 표면은 본문 검색, sourceRef/dataAsOf/answerable, hard isolation, canary/gold gate 를 기준으로 설명한다.
34. local end-to-end pipeline drill 도 추가했다. `runSearchPipelineDrill.py` 는 synthetic raw allFilings/dartPanel/edgarPanel/newsPublic parquet 에서 source catalog 와 `source_manifest_set.json` 을 만든 뒤 catalog diff, BM25 artifact build, staging upload/current manifest pointer publish, local staged activation, rollback 을 한 번에 검증한다. 실제 HF round-trip 증거는 아니지만 hfPipeline/localUpdater smoke 의 로컬 재현 가능한 게이트다.
35. local activation selfcheck 는 schema compatibility 와 manifest 내 `sourceCanaryPack` 까지 본다. `validateSearchManifest(..., codeSchemaVersion=...)` 가 schema 불일치를 차단하고, `localUpdate.py` 는 expected source/sourceRef/no-answer trap canary 를 active pointer 전환 전에 평가한다.
36. `searchIndexDelta.yml` 의 manual env override 버그를 막았다. `prepareSearchDeltaInputs.py` 가 쓴 `GITHUB_ENV` 값을 build step 의 빈 `env:` 가 덮지 않도록 manual catalog inputs 는 별도 step 에서만 `GITHUB_ENV` 로 쓴다.
37. expected source catalog 는 빈 full snapshot 으로 통과하지 못한다. `planCatalogDelta()` 는 expected source 의 `totalRows <= 0` 또는 current catalog row 0 을 invalid 로 처리한다.
38. query-log gold hit 는 `answerable=True` 결과만 인정한다. sourceRef 가 맞아도 `answerable=False` 인 row 는 `docHit10`/`memoryCitationTop3Exact` hit 가 아니다.
39. contentIndex publish 는 current path 에 개별 artifact 파일을 직접 overwrite 하지 않는 manifest pointer 방식으로 전환했다. 실제 files 는 `_staging/{runId}` 에 있고 current `manifest.json` 이 `fileSources` 로 그 staging files 를 가리킨다. local updater 는 `fileSources` 를 따라 active staging dir 로 내려받고, rollback window 동안 이전 current 파일 삭제는 하지 않는다.
40. EDGAR freshness 는 accession 문자열에서 추정하지 않는다. EDGAR panel parquet 에 `filing_date`/`date`/`sourceDataAsOf` 류 원천 날짜 컬럼이 있으면 `rcept_dt`/`sourceDataAsOf` 로 보존하고, 없으면 `period=YYYYQn` 을 분기말 `YYYYMMDD` 로 정규화해 `sourceDataAsOf` 로 쓴다. 기존 local meta 는 period 를 보존하지 않아 한때 EDGAR freshness blocker 가 있었고, 77번 live proof bundle 에서 `edgar-panel:20260630` 으로 해소됐다.
41. 실제 HF manifest round-trip 검증 CLI 를 추가했다. `verifySearchHfRoundTrip.py` 는 HF current manifest 또는 explicit staged candidate manifest 를 내려받아 temp/local contentIndex 에 activate 하고 rollback 까지 검증한다. `searchIndexDelta.yml` 과 `searchIndexMain.yml` 은 current promote 전에 candidate manifest 를 이 smoke 로 검증하고 evidence JSON 을 artifact 로 업로드한다. 실제 run 증거는 다음 Actions run 에서 채워야 한다.
42. 초기 HF `eddmpython/dartlab-data` 에는 `dart/contentIndex/manifest.json` 과 `dart/contentIndex/lite/manifest.json` 이 없었다. 2026-06-16 local bootstrap 에서 full/lite staged candidate 를 검증한 뒤 current manifest pointer 를 승격해 이 blocker 는 해소했다.
43. artifact 기반 source/no-answer canary pack 을 manifest 에 자동 주입한다. `artifactCanary.py` 가 `main_meta.parquet` 에서 source별 대표 row 와 no-answer trap 을 만들고, `writeIndexManifest()` 가 `sourceCanaryPack`/`canaryPackVersion` 을 기록한다. publish preflight 와 local activation 은 이 pack 을 실제 BM25 artifact 에 대해 평가한다.
44. 초기 HF `eddmpython/dartlab-data` 에는 `dart/searchCatalog/{allFilings,dartPanel,edgarPanel,newsPublic}/` 의 source manifest/catalog snapshot 이 없었다. 2026-06-16 local HF bootstrap 으로 4개 source manifest/catalog snapshot 을 업로드했고, remote evidence audit 가 full snapshot 과 `producerRun` 을 확인했다.
45. 운영 문서 업데이트 계약을 명시했다. 앞으로 source/workflow/manifest/local activation/quality gate/search surface 의미가 바뀌면 `03`, `08`, `10`, `11`, `12`, `02`, `06`, Skill OS `engines.search` 중 해당 문서를 같은 변경 단위에서 갱신해야 운영 완료로 본다.
46. 실제 query-log gold 저장 위치와 운영 라벨링 절차를 코드/문서로 고정했다. raw log 는 `data/search/queryLogRaw.jsonl`, reviewer labels 는 `data/search/queryLogLabels.reviewed.jsonl`, canonical release gate 입력은 `data/search/queryLogGold.real.jsonl`, summary 는 `data/search/queryLogGold.summary.json` 으로 둔다. `goldLog.py` 와 `prepareSearchGold.py` 가 raw+label merge, sourceRef 필수 검증, real/reviewed/release coverage summary 를 만든다.
47. source catalog full snapshot 빈 입력 차단을 코드화했다. `buildSearchCatalog.py` 는 기본 `--min-files 1 --min-rows 1 --min-catalog-rows 1` 로 동작하고, `sourceCatalog.py` 는 `completenessCheck` 를 manifest 에 기록하며 full snapshot 의 빈 files/rows/catalogRows 를 실패시킨다. 실제 Actions run 의 row/files count 증거는 아직 남아 있다.
48. result contract audit 를 제품 표면 gate 로 추가했다. `resultContract.py` 는 검색 결과 row 의 `source/sourceRef/dataAsOf/snippet/answerable/fieldCards` 와 card evidence 를 검사하고, `evaluateSearchResultContract.py` 는 실제 `dartlab.search(...)` 또는 precomputed results 로 report 를 만든다. `searchIndexDelta.yml` 과 `searchIndexMain.yml` 은 publish/round-trip 뒤 이 report 를 evidence artifact 로 업로드하도록 배선했다. 실제 full-source HF artifact 에서 이 report 를 확인하는 것이 다음 운영 증거다.
49. top-level `dartlab.search` 는 함수이면서 `indexInfo()` 와 `prefetch()` helper 를 attribute 로 노출한다. 초기 `dartlab.search.indexInfo()` smoke 는 local active cache 에서 `available=True`, `nDocs=467752`, `compatible=True` 를 반환했고, 최신 live proof bundle 기준 local active cache 는 `nDocs=361136`, `compatible=True` 다. 새 sibling public call 은 추가하지 않았다.
50. 운영 문서의 proof bundle 계약을 보강했다. 본진 교체/운영 인계는 source catalog inventory, search publish evidence, HF round-trip report, result contract report, local `indexInfo()` smoke, rollback evidence, query-log gold/miss ledger status 가 함께 있어야 한다. 이 증거는 `10`, `11`, `12`, `06` 에 연결해 기록한다.
51. 원격 HF evidence audit 를 추가했다. `checkSearchRemoteEvidence.py` 는 HF `dart/searchCatalog/{source}/` 와 `dart/contentIndex/{tier}/manifest.json` 존재 여부, manifest summary, blocker 를 JSON 으로 남기고, searchIndexDelta/Main workflow 는 `searchRemoteEvidence.{delta,main}.json` 을 evidence artifact 에 포함한다.
52. 실제 HF remote evidence audit 를 2026-06-16 KST 에 처음 실행했을 때는 `valid=false`, blockers=`sourceCatalogMissing`, `contentIndexManifestMissing` 였다. EDGAR raw mirror 보정, source catalog upload, full/lite contentIndex stage/round-trip/promote 뒤 재실행한 remote evidence audit 는 `valid=true`, errors=[] 로 통과했다.
53. 최신 원격 Actions 스냅샷을 확인했다. Search Index Delta 최신 scheduled run 27510846976 은 HF `preupload/main` 429 로 실패했고, Search Index Main 최근 dispatch run 들은 2026-06-10 에 HF 429/silent partial pull 로 실패 또는 취소됐다. Original SSOT Sync 최근 scheduled run 들은 취소, News Archive Sync 와 EDGAR Data Sync 는 최신 run 성공이다.
54. HF 429 완화를 위해 `publishIndex.py` 의 manifest-pointer publish 를 파일별 `upload_file` 반복에서 단일 `create_commit` batch 로 전환했다. staging files 와 current manifest pointer 가 한 commit 으로 올라가므로 preupload/commit API 호출 수를 줄인다. 실제 효과는 다음 Actions publish run 에서 확인해야 한다.
55. source catalog upload 도 파일별 `upload_file` 반복에서 단일 `create_commit` batch 로 전환했다. `{source}.source_manifest.json` 과 `{source}.catalog_snapshot.parquet` 가 같은 commit 으로 올라가므로 source owner workflow 의 HF 429 표면도 줄인다. 실제 `dart/searchCatalog/{source}/` 원격 생성 증거는 다음 source owner Actions run 에서 확인해야 한다.
56. 공개 search surface 는 `topK` 를 `limit` 의 호환 alias 로 받는다. Skill OS 와 제품 문서가 말하던 `topK` 계약이 실제 `dartlab.search(..., topK=N)` 에서 깨지던 문제를 본진 public call 과 provider API 양쪽에서 막았다.
57. 회사명이 query 본문에 들어간 경우도 덕지덕지 mapper 없이 ListingResolver 기반 `stockCode` facet 으로 승격한다. `"삼성전자 대표이사 변경"` 은 이제 pre-rank stock mask 를 타며, 기존처럼 삼성카드/삼성SDS/삼성SDI 등 계열사로 새는 문제를 차단한다. 명시적 `corp="삼성전자"` 도 `nameToCode()` 와 한국어 `종목코드` 컬럼 fallback 으로 안정화했다.
58. 제품화 상태 감사 CLI 를 추가했다. `evaluateSearchProductizationStatus.py` 는 remote evidence, local `indexInfo`, HF round-trip, result contract, canary, quality report 를 한 proof bundle 로 읽어 `designReady/opsReady/releaseReady` 와 blocker 를 산출한다. source catalog 는 full snapshot/dataAsOf/row/file count 를 가져야 하고, contentIndex/local index 는 expected source별 `nDocsBySource` 와 `sourceDataAsOf` 를 가져야 한다.
59. source/no-answer canary CLI 는 별도 canary 파일뿐 아니라 manifest 의 `sourceCanaryPack` 도 직접 읽는다. `searchIndexDelta.yml` 과 `searchIndexMain.yml` 은 `evaluateSearchCanary.py --manifest data/dart/contentIndex/manifest.json` 결과와 `evaluateSearchProductizationStatus.py` 결과를 evidence artifact 에 포함한다. artifact canary v3 는 news 를 특정 최신 기사 sourceRef 가 아니라 `news` lane smoke 로 검사하고, 상태 감사는 canary source coverage 를 allFilings/panel/edgar-panel/news 모두에서 확인한다.
60. searchIndexDelta/Main workflow 는 proof bundle 을 업로드만 하지 않고 hard gate 로 쓴다. 기본 `productization_gate=ops` 는 `--fail-on-ops-not-ready` 로 source catalog/contentIndex/round-trip/result-contract/canary/local-index evidence 를 차단하고, `productization_gate=release` 는 real query-log gold quality report 와 `--fail-on-release-not-ready` 까지 요구한다.
61. 2026-06-16 초기 local productization status 실측은 `designReady=true`, `opsReady=false`, `releaseReady=false` 였고 `localIndexMissingSourceDataAsOf:edgar-panel` blocker 가 있었다. 이 값은 이후 live proof bundle 과 direct-review S4 proof 로 supersede 됐다.
62. 본진 교체 기준은 이제 "품질 가능성" 이 아니라 productization status hard gate 다. local/search code 가 좋아도 sourceCatalog/contentIndex 원격 증거, HF round-trip, result contract, canary coverage, source freshness, real quality report 중 하나가 빠지면 본진 release-ready 로 보지 않는다.
63. source catalog 생성은 raw block/text dump 가 아니라 검색 문서 단위 catalog 여야 한다. DART/EDGAR panel 은 `rceptNo/accession` filing 롤업으로 만들고, allFilings 는 `fetch_status=ok` + non-empty 본문 + stable `docKey` dedupe 를 통과한 row 만 catalog row 로 쓴다.
64. allFilings source catalog 는 XML/HTML 원문 전체를 그대로 싣지 않는다. 검색/evidence 용 bounded plain text 로 정규화해 catalog 크기와 검색 품질을 동시에 맞춘다. 원문 전체 복구는 source artifact/sourceRef 로 돌아가서 해결한다.
65. source catalog manifest 의 `totalRows` 는 search catalog doc row 수다. raw block/source row 수가 다르면 `rawRows` 로 보존한다. 이 기준이 없으면 source count drop gate 와 catalog delta 가 서로 다른 단위를 비교하게 된다.
66. `prepareSearchDeltaInputs.py` 의 current catalog 결합은 Polars full concat/write 가 아니라 parquet row-group streaming writer 를 사용한다. 4-source current catalog 결합은 174.5MB 산출물로 약 154초에 성공했다.
67. catalog delta dry-run 은 full `searchText` 를 읽지 않고 `docKey/source/textHash/metadataHash/deleted` fingerprint 만 읽는다. 361,136-row current catalog dry-run 은 약 2.1초, `valid=true`, sourceCounts allFilings 191,827 / panel 104,759 / edgarPanel 58,901 / newsPublic 5,649 로 통과했다.
68. catalog-mode main rebuild 는 catalog rows 를 list/DataFrame 으로 재구성하지 않고 `_IncrementalBuilder` 에 직접 feed 한다. 361,136 docs full main rebuild 는 약 245초에 성공했고 local `indexInfo()` 는 expected source counts/freshness 를 반환한다.
69. artifact canary 는 publish/local activation 안전장치로 둔다. allFilings 는 sourceRef exact 를 유지하지만, panel/EDGAR/news 의 자동 artifact canary 는 source lane/no-answer 검증으로 둔다. generic rolled text 의 exact sourceRef 품질은 real query-log gold/miss ledger 에서 판정한다.
70. 2026-06-16 local catalog-mode proof bundle 초기값은 `designReady=true`, `opsReady=false`, `releaseReady=false` 였다. HF full/lite manifest-pointer publish/round-trip/promote 뒤 quality 미포함 full_lite proof bundle 은 `opsReady=true`, `releaseReady=false` 였고, direct-review 품질팩 이후 `releaseReady=true` 로 supersede 됐다.
71. real query-log 품질 루프는 평가 CLI 에서 멈추면 안 된다. `DARTLAB_SEARCH_QUERY_LOG` 가 켜진 `dartlab.search(...)` 호출은 raw candidate JSONL 을 남기고, reviewer label 이 붙은 row 만 `prepareSearchGold.py` 를 통해 release gold 가 된다. raw capture 는 품질 flywheel 입력이고, release graduation 증거는 여전히 reviewed real gold 100~300 rows 다.
72. delta publish 의 얇은 운영 리스크를 차단했다. `pullSearchCurrentIndex.py` 는 HF current manifest pointer 를 따라 기존 full `main.*` required files 를 flat build dir 로 복원하고 `previous_manifest.json` 을 보존한다. `buildSearchDelta.py` 는 publish 때 previous manifest 의 `fileSources` 를 seed 로 써서 main fileSources 를 잃지 않고 새 `delta.*` 경로만 덮어쓴다.
73. 원격 evidence audit 는 manifest 존재만 보지 않는다. `checkSearchRemoteEvidence.py` 는 contentIndex `requiredFiles` 가 `fileSources` 로 실제 HF path 에 해소되는지 확인하고, 대상 누락은 `contentIndexFileSourceMissing` blocker 로 올린다.
74. productization status 는 full 하나의 HF round-trip 으로 opsReady 를 주지 않는다. `--hf-round-trip` 은 tier별 반복 입력을 받고, full/lite 모두 `activation.activated=true` 와 `rollback.rolledBack=true` 여야 한다. 실제 `verifySearchHfRoundTrip.py` 의 nested report 구조도 status 가 해석한다.
75. lite tier 는 제품 source 계약과 맞게 EDGAR panel 도 포함한다. 경량화는 `DARTLAB_LITE_MONTHS`, `DARTLAB_LITE_MAX_MB`, `DARTLAB_LITE_MIN_DOCS` 로 조절하고, source 자체를 조용히 빼지 않는다.
76. proof bundle CLI 를 추가했다. `buildSearchProofBundle.py` 는 remote evidence, local indexInfo, result contract, canary, full/lite HF round-trip, optional quality report 를 한 디렉터리에 모으고 `searchProofBundle.json` 과 `searchProductizationStatus.json` 을 쓴다. searchIndexDelta/Main workflow 는 성공/실패와 무관하게 이 bundle 을 evidence artifact 에 포함한다.
77. 2026-06-16 live proof bundle 초기값은 local indexInfo `nDocs=361136` 기준으로 result contract 30 rows invalidRows 0, canary 5/5 pass 였지만 원격 source/content/round-trip blocker 가 남아 있었다. HF bootstrap 이후 full_lite proof bundle 은 remote evidence valid, full/lite round-trip valid, result contract valid, canary pass 로 `opsReady=true` 를 반환했고, direct-review quality report 이후 `releaseReady=true` 로 갱신됐다.
78. 제품화 판단을 얇은 개선 목록이 아니라 cutover 상태 기계로 고정했다. `13-cutover-contract.md` 는 S1 designReady, S2 opsReady, S3 releaseReady, S4 defaultReplacement 를 분리하고, 본진 기본값 교체는 S2 proof bundle, 제품 졸업은 S3 real query-log gold 로만 승인한다.
79. source snapshot lineage 를 contentIndex 증거로 승격했다. source owner workflows 는 `search-catalog-{source}-{job}-{run}` Actions artifact 를 남기고, `prepareSearchDeltaInputs.py` 는 `source_manifest_set.json` 을 생성한다. catalog-mode main/delta/lite publish 는 이 파일을 contentIndex `requiredFiles`/`fileHashes` 에 포함하며, productization status 는 remote content manifest 에 `sourceManifestSetId` 가 없으면 S2 opsReady 를 주지 않는다.
80. quality report 는 자체 `releaseEligible=true` 만으로 releaseReady 를 만들 수 없다. `evaluateSearchProductizationStatus.py` 가 `realReviewedRows>=100`, `goldOriginCounts`, `reviewStatusCounts`, filing/news/noAnswer/edgar coverage 를 다시 검사하고 synthetic/proxy/unreviewed rows 를 blocker 로 올린다.
81. query-log quality drill 은 release evidence 가 아니다. `runSearchQualityDrill.py` 는 canonical drill rows 를 `goldOrigin=drillSynthetic`, `reviewStatus=drillReviewed` 로 표식하고, status gate 는 이 rows 를 real reviewed gold 로 인정하지 않는다.
82. artifact source canary positive row 는 source lane 만 맞아도 통과하지 않는다. `artifactCanary.py` 의 자동 생성 positive canary 는 `requireAnswerable=true` 를 요구하므로 publish/local activation smoke 에서 answerability 없는 row 는 실패한다.
83. bootstrap plan 은 단순 missing 파일 목록이 아니라 productization status blocker 를 실행계획으로 바꾼다. `sourceCatalogNotFull:*`, `sourceCatalogMissingProducerRun:*`, `remoteContentManifestSetMissingProducerRun:*`, `remoteContentMissingFileSources:*` 는 source-owner bootstrap 또는 catalog-mode Search Main action 으로 변환된다.
84. S4 defaultReplacement 는 catalog 단일 기본값과 fail-closed publish 증거가 있어야 한다. `evaluateSearchCutover.py` 는 `defaultBuildMode=catalog`, `scheduledBuildMode=catalog`, `legacyFallbackOperatorOnly=true`, `failClosedPublish=true`, active/previous manifest id, rollback command/검증, run evidence 기록, surface naming review 가 없으면 releaseReady 여도 S3 에서 멈춘다.
85. publish-before-gate 문제를 완전히 풀기 위한 하부 계약을 추가했다. `publishContentIndexFiles(..., promoteCurrent=False)` 는 current pointer 를 바꾸지 않고 staging files 와 staging pointer manifest 만 올리며, `verifySearchHfRoundTrip.py --manifest-repo-path` 는 그 candidate manifest 를 직접 activate/rollback 검증한다.
86. Search Main/Delta workflow 를 stage -> candidate round-trip -> result contract -> canary -> optional real quality -> promote -> remote evidence/status/proof 순서로 재배치했다. 이제 current pointer 는 pre-promote gate 이후 `promoteSearchCandidate.py` 에서만 바뀐다. 실제 Actions run 증거 전에는 S4 `failClosedPublish=true` 로 보지 않는다.
80. query-log gold toolchain drill 을 추가했다. `runSearchQualityDrill.py` 는 raw query log, reviewer label template, canonical gold, quality report, miss ledger 경로가 깨지지 않았는지 synthetic reviewed rows 로 확인한다. 이 report 는 `releaseEvidence=false` 이며 real query-log gold 를 대체하지 않는다. searchIndexDelta/Main workflow 는 `searchQualityDrill.{delta,main}.json` 을 evidence artifact 로 업로드한다.
81. source catalog 는 HF 파일 존재만으로 S2 증거가 아니다. `buildSearchCatalog.py` 는 GitHub Actions 환경에서 source manifest `producerRun.workflow/job/runId/sha/artifactName` 을 기록하고, `prepareSearchDeltaInputs.py` 는 이 lineage 를 `source_manifest_set.json` 에 보존한다. `evaluateSearchProductizationStatus.py` 는 원격 source manifest 에 `producerRun` 이 없으면 `sourceCatalogMissingProducerRun:*` blocker 로 S2 opsReady 를 차단한다.
82. 거짓 full source catalog publish 를 차단했다. `sourceCatalog.py` 는 이전 full manifest 대비 `previousFileDrop`, `previousRowDrop`, `previousCatalogRowDrop` 을 completeness error 로 올리고, `buildSearchCatalog.py` 는 `--compare-remote-manifest --require-previous-manifest` 로 HF 직전 source manifest 를 요구할 수 있다. `originalSync.yml`, `edgarSync.yml`, `newsArchiveSync.yml` 의 source-owner catalog steps 는 이 hard gate 를 사용한다. 첫 canonical source catalog 는 `searchIndexMain.yml` raw full HF pull bootstrap 이 만든다.
83. main bootstrap 이 source catalog 만 만들고 legacy main 으로 끝나는 갭을 막았다. `searchIndexMain.yml` 은 canonical source catalog bootstrap 직후 `Prepare canonical catalog main inputs after bootstrap` 단계로 `prepareSearchDeltaInputs.py` 를 다시 실행한다. 따라서 source catalog 가 없던 첫 full pull run 도 `source_manifest_set.json` 을 가진 catalog-mode main evidence 를 만들 수 있어야 한다. explicit `build_mode=legacy` 는 이 bootstrap/freeze 를 건너뛴다.
84. local pipeline drill 의 기준을 source catalog 이후가 아니라 source owner raw input 부터 올렸다. `runSearchPipelineDrill.py` 는 synthetic raw source parquet 에서 source catalog 4종을 생성하고, `prepareSearchDeltaInputs.py` 로 `source_manifest_set.json` 과 catalog-mode current catalog 를 freeze 한 뒤 contentIndex publish/activate/rollback 을 검증한다. 이 drill 은 실제 HF evidence 를 대체하지 않지만, 본진 배선이 운영 bootstrap 계약을 깨면 preflight 에서 먼저 실패한다.
85. `sourceManifestSetId` 만으로는 S2 운영 증거가 아니라고 고정했다. `checkSearchRemoteEvidence.py` 는 contentIndex manifest 의 `fileSources` 를 따라 실제 `source_manifest_set.json` 을 열고, set 내부 source별 `producerRun.workflow/job/runId/sha/artifactName` 누락을 summary 로 남긴다. `evaluateSearchProductizationStatus.py` 는 누락 source 를 `remoteContentManifestSetMissingProducerRun:{tier}:{source}` blocker 로 올려 `opsReady=false` 를 유지한다.
86. 최신 원격 실패 원인을 제품화 회귀 테스트로 흡수했다. 2026-06-14 Delta 실패는 old `upload_file` 반복의 HF 429, 2026-06-10 Main 실패는 raw HF pull quota/old news path/retry 부족이었다. 현재 checkout 은 content/source publish 를 batch `create_commit` 으로 묶고 Main raw bootstrap 은 12회 resume, 310초 quota window, `news/public/rss` + `news/public/rss_enriched` 경로를 정적 테스트로 고정한다.
87. 첫 canonical source catalog 를 Main raw pull 하나에만 의존하지 않도록 source-owner explicit bootstrap 경로를 추가했다. `originalSync.yml`, `newsArchiveSync.yml`, `edgarSync.yml` 은 `workflow_dispatch` input `search_catalog_bootstrap` 을 받고, true 일 때만 `--require-previous-manifest` 를 해제한다. 대신 allFilings 150k, DART panel 90k, EDGAR panel 50k, news 100 catalog row 하한을 걸어 partial runner tree 가 첫 full claim 으로 승격되지 않게 했다.
88. 원격 source catalog/contentIndex evidence 가 비어 있을 때의 실행 순서를 사람이 기억하지 않도록 bootstrap plan CLI 를 추가했다. `planSearchBootstrap.py` 는 현재 `searchRemoteEvidence` 또는 live audit 를 읽고, source-owner `search_catalog_bootstrap=true` dispatch, catalog-mode `searchIndexMain.yml`, 이후 remote evidence/proof bundle 검증 명령을 JSON 으로 산출한다. 이 CLI 는 GitHub/HF 를 변경하지 않는 실행계획 생성기다.
89. proof bundle 이 실패 결과만 남기고 운영자가 별도 plan CLI 를 떠올려야 하는 구멍을 막았다. `buildSearchProofBundle.py` 는 remote source/content blocker 가 있으면 같은 bundle 디렉터리에 `searchBootstrapPlan.json` 을 만들고, `searchProofBundle.json` 의 `reports.bootstrapPlan` 과 `nextActions.bootstrapPlan` 에 누락 source/tier/action id 를 남긴다. 따라서 `opsReady=false` proof 도 다음 source-owner/Search Main/검증 순서를 포함한다.
90. S2/S3 와 S4 default replacement 를 혼동하지 않도록 cutover state CLI 를 추가했다. `evaluateSearchCutover.py` 는 `searchProofBundle.json` 과 optional replacement evidence 를 읽어 `S1_DESIGN_READY`, `S2_OPS_READY`, `S3_RELEASE_READY`, `S4_DEFAULT_REPLACEMENT` 를 판정한다. S4 는 `opsReady=true` 만으로 주지 않고, 단일 엔진 기본값, active/previous manifest, rollback command, run evidence 기록, surface naming review 가 있어야 한다. searchIndexDelta/Main workflow 는 `searchCutover.{delta,main}.json` 을 evidence artifact 에 포함한다.
91. HF에는 raw source parquet 가 이미 있다. 2026-06-16 현재 원격에는 `dart/allFilings` 430 files, `dart/panel` 2930 files, `edgar/panel` 2622 files, `news/public/rss_enriched` 18 files 가 있고, `dart/searchCatalog/**` 는 0 files 다. 따라서 병목은 raw data 부재가 아니라 raw HF parquet 를 canonical source catalog/contentIndex 로 승격하고 publish evidence 를 남기는 단계다.
92. HF raw parquet 기반 로컬 bootstrap 을 실제 실행했다. allFilings 430 files -> 192,095 catalog rows, DART panel 2,930 files -> 104,761 rows, EDGAR panel local HF cache 3,106 files -> 74,787 rows, news enriched 18 files -> 81,798 rows, combined catalog 453,441 rows, catalog-mode main contentIndex 453,441 docs 를 생성했다. `HF_TOKEN`/cached token 이 없어 publish 는 스킵됐고, EDGAR exact HF mirror 는 292 files 다운로드가 네트워크 타임아웃으로 미완료라 원격 증거로는 인정하지 않는다.
93. HF raw 기반 대형 인덱스에서 artifact canary 가 panel row 를 `facetMismatch:report` 로 떨어뜨리는 실제 품질 결함을 발견했다. panel 롤업 row 는 `report_nm` 이 비어도 evidence/snippet/text 에 `사업보고서` 같은 report term 이 있으면 answerable 해야 하므로, report facet matching 이 evidence text 도 보도록 고쳤다. 수정 후 canary 는 5/5 pass 로 회복됐다.
94. EDGAR raw 원격/로컬 불일치를 실제로 보정했다. 초기 원격 `edgar/panel` 은 2,622 files, 로컬은 3,106 files 였고, 원격에 있는데 로컬에 없는 292 files 와 로컬에만 있는 776 files 가 있었다. 292 files 는 HF/curl download 로 로컬에 채우고, 776 local-only files(약 3.4GB) 는 HF 에 업로드해 최종 원격/로컬 모두 3,398 files, missing/extra 0 으로 맞췄다.
95. EDGAR mirror 보정 뒤 canonical source catalog 를 재생성했다. final combined catalog 는 462,947 rows = allFilings 192,095 + DART panel 104,761 + EDGAR panel 84,293 + newsPublic 81,798 이며, catalog-mode full contentIndex 는 462,947 docs 로 재빌드됐다.
96. source catalog 4종을 HF 에 업로드했다. 원격 `dart/searchCatalog/{allFilings,dartPanel,edgarPanel,newsPublic}/` 는 각각 `{source}.source_manifest.json` 과 `{source}.catalog_snapshot.parquet` 를 갖고, remote evidence audit 는 full snapshot, row/file count, `producerRun` 을 확인했다.
97. full contentIndex 는 stage-only publish -> staged manifest round-trip -> promote 순서로 승격했다. candidate manifest 는 `dart/contentIndex/_staging/full-20260616094524/manifest.json`, round-trip 은 `valid=true`, activation/rollback true, current full manifest 는 `nDocsBySource={allFilings:192095, panel:104761, edgar-panel:84293, news:81798}` 와 `sourceDataAsOf={allFilings:20260612, panel:20260615, edgar-panel:20260630, news:20260615}` 를 가진다.
98. lite contentIndex 는 raw 재스캔이 아니라 `main.current.catalog_snapshot.parquet` 를 date 필터로 잘라 catalog-mode 로 빌드하도록 `buildSearchMain.py` 를 보강했다. 18개월 lite 는 280,747 docs = allFilings 167,758 + DART panel 18,030 + EDGAR panel 13,161 + news 81,798 이고, candidate manifest `dart/contentIndex/lite/_staging/lite-20260616101609/manifest.json` round-trip/promote 를 통과했다. 산출물은 326.3MB 로 `DARTLAB_LITE_MAX_MB=300` 경고를 냈으므로, default 경량성은 후속으로 12개월 또는 top universe 정책 실험이 필요하다.
99. 2026-06-16 full+lite remote evidence audit 는 `valid=true`, errors=[] 다. `buildSearchProofBundle.py --content-tiers full,lite --skip-quality` 결과는 품질 미포함이라 `opsReady=true`, `releaseReady=false` 였다. direct-review quality report 를 포함한 proof bundle 은 `releaseReady=true` 이며, 운영상 다음 목표는 real reviewed query-log gold 를 300 rows 방향으로 늘리는 것이다.
100. 실제 샘플 검색은 full active index 에서 확인했다. `환율 리스크` content 는 news lane, `공시 말고 뉴스로 반도체` news scope 는 news-only, `edgar revenue risk` 는 edgar-panel, `유상증자` 는 allFilings 결과를 반환했다. PowerShell stdin 한글 인코딩은 `??` 로 깨질 수 있어 테스트/운영 명령은 UTF-8 파일 또는 Python unicode escape 로 넣는다.
101. graph catalog sidecar 를 contentIndex 운영 산출물로 연결했다. 표준 파일명은 `entityGraphCatalog.parquet` 이고, 존재하면 `writeIndexManifest()` 가 `requiredFiles/fileHashes/entityGraphCatalog` summary 에 기록한다. `entityGraphCatalog.py` 는 env 로 지정된 catalog 를 contentIndex 로 복사하거나, `DARTLAB_SEARCH_ENTITY_GRAPH_BUILD=1` 일 때 seed codes/current catalog 에서 offline build 를 수행한다. `buildSearchMain.py`, `buildSearchDelta.py`, `pushContentIndex()`, `pullContentIndex()` 는 이 파일을 배포/다운로드 후보에 포함하므로 요청 경로 live traversal 없이 기존 manifest pointer, local update, rollback 경로를 탄다.
102. remote evidence/status 에 graph catalog visibility 를 추가했다. `checkSearchRemoteEvidence.py` 는 contentIndex manifest 의 `entityGraphCatalog.parquet` presence, repo path, fileSource existence, schemaVersion, nEntities, stockCodeCount, dataAsOf 를 summary 로 남긴다. `evaluateSearchProductizationStatus.py` 는 이 summary 를 `evidence.remoteEvidence.entityGraphCatalog.{tier}` 로 전달한다. optional artifact 이므로 부재만으로 ops blocker 는 만들지 않는다.
103. direct-review 품질팩을 실제로 돌렸다. `data/dart/searchCatalog/searchQualityReviewPack.directReview/qualityCycleDirect/qualityReport.json` 은 `totalRows=106`, `realReviewedRows=106`, coverage filing 54 / news 20 / EDGAR 20 / noAnswer 12, `releaseEligible=true`, blockers=[] 를 반환했다.
104. direct-review 품질 지표는 `overallReadyRate=1.0`, `docHit10=1.0`, `memoryCitationTop3Exact=1.0`, `newsSourcePrecision10=1.0`, `noAnswerFalseAcceptRate=0.0` 이다. CAPEX/AI 데이터센터 사업보고서 2개 후보는 sourceHint mismatch 로 reviewable set 에서 정직하게 제외했다.
105. `buildSearchReplacementEvidence.py` 를 추가하고 Search Main/Delta workflow 기본 모드를 catalog 로 고정했다. workflow evidence artifact 는 `searchReplacementEvidence.{main,delta}.json` 을 포함하며, S4 는 이 파일 없이는 통과하지 않는다.
106. `data/dart/searchCatalog/searchProofBundle.directReview/searchReplacementEvidence.json` 은 `singleEngineDefault=true`, `defaultBuildMode=catalog`, `scheduledBuildMode=catalog`, `legacyFallbackOperatorOnly=true`, `failClosedPublish=true`, active/previous manifest id, rollback command/검증, run evidence 기록, surface naming review 를 모두 갖고 `valid=true` 다.
107. `data/dart/searchCatalog/searchProofBundle.directReview/searchCutover.json` 은 blockers=[], `releaseReady=true`, `defaultReplacement=true`, state=`S4_DEFAULT_REPLACEMENT` 다. 현재 checkout 의 본진 기본값 교체 증거는 S4 까지 닫혔다. 단 새 workflow 가 원격 Actions 에서 다시 실행된 artifact 는 별도 운영 확인 대상이다.
108. source-owner incremental catalog publish 의 구조적 실패 원인을 수정했다. 부분 runner tree 가 full source catalog 로 발행되면 `previousFileDrop/previousRowDrop` 으로 막히던 상태에서, 이제 `buildSearchCatalog.py --merge-previous-catalog` 가 HF 직전 full manifest/catalog 를 내려받아 현재 변경 parquet 를 source별 파티션/docKey 규칙으로 병합한 뒤 full snapshot 으로 검증한다.
109. `originalSync.yml`, `newsArchiveSync.yml`, `edgarSync.yml` 의 source catalog build step 은 `--compare-remote-manifest --require-previous-manifest --merge-previous-catalog` 조합으로 바뀌었다. allFilings 는 docKey upsert, dartPanel 은 stockCode 파일 파티션 교체, edgarPanel 은 ticker 파티션 교체, newsPublic 은 date 파티션 교체로 stale row 를 제거한다.
110. 실제 HF previous source catalog 를 내려받는 no-upload dry-run 을 4개 source 에 대해 실행했다. 결과는 allFilings 192,096 rows / DART panel 104,762 rows / EDGAR panel 84,294 rows / news 81,799 rows, 모두 `snapshotScope=full`, `valid=true`, `previousManifestId=true` 다. local `dartlab.search.indexInfo()` 는 full active 462,947 docs compatible, 실제 질의 `유상증자`, `반도체 HBM 투자`, `공시 말고 뉴스로 환율 기사` 는 answerable 결과를 반환했다. 새 workflow 가 원격 Actions 에서 성공하는지는 패치 push 후 별도 확인 대상이다.
111. 본문 의미 rerank 는 꺼져 있던 `_rerankBodySemanticHits` 경로를 실제 `searchUnified()` auto path 에 연결했다. `공시 원문` 같은 단어가 들어가도 `언급/다룬/수혜/증설/설비투자/전력/인프라` 류 본문 의미 cue 가 있으면 title lane merge 를 타지 않는다.
112. no-answer false accept 는 low-confidence answerability 로 막는다. 전체 후보군 score 가 floor 아래면 검색 row 는 유지하되 `answerable=false`, `notAnswerableReason=lowConfidence` 로 내려서 canary/gold/memory-card 가 답변 근거로 쓰지 못하게 한다.
113. full query-log gold 회복 과정에서 body semantic rerank 를 정형 content 질의와 분리했다. `본문/주석/위험요인/사업보고서` 류 질의는 title lane 을 타지 않되 기존 content lane rank 를 보존하고, 주제형 cue 가 있는 자연어 의미 질의만 강한 body rerank 를 탄다.

---

## 2. 실측 기준선

| 실험 | 결과 |
|---|---:|
| corpus | 57337 docs |
| allFilings | 43717 |
| panel | 8620 |
| news | 5000 |
| combined product readiness | pass |
| random curatedDraft 300 readyRate | 0.99 |
| filing docHit10 / memoryCitationTop3Exact | 1.0 / 1.0 |
| filing memoryAnswerReady / fieldCoverage | 0.9929 / 0.9976 |
| news exactHit10 / sourcePrecision10 / targetSourceTop1 | 0.975 / 0.975 / 0.975 |
| noAnswer falseAcceptRate | 0.0 |
| demo-ops ceiling corpus | 301579 docs = allFilings 191827 + panel 104752 + news 5000 |
| demo-ops 3 seeds × 100 rows | readyRate 0.9867 |
| demo-ops filing / news / noAnswer | memoryAnswerReady 0.98 / sourcePrecision10 0.9867 / falseAcceptRate 0.0 |
| demo-ops warm latency | p50 123.1ms, p95 157.9ms, max 173.9ms |
| demo-ops sparse memory | content CSR 약 591MB, metadata CSR 약 36.9MB |
| local sourceCatalog allFilings | rawRows 421,726 → catalogRows 191,827, 121.8MB, bounded plain text |
| local sourceCatalog DART panel | rawRows 85,210,459 → catalogRows 104,759, 78.5MB, filing rollup |
| local sourceCatalog EDGAR panel | rawRows 16,831,346 → catalogRows 58,901, 47.1MB, accession rollup |
| local sourceCatalog newsPublic | catalogRows 5,649, 1.7MB |
| local current catalog | 361,136 docs, 174.5MB, source별 unique docKey 100% |
| local catalog dry-run | valid=true, fingerprint-only, 약 2.1초 |
| local catalog-mode main rebuild | 361,136 docs, 약 245초 |
| local catalog-mode canary/result contract | canary passRate 1.0, result contract 30 rows invalidRows 0 |
| live proof bundle status | superseded by direct-review S4; see direct-review rows below |
| current session ops hardening tests | `tests/search tests/providers/dart/search` 285 passed, remote source manifest set producerRun gate focused tests 25 passed, pipeline/prepare focused tests 4 passed, Python ruff passed, workflow YAML parse passed |
| current session fail-closed publish tests | stage-only candidate publish, explicit staged manifest round-trip, candidate promote CLI, productization status/cutover/quality gates, workflow static smoke 포함 60 passed |
| HF raw local bootstrap | combined catalog 453,441 rows = allFilings 192,095 + panel 104,761 + edgar-panel 74,787 + news 81,798 |
| HF raw catalog-mode main rebuild | 453,441 docs, 2.2분, result contract 30 rows invalidRows 0, canary 5/5 pass |
| EDGAR HF mirror reconciliation | remote/local `edgar/panel` 3,398 files, missing/extra 0 |
| canonical source catalog final | 462,947 rows = allFilings 192,095 + panel 104,761 + edgar-panel 84,293 + news 81,798 |
| HF sourceCatalog final | 4 sources x manifest+catalog = 8 remote files, remote evidence valid |
| HF full contentIndex current | 462,947 docs, sourceDataAsOf allFilings 20260612 / panel 20260615 / edgar-panel 20260616 / news 20260615 |
| HF lite contentIndex current | 280,747 docs, 326.3MB, 18개월 window, full/lite round-trip valid |
| direct-review proof bundle | opsReady=true, releaseReady=true, defaultReplacement=true, state=`S4_DEFAULT_REPLACEMENT` |
| graph catalog operationalization | `entityGraphCatalog.parquet` offline/copy prep + manifest required file + publish fileSources + active contentIndex discovery verified |
| graph catalog evidence | remote evidence/status summary includes graph catalog presence, fileSource existence, nEntities, dataAsOf |
| source-owner merge dry-run | HF previous catalog download + partial parquet merge: allFilings 192,096 / panel 104,762 / EDGAR 84,294 / news 81,799 rows, all valid |
| live body-semantic/no-answer spot check | HBM 원문 질의 top-5 HBM 관련 panel/allFilings, no-answer trap top-5 `answerable=false(lowConfidence)` |
| full query-log gold after body rerank guard | `releaseEligible=true`, blockers=[], overallReadyRate 0.9811, docHit10 0.9787, memoryCitationTop3Exact 0.9468, noAnswerFalseAcceptRate 0.0 |

주의: random curatedDraft 는 제품 졸업 증거가 아니라 압박 실험이다.

---

## 3. 남은 약점

1. 실제 query-log gold 는 direct-review 106 rows 로 첫 release gate 를 통과했다. 다음 약점은 장기 안정성 확인을 위해 300 rows 방향으로 늘리는 것이다.
2. 실제 GitHub Actions run 으로 source owner manifest 생성과 scheduled catalog delta 전환을 확인해야 한다. 2026-06-16 local HF bootstrap 으로 원격 evidence 는 확보했지만, scheduled/dispatch workflow evidence 는 별도다.
3. 제품 UI/API 에서 evidence card 는 row-level sourceRef/snippet card 와 bounded `evidenceText` query chunk card 까지 올라왔다. result contract/canary/HF round-trip 과 direct-review 품질 리포트는 통과했고, 신규 miss 는 miss ledger 로 관리한다.
4. 로컬 rebuild 는 가능하지만 제품 운영 기본값은 prebuilt main+delta artifact 다. 사용자는 HF current manifest pointer 의 `fileSources` 를 내려받아 atomic activation 해야 한다.
5. 현재 daily delta 는 scheduled/default 에서 catalog mode 로 들어간다. legacy 는 운영자 명시 dispatch 예외이며, 다음 확인은 actual `mode=catalog` scheduled/dispatch run 증거다.
6. CLI `dartlab search`, public `/search`, viewer in-page search 의 명칭 충돌은 S4 surface naming review 에서는 통과했다. 이후 UI/CLI 문구 변경 시 같은 review 를 다시 해야 한다.
7. query 본문 회사명 facet 은 본진 품질 bugfix 로 들어갔지만, real query-log gold 에서 유사 회사명/계열사/접미사 trap 을 더 넓게 검증해야 한다.
8. lite 18개월 tier 는 326.3MB 로 기본 경량 배포 목표 300MB 를 넘었다. 운영 가능성은 확인됐지만, pip 기본 경험을 더 작게 만들려면 12개월/상위 universe/metadata 압축 정책을 별도 실험해야 한다.
9. 본문 의미 rerank 는 규칙 기반 sparse path 로 회복했지만, 장기 품질은 real query-log gold 300 rows 와 miss ledger 에서 "토픽 정확도" 유형을 더 넓게 확인해야 한다.

---

## 4. NEXT

- [ ] Phase 0 리뷰: 이 PRD 가 제품화 방향으로 충분한지 확인.
- [x] `_attempts` 에 multi-seed random pressure runner 추가. (`productRandomPressureSweep.py`)
- [x] 실제 데모 운영형 ceiling run 실행. 301579 docs, 300 queries, readyRate 0.9867, p95 157.9ms.
- [x] query-log gold 저장 row 계약과 review status gate 구현. (`qualityGate.py`, `evaluateSearchGold.py`)
- [x] 실제 query-log gold 저장 위치와 운영 라벨링 절차 확정. (`goldLog.py`, `prepareSearchGold.py`, `data/search/queryLogGold.real.jsonl` 계약)
- [x] `dartlab.search(...)` raw query-log candidate capture 훅 구현. (`DARTLAB_SEARCH_QUERY_LOG`, `goldLog.py`, `api.py`)
- [x] 전문 검토 반영: runtime/HF 증분/local-public-library/품질 gate 설계 문서화. (`07-specialist-review.md`, `08-completion-design.md`)
- [x] 혁신 방향 문서화: 빠른 의미검색, sourceRef graph, intent kernel, 증분 운영, 덕지덕지 방지. (`09-innovation-roadmap.md`)
- [x] 본진 이식 파일 지도 작성: planner/evidence/memory/sourcePolicy/test slots.
- [x] result schema 와 manifest/indexInfo 1차 본진 계약 구현. (`resultSchema.py`, `manifest.py`, `localUpdate.py`)
- [x] PRD급 제품 파이프라인과 운영 런북 작성. (`10-production-pipeline-prd.md`, `11-operator-runbook.md`)
- [x] 실제 workflow 기준 파이프라인·유지보수 맵 작성. (`12-pipeline-maintenance-map.md`)
- [x] PRD급 운영 요구사항/승인 매트릭스/장기 유지보수 모델/운영 인계 기준 보강. (`10-production-pipeline-prd.md`, `11-operator-runbook.md`, `12-pipeline-maintenance-map.md`)
- [x] 본진 교체 cutover 상태 계약 고정. (`13-cutover-contract.md`, `README.md`, `10-production-pipeline-prd.md`, `11-operator-runbook.md`, `12-pipeline-maintenance-map.md`)
- [x] 실제 run evidence 기록 슬롯과 운영 증거 원장 추가. (`11-operator-runbook.md`, `12-pipeline-maintenance-map.md`)
- [x] 앞으로의 데이터 증가와 유지보수 운영 루프를 mainPlan 에 반영. (`03-data-indexing-ops.md`, `10-production-pipeline-prd.md`, `11-operator-runbook.md`, `12-pipeline-maintenance-map.md`)
- [x] allFilings/panel/news/EDGAR catalog delta 설계를 `_attempts` 졸업 산출물과 맞춰 본진 이식 단위로 쪼갬. (`sourceManifest.py`, `catalog.py`)
- [x] source intent hard isolation 과 answerability 1차 본진 모듈 구현. (`sourceIntent.py`, `answerability.py`)
- [x] row-level evidence card 와 LLM memory-card set 1차 본진 모듈 구현. (`evidencePack.py`, `memoryCard.py`)
- [x] facet no-answer 와 query-focused bounded chunk evidence 1차 구현. (`facetPlanner.py`, `answerability.py`, `fieldIndex.py`, `evidencePack.py`)
- [x] content index meta 에 bounded `evidenceText` 저장. (`fieldIndex.py`, `fieldIndexRebuild.py`)
- [x] local updater HF/current manifest 비교 및 동일/오래된 manifest skip 구현. (`localUpdate.py`)
- [x] `searchIndexDelta.yml` catalog mode 진입점 추가. (`DARTLAB_SEARCH_DELTA_MODE=auto|catalog|legacy`)
- [x] source owner workflows 의 search source manifest/catalog snapshot 생성 step 추가. (`buildSearchCatalog.py`, `sourceCatalog.py`)
- [x] `searchIndexDelta.yml` scheduled path 의 HF searchCatalog pull + catalog env 준비 step 추가. (`prepareSearchDeltaInputs.py`)
- [x] targeted regression test 목록을 `tests/search` / `tests/providers/dart/search` 기준으로 쪼개고 focused 회귀를 실행함.
- [x] 실제 HF `dart/searchCatalog/{source}/` source manifest/catalog 업로드 및 remote evidence 확인. (2026-06-16 local bootstrap)
- [ ] 실제 GitHub Actions source owner run 에서 `dart/searchCatalog/{source}/` artifact 생성 확인.
- [ ] 실제 GitHub Actions `searchIndexDelta.yml` scheduled/dispatch run 에서 catalog mode delta publish 확인.
- [x] HF contentIndex staging upload + current manifest pointer publish 경로 1차 구현. (`publishIndex.py`, `buildSearchMain.py`, `buildSearchDelta.py`, `fieldIndexRebuild.py`)
- [x] HF contentIndex publish 전 local manifest/hash/canary selfcheck 차단 구현. (`publishIndex.py`)
- [x] local active rollback helper 구현. (`rollbackActiveIndex`, previous active pointer)
- [x] source/no-answer canary pack gate 구현. (`canaryPack.py`, `evaluateSearchCanary.py`)
- [x] Skill OS `engines.search` 갱신. (`src/dartlab/skills/specs/engines/search/SKILL.md`, `disclosureSearch.md`)
- [x] local end-to-end pipeline drill 구현 및 searchIndexDelta/Main preflight 에 배선. (`runSearchPipelineDrill.py`)
- [x] local pipeline drill 을 raw source parquet -> source catalog -> source manifest set freeze -> contentIndex publish/activate/rollback 경로로 강화. (`runSearchPipelineDrill.py`)
- [x] local activation schema compatibility 와 `sourceCanaryPack` 차단 연결. (`manifest.py`, `localUpdate.py`)
- [x] delta workflow catalog env override 차단. (`searchIndexDelta.yml`)
- [x] expected source empty full snapshot 차단. (`pipeline.py`)
- [x] query-log gold non-answerable hit 차단. (`qualityGate.py`)
- [x] 실제 HF current manifest round-trip 검증 CLI 와 workflow evidence artifact 업로드 배선. (`verifySearchHfRoundTrip.py`, `searchIndexDelta.yml`, `searchIndexMain.yml`)
- [x] artifact 기반 source/no-answer canary pack 자동 생성 및 manifest/local activation 연결. (`artifactCanary.py`, `fieldIndexRebuild.py`)
- [x] raw query log + reviewer label 을 canonical real gold JSONL 로 정규화하는 운영 CLI 구현. (`goldLog.py`, `prepareSearchGold.py`)
- [x] HF contentIndex full/lite staging upload/current manifest pointer publish 실제 HF round-trip 및 rollback drill 실증. (`searchHfRoundTrip.full.json`, `searchHfRoundTrip.lite.json`)
- [x] source catalog expected source set 과 full snapshot completeness enforcement 1차 구현. (`snapshotScope`, expected sources, source drop check)
- [x] source catalog 생성 시 빈 full snapshot/빈 normalized catalog 차단 구현. (`buildSearchCatalog.py --min-files/--min-rows/--min-catalog-rows`, `completenessCheck`)
- [x] source-owner 거짓 full publish 차단 구현. (`buildSearchCatalog.py --compare-remote-manifest --require-previous-manifest`, `previousFileDrop/previousRowDrop/previousCatalogRowDrop`)
- [x] stale source answerability 1차 구현. (`freshnessRequired`, `staleSource`)
- [x] `searchIndexMain.yml` 을 source manifest snapshot 기반 compaction 우선 경로로 전환. (`DARTLAB_SEARCH_MAIN_MODE`, `rebuildMainFromCatalog`)
- [x] `searchIndexMain.yml` raw full HF pull fallback 에 canonical source catalog bootstrap 배선. (`searchIndexMain.full-pull`)
- [x] source-owner workflow 에 명시적 첫 source catalog bootstrap 경로 배선. (`search_catalog_bootstrap=true`, high min row/file gates)
- [x] main bootstrap 직후 catalog-mode input 재준비 배선. (`Prepare canonical catalog main inputs after bootstrap`)
- [x] result row contract audit 구현 및 searchIndexDelta/Main evidence artifact 업로드 배선. (`resultContract.py`, `evaluateSearchResultContract.py`)
- [x] `dartlab.search.indexInfo()` / `dartlab.search.prefetch()` top-level helper surface 연결 및 smoke. (`src/dartlab/__init__.py`, `test_manifest_info.py`)
- [x] 운영 proof bundle 과 장기 유지보수 control points 를 mainPlan 운영 문서에 반영. (`03-data-indexing-ops.md`, `10-production-pipeline-prd.md`, `11-operator-runbook.md`, `12-pipeline-maintenance-map.md`)
- [x] 원격 HF source/search evidence audit CLI 와 workflow artifact 업로드 배선. (`checkSearchRemoteEvidence.py`, `searchRemoteEvidence.{delta,main}.json`)
- [x] 실제 HF remote evidence audit 실행 및 원격 blocker/해소 기록. (초기 `valid=false` -> EDGAR mirror/sourceCatalog/contentIndex promote 후 `valid=true`)
- [x] remote evidence 기반 search catalog bootstrap 실행 계획 CLI 구현. (`planSearchBootstrap.py`, `searchBootstrapPlan.json`)
- [x] proof bundle 실패 시 bootstrap next actions 자동 포함. (`buildSearchProofBundle.py`, `searchProofBundle.json.nextActions.bootstrapPlan`)
- [x] cutover state audit CLI 및 workflow evidence artifact 배선. (`evaluateSearchCutover.py`, `searchCutover.{delta,main}.json`)
- [x] HF manifest-pointer publish 단일 `create_commit` batch 전환. (`publishIndex.py`)
- [x] HF source catalog upload 단일 `create_commit` batch 전환. (`buildSearchCatalog.py`)
- [x] public `dartlab.search(..., topK=N)` alias 와 provider API 호환 계약 구현. (`src/dartlab/__init__.py`, `api.py`)
- [x] query 본문 회사명 resolver 를 pre-rank stockCode facet 으로 연결. (`facetPlanner.py`, `api.py`)
- [x] 제품화 상태 감사 CLI 구현 및 searchIndexDelta/Main hard gate 배선. (`evaluateSearchProductizationStatus.py`, `searchProductizationStatus.{delta,main}.json`, `--fail-on-ops-not-ready`, `--fail-on-release-not-ready`)
- [x] manifest `sourceCanaryPack` 기반 canary report 생성 경로 구현 및 workflow evidence artifact 배선. (`evaluateSearchCanary.py --manifest`, `searchCanary.{delta,main}.json`)
- [x] 실제 full-source HF artifact 결과로 result contract/canary/proof bundle 통과 report 확보. (`searchProofBundle.full_lite`)
- [x] EDGAR freshness 를 채운 새 full rebuild artifact 로 `localIndexMissingSourceDataAsOf:edgar-panel` blocker 제거. live proof bundle local indexInfo 가 `edgar-panel:20260630` 을 반환한다.
- [x] productization proof bundle 생성 CLI 와 workflow artifact 배선.
- [x] productization proof bundle 실패 시 bootstrap next actions 포함. (`buildSearchProofBundle.py`, `searchBootstrapPlan.json`, `nextActions.bootstrapPlan`)
- [x] S1/S2/S3/S4 cutover state audit 구현. (`evaluateSearchCutover.py`)
- [x] source owner search catalog Actions evidence artifact 배선.
- [x] source manifest set freeze 를 contentIndex required file 과 productization ops gate 에 연결.
- [x] graph catalog sidecar 를 offline/copy prep, contentIndex required file/publish/pull 후보, runtime discovery 에 연결. (`entityGraphCatalog.parquet`, `entityGraph.py`, `entityGraphCatalog.py`, `fieldIndexRebuild.py`)
- [x] graph catalog sidecar 를 remote evidence/status summary 에 노출. (`checkSearchRemoteEvidence.py`, `evaluateSearchProductizationStatus.py`)
- [x] query-log quality toolchain drill 구현 및 workflow artifact 배선. (`runSearchQualityDrill.py`, `searchQualityDrill.{delta,main}.json`)
- [x] source catalog producerRun lineage 를 source manifest/source_manifest_set/status ops gate 에 연결.
- [x] contentIndex `source_manifest_set.json` 원격 파일을 직접 열어 내부 source별 `producerRun` 누락을 S2 blocker 로 연결.
- [ ] `searchIndexMain.yml` catalog mode 실제 Actions run 에서 source manifest snapshot lineage 확인.
- [ ] 실제 query-log 100~300 rows 확보 후 졸업 gate 실행.

---

## 5. 본진 구현 현황

완료된 1차 구현:

- `resultSchema.py`: `source/sourceRef/dataAsOf/snippet/answerable/notAnswerableReason/fieldCards` 기본 결과 계약을 보정한다.
- `resultContract.py`: 제품 결과 row 의 `source/sourceRef/dataAsOf/snippet/answerable/fieldCards` 와 card evidence 를 감사한다.
- `sourceManifest.py`: allFilings, DART panel, EDGAR panel, public news, GDELT 후보 source manifest 를 검증한다.
- `catalog.py`: `docKey/textHash/metadataHash/deleted` 기반 new/changed/deleted/unchanged diff 를 계산한다.
- `pipeline.py`: previous/current catalog snapshot 과 source manifest 를 읽어 delta dry-run/selfcheck report 를 만들고, new/changed rows 를 `buildContentSegment` 입력으로 export 한다.
- `pipeline.py`: expected source set 의 빈 full snapshot 과 current catalog row 0 을 invalid 로 처리한다.
- `fieldIndex.py` / `unified.py`: content/auto 직접 검색 결과도 제품 결과 계약을 통과한다.
- `sourceIntent.py`: 뉴스/공시 source 의도를 작은 일반 정책으로 판정한다. `공시 말고 뉴스`, `뉴스 말고 공시`, `뉴스만`, `공시 원문` 류를 source family 로 바꾸되 회사/이벤트별 mapper 는 만들지 않는다.
- `fieldIndex.py` / `unified.py`: source family mask 를 corp/stock mask 처럼 랭킹 전에 적용한다. 뉴스가 전역 top-N 에 밀려 사라지는 사후 필터 결함을 막는다.
- `answerability.py`: source mismatch, missing sourceRef, missing snippet, missing dataAsOf 를 `notAnswerableReason` 으로 분리한다.
- `facetPlanner.py`: receipt/date/report/company facets 를 추출하고, answerability 에서 불일치 row 를 `facetMismatch:*` 로 내린다.
- `evidencePack.py`: normalized row 에서 sourceRef, source, company/report/section/date/url/snippet 기반 evidence cards 를 만든다.
- `fieldIndex.py` / `fieldIndexRebuild.py`: `evidenceText` 를 bounded 메타로 저장해 snippet 밖 query window 를 고를 수 있게 한다.
- `fieldIndexRebuild.py` / `sourceCatalog.py`: EDGAR panel 의 실제 filing date 계열 컬럼을 freshness 로 보존하되 accession 에서 날짜를 추정하지 않는다.
- `evidencePack.py`: query-focused bounded chunk evidence card 를 추가한다.
- `memoryCard.py`: answerable rows 를 `sourceRefs + cards + dataAsOfBySource` 형태의 LLM memory-card set 으로 바꾼다.
- `qualityGate.py`: query-log gold 를 real/proxy/reviewed 로 분리하고 product readiness metrics 와 release blockers 를 산출한다.
- `qualityGate.py`: `answerable=False` result 는 sourceRef 가 맞아도 doc/citation hit 로 세지 않는다.
- `canaryPack.py`: source intent/sourceRef/no-answer trap canary pack 을 평가한다.
- `artifactCanary.py`: `main_meta.parquet` 에서 source별 canary row 와 no-answer trap 을 생성한다.
- `sourceCatalog.py`: local source parquet 에서 source manifest 와 normalized catalog snapshot 을 만든다.
- `sourceCatalog.py`: full snapshot completeness 를 검증하고 manifest 에 `completenessCheck` 를 기록한다.
- `sourceCatalog.py`: 이전 full source manifest 대비 files/rows/catalogRows 급락을 `previousFileDrop`/`previousRowDrop`/`previousCatalogRowDrop` 으로 차단한다.
- `.github/scripts/search/buildSearchCatalog.py`: source owner workflow 가 source manifest/catalog snapshot 을 만들고 HF 에 단일 `create_commit` batch 로 업로드하는 CLI.
- `.github/scripts/search/buildSearchCatalog.py`: GitHub Actions run lineage 를 source manifest `producerRun` 으로 보존한다.
- `.github/scripts/search/buildSearchCatalog.py`: `--compare-remote-manifest --require-previous-manifest` 로 source-owner incremental runner 가 직전 HF full manifest 없이 full publish 하지 못하게 한다.
- `.github/workflows/searchIndexMain.yml`: source catalog 가 없어서 raw full HF pull fallback 으로 간 run 에서 canonical source catalog 4종을 `searchIndexMain.full-pull` producer 로 publish 한다.
- `.github/workflows/searchIndexMain.yml`: canonical source catalog bootstrap 직후 `prepareSearchDeltaInputs.py` 를 다시 실행해 같은 run 의 main build 를 catalog-mode lineage 로 고정한다.
- `.github/workflows/originalSync.yml`, `.github/workflows/newsArchiveSync.yml`, `.github/workflows/edgarSync.yml`: manual `search_catalog_bootstrap=true` input 일 때만 previous manifest 요구를 해제하고, source별 높은 min-files/min-rows/min-catalog-rows 하한으로 첫 canonical source catalog 를 만들 수 있게 한다.
- `.github/scripts/search/planSearchBootstrap.py`: current remote evidence 또는 live audit 를 읽어 missing source catalog/contentIndex tier 를 판정하고, source-owner bootstrap, catalog-mode Search Main, remote evidence/proof bundle 검증 명령을 JSON plan 으로 남긴다.
- `.github/scripts/search/planSearchBootstrap.py`: productization status 의 의미적 blocker 를 받아 source-owner bootstrap/Search Main action 으로 변환한다.
- `.github/scripts/search/prepareSearchDeltaInputs.py`: HF 에서 받은 source catalog artifacts 를 current catalog 로 합치고 `searchIndexDelta` catalog mode env 를 준비한다.
- `.github/scripts/search/prepareSearchDeltaInputs.py`: source별 `producerRun` 을 `source_manifest_set.json` 에 보존한다.
- `.github/scripts/search/evaluateSearchGold.py`: real query-log gold 를 실제 `dartlab.search(...)` 또는 precomputed results 로 평가하고 quality report/miss ledger 를 만든다.
- `.github/scripts/search/prepareSearchGold.py`: raw query log 와 reviewer label 을 canonical `queryLogGold.real.jsonl` 로 합치고 release coverage/sourceRef/review status 를 검증한다.
- `api.py` / `goldLog.py`: `DARTLAB_SEARCH_QUERY_LOG` 가 켜진 검색 호출을 `queryLogRaw.jsonl` 후보 row 로 기록한다. top sourceRef/source/answerability/dataAsOf 를 같이 남겨 reviewer 가 바로 label 을 붙일 수 있게 한다.
- `.github/scripts/search/evaluateSearchResultContract.py`: 실제 검색 또는 precomputed results 로 제품 result row 계약 report 를 만든다. searchIndexDelta/Main workflow 는 이 report 를 evidence artifact 에 포함한다.
- `.github/scripts/search/evaluateSearchCanary.py`: source/no-answer canary pack 을 실제 검색 또는 precomputed results 로 평가하고 canary report 를 만든다.
- `.github/scripts/search/evaluateSearchCanary.py`: search manifest 의 `sourceCanaryPack` 을 직접 읽어 artifact 기반 canary report 를 만든다.
- `.github/scripts/search/runSearchPipelineDrill.py`: synthetic raw source parquet 에서 source catalog 4종을 만들고, `prepareSearchDeltaInputs.py` 로 `source_manifest_set.json` 과 catalog-mode current catalog 를 freeze 한 뒤 catalog diff, contentIndex build, staging upload/current manifest pointer publish, activation, rollback 을 검증한다.
- `.github/scripts/search/verifySearchHfRoundTrip.py`: 실제 HF current manifest 를 내려받아 local staged activation 과 rollback 을 검증하고 evidence JSON 을 남긴다.
- `.github/scripts/search/checkSearchRemoteEvidence.py`: 실제 HF source catalog 와 contentIndex current manifest inventory 를 감사하고 proof bundle 용 JSON 을 남긴다.
- `.github/scripts/search/checkSearchRemoteEvidence.py`: source manifest `producerRun` 을 remote evidence summary 에 포함한다.
- `.github/scripts/search/checkSearchRemoteEvidence.py`: contentIndex `fileSources` 로 `source_manifest_set.json` 을 실제 로드하고 set 내부 source별 `producerRun` 누락을 summary 에 포함한다.
- `.github/scripts/search/evaluateSearchProductizationStatus.py`: remote evidence, local indexInfo, HF round-trip, result contract, canary, quality report 를 모아 design/ops/release readiness 와 blockers 를 산출한다.
- `.github/scripts/search/evaluateSearchProductizationStatus.py`: source catalog `producerRun` 이 없으면 S2 opsReady 를 차단한다.
- `.github/scripts/search/evaluateSearchProductizationStatus.py`: contentIndex source manifest set 내부 source별 `producerRun` 이 없으면 `remoteContentManifestSetMissingProducerRun:*` 로 S2 opsReady 를 차단한다.
- `.github/scripts/search/evaluateSearchProductizationStatus.py`: quality report 의 `releaseEligible` 외에 `realReviewedRows`, origin/review counts, target coverage 를 재검증해 synthetic/proxy/unreviewed rows 로 releaseReady 가 되지 않게 한다.
- `.github/scripts/search/runSearchQualityDrill.py`: drill canonical gold 는 `drillSynthetic`/`drillReviewed` 로 표식해 real query-log gold 와 분리한다.
- `.github/scripts/search/buildSearchProofBundle.py`: remote source/content blocker 가 있으면 `searchBootstrapPlan.json` 을 함께 생성하고 `searchProofBundle.json.nextActions.bootstrapPlan` 으로 다음 운영 명령 plan 을 연결한다.
- `.github/scripts/search/evaluateSearchCutover.py`: proof bundle 과 optional replacement evidence 를 읽어 cutover state, defaultReplacement, replacement blockers 를 산출한다.
- `.github/scripts/search/evaluateSearchCutover.py`: S4 는 catalog default/scheduled mode, legacy fallback 운영자 전용, fail-closed publish, rollback/run evidence 없이는 통과하지 않는다.
- `publishIndex.py`: `promoteCurrent=False` 로 current pointer 를 바꾸지 않는 staged candidate manifest publish 를 지원한다.
- `verifySearchHfRoundTrip.py` / `localUpdate.py`: current manifest 뿐 아니라 explicit staged `manifestRepoPath` 도 activate/rollback 검증할 수 있다.
- `api.py`: `scope="both"` 가 title/content 공통 컬럼만 남기던 문제를 union concat 으로 수정했다.
- `manifest.py`: `manifest.json` 기반 `indexInfo()` freshness/source count/compatibility 계약을 추가했다.
- `src/dartlab/__init__.py`: `dartlab.search.indexInfo()` 와 `dartlab.search.prefetch()` helper 를 기존 search 함수 attribute 로 노출한다.
- `fieldIndexRebuild.writeIndexManifest()`: artifact 기반 `sourceCanaryPack` 을 manifest 에 싣는다.
- `artifactCanary.py`: positive canary row 는 `requireAnswerable=true` 로 생성해 source lane 만 맞는 빈 evidence 결과를 publish/local activation smoke 에서 통과시키지 않는다.
- `localUpdate.py`: HF manifest artifact 를 staging 으로 받은 뒤 required files/hash/load smoke/canary query 를 통과하면 `active.json` 을 atomic swap 한다.
- `localUpdate.py`: local activation 전 schema compatibility 와 `sourceCanaryPack` source/no-answer canary 를 함께 검증한다.
- `localUpdate.py`: active pointer 에 `previousActiveDir` 를 보존하고 `rollbackActiveIndex()` 로 이전 active 를 selfcheck 후 복구한다.
- `publishIndex.py`: HF upload 전에 local manifest/hash/canary selfcheck 를 수행하고, 통과한 artifact 파일은 staging 에 올린 뒤 current 에는 `fileSources` 를 가진 manifest pointer 만 publish 한다.
- `publishIndex.py`: manifest-pointer publish 는 staging files 와 current manifest pointer 를 단일 `create_commit` batch 로 묶어 HF 429 표면을 줄인다.
- `buildSearchCatalog.py`: source manifest 와 catalog snapshot 도 단일 `create_commit` batch 로 묶어 source owner publish 의 HF 429 표면을 줄인다.
- `fieldIndexRebuild.writeIndexManifest()`: main/delta segment 의 source count, sourceDataAsOf, requiredFiles, fileHashes 를 `manifest.json` 으로 쓴다.
- `.github/scripts/search/buildSearchMain.py` / `buildSearchDelta.py`: contentIndex publish 대상에 `manifest.json` 을 포함한다.
- `fieldIndexRebuild.ensureContentIndex()`: manifest 기반 staged activate 를 먼저 시도하고, manifest 없는 기존 HF artifact 는 legacy direct pull 로 fallback 한다.
- `api.py`: `"삼성전자"` 같은 짧은 한글 회사명이 US ticker 안내로 빠지는 오판을 막았다.
- `src/dartlab/__init__.py` / `api.py`: `topK` 를 `limit` alias 로 받아 기존 문서/Skill OS 호출 계약과 실제 public call 을 맞췄다.
- `facetPlanner.py` / `api.py`: query 본문 안의 회사명을 `ListingResolver.nameToCode()` 로 해석해 `stockCode` pre-rank facet 으로 적용한다. 이 일반 정책으로 계열사명 누수를 줄이고, 명시적 `corp="삼성전자"` 도 한국어 resolver 컬럼까지 처리한다.

검증:

- `tests/search/test_product_result_schema.py`: 3 passed.
- `tests/search/test_catalog_delta.py`, `tests/providers/dart/search/test_sourceManifest.py`: 5 passed.
- `tests/search/test_unified_fusion.py`, `test_news_integration.py`, `test_scope.py`: 19 passed, 1 skipped.
- `tests/providers/dart/search/test_localUpdate.py`, `tests/search/test_active_pointer.py`: 9 passed.
- `tests/search/test_manifest_info.py`, `tests/providers/dart/search/test_manifest.py`, `tests/search/test_schema_version.py`, `test_distribution.py`, `test_index_tier.py`: 28 passed.
- `tests/search/test_search_publish_scripts.py`, `tests/search/test_index_tier.py`, `tests/providers/dart/search/test_fieldIndexRebuild.py`: 13 passed.
- `tests/search/test_pipeline_delta_plan.py`, `tests/search/test_search_publish_scripts.py`: 21 passed, `buildSearchDelta.py` dry-run/catalog build subprocess, empty expected source 차단, workflow env override smoke 포함.
- `tests/search/test_schema_version.py`, `test_distribution.py`, `test_index_tier.py`: 16 passed.
- `tests/search/test_source_intent_answerability.py`, `test_news_integration.py`, `test_product_result_schema.py`, `test_unified_fusion.py`, `test_scope.py`: 27 passed, 1 skipped. source intent hard isolation, pre-rank source mask, answerability 기본 판정, evidence/memory card 기본 계약, EDGAR filing date freshness 보존 포함.
- `tests/providers/dart/search/test_localUpdate.py`: 15 passed. active manifest 비교, 동일/오래된 remote skip, manifest `fileSources` download, sourceCanaryPack activation gate 포함.
- `tests/providers/dart/search/test_localUpdate.py`, `tests/search/test_active_pointer.py`: 13 passed. active rollback helper 와 invalid rollback 보존 포함.
- `tests/search/test_search_publish_scripts.py`: 10 passed. catalog delta mode, workflow inputs, source workflow catalog build step smoke 포함.
- `tests/search/test_prepare_search_delta_inputs.py`, `test_search_catalog_script.py`, `tests/providers/dart/search/test_sourceCatalog.py`: 8 passed. source manifest/catalog generation, EDGAR filing date freshness, delta env preparation 포함.
- `tests/providers/dart/search/test_sourceCatalog.py`, `tests/search/test_search_catalog_script.py`, `tests/search/test_search_publish_scripts.py`: 33 passed. source catalog completeness check, empty full snapshot 차단, previous full manifest drop guard, source-owner previous manifest requirement, main canonical bootstrap workflow smoke, publish script contract 포함.
- `tests/providers/dart/search/test_publishIndex.py`, `test_localUpdate.py`, `test_sourceCatalog.py`, `tests/search/test_search_pipeline_drill_script.py`, `test_search_publish_scripts.py`, `test_unified_fusion.py`: 45 passed. manifest pointer publish, local `fileSources` activation, EDGAR freshness, local pipeline drill 포함.
- `tests/providers/dart/search/test_qualityGate.py`, `tests/search/test_search_quality_gate_script.py`: 8 passed. query-log gold/miss ledger gate, non-answerable hit 차단, CLI precomputed result path 포함.
- `tests/providers/dart/search/test_publishIndex.py`, `tests/search/test_search_remote_evidence_script.py`, `tests/search/test_search_publish_scripts.py`: 23 passed. publish selfcheck hash mismatch 차단, manifest pointer `fileSources`, batch `create_commit`, remote evidence audit, workflow evidence path 포함.
- `tests/search/test_search_catalog_script.py`, `tests/search/test_search_publish_scripts.py`: 20 passed. source catalog upload batch `create_commit` helper, previous-manifest drop guard, workflow/static publish 계약 포함.
- `tests/providers/dart/search/test_answerability.py`, `test_facetPlanner.py`, `test_api.py`: 24 passed. query 회사명 facet, 명시적 회사명 corp resolver, stockCode match answerability 포함.
- `tests/search/test_source_intent_answerability.py`, `test_scope.py`: 15 passed. public `topK` alias, query 회사명 pre-rank stock filter, source intent/answerability regression 포함.
- live product smoke: `dartlab.search("삼성전자 대표이사 변경", topK=5)` 는 수정 후 `stock_code=005930` 결과만 반환. 수정 전에는 삼성카드/삼성에스디에스/삼성SDI 가 상위에 섞였다.
- `tests/search tests/providers/dart/search`: 285 passed. search 하위 전체 회귀, source-owner drop guard, main canonical bootstrap workflow smoke, productization proof bundle/status/remote evidence gate 포함.
- `ruff check src/dartlab/providers/dart/search .github/scripts/search tests/providers/dart/search tests/search`: pass.
- `ruff format --check src/dartlab/providers/dart/search .github/scripts/search tests/providers/dart/search tests/search`: pass, 105 files already formatted.
- workflow YAML parse: `originalSync.yml`, `newsArchiveSync.yml`, `edgarSync.yml`, `searchIndexDelta.yml`, `searchIndexMain.yml` pass.
- `tests/providers/dart/search/test_canaryPack.py`, `tests/search/test_search_canary_script.py`: 5 passed. source/no-answer canary pack 과 CLI precomputed result path 포함.
- `tests/search/test_search_productization_status_script.py`, `test_search_canary_script.py`, `test_search_publish_scripts.py`, `tests/providers/dart/search/test_artifactCanary.py`, `test_canaryPack.py`, `test_fieldIndexRebuild.py`: 30 passed. 제품화 상태 감사 CLI, canary source coverage, manifest 기반 canary pack, workflow hard gate, EDGAR period freshness 계약 포함.
- actual productization status CLI 초기값은 `localIndexMissingSourceDataAsOf:edgar-panel` blocker 를 포함했지만, 이후 proof bundle 재실행에서 `sourceDataAsOf.edgar-panel` 이 해소됐다. 최종 direct-review proof bundle 은 `opsReady=true`, `releaseReady=true`, blockers=[] 다.
- 초기 remote evidence 재확인(2026-06-16): `checkSearchRemoteEvidence.py --expected-sources allFilings,dartPanel,edgarPanel,newsPublic --content-tiers full,lite` 는 `valid=false`, blockers=`sourceCatalogMissing`, `contentIndexManifestMissing` 였다. EDGAR mirror 보정, source catalog upload, full/lite promote 뒤 같은 audit 는 `valid=true`, errors=[] 로 통과했다.
- `tests/search/test_search_pipeline_drill_script.py`: 1 passed. raw source parquet -> source catalog -> source manifest set freeze -> local end-to-end pipeline drill subprocess 포함.
- `tests/search/test_search_pipeline_drill_script.py`, `tests/search/test_search_publish_scripts.py`, `tests/search/test_prepare_search_delta_inputs.py`: 20 passed. post-bootstrap catalog input freeze, sourceManifestSet drill report, workflow static smoke, prepare env 계약 포함.
- `tests/search/test_search_hf_roundtrip_script.py`: 1 passed. local fake HF 로 실제 round-trip CLI activate/rollback path 포함.
- `tests/search/test_search_remote_evidence_script.py`: local fake HF 로 remote evidence audit complete/missing path 포함.
- `tests/search/test_search_remote_evidence_script.py`, `tests/search/test_search_productization_status_script.py`, `tests/search/test_search_publish_scripts.py`: 25 passed. contentIndex `source_manifest_set.json` 원격 fileSources load, set 내부 `producerRun` summary, `remoteContentManifestSetMissingProducerRun:*` blocker 포함.
- `tests/search/test_search_pipeline_drill_script.py`, `tests/search/test_prepare_search_delta_inputs.py`: 4 passed. raw source -> source catalog -> source manifest set freeze drill 과 catalog env/fallback 계약 포함.
- `tests/search/test_search_publish_scripts.py`: 16 passed. searchIndexMain raw bootstrap 12회 resume, 310초 quota window, public news path, source/catalog/proof bundle workflow wiring 퇴행 차단 포함.
- `tests/search/test_search_catalog_script.py`, `tests/providers/dart/search/test_sourceCatalog.py`, `tests/search/test_search_publish_scripts.py`: 33 passed. source catalog completeness, previous-manifest drop guard, source-owner explicit bootstrap input/high threshold wiring 포함.
- `tests/search/test_search_bootstrap_plan_script.py`, `tests/search/test_search_publish_scripts.py`: 18 passed. missing remote evidence 를 source-owner bootstrap/Search Main/검증 명령 plan 으로 바꾸는 계약과 source-owner workflow wiring 포함.
- `tests/search/test_search_proof_bundle_script.py`, `tests/search/test_search_bootstrap_plan_script.py`, `tests/search/test_search_productization_status_script.py`: 10 passed. proof bundle 이 complete evidence 에서는 bootstrap plan 을 만들지 않고, source/content 원격 blocker 에서는 `searchBootstrapPlan.json` 과 `nextActions.bootstrapPlan` 을 포함하는 계약 검증.
- `tests/search/test_search_cutover_script.py`, `tests/search/test_search_publish_scripts.py`, `tests/search/test_search_proof_bundle_script.py`: 21 passed. S1/S3/S4 cutover 판정, replacement evidence 요구, workflow `searchCutover.{delta,main}.json` artifact wiring 포함.
- 초기 live proof bundle 재실행(2026-06-16): `buildSearchProofBundle.py --query "삼성전자 대표이사 변경" --skip-quality` 는 원격 산출물/round-trip 증거 부재로 `opsReady=false` 를 반환했다. 이 상태는 full_lite HF publish/round-trip/promote 뒤 `opsReady=true` 로, direct-review 품질팩 뒤 `releaseReady=true` 로 supersede 됐다.
- 초기 bootstrap plan 생성(2026-06-16): 원격 source/content manifest 가 비어 있을 때 `planSearchBootstrap.py --out <temp>` 는 missingSources=`allFilings,dartPanel,edgarPanel,newsPublic`, missingContentTiers=`full,lite` 를 반환했다. 이후 local HF bootstrap 으로 이 plan 의 원격 blocker 는 해소됐다.
- `tests/search/test_search_bootstrap_plan_script.py`, `test_search_proof_bundle_script.py`, `test_search_productization_status_script.py`, `test_search_cutover_script.py`, `test_search_quality_drill_script.py`, `test_search_publish_scripts.py`, `tests/providers/dart/search/test_artifactCanary.py`, `test_canaryPack.py`: 40 passed. semantic blocker -> bootstrap action, quality report 재검증, S4 replacement evidence hardening, artifact positive canary answerability 포함.
- `ruff check` / `ruff format --check` on productization scripts/tests/artifactCanary: pass, 14 files already formatted.
- workflow YAML parse 재확인: `originalSync.yml`, `newsArchiveSync.yml`, `edgarSync.yml`, `searchIndexDelta.yml`, `searchIndexMain.yml` pass.
- 초기 cutover audit 재실행(2026-06-16): 당시 proof bundle 은 `state=S1_DESIGN_READY`, `opsReady=false`, `releaseReady=false`, `defaultReplacement=false` 로 판정됐다. 최신 cutover 기준은 `13-cutover-contract.md` v0.8 을 따른다: direct-review proof 는 `S4_DEFAULT_REPLACEMENT` 다.
- `tests/search/test_search_bootstrap_plan_script.py`, `test_search_proof_bundle_script.py`, `test_search_productization_status_script.py`, `test_search_cutover_script.py`, `test_search_quality_drill_script.py`, `test_search_publish_scripts.py`, `test_search_hf_roundtrip_script.py`, `tests/providers/dart/search/test_artifactCanary.py`, `test_canaryPack.py`, `test_publishIndex.py`, `test_fieldIndexRebuild.py`: 57 passed. stage-only candidate publish, staged manifest round-trip, quality/status/cutover hardening 포함.
- `tests/providers/dart/search/test_publishIndex.py`, `tests/search/test_search_promote_candidate_script.py`, `test_search_hf_roundtrip_script.py`, `test_search_publish_scripts.py`: 31 passed. candidate manifest promote helper/CLI, workflow stage-only gate/promote wiring 포함.
- `tests/search/test_search_publish_scripts.py`: 18 passed. catalog-mode lite filter regression 포함.
- `ruff check .github/scripts/search/buildSearchMain.py tests/search/test_search_publish_scripts.py`: pass.
- `ruff format --check .github/scripts/search/buildSearchMain.py tests/search/test_search_publish_scripts.py`: pass.
- live HF source/content evidence 재확인(2026-06-16): `checkSearchRemoteEvidence.py --expected-sources allFilings,dartPanel,edgarPanel,newsPublic --content-tiers full,lite --fail-on-missing` 는 `valid=true`, errors=[].
- live full/lite proof bundle(2026-06-16): `buildSearchProofBundle.py --content-tiers full,lite --skip-quality` 는 quality 미포함이라 `opsReady=true`, `releaseReady=false` 였고, direct-review quality report 포함 proof 는 `releaseReady=true` 로 supersede 됐다.
- live sample search(2026-06-16): `환율 리스크`, `공시 말고 뉴스로 반도체`, `edgar revenue risk`, `유상증자` 가 각각 news/news/edgar-panel/allFilings sourceRef 결과를 반환.
- `tests/search/test_search_bootstrap_plan_script.py`, `test_search_proof_bundle_script.py`, `test_search_productization_status_script.py`, `test_search_cutover_script.py`, `test_search_quality_drill_script.py`, `test_search_publish_scripts.py`, `test_search_hf_roundtrip_script.py`, `test_search_promote_candidate_script.py`, `tests/providers/dart/search/test_artifactCanary.py`, `test_canaryPack.py`, `test_publishIndex.py`, `test_fieldIndexRebuild.py`: 60 passed. fail-closed staged candidate publish, candidate round-trip, promote CLI, productization status, cutover, canary, quality drill, workflow static smoke 를 한 번에 검증.
- `ruff check` / `ruff format --check` on publish/promote/round-trip scripts, publish/local update helpers, workflow tests: pass.
- workflow YAML parse 재확인: `originalSync.yml`, `newsArchiveSync.yml`, `edgarSync.yml`, `searchIndexDelta.yml`, `searchIndexMain.yml` pass.
- `ruff check src/dartlab/providers/dart/search .github/scripts/search tests/providers/dart/search tests/search`: pass.
- `ruff format --check src/dartlab/providers/dart/search .github/scripts/search tests/providers/dart/search tests/search`: pass, 105 files already formatted.
- workflow YAML parse 재확인: `originalSync.yml`, `newsArchiveSync.yml`, `edgarSync.yml`, `searchIndexDelta.yml`, `searchIndexMain.yml` pass.
- `tests/providers/dart/search/test_artifactCanary.py`, `test_fieldIndexRebuild.py`, `test_publishIndex.py`, `test_localUpdate.py`, `tests/search/test_search_hf_roundtrip_script.py`, `test_search_pipeline_drill_script.py`: 30 passed. artifact canary pack 생성, manifest 주입, publish/local activation 평가 포함.
- `tests/providers/dart/search/test_goldLog.py`, `tests/search/test_prepare_search_gold_script.py`: 6 passed. raw query log + reviewer label merge, canonical JSONL output, release eligibility summary, proxy/unreviewed/missing sourceRef 차단 포함.
- `tests/providers/dart/search/test_goldLog.py`, `test_api.py`: raw query-log candidate append 와 `DARTLAB_SEARCH_QUERY_LOG` 기반 search hook 포함.
- `tests/providers/dart/search/test_resultContract.py`, `tests/search/test_search_result_contract_script.py`: 6 passed. result row 필수 필드, fieldCards evidence, JSON/JSONL nested result flatten, precomputed/live CLI 경로 포함.
- `tests/search/test_search_publish_scripts.py`: workflow static smoke 에 result contract audit step 과 evidence artifact path 포함.
- `tests/search/test_manifest_info.py`: top-level `dartlab.search.indexInfo()` / `prefetch()` helper surface 포함.
- local runtime result contract smoke: `evaluateSearchResultContract.py --query "유상증자" --query "공시 말고 뉴스로 환율 기사" --query "HBM 투자 계획" --min-rows 3 --fail-on-error` 통과. 30 result rows, invalidRows 0, validRate 1.0. HF/Actions full-source evidence 는 아님.
- `ruff format --check` / `ruff check` on search provider, search tests, search scripts, top-level public search: pass. 98 files formatted/check scope.
- focused post-format smoke: `tests/providers/dart/search/test_fieldIndexRebuild.py`, `tests/search/test_search_productization_status_script.py`: 8 passed.
- `tests/audit/dartlabGuard.py strict --scope l0-l15 --providers dart,edgar`: pass. files scanned 1427, rules passed 7, cycleScan, architecturePytest, folderMirror, gatherGate, providerGate, publicApiSmoke 포함.
- HF raw local bootstrap(2026-06-16): HF file list 는 allFilings 430, dartPanel 2930, edgarPanel 2622, news enriched 18 을 확인했다. `snapshot_download` 와 EDGAR missing-file direct download 는 로컬 네트워크 timeout 으로 완전 mirror 에 실패했지만, 기존 HF local cache 와 복구한 news enriched 로 source catalog 4종과 combined catalog 453,441 rows 를 생성했다.
- `buildSearchMain.py` catalog mode: `DARTLAB_SEARCH_CURRENT_CATALOG=data/dart/searchCatalog/main.current.catalog_snapshot.parquet` 로 453,441 docs main contentIndex 를 2.2분에 빌드했다. `HF_TOKEN`/cached HF token 이 없어 upload 는 스킵됐다.
- HF raw local proof 초기 재실행(2026-06-16): EDGAR mirror 보정 전 local indexInfo 는 `nDocs=453441`, `nDocsBySource={allFilings:192095, panel:104761, edgar-panel:74787, news:81798}` 였고 result contract/canary 는 통과했다. EDGAR mirror 보정 후 최종 full current 는 462,947 docs 로 승격됐다.
- `tests/providers/dart/search/test_answerability.py`, `test_canaryPack.py`, `test_artifactCanary.py`: 10 passed. panel report facet 이 `report_nm` 없이 evidence text 로도 answerable 처리되는 회귀 포함.
- `evaluateSearchCanary.py --manifest data/dart/contentIndex/manifest.json --fail-on-error`: passRate 1.0, failureCount 0.
- `ruff check src/dartlab/providers/dart/search/facetPlanner.py tests/providers/dart/search/test_answerability.py`: pass.
- graph catalog enrichment 1차 본진 연결(2026-06-16): `tests/_attempts/searchGraphCatalog` probe 로 small/multi-seed join 을 확인한 뒤 `entityGraph.py` 를 추가하고 `api.search()` 가 catalog 가 있을 때만 `entityCards/entityResolved/entityStockCode/entityCardCount` 를 붙이게 했다. `memoryCard.py` 는 `entityCards` 를 LLM memory-card 에 포함한다. catalog discovery 는 `DARTLAB_SEARCH_ENTITY_GRAPH_CATALOG` 또는 active contentIndex directory 의 `entityGraphCatalog.parquet`/`graph_catalog.parquet` 이며, 요청 경로 live traversal 은 없다. live smoke: env catalog 로 `dartlab.search("반도체 HBM 투자", scope="content", limit=3)` 가 한미반도체 rows 에 peer/stage/credit cards 를 반환했다.
- direct-review quality cycle 재실행(2026-06-16): `runSearchQualityCycle.py` 는 106 reviewable rows 에서 `valid=true`, `failedPhase=""` 를 반환했다. 산출물은 `data/dart/searchCatalog/searchQualityReviewPack.directReview/qualityCycleDirect/qualityReport.json`.
- direct-review replacement evidence 재실행(2026-06-16): `buildSearchReplacementEvidence.py --fail-on-incomplete` 는 `valid=true`, blockers=[] 를 반환했고 active manifest id `active:556922335c7dbae8`, previous manifest id `previous:d232e99ec3d5d319` 를 기록했다.
- direct-review cutover 재실행(2026-06-16): `evaluateSearchCutover.py --fail-on-default-not-ready` 는 `state=S4_DEFAULT_REPLACEMENT`, `defaultReplacement=true`, `releaseReady=true`, blockers=[] 를 반환했다.
- focused validation(2026-06-16): ruff check/format on replacement/proof/gold/status/search touched files pass. `tests/search/test_search_cutover_script.py`, `test_search_publish_scripts.py`, `test_search_quality_cycle_script.py`, `tests/providers/dart/search/test_qualityGate.py` 는 38 passed. search API/answerability/facet/result/product status/review pack 관련 focused set 은 51 passed.

아직 완료 아님:

- `searchIndexDelta.yml` 은 catalog default 이고 legacy 는 운영자 명시 dispatch 예외다. 다음 단계는 실제 scheduled run 에서 catalog artifacts 생성과 catalog-mode publish 를 확인하는 것이다.
- search publish 는 local manifest/hash/canary selfcheck 후 staging upload + current manifest pointer publish 를 코드상 사용하고, 2026-06-16 full/lite staged candidate 의 실제 HF round-trip/rollback/promote 를 통과했다. 다음 단계는 같은 순서를 GitHub Actions run artifact 로 남기는 것이다.
- local update 는 hash/load/canary smoke, sourceCanaryPack, schema compatibility, active manifest 비교, same/older remote skip, active swap, previous active rollback helper 까지 연결됐고, full/lite HF candidate round-trip 에서 활성화/롤백을 검증했다. 운영 runbook 상 주기적 rollback drill 은 계속 필요하다.
- `answerable` 은 source intent mismatch, missing evidence, receipt/date/report/company facet mismatch, stale source 까지 들어갔다.
- `fieldCards` 는 row-level sourceRef/snippet evidence card 와 bounded `evidenceText` chunk evidence 까지 들어갔고, result contract audit 와 workflow evidence upload 배선도 들어갔다. 실제 HF full-source artifact 기반 result contract 는 full_lite proof bundle 에서 통과했고, 더 넓은 evidence 품질은 real query-log gold/miss ledger 로 관리한다.
- source workflow 와 searchIndexDelta workflow 배선은 코드/정적 smoke 및 direct-review replacement evidence 로 검증했다. 실제 새 Actions run artifact 는 아직 재확인해야 한다.
- `prepareSearchDeltaInputs.py` 는 expected source set 을 강제한다. 일부 source catalog 만 있거나 `snapshotScope=partial` 이면 catalog mode env 를 만들지 않고 legacy fallback 으로 둔다. 실제 Actions run 에서 이 차단이 의도대로 동작하는지 확인이 필요하다.
- expected source catalog 가 0 row full snapshot 이면 source catalog 생성 CLI 와 catalog mode selfcheck 양쪽에서 막힌다. source-owner daily/incremental job 은 이전 full manifest 대비 drop guard 를 통과해야 하므로 partial runner tree 를 full 로 publish 할 수 없다. 실제 Actions run 에서 이 차단이 의도대로 동작하는지 확인이 필요하다.
- monthly main 은 source manifest snapshot lineage 를 코드상 우선 사용한다. source catalog 가 준비되지 않은 run 은 raw HF pull fallback 이며, 이때 canonical source catalog bootstrap 과 post-bootstrap catalog input freeze 를 같이 수행한다. 실제 Actions run 에서 bootstrap publish 와 이후 catalog mode 성공 증거가 필요하다.
- query-log gold 준비/평가 게이트, canonical 저장 위치, raw capture hook 은 들어갔다. direct-review 106 reviewer-labeled rows 는 release gate 를 통과했고, 남은 운영 목표는 300 rows 방향 확장이다.
- source/no-answer canary gate 와 local activation 연결, artifact 기반 canary pack 자동 생성, manifest 기반 canary report workflow 배선은 구현됐다. 다만 실제 Actions artifact 에서 생성된 canary report 와 운영자가 큐레이션한 최신 사건 rows 는 아직 필요하다.
- 제품화 상태 감사 CLI 는 direct-review 기준 현재 상태를 `opsReady=true`, `releaseReady=true` 로 판정한다. 원격 sourceCatalog/contentIndex manifest, expected source별 freshness, full/lite HF round-trip, result contract, canary source coverage, quality report 가 모두 통과했다.
- S4 defaultReplacement 는 releaseReady 와 별도다. 본진 기본값 교체는 catalog 단일 기본값, scheduled catalog mode, legacy fallback 운영자 전용, fail-closed publish, active/previous manifest, rollback/run evidence 가 replacement evidence 로 남아야 한다. direct-review replacement evidence 는 이 조건을 통과했다.
