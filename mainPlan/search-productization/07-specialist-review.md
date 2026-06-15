# 07. 전문 검토 결론 — 검색 엔진 완성 방향

상태: v0.1 (2026-06-15)
범위: runtime, HF 증분, local/public/library surface, 품질 gate 를 함께 검토한 최종 설계 판단.

---

## 1. 최종 판정

검색 제품화는 착수 가능하다. 단 완성 선언은 아직 아니다.

현재 실험은 300k 문서급에서도 warm p95 200ms 안쪽, readyRate 0.9867 로 본진 이식 가치가 충분하다. 그러나 실제 사용자 query-log gold 가 없으므로 릴리즈 졸업은 차단한다. 제품화는 `dartlab.search(...)` 공개계약을 유지한 채 내부 검색기, catalog 증분, evidence-card, no-answer, source isolation 을 교체하는 방식으로 간다.

---

## 2. 합의된 결정

| 영역 | 결정 |
|---|---|
| 공개 API | `dartlab.search(query, *, corp=None, start=None, end=None, limit=10, scope=...)` 하나만 유지한다. |
| 검색 엔진 | R* sparse CSR main+delta 를 기본으로 둔다. dense embedding 은 전역 ranker 가 아니라 evidence sidecar 후보로만 쓴다. |
| DuckDB | runtime 검색기가 아니라 catalog stage, diff, changed export, query-log 분석 계층이다. |
| source intent | 뉴스/공시 의도가 명확하면 hard isolation 한다. 목표 source 후보가 있으면 다른 source fallback 금지. |
| RAG/memory | 전체 본문을 주입하지 않고 `sourceRef set + snippet + fieldCards + dataAsOf` memory-card 를 반복 사용한다. |
| 품질 판정 | random pressure 는 overfit 감지, 실제 query-log gold 는 제품 졸업 gate 로 분리한다. |
| 재색인 | 데이터 추가는 delta 로 흡수한다. tokenizer/normalizer/doc_key/schema/sourceRef 의미가 바뀔 때만 full rebuild 한다. |

---

## 3. 차단 리스크

1. 본진 runtime 에 source intent planner, receipt/news-title anchor, no-answer, evidence-card 가 아직 없다.
2. daily delta 가 현재 allFilings 중심이라 panel/news 최신성이 월간 main 전까지 비어 있다.
3. `indexInfo()` 의 `dataAsOf` 는 build time 성격이라 source 별 최신성을 설명하지 못한다.
4. 결과 row 에 `sourceRef`, `dataAsOf`, `answerable`, `notAnswerableReason`, `fieldCards` 가 필수 계약으로 붙어 있지 않다.
5. `dartlab search` CLI 는 현재 종목명 검색이고, public landing `/search` 는 사이트 검색이다. 공시/뉴스 corpus search 와 이름이 충돌한다.
6. 실제 query-log gold 100~300 rows 가 없어서 제품 졸업 metric 은 아직 실행할 수 없다.

---

## 4. Surface 결론

| surface | 제품화 방식 |
|---|---|
| Python library | 최우선 surface. HF contentIndex lazy pull, lite/full tier, `indexInfo()` freshness, result row evidence 계약을 붙인다. |
| Local UI | Python runtime adapter 또는 `/api/search` 로 full/local cache 를 사용한다. terminal/viewer 는 같은 evidence-card schema 를 소비한다. |
| Public landing | full 300k index 를 브라우저에 강제하지 않는다. static/lite artifact 로 시작하고 stale 상태를 노출한다. 최신/live 성격 질문은 library/local 로 승격한다. |
| Viewer in-page search | 현재 문서 검색으로 유지한다. global corpus search 와 섞지 않고 같은 evidence-card shape 로 변환만 한다. |
| CLI | 기존 `dartlab search` 를 공시 검색으로 갑자기 바꾸지 않는다. 회사 검색임을 명확히 하거나 별도 명시 명령을 설계한다. |

---

## 5. 이식 원칙

본진 승격은 `_attempts` 코드를 그대로 옮기는 작업이 아니다. 다음 책임으로 작게 나눈다.

- `api.py`: 공개 facade 유지.
- `fieldIndex.py`: CSR main/delta segment search 유지.
- `unified.py`: R* fusion, router expansion, source-aware ranking.
- `catalog.py`: DuckDB catalog stage, `doc_key/text_hash` diff, changed export.
- `sourceAdapters.py`: allFilings, panel, news row 를 canonical catalog row 로 변환.
- `sourceIntent.py`: source hard isolation.
- `facetPlanner.py`: corp/date/report/receipt/news-title anchor.
- `sourceRefPolicy.py`: primary citation 과 sourceRef set 정책.
- `evidencePack.py`: chunk/field evidence 선택.
- `memoryCard.py`: LLM 소비용 card 생성.
- `answerability.py`: no-answer 판정.
- `manifest.py`: schemaVersion, source counts, sourceDataAsOf, tier, delta compatibility.

---

## 6. 금지선

- `searchSemantic`, `ragSearch`, `vectorSearch` 같은 sibling public API 금지.
- dense global ranker 기본화 금지.
- DuckDB FTS 를 제품 ranking 으로 승격 금지.
- source intent fallback 금지.
- panel/news 증분 없이 "자동 최신" 주장 금지.
- 실제 query-log gold 없이 제품 완성 선언 금지.
- miss 1건마다 특수 mapper 를 붙이는 방식 금지.

