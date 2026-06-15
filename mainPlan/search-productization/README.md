# 검색 제품화 준비 — 공시·뉴스 의미검색을 제품 계약으로 승격

상태: 제품화 PRD v0.1 (2026-06-15)
범위: `dartlab.search(...)` 공개계약은 유지하고, 내부 검색·RAG evidence·운영 gate 를 제품 수준으로 승격한다.

---

## 한 줄 결론

**제품화 방향은 새 검색 API 를 만드는 것이 아니라, 기존 `dartlab.search(...)` 안쪽을 large corpus · source isolation · evidence card · query-log gold gate 로 교체하는 것이다.**

실험은 충분히 강하다. 57337 docs large gate 에서 combined product readiness 는 통과했고, seeded random curatedDraft 300 rows 는 readyRate 0.99 까지 나왔다. 하지만 실제 사용자 query-log gold 가 아직 없으므로 제품 졸업이라고 부르지는 않는다. 제품화 준비의 핵심은 이 경계를 코드·문서·gate 로 고정하고, 실제 로그가 들어오면 같은 표면에서 졸업 여부를 자동 판정하게 만드는 것이다.

2026-06-15 demo-ops ceiling run 에서는 로컬 최대에 가까운 301579 docs(allFilings 191827 + panel 104752 + news 5000)를 한 번 로드·인덱싱한 뒤 3 seeds × 100 운영형 질의를 처리했다. 결과는 readyRate 0.9867, filing memoryAnswerReady 0.98, news sourcePrecision10 0.9867, noAnswer falseAcceptRate 0.0, warm query p95 157.9ms, max 173.9ms 였다. 즉 본진 이식 착수 기준은 확보됐고, 릴리즈 졸업만 실제 query-log gold 로 남는다.

---

## 제품 계약

공개 표면은 그대로 간다.

```python
import dartlab

dartlab.search("유상증자")
dartlab.search("반도체 HBM 투자", scope="content")
dartlab.search("공시 말고 뉴스로 환율 기사", scope="news")
dartlab.search("대표이사 변경", corp="005930", start="20240101")
```

새 sibling public call 을 만들지 않는다. RAG, sourceRef set, evidence pack, DuckDB catalog, query planner 는 내부 구현이다. 외부 사용자는 검색 결과와 `dataAsOf`, `source`, `sourceRef`, `dartUrl`/article URL 만 본다.

---

## 문서 지도

1. [00-product-vision.md](00-product-vision.md) — 무엇을 제품으로 만들고, 무엇을 졸업 증거로 볼지.
2. [01-architecture-contract.md](01-architecture-contract.md) — DuckDB catalog, CSR main/delta, source isolation, RAG memory-card 의 책임 분리.
3. [02-quality-gates.md](02-quality-gates.md) — 제품화 gate, 실제 query-log gold, multi-seed random 압박 기준.
4. [03-data-indexing-ops.md](03-data-indexing-ops.md) — allFilings, panel parquet, news 수집·증분·재색인 운영.
5. [04-rag-memory-contract.md](04-rag-memory-contract.md) — LLM 이 자기 지식처럼 쓰는 evidence card 계약.
6. [05-scope-phasing-guardrails.md](05-scope-phasing-guardrails.md) — Phase, kill list, 착수·중단 기준.
7. [06-progress-ledger.md](06-progress-ledger.md) — 현재 실측, 결정, NEXT.
8. [07-specialist-review.md](07-specialist-review.md) — runtime, HF 증분, surface, 품질 gate 전문 검토 결론.
9. [08-completion-design.md](08-completion-design.md) — HF 증분과 local/public/library 완성 설계.

---

## 제품화 척추

- `dartlab.search(...)` 단일 공개계약 유지.
- DuckDB 는 런타임 검색 엔진이 아니라 수집 카탈로그·변경 감지·증분 export 레이어.
- 기본 랭킹은 R* sparse CSR main+delta. dense embedding 은 전역 랭킹이 아니라 evidence sidecar 후보로만.
- source intent 는 soft preference 가 아니라 hard isolation. `공시 말고 뉴스`, `뉴스 말고 공시`는 fallback 하지 않는다.
- LLM 용 지식화는 전체 본문 주입이 아니라 `sourceRef set + snippet + field card + dataAsOf` memory-card 반복 주입.
- 제품 졸업은 실제 query-log gold 100~300 rows 통과 후에만. curatedDraft, stratifiedSynthetic 은 압박 실험일 뿐이다.
- 본진 이식은 가능하다. 단 이식 대상은 runtime 구조와 gate 이며, 제품 완성 선언은 실제 query-log gold 이후다.
- HF 증분은 source별 `doc_key/text_hash` catalog diff 로 처리한다. allFilings, panel, news 정상 갱신은 delta CSR 로 흡수하고, full rebuild 는 schema/tokenizer/normalizer/sourceRef 의미 변경 때만 한다.
