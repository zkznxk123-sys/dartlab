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

주의: random curatedDraft 는 제품 졸업 증거가 아니라 압박 실험이다.

---

## 3. 남은 약점

1. 실제 query-log gold 부재.
2. multi-seed random pressure runner 는 생겼지만 large 5-seed 본실행은 아직 안 함.
3. 300-row miss 3건의 반복성 미확인.
4. 실험 코드가 probe 중심이라 본진 모듈 경계로 아직 분해되지 않음.
5. 제품 UI/API 에서 evidence card 와 answerable 상태 노출 계약이 아직 없음.

---

## 4. NEXT

- [ ] Phase 0 리뷰: 이 PRD 가 제품화 방향으로 충분한지 확인.
- [x] `_attempts` 에 multi-seed random pressure runner 추가. (`productRandomPressureSweep.py`)
- [ ] 실제 query-log gold 저장 위치와 review status 절차 확정.
- [ ] 본진 이식 파일 지도 작성: planner/evidence/memory/sourcePolicy/test slots.
- [ ] targeted regression test 목록을 `tests/search` 기준으로 쪼갬.
- [ ] 실제 query-log 100~300 rows 확보 후 졸업 gate 실행.

---

## 5. 착수 게이트

본진 `src/dartlab/**` 변경은 아직 시작하지 않는다. `_attempts` 졸업 게이트상 제품화 설계와 multi-seed 압박이 먼저다. 본진 이식은 Phase 0 승인 뒤 작은 모듈 단위로 진행한다.
