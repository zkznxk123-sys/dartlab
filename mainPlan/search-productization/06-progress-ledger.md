# 06. 진행 원장 — 결정 · 실측 · NEXT

상태: v0.1 (2026-06-15)
범위: 검색 제품화 준비 결정과 다음 작업.

---

## 1. 확정 결정

1. 공개계약은 `dartlab.search(...)` 유지. 새 public call 은 만들지 않는다.
2. DuckDB 는 catalog/export/diff 레이어로만 쓴다.
3. 기본 검색은 R* sparse CSR main+delta.
4. dense embedding 은 evidence sidecar 후보로만 둔다.
5. source intent 는 hard isolation.
6. RAG memory 는 전체 문서 주입이 아니라 sourceRef set 기반 memory-card.
7. 제품 졸업은 실제 query-log gold 통과 후에만.
8. 전문 검토 결론: 본진 이식 착수는 가능하나 release graduation 은 실제 query-log gold 로 차단한다.
9. HF 증분은 source별 catalog diff 로 간다. allFilings, panel, news 정상 갱신은 delta CSR 이며, full rebuild 는 schema/tokenizer/normalizer/sourceRef 의미 변경 때만 한다.
10. 혁신 방향은 typed sourceRef graph, runtime intent kernel, sparse-first hybrid, incremental knowledge fabric, quality flywheel 로 묶는다. prebuild intent dictionary, 덕지덕지 mapper, 새 public API 는 금지한다.

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

주의: random curatedDraft 는 제품 졸업 증거가 아니라 압박 실험이다.

---

## 3. 남은 약점

1. 실제 query-log gold 부재.
2. 실험 코드가 probe 중심이라 본진 모듈 경계로 아직 분해되지 않음.
3. 제품 UI/API 에서 evidence card 와 answerable 상태 노출 계약이 아직 없음.
4. 초기 load/build 가 무겁다. 본진에서는 prebuilt main+delta artifact 로 넘겨야 한다.
5. 현재 daily delta 는 allFilings 중심이라 panel/news 최신성이 월간 main 전까지 지연된다.
6. CLI `dartlab search`, public `/search`, viewer in-page search 가 서로 다른 검색이라 surface 명칭 충돌이 있다.

---

## 4. NEXT

- [ ] Phase 0 리뷰: 이 PRD 가 제품화 방향으로 충분한지 확인.
- [x] `_attempts` 에 multi-seed random pressure runner 추가. (`productRandomPressureSweep.py`)
- [x] 실제 데모 운영형 ceiling run 실행. 301579 docs, 300 queries, readyRate 0.9867, p95 157.9ms.
- [ ] 실제 query-log gold 저장 위치와 review status 절차 확정.
- [x] 전문 검토 반영: runtime/HF 증분/local-public-library/품질 gate 설계 문서화. (`07-specialist-review.md`, `08-completion-design.md`)
- [x] 혁신 방향 문서화: 빠른 의미검색, sourceRef graph, intent kernel, 증분 운영, 덕지덕지 방지. (`09-innovation-roadmap.md`)
- [x] 본진 이식 파일 지도 작성: planner/evidence/memory/sourcePolicy/test slots.
- [ ] result schema 와 manifest/indexInfo 계약을 본진 변경 전 확정.
- [ ] allFilings/panel/news catalog delta 설계를 `_attempts` 졸업 산출물과 맞춰 본진 이식 단위로 쪼갬.
- [ ] targeted regression test 목록을 `tests/search` 기준으로 쪼갬.
- [ ] 실제 query-log 100~300 rows 확보 후 졸업 gate 실행.

---

## 5. 착수 게이트

본진 `src/dartlab/**` 변경은 아직 시작하지 않는다. `_attempts` 졸업 게이트상 제품화 설계와 multi-seed 압박이 먼저다. 본진 이식은 Phase 0 승인 뒤 작은 모듈 단위로 진행한다.
