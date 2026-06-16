# 08. 완성 설계 — HF 증분 · 로컬/퍼블릭/라이브러리 검색

상태: v1.4 (2026-06-16)
범위: 검색 엔진을 제품 수준으로 이식하기 위한 target architecture, artifact 운영, surface 계약.

---

## 1. 목표 계약

공개 Python 호출은 하나다.

```python
dartlab.search(
    query,
    corp=None,
    start=None,
    end=None,
    limit=10,
    topK=None,    # limit alias
    scope="auto",  # auto | title | content | both | news
)
```

제품 결과는 DataFrame 기반을 유지하되, row 또는 envelope 에 다음 필드를 필수로 둔다.

| 필드 | 의미 |
|---|---|
| `source` | `allFilings`, `panel`, `news` 등 source identity |
| `sourceRef` | 안정 citation id. 예: `dart:allFilings:{rceptNo}#section={sectionOrder}`, `news:{urlHash}` |
| `url` | DART viewer URL 또는 article URL |
| `dataAsOf` | source 또는 segment 기준 최신성 |
| `snippet` | LLM/UI 에 바로 줄 수 있는 짧은 근거 |
| `answerable` | facet/source/date/report 조건을 만족해 답변 가능한지 |
| `notAnswerableReason` | 후보가 있어도 답변 불가인 이유 |
| `fieldCards` | answer-critical field label, value, evidence |

빈 결과, 근거 부족 no-answer, stale index, answerable true 를 분리한다. 특히 "최신 공시" 성격은 stale index 에서 단정하지 않고 `Company.disclosure()` 또는 live path 로 라우팅한다.

2026-06-15 1차 본진 구현 상태:

- `resultSchema.py` 가 `sourceRef/dataAsOf/snippet/answerable/notAnswerableReason/fieldCards` 기본 필드를 보정한다.
- `sourceManifest.py` 와 `catalog.py` 가 source manifest 검증과 catalog changed-set diff 를 제공한다.
- `pipeline.py` 가 previous/current catalog + source manifest 기반 dry-run/selfcheck report 와 content-index delta export 를 제공한다. `buildSearchDelta.py` 는 dry-run 모드와 catalog delta build 모드 모두 subprocess 검증됐다.
- `fieldIndex.searchContent`, `unified.searchUnified`, `api.search` 는 focused test 기준 이 기본 결과 계약을 통과한다.
- `localUpdate.py` 와 `ensureContentIndex()` 는 manifest 기반 artifact 를 staging 에 받은 뒤 hash/load/canary selfcheck 통과 시 active pointer 를 전환한다. active manifest 와 같거나 더 오래된 remote manifest 는 required files download 전에 `skipped=notNewer` 로 거부한다.
- local activation selfcheck 는 schema compatibility 와 manifest 내 `sourceCanaryPack` 도 평가한다. source/sourceRef/no-answer trap 이 깨지면 active pointer 를 전환하지 않는다.
- `fieldIndexRebuild.writeIndexManifest()` 와 search publish scripts 는 `manifest.json` 을 빌드하고 HF 업로드 대상에 포함한다.
- `publishIndex.py` 는 contentIndex artifact 파일을 HF `_staging/{runId}` 에 먼저 올리고 current path 에는 `fileSources` 를 가진 `manifest.json` pointer 만 publish 한다. `buildSearchMain.py`, `buildSearchDelta.py`, `pushContentIndex()` 가 이 helper 를 사용한다.
- `publishIndex.py` 는 `promoteCurrent=False` stage-only publish 도 지원한다. 이 경우 current pointer 는 바뀌지 않고 staging candidate manifest 만 올라가며, `verifySearchHfRoundTrip.py --manifest-repo-path` 로 candidate 를 직접 activate/rollback 검증할 수 있다.
- Search Main/Delta workflow 는 stage-only candidate publish 후 candidate round-trip/result contract/canary/optional real quality 를 통과해야 `promoteSearchCandidate.py` 로 current pointer 를 바꾼다.
- `sourceIntent.py` 와 `answerability.py` 가 1차 본진 모듈로 들어갔다. `api.search()` 는 source intent 를 판정하고, `fieldIndex.py` / `unified.py` 는 source mask 를 랭킹 전에 적용한다.
- `evidencePack.py` 와 `memoryCard.py` 가 1차 본진 모듈로 들어갔다. fieldCards 는 sourceRef/snippet 기반 row-level evidence card 와 bounded `evidenceText` 기반 chunk card 를 담고, memory card set 은 answerable row 의 sourceRef set 을 LLM turn 에 넘긴다.
- `facetPlanner.py` 가 1차 본진 모듈로 들어갔다. receipt/date/report/company facets 를 추출하고 answerability 에서 mismatch 를 `facetMismatch:*` 로 표시한다.
- query 본문 회사명도 `ListingResolver` 기반 stockCode facet 으로 승격한다. `"삼성전자 대표이사 변경"` 같은 질의는 명시적 `corp` 가 없어도 pre-rank stock mask 를 적용하고, 계열사/유사명 누수를 regression 으로 막는다.
- public `topK` 는 `limit` alias 로 동작한다. Skill OS/문서 호출 계약과 실제 top-level/provider API 를 맞췄다.
- `fieldIndex.py` / `fieldIndexRebuild.py` 는 `evidenceText` 를 bounded 메타로 저장하고, `evidencePack.py` 는 query-focused chunk card 를 붙인다. 실제 full-source artifact 기반 품질 확인은 후속이다.
- `answerable` 은 source mismatch, missing sourceRef, missing snippet/dataAsOf, receipt/date/report/company facet mismatch, stale source 까지 판정한다.
- `sourceCatalog.py`, `buildSearchCatalog.py`, `prepareSearchDeltaInputs.py` 가 1차 본진/CI 배선으로 들어갔다. source owner workflow 는 source manifest/catalog snapshot 을 HF `dart/searchCatalog/{source}/` 로 올리고, search delta workflow 는 이를 current catalog 로 합쳐 catalog mode 를 준비한다. 실제 Actions run 에서 source catalog publish 와 scheduled catalog delta publish 를 확인해야 운영 완료다.
- `searchIndexMain.yml` 과 `buildSearchMain.py` 는 source catalog snapshot 이 준비되면 catalog 기반 main compaction 을 우선 사용한다. catalog 가 없으면 legacy raw rebuild 로 fallback 한다. 실제 Actions run 에서 catalog lineage 를 확인해야 운영 완료다.
- `qualityGate.py`, `evaluateSearchGold.py`, `runSearchQualityDrill.py`, `evaluateSearchProductizationStatus.py` 가 1차 본진/CI 배선으로 들어갔다. real/proxy/review status, release blockers, miss ledger 를 자동 산출하고, productization status 는 quality report 의 `releaseEligible` 외에 real reviewed rows/origin/review counts/target coverage 를 다시 검사한다. 실제 real query-log rows 로 실행한 증거는 아직 필요하다.
- `artifactCanary.py`, `canaryPack.py`, `evaluateSearchCanary.py` 가 1차 본진/CI 배선으로 들어갔다. `main_meta.parquet` 기반 source/no-answer canary pack 을 manifest 에 싣고, source isolation, expected sourceRef, positive answerability, no-answer false accept 를 빠르게 막는 canary report 를 만든다. 실제 Actions artifact report 와 운영 curated rows 는 아직 필요하다.
- `runSearchPipelineDrill.py` 가 1차 CI preflight 로 들어갔다. synthetic raw source parquet 에서 source catalog 와 `source_manifest_set.json` 을 freeze 한 뒤 catalog diff, contentIndex artifact build, staging upload/current manifest pointer publish, local activation, rollback 을 한 사이클 검증한다. 실제 HF/Actions 운영 증거는 별도 필요하다.
- `verifySearchHfRoundTrip.py` 가 post-publish smoke 로 들어갔다. 실제 HF current manifest 를 temp/local contentIndex 에 내려받아 activation/rollback 을 검증하고 workflow artifact 로 report 를 남긴다. 실제 Actions run 증거 확인은 아직 필요하다.
- `checkSearchRemoteEvidence.py` 와 `evaluateSearchProductizationStatus.py` 는 contentIndex `fileSources` 로 실제 `source_manifest_set.json` 을 열고, set 내부 source별 `producerRun` 이 비면 `remoteContentManifestSetMissingProducerRun:*` 로 S2 `opsReady` 를 차단한다. 따라서 manifest id 만 있는 수동/legacy artifact 는 본진 교체 증거가 아니다.
- `planSearchBootstrap.py` 와 `buildSearchProofBundle.py` 는 remote source/content blocker 가 있을 때 `searchBootstrapPlan.json` 과 `searchProofBundle.json.nextActions.bootstrapPlan` 을 남긴다. status 의 의미적 blocker 도 source-owner/Search Main/검증 실행 순서로 변환하므로 실패 proof bundle 도 운영자가 바로 실행할 다음 순서를 포함해야 인계 가능 상태다.
- `evaluateSearchCutover.py` 는 S2/S3 와 S4 를 분리한다. 본진 기본 교체는 `defaultBuildMode=catalog`, `scheduledBuildMode=catalog`, legacy fallback 운영자 전용, fail-closed publish, rollback/run evidence 가 있어야만 통과한다.

---

## 2. Runtime 구조

기존 검색기는 유지하고 내부를 보강한다.

1. `api.py` 는 공개 `search/prefetch/indexInfo` facade 로 남긴다.
2. `fieldIndex.py` 는 본문 content CSR main/delta load, source-aware metadata, dedup 을 책임진다.
3. `unified.py` 는 R* fusion 과 router expansion 을 맡는다.
4. `sourceIntent.py` 가 source hard isolation 을 먼저 결정한다.
5. `facetPlanner.py` 가 corp/date/report/receipt/news-title anchor 를 만든다.
6. `sourceRefPolicy.py` 가 top docs 를 citation set 으로 정규화한다.
7. `evidencePack.py` 가 chunk/field evidence 를 고른다.
8. `answerability.py` 가 no-answer 를 판정한다.
9. `memoryCard.py` 가 LLM 소비용 card 를 만든다.
10. `manifest.py` 가 index compatibility, sourceDataAsOf, tier, delta 상태를 노출한다.

이 구조에서 기본 recall 은 본문 검색이다. 제목/보고서명/section title 은 보조 anchor 로만 쓰고, `scope="content"` 와 `scope="both"` 는 공시 원문·panel 롤업 본문·뉴스 본문을 검색해야 한다. embedding 은 7번 evidence 선택 sidecar 로만 들어간다. 전역 후보 검색과 source isolation 은 sparse R* 가 담당한다.

---

## 3. HF 증분 운영

검색 artifact 는 원천 데이터가 아니라 파생 인덱스다.

| 레이어 | 소유 |
|---|---|
| allFilings parquet | source owner sync |
| panel parquet | panel/original sync |
| news public/private parquet | news sync |
| contentIndex main/delta | search index workflow |
| catalog snapshot/manifest | search index workflow |

증분의 SSOT 는 `doc_key + text_hash` 다.

상세 source manifest, search index manifest, staging promote, local atomic swap 계약은 [10-production-pipeline-prd.md](10-production-pipeline-prd.md) 를 기준으로 한다. 운영 절차와 장애 대응은 [11-operator-runbook.md](11-operator-runbook.md) 를 따른다.

권장 catalog 필드:

- `doc_key`
- `source`
- `sourceRef`
- `rceptNo` 또는 `url`
- `sectionOrder`
- `corp_code`
- `stock_code`
- `rcept_dt` 또는 `date`
- `report_nm` 또는 `title`
- `text_hash`
- `metadata_hash`
- `content_len`
- `deleted`
- `sourceDataAsOf`
- `updatedAt`
- `schemaVersion`
- `tokenizerVersion`
- `normalizerVersion`
- `sourceAdapterVersion`

doc key 원칙:

- DART filing: `dart:{rceptNo}:{sectionOrder}` 계열.
- allFilings 와 panel 이 같은 접수번호를 갖는 경우 panel priority 또는 sourceRefPolicy 로 중복을 해소한다.
- news: 정규화 URL hash 기반 `news:{urlHash}`.
- public contentIndex 에는 public news 만 넣는다. private news 는 별도 local/private index 정책 없이는 섞지 않는다.

---

## 4. Delta 파이프라인

일상 갱신은 full rebuild 가 아니다.

1. source sync 가 allFilings, panel, EDGAR, news source manifest 를 갱신한다.
2. search delta workflow 가 source job 이후 실행된다.
3. DuckDB catalog 에 source row 를 stage 한다.
4. 이전 catalog 와 `doc_key/text_hash/metadata_hash/deleted` 를 비교한다.
5. new/changed/deleted 만 delta target 으로 export 한다.
6. delta CSR, delta stems, delta meta, delta info, delta manifest 를 만든다.
7. HF staging 에 파일을 업로드한 뒤 current `manifest.json` pointer 만 publish 한다.
8. runtime lazy pull 은 staging directory 에 받은 뒤 required file set 과 manifest 검증이 끝난 경우에만 active 로 전환한다.

main compaction 조건:

- 월간 planned compaction.
- `delta_docs/main_docs > 0.1~0.2`.
- tombstone 누적.
- panel reconcile 또는 backfill 대량 발생.
- sourceAdapter/tokenizer/normalizer/schemaVersion 변경.
- artifact 크기 또는 load time 예산 초과.

main compaction 후에는 `delta.npz` 만 지우지 않고 `delta_stems.json`, `delta_meta.parquet`, `delta_info.json`, delta manifest 까지 함께 정리한다.

---

## 5. Manifest 계약

`builtAt` 과 `dataAsOf` 는 다르다.

manifest 필수 필드:

- `artifactVersion`
- `schemaVersion`
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
- `compatible`
- `buildCommand`
- `gitSha`

`indexInfo()` 는 이 manifest 를 읽어 사용자가 "얼마나 최신인가"를 판단할 수 있게 한다. source 별 `dataAsOf` 가 없으면 public/local UI 에서 최신성 badge 를 정직하게 그릴 수 없다.

---

## 6. Local · Public · Library

### Library

- 기본은 lite tier lazy pull.
- `DARTLAB_SEARCH_TIER=full|lite` 로 tier 선택.
- `DARTLAB_NO_HF_DOWNLOAD=1` 에서는 local cache 만 사용.
- `prefetch()`/lazy pull 은 manifest artifact 가 있으면 staging 검증 뒤 active pointer 를 전환한다. manifest 에 `canaryQueries` 가 있으면 활성화 전에 query smoke 를 수행한다. manifest 없는 기존 HF artifact 는 legacy fallback 으로 읽는다.
- 결과에는 `sourceRef/dataAsOf/answerable` 이 항상 있다.

### Local UI

- full 또는 local cache 를 Python runtime adapter 로 사용한다.
- `/api/search` 또는 library call adapter 가 ranking 을 담당한다.
- terminal, viewer, AI drawer 는 ranking 코드를 갖지 않고 shared `SearchResults/EvidenceCard/FreshnessBadge/NoAnswerNotice` schema 만 소비한다.

### Public Landing

- public site 의 `/search` 는 현재 site search 이므로 corpus search 와 혼동시키지 않는다.
- 브라우저에 full 300k index 를 강제하지 않는다.
- static/lite artifact 또는 curated public demo 로 시작한다.
- stale index, source scope, latest/live 한계를 UI 에 노출한다.
- "최신 공시 원문" 같은 질문은 library/local 사용 경로로 승격한다.

### CLI

- 기존 `dartlab search` 는 회사 검색이다.
- 공시/뉴스 corpus search 는 기존 의미를 깨지 않고 별도 명시 명령 또는 help 정리 후 붙인다.
- CLI 출력도 `sourceRef/dataAsOf/answerable` 을 잃으면 안 된다.

---

## 7. 테스트와 졸업

본진 이식 전후 최소 gate:

- public contract: `limit` 계약, `topK` alias, public/provider API 드리프트 방지.
- source isolation: 뉴스 의도는 news 만, 공시 의도는 filing/panel 만.
- facet anchor: query/corp 회사명, date/report/receipt/news-title.
- R* regression: BM25, router expansion, RRF, main/delta dedup.
- catalog delta: allFilings/panel/news changed-only export, tombstone, panel priority.
- manifest/indexInfo: sourceDataAsOf, source counts, schema compatibility.
- lazy pull: partial artifact reject, offline mode, lite fallback.
- no-answer: unknown company, wrong date, wrong event, suffix/near-name traps.
- source canary: news-only, filing-only, expected sourceRef, no-answer trap.
- evidence-card: top3 sourceRef, primarySourceRef, fieldCards, dataAsOf.
- surface smoke: library, local adapter, public static adapter, CLI naming.

제품 졸업 gate:

- real query-log gold rows >= 100, 권장 300.
- filing/news/noAnswer coverage 필수.
- overall readyRate >= 0.9.
- filing `docHit10`, `memoryCitationTop3Exact`, `memoryAnswerReady` >= 0.9.
- news `exactHit10`, `targetSourceTop1`, `sourcePrecision10` >= 0.9.
- noAnswer `negativeRejectRate` >= 0.9, `falseAcceptRate` <= 0.1.
- proxy origin 은 졸업 증거로 금지.

현재 실행 명령은 `evaluateSearchGold.py --fail-on-ineligible` 다. `--allow-proxy-query-log` 는 `_attempts`/회귀 압박 전용이며 release graduation 에서는 금지한다.

---

## 8. 다음 구현 순서

1. result schema 와 manifest/indexInfo 계약부터 고정한다. (1차 구현 완료)
2. source manifest 와 search index manifest 를 코드 schema 로 고정한다. (1차 구현 완료)
3. DuckDB/Polars catalog diff 를 allFilings, DART panel, EDGAR panel, public news source 로 확장한다. (source manifest/catalog generation + diff/dry-run/delta export 1차 완료, 실제 source owner run 확인 남음)
4. search delta workflow 를 source sync 이후로 옮기고 panel/news/EDGAR delta 를 포함한다. (catalog delta build 모드 + HF searchCatalog pull/env prep, staging upload/current manifest pointer helper 완료, 실제 scheduled catalog publish 확인 남음)
5. source intent 와 answerability 를 runtime 에 작게 붙인다. (source hard isolation + missing evidence + facet mismatch + stale source 1차 완료)
6. evidence-card 와 memory-card 를 internal opt-in 으로 붙인다. (row/bounded chunk 1차 완료, 실제 full-source evidence 품질 확인 남음)
7. library result row 에 `sourceRef/dataAsOf/answerable` 을 노출한다.
8. local updater staged download, selfcheck, atomic swap 을 붙인다. (hash/load/canary smoke + active manifest 비교 1차 완료)
9. monthly main compaction 을 source catalog snapshot 기반으로 전환한다. (1차 구현 완료, 실제 Actions catalog run 확인 남음)
10. local end-to-end pipeline drill 을 CI preflight 로 유지한다. (1차 구현 완료)
11. HF current manifest round-trip smoke 를 publish 후 workflow evidence artifact 로 남긴다. (CLI/workflow 배선 완료, 실제 run 증거 확인 남음)
12. local/public/shared surface 는 같은 result schema 를 소비하게 한다.
13. source/no-answer canary pack 을 artifact 기반으로 자동 생성하고 운영 curated rows 로 보강한다. (artifact pack 구현 완료, 실제 Actions artifact report 와 운영 rows 남음)
14. 실제 query-log gold 100~300 rows 를 확보해 `evaluateSearchGold.py --fail-on-ineligible` 졸업 gate 를 실행한다.
