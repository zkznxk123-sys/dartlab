# 05. Phase · Guardrails — 제품화 순서와 금지선

상태: v0.1
범위: 착수 순서, 중단 기준, kill list.

---

## Phase 0 — 계약 동결

목표:

- `dartlab.search(...)` 공개계약 유지.
- sourceRef/result schema 최소 필드 확정.
- query-log gold schema 확정.
- 실제 로그 저장 위치·리뷰 절차 확정.

완료 기준:

- PRD 리뷰 완료.
- 본진 변경 전 실험 metrics baseline 문서화.
- 실제 query-log gold 파일 샘플이 제품 증거와 proxy 증거를 분리.

---

## Phase 1 — 본진 이식 설계

목표:

- 실험 코드를 작은 search 내부 모듈로 분해할 파일 지도 확정.
- source intent planner, facet recall, evidence pack, memory-card 계약 분리.
- test mirror 슬롯 확정.

완료 기준:

- 새 public API 0.
- L1/L1.5 import 경계 위반 0.
- 테스트 목록과 fixture 전략 확정.
- demo-ops ceiling 기준 readyRate >= 0.98, warm p95 < 200ms 수준을 유지.

---

## Phase 2 — runtime 승격

목표:

- 현재 `searchUnified` 내부에 source-aware R* 흐름 반영.
- `scope="news"` source isolation 개선.
- receipt number anchor, news title anchor 반영.
- evidence card 는 내부 opt-in 으로 생성.

완료 기준:

- 기존 `tests/search/*` green.
- 신규 targeted tests green.
- product readiness proxy 재실행.
- 300k docs demo-ops ceiling 재실행에서 품질·속도 회귀 없음.

---

## Phase 3 — 제품 gold

목표:

- 실제 query-log gold 100~300 rows 확보.
- `productQueryLogGoldProbe` 성격의 gate 를 본진 테스트/감사 경로로 승격.
- multi-seed random pressure 를 nightly 또는 수동 release gate 로 둔다.

완료 기준:

- queryLogProductReady true.
- proxy/real origin guard 통과.
- miss ledger 가 남고 반복 miss type 이 정책 backlog 로 분류.

---

## Phase 4 — UX/API 연결

목표:

- 검색 결과에 `dataAsOf`, `source`, `sourceRef`, URL, answerable 상태를 노출.
- terminal/viewer/AI consumer 가 같은 evidence card 를 읽는다.
- stale 인덱스와 no-answer 를 사용자에게 구분해 보여준다.

완료 기준:

- UI 는 sourceRef 없는 답변을 만들지 않는다.
- 최신성 표현이 `dataAsOf` 기반.
- 공시/뉴스 source 혼동 0.

---

## Kill List

- 새 공개 함수 추가.
- `searchSemantic`, `ragSearch`, `vectorSearch` 같은 sibling API.
- Dense global ranker 를 기본 검색으로 승격.
- DuckDB FTS 를 제품 랭킹으로 승격.
- source intent fallback.
- 실제 query-log gold 없이 제품 완성 선언.
- miss 1건마다 특수 mapper 추가.
- 전체 재색인을 일상 운영으로 전제.
