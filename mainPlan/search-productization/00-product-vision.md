# 00. 제품 비전 — 모든 공시·뉴스를 빠른 의미검색 진입점으로

상태: v0.1
범위: 제품 목표, 사용자 가치, 졸업 증거 정의.

---

## 1. 만들 제품

사용자는 "유상증자 원문", "뉴스 말고 공시", "이 회사가 그때 투자설명회 한 원문", "환율 관련 기사"처럼 부정확하고 구어적인 질의를 던진다. 제품은 이 질의를 다음 결과로 바꿔야 한다.

1. 공시 원문의 정확한 `rceptNo` 또는 뉴스 원문 URL.
2. 왜 이 문서가 맞는지 보여주는 sourceRef.
3. LLM 이 다음 턴에서 재사용할 수 있는 짧은 evidence card.
4. 답할 수 없는 질문이면 검색 결과가 있어도 답변 거절.

이것은 일반 챗봇 검색이 아니다. dartlab 의 차별점은 공시 원문을 찾는 데 있다. 뉴스는 공시와 같은 검색면에 들어오되, source intent 에 따라 분리되어야 한다.

---

## 2. 사용자 워크플로

1. 사용자가 자연어로 묻는다.
2. search 가 공시·뉴스 source intent 를 판정한다.
3. source 별 후보를 만들고 entity/date/event/report facet 으로 재정렬한다.
4. 상위 문서에서 evidence pack 을 만든다.
5. memory-card 를 세션에 남긴다.
6. 후속 질문은 memory-card 를 우선 사용하되, 불충분하면 다시 search 한다.

LLM 이 "자기 지식처럼" 쓰는 개념은 모델 파라미터에 넣는 것이 아니라, 세션과 장기 캐시에 작은 근거팩을 저장하고 반복 주입하는 것이다.

---

## 3. 현재 실측

`tests/_attempts/searchCatalogDuckdb` 기준:

| 항목 | 현재 수치 |
|---|---:|
| large corpus | 57337 docs = allFilings 43717 + panel 8620 + news 5000 |
| combined readiness | productReady true |
| RAG session | memoryAnswerReady 0.9988, memoryCitationTop3Exact 0.9988, field 1.0 |
| source intent | eventHit1 0.9967, exactHit10 0.9989, sourcePrecision10 0.9820 |
| manual operator gold | filing required 1.0, news exactHit1 0.9938 |
| no-answer | falseAcceptRate 0.0 |
| random curatedDraft 300 | readyRate 0.99, miss 3 |

이 수치는 제품 후보로 충분하다. 하지만 실제 로그 gold 가 아니므로 "제품 졸업"은 아니다.

---

## 4. 졸업 증거

제품 졸업은 다음 모두가 참일 때만 부른다.

1. 실제 사용자 또는 운영자 라벨 query-log gold 100~300 rows.
2. filing/news/noAnswer target coverage 모두 존재.
3. overall readyRate >= 0.9.
4. filing docHit10, memoryCitationTop3Exact, memoryAnswerReady >= 0.9.
5. news exactHit10, targetSourceTop1, sourcePrecision10 >= 0.9.
6. noAnswer negativeRejectRate >= 0.9, falseAcceptRate <= 0.1.
7. 같은 corpus 에서 multi-seed curatedDraft 압박이 안정적으로 통과.
8. `dataAsOf` 와 sourceRef 가 모든 사용자 노출 결과에 남는다.

---

## 5. 비목표

- 새 공개 API 를 늘리지 않는다.
- DuckDB FTS 를 기본 검색 엔진으로 승격하지 않는다.
- 전체 문서 dense embedding 을 메인 랭킹으로 쓰지 않는다.
- CAG 처럼 공시 전체를 LLM 컨텍스트에 넣으려 하지 않는다.
- source intent 를 애매한 preference 로 두지 않는다.
- query-log gold 없는 상태에서 제품 완성이라고 말하지 않는다.

