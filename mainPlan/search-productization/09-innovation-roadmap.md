# 09. 혁신 로드맵 — 빠른 의미검색과 운영 혁신

상태: v0.1 (2026-06-15)
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
| Intent Kernel | source, entity, date, report, event 를 먼저 구조화 | 의미검색을 dense vector 유사도에만 맡기지 않는다 |
| Sparse-First Hybrid | R* sparse + facet anchor 를 기본, embedding 은 evidence sidecar | 속도와 설명가능성을 유지하면서 의미 보강 가능 |
| Incremental Knowledge Fabric | `doc_key/text_hash` delta + manifest + compaction | 데이터가 늘수록 더 강해지고 운영비는 선형으로 억제 |
| Quality Flywheel | query-log miss 를 taxonomy 로 쌓고 정책만 승격 | 덕지덕지 특수 mapper 없이 품질이 누적된다 |

---

## 3. 의미검색을 잘하게 만드는 구조

의미검색은 "비슷한 문장 찾기"가 아니라 "질문의 제약을 만족하는 근거 찾기"다.

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

---

## 4. 속도 혁신

속도는 단일 엔진 최적화보다 tiered execution 으로 만든다.

1. **Hot delta** — 최근 allFilings/news/EDGAR filing 은 작은 delta segment 에서 먼저 찾는다.
2. **Source shard** — `sourceIntent` 가 명확하면 해당 source CSR 만 탐색한다.
3. **Facet prefilter** — corp/date/report/receipt/accession 이 있으면 row mask 를 먼저 좁힌다.
4. **R* candidate pool** — sparse BM25/router/RRF 로 후보를 작게 만든다.
5. **Evidence sidecar** — embedding 또는 chunk rerank 는 후보 50~200개 안에서만 실행한다.
6. **Memory-card reuse** — 후속 질문은 이미 찾은 sourceRef set 을 먼저 검증하고 필요할 때만 재검색한다.

이 방식이면 문서가 늘어도 전체를 매번 의미 임베딩으로 훑지 않는다. full corpus 는 넓은 recall 을 담당하고, 의미 비용은 좁은 후보에만 쓴다.

---

## 5. 운영 혁신

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

## 6. 덕지덕지 방지 원칙

특수 규칙을 붙일 수 있는 조건을 제한한다.

허용:

- 반복 miss type 이 query-log gold 에서 확인됨.
- sourceRef/evidence-card 로 개선 효과가 재현됨.
- source adapter, intent kernel, facet planner, manifest 중 한 계층의 일반 정책으로 표현됨.
- 기존 query pack 에 회귀가 없음.

금지:

- 특정 회사명, 특정 제목, 특정 날짜만 맞추는 mapper.
- dense score 하나로 source intent 를 덮어쓰는 fallback.
- no-answer 를 top result 없음과 같은 상태로 처리.
- public API 를 늘려 내부 불확실성을 외부에 떠넘김.
- full rebuild 를 일상 운영으로 전제.

---

## 7. 추가할 수 있는 고급 능력

제품 코어가 안정된 뒤 넣을 수 있는 능력이다.

| 능력 | 위치 | 조건 |
|---|---|---|
| Query-log policy learner | offline quality loop | miss taxonomy 가 100건 이상 쌓인 뒤 |
| Embedding sidecar | evidencePack 내부 | sparse 후보 안 rerank 로만 사용 |
| Cross-source event cluster | sourceRefPolicy 내부 | filing/news/EDGAR 같은 사건 묶기 |
| Temporal answer memory | memoryCard 내부 | sourceDataAsOf 검증 필수 |
| Public lite semantic demo | landing adapter | stale/lite 한계 노출 필수 |
| EDGAR bilingual bridge | sourceAdapters + facetPlanner | accession/item/source namespace 고정 후 |

이 능력들은 public call 을 늘리지 않는다. 모두 `dartlab.search(...)` 결과의 근거 품질을 올리는 내부 계층이다.

---

## 8. 성공 기준

혁신이라고 부르려면 다음을 모두 만족해야 한다.

- 1M 문서급에서도 warm query p95 가 제품 사용 가능한 범위에 있음.
- sourceRef 없는 검색 결과가 없음.
- source intent fallback 이 없음.
- 실제 query-log gold 에서 filing/news/noAnswer/EDGAR coverage 를 통과.
- artifact publish 는 manifest 검증과 canary query 를 통과한 경우에만 이뤄짐.
- 새 데이터 추가의 기본 경로가 delta 이며, full rebuild 는 예외로 남음.
- miss ledger 가 특수 mapper 목록이 아니라 policy backlog 로 유지됨.
