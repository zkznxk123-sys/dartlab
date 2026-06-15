# 01. 아키텍처 계약 — catalog · retrieval · evidence · memory 분리

상태: v0.1
범위: 제품화 시 본진 배치 책임과 import 경계.

---

## 1. 책임 분리

| 층 | 책임 | 제품화 위치 후보 |
|---|---|---|
| Catalog | doc_key, source, text_hash, dataAsOf, changed/new 판정 | `providers/dart/search` 또는 prebuild/sync 경로 |
| Sparse Index | CSR main+delta, source-aware metadata, tier/lazy pull | 기존 `fieldIndex*` |
| Planner | source intent, entity/date/event/report facet, no-answer facet | `providers/dart/search` 내부 모듈 |
| Evidence | top docs 에서 chunk/field/sourceRef evidence pack | `providers/dart/search` 내부 모듈 |
| Memory Card | LLM 세션 재사용용 sourceRef set + snippet + field card | AI/tool boundary 에서 소비, 생성은 search 내부 |
| Gate | product readiness, query-log gold, multi-seed random | `tests/search` 승격 전 `_attempts` |

공개 surface 는 `dartlab.search(...)` 하나다. 내부 모듈명은 제품 계약이 아니다.

---

## 2. DuckDB 의 위치

DuckDB 는 "검색 런타임"이 아니다.

쓰는 곳:

- allFilings, panel parquet, news row 를 같은 catalog row 로 stage.
- `doc_key + text_hash` 로 unchanged/new/changed 판정.
- delta CSR 빌드 대상 export.
- 월간 main compaction 대상 export.
- query-log/gold coverage 분석.

쓰지 않는 곳:

- 한국어 full-text ranking.
- LLM 근거 생성.
- 사용자 런타임 질의의 직접 검색 엔진.

---

## 3. 랭킹 구조

기본 랭킹은 R* sparse 이다.

1. content/body BM25 lane. 공시 원문, panel 롤업 본문, 뉴스 본문/요약을 기본 검색 대상으로 둔다.
2. curated synonym + deterministic router canon lane.
3. RRF fusion.
4. source intent hard isolation.
5. filing 은 entity/date/event/report facet recall 로 보강.
6. title/report name/section title 은 recall 보조 anchor 이며, 본문 검색을 대체하지 않는다.
7. news 는 content R* + title anchor + source filter.
8. exact receipt number 가 질의에 있으면 metadata anchor.
9. evidence pack 은 랭킹을 바꾸는 메인 엔진이 아니라 근거 조각 선택기.

dense embedding 은 전역 검색을 대체하지 않는다. 쓰려면 R* 후보 안에서 chunk evidence 를 고르는 sidecar 로만 쓴다.

제품 검색의 기본은 제목 검색이 아니다. 제목, 보고서명, section title 은 빠른 anchor 로 쓰되, 답변 가능한 검색은 본문 content lane 과 sourceRef evidence 를 반드시 통과해야 한다.

---

## 4. source 계약

`source` 는 검색 품질의 핵심 차원이다.

| source | 의미 | 사용자 노출 |
|---|---|---|
| `allFilings` | 비정기/전체 공시 원문 | DART viewer URL, rceptNo |
| `panel` | 정기공시 섹션 롤업 | DART viewer URL, rceptNo, section refs |
| `news` | 뉴스 row | article URL 또는 `news:` id |

`공시 말고 뉴스`, `기사로`, `뉴스 말고 공시`, `공시 원문` 같은 질의는 source isolation 을 강제한다. 목표 source 후보가 하나라도 있으면 다른 source 로 fallback 하지 않는다.

---

## 5. no-answer 구조

검색 결과가 있다는 것과 답할 수 있다는 것은 다르다.

답변 가능 조건:

- sourceRef set 이 query 의 entity/date/event/report/source facet 을 동시에 만족.
- 공시 질의에서 receipt number 가 명시되면 해당 rceptNo 가 포함.
- no-answer target 은 가까운 문서가 있어도 facet 불일치면 reject.

제품화 시 이 조건은 UI/API 에서 "근거 부족" 상태로 드러나야 한다. 빈 결과와 구분한다.

---

## 6. 본진 승격 후보 파일

실험에서 바로 들고 올 개념:

- sourceRef/report intent policy.
- source isolation planner.
- receipt number anchor.
- news title anchor + source filter.
- evidence pack field diversity.
- memory-card sourceRef set.
- query-log gold contract.

실험에서 버릴 것:

- 실험용 긴 파일 구조.
- probe 전용 aggregate 출력.
- corpus proxy gold 를 제품 ready 로 취급하는 옵션.
- narrow template 의 특수 case 분기.
