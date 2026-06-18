# 09. 혁신 로드맵 — 빠른 의미검색과 운영 혁신

상태: v0.3 (2026-06-18)
범위: 기존 검색 제품화 설계 위에 얹을 수 있는 더 강한 방향. 기능 추가 목록이 아니라, 속도·의미·운영을 동시에 올리는 원칙이다.

---

## 1. 혁신의 정의

여기서 혁신은 "벡터DB를 붙인다"가 아니다.

목표는 다음 네 가지를 동시에 만족하는 검색이다.

1. **빠르다** — 300k~수백만 문서에서도 interactive search latency 를 유지한다.
2. **의미를 잡는다** — 회사, 날짜, 보고서, 사건, source, section 을 동시에 맞춘다.
3. **덕지덕지 없다** — miss 1건마다 특수 규칙을 붙이지 않고 반복되는 실패만 정책으로 승격한다.
4. **운영이 자동화된다** — allFilings, panel, news, EDGAR 증가분을 full rebuild 없이 delta 로 흡수한다.

---

## 2. 핵심 방향

| 방향 | 의미 | 왜 혁신인가 |
|---|---|---|
| Typed SourceRef Graph | 모든 결과를 source/type/section/date 를 가진 ref 로 고정 | LLM 이 "문서"가 아니라 검증 가능한 근거 노드를 기억한다 |
| Data-Compiled Intent Kernel | 질의 1건을 source, entity, date, report, event 의 runtime plan 으로 해석 | 사람이 관리하는 query mapper 대신 source metadata 에서 컴파일한 typed mapper 로 의미 제약을 만든다 |
| Sparse-First Hybrid | R* sparse + facet anchor 를 기본, embedding 은 evidence sidecar | 속도와 설명가능성을 유지하면서 의미 보강 가능 |
| Incremental Knowledge Fabric | `doc_key/text_hash` delta + manifest + compaction | 데이터가 늘수록 더 강해지고 운영비는 선형으로 억제 |
| Quality Flywheel | query-log miss 를 taxonomy 로 쌓고 정책만 승격 | 덕지덕지 특수 mapper 없이 품질이 누적된다 |

---

## 3. 의미검색을 잘하게 만드는 구조

의미검색은 "비슷한 문장 찾기"가 아니라 "질문의 제약을 만족하는 근거 찾기"다. 여기서 runtime plan 은 질의가 들어온 순간 생성되고 검색이 끝나면 버려진다. 다만 plan 을 만드는 mapper 자체는 인정한다. 조건은 하나다. 사람이 query별로 관리하는 mapper 가 아니라 source catalog 와 문서 metadata 에서 자동 컴파일되는 typed mapper 여야 한다.

관리해야 하는 것은 query 예외 목록이 아니라 mapper compiler 의 입력/출력 계약이다. 회사 코드, 접수번호, accession, 날짜, 보고서 유형, report title, section, source family, event role 처럼 데이터에 원래 있는 필드를 쓴다. 사람이 계속 손으로 갱신하는 의미 사전이면 폐기하지만, source adapter 가 만드는 catalog 에서 alias/event/report/period mapper 를 재생성하는 방식은 허용한다.

질의는 먼저 작은 의미 구조로 바뀐다.

```text
query
-> sourceIntent: filing | panel | news | edgar | auto
-> entityFacet: corpCode | ticker | cik | companyName
-> timeFacet: date | range | quarter | fiscalYear
-> reportFacet: businessReport | quarterlyReport | 10-K | 10-Q | 8-K
-> eventFacet: offering | CEO change | risk factor | litigation | capex
-> fieldFacet: amount | counterparty | date | ratio | section
```

랭킹은 이 구조를 만족하는 후보 안에서 작동한다. 따라서 "삼성전자 2024년 유상증자 공시 원문", "Apple 10-K risk factor supply chain", "뉴스 말고 공시로만" 같은 질의가 같은 검색 surface 에서 처리된다.

이 plan 은 저장하지 않는다. query-log 에 남기는 것은 plan 자체가 아니라 실패 유형과 개선 근거다. 반복 실패가 생겨도 특정 쿼리 전용 규칙을 붙이지 않고, sourceRef policy 나 facet parser 같은 일반 정책으로만 승격한다.

본문 검색은 필수다. title/report/section title 은 빠른 anchor 이지만 의미검색의 본체는 filing body, panel rolled body, EDGAR item body, news body 를 대상으로 한 content lane 이다. 제목만 맞는 결과는 evidence-card 에서 탈락할 수 있어야 한다.

---

## 4. Constraint Rerank 승격 후보

2026-06-18 `tests/_attempts/searchConstraintRerank/`에서 구조적 제약 랭킹을 작은 hard-negative gold 로 검증했다.

결과:

| arm | exactHit1 | hardNegativeWinRate | forbiddenTop3Rate | top1ConstraintViolationRate |
|---|---:|---:|---:|---:|
| bm25 | 0.4286 | 0.4286 | 1.0000 | 0.5714 |
| rrf | 0.4286 | 0.4286 | 1.0000 | 0.5714 |
| bodyCue | 0.4286 | 0.4286 | 1.0000 | 0.5714 |
| mapperCompiledFiltered | 1.0000 | 1.0000 | 0.0000 | 0.0000 |
| mapperInferredFiltered | 1.0000 | 1.0000 | 0.0000 | 0.0000 |
| constraintFacetOnly | 0.5714 | 0.5714 | 1.0000 | 0.4286 |
| constraintNoEventRole | 0.8571 | 0.8571 | 0.8571 | 0.1429 |
| constraint | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| constraintFiltered | 1.0000 | 1.0000 | 0.0000 | 0.0000 |

해석:

- 방향은 유효하다. 가까운 오답은 cue 단어보다 `entity + source + report + fiscalYear + eventRole` 제약 불만족으로 더 잘 걸린다.
- 아직 release evidence 는 아니다. fixture 는 deterministic/synthetic 이고 7질의뿐이다.
- 중요한 설계 결함도 드러났다. 현재 `year` facet 은 `rcept_dt` 접수연도와 보고 vintage 를 섞을 수 있다. 2023 사업보고서가 2024년에 접수되면 `2024` 제약을 통과할 수 있으므로 `fiscalYear`/`periodYear`를 별도 facet 으로 승격해야 한다.
- ablation 도 같은 결론이다. 현재 `QueryFacets`만 쓰는 `constraintFacetOnly`는 0.5714에서 멈추고, `eventRole`을 뺀 `constraintNoEventRole`은 원공시/정정공시 hard-negative에서 0.8571로 떨어진다. 제품급 승격에는 `sourceKind`, `fiscalYear`/`periodYear`, `eventRole`이 planner-owned facet 이어야 한다.
- 추가로 `constraint` rank sink 만으로는 부족하다. 정답을 1등으로 올려도 금지 후보가 top3 evidence 후보에 남는다. RAG/memory-card 안전성까지 보려면 `constraintFiltered`처럼 제약 위반 row 를 answerable evidence 후보에서 제거하거나 `answerable=false`로 내려야 한다.
- gold facet 없이 corpus metadata 에서 mapper 를 컴파일한 `mapperCompiledFiltered`도 synthetic hard-negative 에서는 1.0/0.0을 달성했다. 이게 현재 가장 강한 핵심 개념 후보: **data-compiled semantic mapper + constraint-filtered ranking** 이다.
- `eventRole` 라벨을 직접 쓰지 않고 sourceRef/report/title/body 에서 role profile을 유도한 `mapperInferredFiltered`도 같은 결과를 냈다. 즉 제품 방향은 사람이 eventRole 사전을 관리하는 것이 아니라, source adapter/catalog 가 가진 텍스트와 namespace 에서 role profile artifact 를 재생성하는 쪽이다.

본진 이식 형태:

- `constraintRanker.py` 를 새 내부 모듈로 둔다. `unified.py` 안에 cue 규칙을 더 붙이지 않는다.
- `semanticMapperCompiler.py` 를 offline/catalog-adjacent 내부 모듈로 둔다. 입력은 source catalog/meta rows, 출력은 company alias, report alias, sourceKind, fiscalYear/periodYear, eventRole profile artifact 다.
- candidate generation 은 R*/RRF 를 유지한다. constraint 는 후보 생성기가 아니라 rerank/sink 계층이다.
- 제약 불만족은 작은 보너스/패널티가 아니라 1차 ordering key 여야 한다.
- 같은 제약 만족 후보 안에서만 sparse score, body evidence, source freshness 를 tie-break 로 쓴다. 제약 위반 후보는 memory-card/evidence sourceRef set 에 들어가면 안 된다.
- `sourceKind`, `fiscalYear`, `eventRole`은 planner-owned facet 으로 승격하기 전까지 production claim 을 금지한다.
- mapper compiler artifact 는 manifest 에 schemaVersion, source counts, alias counts, eventRole counts, build source hash 를 남겨야 한다. 재현 불가능한 수작업 mapper 는 금지한다.

졸업 gate:

- HF current allFilings/panel/news/EDGAR 샘플에서 300행 hard-negative gold 를 만든다.
- 유형은 same-company-different-year, sibling filing, similar-event-other-company, report-type-mismatch, news/filing confusion, DART/EDGAR confusion, panel/filing confusion 을 필수 포함한다.
- release blocker 는 relaxed `docHit10` 이 아니라 `exactDocHit10`, `hardNegativeWinRate`, `forbiddenTop3Rate`, `forbiddenTop10Rate`, `top1ConstraintViolationRate` 다.
- synthetic 7행 결과는 설계 후보 증거로만 보존한다.

2026-06-18 current-data 결과:

- `.github/scripts/search/buildSearchHardNegativeGold.py` 로 `.tmp/hf-contentIndex/catalog_snapshot.parquet` 475,549 rows 에서 300행 candidate hard-negative 를 생성했다.
- 생성 분포: edgar-dart-confusion 47, news-filing-confusion 47, panel-filing-confusion 44, report-type-mismatch 47, same-company-different-year 43, same-company-sibling-filing 41, filing-news-confusion 24, similar-event-other-company 7.
- 실제 `.tmp` active index 475,611 docs 에서 본진 `dartlab.search` 를 평가했다.
- 초기 baseline: overallReadyRate 0.4367, docHit10 0.4367, hardNegativeExactDocHit10 0.2400, hardNegativeWinRate 0.2367, forbiddenTop3Rate 0.0233, forbiddenTop10Rate 0.0300, sourceIntentLeakRate 0.0.
- 본진 교체 구현: data-compiled semantic mapper, source/entity/year pre-rank mask, metadata constraint lane, constraint-filtered rerank, answerability sink, 최신성 우선 phase tie-break.
- 최신 결과: `.tmp/search-hard-negative/qualityReport.hardNegative.withNoAnswer.eventOnly.candidate.json` 기준 hard-negative 300행 + noAnswer 60행에서 overallReadyRate 0.9806, docHit10 0.9767, exactDocHit10 0.9667, hardNegativeExactDocHit10 0.9667, hardNegativeWinRate 0.9667, noAnswerFalseAcceptRate 0.0, forbiddenTop3Rate 0.0, forbiddenTop10Rate 0.0, sourceIntentLeakRate 0.0, constraintViolationRate 0.0.
- 판정: current-data candidate 360행에서 metric gate 와 noAnswer coverage 는 통과했다. 단 `goldOrigin=currentDataHardNegative`, `reviewStatus=candidate`, `realReviewedRows=0/300` 이므로 제품 졸업 증거가 아니다. 혁신 방향은 유효했고 본진 search 에 흡수됐지만, release 졸업은 reviewer-approved hard-negative/noAnswer gold 승격 뒤에만 가능하다.

---

## 5. 속도 혁신

속도는 단일 엔진 최적화보다 tiered execution 으로 만든다.

1. **Hot delta** — 최근 allFilings/news/EDGAR filing 은 작은 delta segment 에서 먼저 찾는다.
2. **Source shard** — `sourceIntent` 가 명확하면 해당 source CSR 만 탐색한다.
3. **Facet prefilter** — corp/date/report/receipt/accession 이 있으면 row mask 를 먼저 좁힌다.
4. **R* candidate pool** — sparse BM25/router/RRF 로 후보를 작게 만든다.
5. **Body evidence window** — 후보 문서의 본문 chunk 를 열어 실제 근거가 있는지 확인한다.
6. **Evidence sidecar** — embedding 또는 chunk rerank 는 후보 50~200개 안에서만 실행한다.
7. **Memory-card reuse** — 후속 질문은 이미 찾은 sourceRef set 을 먼저 검증하고 필요할 때만 재검색한다.

이 방식이면 문서가 늘어도 전체를 매번 의미 임베딩으로 훑지 않는다. full corpus 는 넓은 recall 을 담당하고, 의미 비용은 좁은 후보에만 쓴다.

---

## 6. 운영 혁신

운영은 "재색인 작업"이 아니라 "지식 fabric 유지"가 되어야 한다.

필수 구조:

- source manifest: allFilings, panel, news, EDGAR panel, EDGAR allFilings 의 source별 기준일과 row count.
- catalog diff: `doc_key/text_hash/metadata_hash/deleted` 로 changed set 산출.
- delta artifact: source별 changed docs 만 CSR/meta/stems 로 publish.
- manifest pointer: required file set 검증 후 마지막에 current pointer 전환.
- source freshness: `sourceDataAsOf` 를 사용자 결과와 `indexInfo()`에 노출.
- compaction policy: delta 비율, tombstone, backfill, schema 변경, artifact size 기준으로 main 재압축.
- canary query pack: source별 대표 질의가 새 artifact 에서 깨지면 publish 중단.

향후 EDGAR 가 들어와도 새 엔진을 만들지 않는다. source adapter 와 doc key namespace 를 추가한다.

```text
dart:allFilings:{rceptNo}:{section}
dart:panel:{rceptNo}:{sectionKey}:{period}
edgar:filing:{accession}:{item}
edgar:panel:{accession}:{sectionKey}:{period}
news:{urlHash}
```

---

## 7. 덕지덕지 방지 원칙

특수 규칙을 붙일 수 있는 조건을 제한한다.

허용:

- 반복 miss type 이 query-log gold 에서 확인됨.
- sourceRef/evidence-card 로 개선 효과가 재현됨.
- source adapter, intent kernel, facet planner, manifest 중 한 계층의 일반 정책으로 표현됨.
- 기존 query pack 에 회귀가 없음.

금지:

- 사람이 계속 관리해야 하는 query/event/date/company 예외 mapper.
- manifest 없이 생성되어 재현/검증할 수 없는 mapper artifact.
- 특정 회사명, 특정 제목, 특정 날짜만 맞추는 mapper.
- dense score 하나로 source intent 를 덮어쓰는 fallback.
- no-answer 를 top result 없음과 같은 상태로 처리.
- public API 를 늘려 내부 불확실성을 외부에 떠넘김.
- full rebuild 를 일상 운영으로 전제.

---

## 8. 추가할 수 있는 고급 능력

제품 코어가 안정된 뒤 넣을 수 있는 능력이다.

| 능력 | 위치 | 조건 |
|---|---|---|
| Query-log policy learner | offline quality loop | miss taxonomy 가 100건 이상 쌓인 뒤 |
| Semantic mapper compiler | sourceAdapters + facetPlanner | mapper input/output schema 와 manifest 검증 후 |
| Embedding sidecar | evidencePack 내부 | sparse 후보 안 rerank 로만 사용 |
| Cross-source event cluster | sourceRefPolicy 내부 | filing/news/EDGAR 같은 사건 묶기 |
| Temporal answer memory | memoryCard 내부 | sourceDataAsOf 검증 필수 |
| Public lite semantic demo | landing adapter | stale/lite 한계 노출 필수 |
| EDGAR bilingual bridge | sourceAdapters + facetPlanner | accession/item/source namespace 고정 후 |

이 능력들은 public call 을 늘리지 않는다. 모두 `dartlab.search(...)` 결과의 근거 품질을 올리는 내부 계층이다.

---

## 9. 성공 기준

혁신이라고 부르려면 다음을 모두 만족해야 한다.

- 1M 문서급에서도 warm query p95 가 제품 사용 가능한 범위에 있음.
- sourceRef 없는 검색 결과가 없음.
- source intent fallback 이 없음.
- 실제 query-log gold 에서 filing/news/noAnswer/EDGAR coverage 를 통과.
- artifact publish 는 manifest 검증과 canary query 를 통과한 경우에만 이뤄짐.
- 새 데이터 추가의 기본 경로가 delta 이며, full rebuild 는 예외로 남음.
- miss ledger 가 특수 mapper 목록이 아니라 policy backlog 로 유지됨.
