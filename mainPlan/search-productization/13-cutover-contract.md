# 13. Cutover Contract — 제품 검색 교체 기준

상태: v0.7 (2026-06-16)
범위: `dartlab.search(...)` 를 제품 검색 엔진으로 교체할 때 필요한 운영·품질·증거 계약.

---

## 1. 원칙

제품화는 얇은 개선을 누적해 "좋아 보인다"로 끝내는 작업이 아니다. 다음 네 가지가 동시에 닫혀야 한다.

1. 사용자는 같은 `dartlab.search(...)` 호출을 쓴다.
2. 검색 엔진은 장기 dual/shadow 기본값 없이 하나로 간다.
3. 데이터 증분은 HF source/search manifest 와 catalog diff 로 자동 흡수한다.
4. 교체 여부는 사람이 기억으로 판단하지 않고 proof bundle 의 readiness 로 판단한다.

따라서 제품화 판정 단위는 개별 코드 변경이 아니라 `searchProofBundle.{delta,main}/searchProductizationStatus.json` 이다.

---

## 2. 상태 정의

| 상태 | 의미 | 통과 조건 | 금지 |
|---|---|---|---|
| S0 experiment | 실험 또는 회귀 압박 | `_attempts`, synthetic/proxy gold, local smoke | 제품 주장 |
| S1 designReady | 본진 이식 가능한 설계·코드 | source intent, answerability, result schema, catalog delta, local updater, proof bundle CLI | 운영 가능 주장 |
| S2 opsReady | 기본값 교체 가능한 운영 증거 | source catalog 4종 + producerRun lineage + previous-manifest drop guard 통과, full/lite contentIndex current manifest, full/lite HF round-trip activate/rollback, canary, result contract, local indexInfo, proof bundle missingEvidence 없음 | release graduation 주장 |
| S3 releaseReady | 제품 졸업 가능 | S2 + reviewed real query-log gold 100~300 rows + miss ledger triage + quality report pass | proxy/generated gold 로 졸업 |
| S4 defaultReplacement | 본진 기본값 교체 완료 | S2 이상, `defaultBuildMode=catalog`, `scheduledBuildMode=catalog`, legacy fallback 운영자 전용, fail-closed publish, rollback manifest, 운영 런북 증거 슬롯 작성, 본진 surface 명칭 정리 | 장기 이중선 |

현재 S2 는 local HF bootstrap 기준으로 한 번 닫았다. 다음 목표는 실제 Actions run 으로 같은 증거를 남기고, 실제 query-log gold 가 쌓이면 S3 로 올리는 것이다.

---

## 3. 현재 판정

2026-06-16 full_lite proof bundle 기준:

| 항목 | 상태 |
|---|---|
| designReady | true |
| opsReady | true |
| releaseReady | false |
| full docs | 462,947 |
| lite docs | 280,747 |
| source counts | full: allFilings 192,095 / panel 104,761 / edgar-panel 84,293 / news 81,798 |
| source freshness | allFilings 20260612 / panel 20260615 / edgar-panel 20260630 / news 20260615 |
| result contract | valid |
| canary | passRate 1.0 |
| blockers | `missingQualityReport` |

해석:

- HF source catalog/current full/lite manifest 와 runtime 계약은 S2 운영 기준을 넘었다.
- 이 증거는 local HF bootstrap 으로 만든 것이므로, 동일 순서의 GitHub Actions evidence artifact 는 별도로 확인해야 한다.
- lite 18개월 tier 는 326.3MB 로 경량 목표를 넘었으므로 S4 기본값 전환 전 개선 후보로 남긴다.
- real query-log gold 가 없으므로 release graduation 은 금지다.

---

## 4. Cutover Gate

본진 기본값 교체는 다음 조건을 모두 만족해야 한다.

| gate | hard condition | 증거 위치 |
|---|---|---|
| source inventory | allFilings, DART panel, EDGAR panel, newsPublic source catalog manifest/snapshot 존재, source owner Actions evidence artifact 존재, manifest `producerRun.workflow/job/runId/sha/artifactName` 존재, source-owner run 은 직전 full manifest 대비 drop guard 통과 | `searchRemoteEvidence.{delta,main}.json`, `search-catalog-*` artifact |
| frozen source set | contentIndex 가 어떤 4개 source snapshot 과 source owner run 을 조합했는지 `source_manifest_set.json` 으로 고정하고, set 내부 source별 `producerRun.workflow/job/runId/sha/artifactName` 을 검증 | contentIndex manifest `sourceManifestSetId`, required/fileSources target `source_manifest_set.json`, `remoteContentManifestSetMissingProducerRun:*` blocker 없음 |
| content manifest | full/lite `dart/contentIndex/**/manifest.json` 존재, `requiredFiles` 와 `fileSources` target 존재 | `searchRemoteEvidence.{delta,main}.json` |
| local round-trip | full/lite 모두 staged download, hash/load/canary, activate, rollback pass | `searchHfRoundTrip.{delta,main}.{full,lite}.json` |
| result surface | `source/sourceRef/dataAsOf/snippet/answerable/fieldCards/evidence` contract valid | `searchResultContract.{delta,main}.json` |
| source safety | allFilings/panel/edgar-panel/news coverage, no-answer false accept 0 | `searchCanary.{delta,main}.json` |
| local runtime | `indexInfo()` compatible, expected sources count/freshness present | proof bundle `localIndexInfo.json` |
| proof bundle | `missingEvidence=[]`, `opsReady=true` | `searchProofBundle.json`, `searchProductizationStatus.json` |
| replacement evidence | `defaultBuildMode=catalog`, `scheduledBuildMode=catalog`, `legacyFallbackOperatorOnly=true`, `failClosedPublish=true`, active/previous manifest id, rollback command, rollback 검증, run evidence 기록, surface naming review | `searchCutover*.json`, replacement evidence JSON, `11-operator-runbook.md`, `12-pipeline-maintenance-map.md` |

이 중 하나라도 빠지면 "코드는 들어갔다"일 수는 있어도 "운영 교체 가능"은 아니다.

---

## 5. Release Gate

제품 졸업은 opsReady 위에 품질 증거가 붙어야 한다.

| gate | hard condition |
|---|---|
| real gold | `goldOrigin=userLog`, `reviewStatus=reviewed`, 100~300 rows |
| coverage | filing/news/noAnswer/EDGAR/company-facet trap 포함 |
| answerable quality | readyRate/docHit/sourceRef 기준 통과 |
| no-answer | falseAcceptRate 0 |
| miss ledger | open miss 가 blocker/non-blocker 로 분류됨 |
| quality report | `releaseEligible=true`, `realReviewedRows>=100`, `goldOriginCounts`/`reviewStatusCounts` 재검증, proxy/generated/drill gold 불허 |

raw query log 는 후보 입력일 뿐이다. reviewer label 전에는 release evidence 가 아니다.

---

## 6. 운영 자동화 계약

자동화 대상은 mapper 목록이 아니라 evidence loop 다.

| loop | 자동화 |
|---|---|
| source freshness | source owner workflow 가 source manifest/catalog snapshot 생성 |
| search delta | search workflow 가 catalog diff 로 changed docs 만 rebuild |
| publish safety | staging upload, current manifest pointer, file hash, canary, result contract, remote evidence audit |
| local update | HF current manifest pull, staged download, atomic active swap, previous rollback |
| quality learning | raw query log, reviewer label, canonical real gold, miss ledger, quality gate |

새 source 가 늘어나도 이 구조는 바뀌지 않는다. source owner 는 catalog 를 만들고, search 는 diff/publish/검증을 맡고, runtime 은 검증된 current manifest 만 활성화한다.

---

## 7. 덕지덕지 방지 규칙

1. 실패한 query 를 즉시 특수 mapper 로 붙이지 않는다.
2. miss 는 먼저 miss ledger 에 쌓고, 반복 유형이 확인되면 일반 정책으로 승격한다.
3. 승격 위치는 source adapter, sourceRef policy, facet planner, answerability, evidence pack, tokenizer/normalizer 중 하나다.
4. release gate 는 proxy/generative sample 로 우회하지 않는다.
5. prebuilt artifact 는 사람이 계속 관리하는 파일 묶음이 아니라 workflow 가 매번 재생성하는 산출물이다.

운영자가 장기 관리해야 하는 것은 개별 query map 이 아니라 source freshness, manifest lineage, proof bundle, gold/miss ledger 다.

---

## 8. 다음 한 사이클

S2 를 닫는 다음 작업 단위:

1. `checkSearchRemoteEvidence.py` 로 현재 원격 blocker 를 확인하고 `planSearchBootstrap.py` 또는 `buildSearchProofBundle.py` 의 `nextActions.bootstrapPlan` 으로 `searchBootstrapPlan.json` 을 만든다. 이 plan 이 source-owner `search_catalog_bootstrap=true`, catalog-mode `searchIndexMain.yml`, remote evidence/proof bundle 검증 명령의 실행 순서다.
2. `Search Index Main` full HF pull bootstrap 또는 source-owner workflow 의 명시적 `search_catalog_bootstrap=true` dispatch 로 canonical source catalog 4종을 실제 HF 에 publish.
3. bootstrap 이후 `Prepare canonical catalog main inputs after bootstrap` 또는 `Prepare catalog delta inputs` 단계가 source set 을 `source_manifest_set.json` 으로 freeze 하고 `DARTLAB_SEARCH_MAIN_MODE=catalog` 또는 `DARTLAB_SEARCH_DELTA_MODE=catalog` 을 세팅.
4. 이후 source owner Actions run 에서 4종 source catalog artifact 를 직전 full manifest 대비 drop guard 로 갱신.
5. source owner Actions artifact `search-catalog-{source}-*` 와 source manifest `producerRun` 으로 manifest/catalog 산출물을 증거화.
6. `prepareSearchDeltaInputs.py` 가 만든 `source_manifest_set.json` 을 full/lite contentIndex required file 로 포함하고 source별 `producerRun` 을 보존.
7. `checkSearchRemoteEvidence.py` 가 contentIndex `fileSources` 로 실제 `source_manifest_set.json` 을 열고 source별 `producerRun` 누락이 없음을 증명.
8. `searchIndexMain.yml` catalog mode 로 full/lite contentIndex current manifest publish.
9. full/lite `verifySearchHfRoundTrip.py` activate/rollback report 확보.
10. `buildSearchProofBundle.py` 로 `opsReady=true` proof bundle 생성.
11. 본진 default replacement 는 S2 가 true 일 때만 진행.
12. 실제 사용자/운영자 query raw log 를 모아 reviewed real gold 로 S3 를 별도 진행.

이 사이클에서 코드 품질 수치보다 중요한 산출물은 proof bundle 과 run evidence 다.
