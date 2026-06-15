# 08. 완성 설계 — HF 증분 · 로컬/퍼블릭/라이브러리 검색

상태: v0.1 (2026-06-15)
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

---

## 2. Runtime 구조

기존 검색기는 유지하고 내부를 보강한다.

1. `api.py` 는 공개 `search/prefetch/indexInfo` facade 로 남긴다.
2. `fieldIndex.py` 는 CSR main/delta load, source-aware metadata, dedup 을 책임진다.
3. `unified.py` 는 R* fusion 과 router expansion 을 맡는다.
4. `sourceIntent.py` 가 source hard isolation 을 먼저 결정한다.
5. `facetPlanner.py` 가 corp/date/report/receipt/news-title anchor 를 만든다.
6. `sourceRefPolicy.py` 가 top docs 를 citation set 으로 정규화한다.
7. `evidencePack.py` 가 chunk/field evidence 를 고른다.
8. `answerability.py` 가 no-answer 를 판정한다.
9. `memoryCard.py` 가 LLM 소비용 card 를 만든다.
10. `manifest.py` 가 index compatibility, sourceDataAsOf, tier, delta 상태를 노출한다.

이 구조에서 embedding 은 7번 evidence 선택 sidecar 로만 들어간다. 전역 후보 검색과 source isolation 은 sparse R* 가 담당한다.

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

1. source sync 가 allFilings, panel, news source manifest 를 갱신한다.
2. search delta workflow 가 source job 이후 실행된다.
3. DuckDB catalog 에 source row 를 stage 한다.
4. 이전 catalog 와 `doc_key/text_hash/metadata_hash/deleted` 를 비교한다.
5. new/changed/deleted 만 delta target 으로 export 한다.
6. delta CSR, delta stems, delta meta, delta info, delta manifest 를 만든다.
7. HF 에 파일을 업로드한 뒤 `current` pointer 또는 manifest 를 마지막에 publish 한다.
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
- `prefetch()` 는 manifest 검증 뒤 active pointer 를 전환한다.
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

- public contract: `limit` 계약, `topK` 드리프트 방지.
- source isolation: 뉴스 의도는 news 만, 공시 의도는 filing/panel 만.
- facet anchor: corp/date/report/receipt/news-title.
- R* regression: BM25, router expansion, RRF, main/delta dedup.
- catalog delta: allFilings/panel/news changed-only export, tombstone, panel priority.
- manifest/indexInfo: sourceDataAsOf, source counts, schema compatibility.
- lazy pull: partial artifact reject, offline mode, lite fallback.
- no-answer: unknown company, wrong date, wrong event, suffix/near-name traps.
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

---

## 8. 다음 구현 순서

1. result schema 와 manifest/indexInfo 계약부터 고정한다.
2. DuckDB catalog diff 를 allFilings, panel, news 세 source 로 확장한다.
3. search delta workflow 를 source sync 이후로 옮기고 panel/news delta 를 포함한다.
4. source intent, facet anchor, answerability 를 runtime 에 작게 붙인다.
5. evidence-card 와 memory-card 를 internal opt-in 으로 붙인다.
6. library result row 에 `sourceRef/dataAsOf/answerable` 을 노출한다.
7. local/public/shared surface 는 같은 result schema 를 소비하게 한다.
8. 실제 query-log gold 100~300 rows 를 확보해 졸업 gate 를 실행한다.

