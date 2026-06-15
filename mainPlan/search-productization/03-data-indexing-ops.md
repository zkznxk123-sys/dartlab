# 03. 데이터·인덱싱 운영 — 계속 늘어나는 문서를 재색인 없이 흡수

상태: v0.1
범위: allFilings, panel parquet, news 를 제품 검색 인덱스로 운영하는 방식.

---

## 1. 입력 데이터

| 입력 | 역할 |
|---|---|
| allFilings | 비정기/전체 공시 원문. 빠른 최신성의 핵심. |
| panel parquet | 정기공시 섹션·재무 표와 연결되는 깊은 원문. |
| news | 공시와 구분되는 외부 기사 source. |

제품 검색은 세 데이터를 한 catalog 에 stage 하되, source 를 잃으면 안 된다.

---

## 2. 증분 원칙

추가 데이터만 들어오면 전체 재색인이 아니다.

1. catalog 에 stage.
2. `doc_key + text_hash` 로 unchanged/new/changed 판정.
3. unchanged 는 skip.
4. new/changed 만 delta CSR 로 빌드.
5. chunk embedding/evidence cache 도 new/changed 만 갱신.
6. 월간 또는 임계치 초과 시 main compaction.

전체 rebuild 가 필요한 경우:

- tokenizer 변경.
- normalizer 변경.
- embedding model 또는 chunk rule 변경.
- index schemaVersion 변경.
- sourceRef 정책 변경으로 기존 metadata 의미가 바뀜.

증분 catalog 는 source 별 manifest 를 소비한다. search index workflow 는 allFilings, panel, news row 를 DuckDB catalog 에 stage 하고 `doc_key/text_hash/metadata_hash/deleted` 로 changed set 을 만든다. daily delta 는 allFilings 만이 아니라 panel changed rcept 와 news changed row 도 포함해야 한다.

---

## 3. main + delta 운영

제품 런타임은 main 과 delta 를 합쳐 검색한다.

- main: 안정 세그먼트, 월간 compaction.
- delta: 일간 또는 수집 직후 증분.
- 같은 `(rceptNo, sectionOrder)` 는 delta 우선.
- `indexInfo()` 는 `dataAsOf`, `nDocs`, `hasDelta`, `schemaVersion`, `compatible` 을 반환.

사용자에게 "최신"이라고 말하려면 `dataAsOf` 가 필요하다. 오래된 인덱스면 `Company.liveFilings()` 같은 라이브 경로를 병행한다.

---

## 4. news 운영

뉴스는 공시와 같은 검색 표면에 들어오지만 같은 source 가 아니다.

- `source=news` 를 metadata 에 보존.
- news URL 또는 `news:` id 를 sourceRef 로 보존.
- article text 는 untrusted external content 로 취급.
- 뉴스 저작권·공개/비공개 경계 때문에 제품 노출은 headline/link 중심으로 시작한다.

제품화 초기에는 "공시 원문 찾기"가 주목표이고, 뉴스는 source intent isolation 과 cross-source answer 에서 보조한다.

---

## 5. 운영 산출물

필수 산출물:

- catalog snapshot: staged docs, source counts, changed/new/unchanged.
- index manifest: artifactVersion, schemaVersion, builtAt, mainDataAsOf, deltaDataAsOf, sourceDataAsOf, source counts, tier, changed/new/deleted/unchanged counts, build command.
- quality report: readiness, query-log gold, random pressure.
- miss ledger: miss query, target, topDocs, 판단.

miss ledger 는 제품 품질 개선의 실제 backlog 다. 특수 case 를 즉시 붙이지 말고, 반복되는 miss type 만 정책으로 승격한다.

---

## 6. 속도·메모리 목표

제품 목표:

- warm search: 사용자가 체감하는 즉시성.
- sparse index 메모리: 현 large 기준 수십 MB대 유지.
- evidence card: 평균 4KB 이하.
- incremental update: unchanged skip 과 chunk reuse 유지.

LLM 호출 비용은 검색 품질을 올리는 수단이 아니라, 검색 결과를 설명하는 소비자 단계로 둔다.

2026-06-15 ceiling run 기준 현재 상한:

| 항목 | 실측 |
|---|---:|
| docs | 301579 |
| loadSec | 574.2 |
| contextSec / indexBuildSec | 151.5 / 148.1 |
| warm query p50 / p95 / max | 123.1ms / 157.9ms / 173.9ms |
| content CSR memory | 약 591MB |
| metadata CSR memory | 약 36.9MB |

빌드·로드는 무겁지만 데모 운영에서는 한 번만 수행된다. warm query 는 300k 문서에서도 200ms 안쪽이라 제품 데모에 충분하다. 본진 이식 시 과제는 query latency 가 아니라 초기 load/build 를 prebuilt main+delta artifact 로 넘기는 것이다.
