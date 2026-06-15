# 02. 품질 Gate — 제품 후보와 제품 졸업을 분리

상태: v0.1
범위: 제품화 전후의 필수 품질 기준.

---

## 1. Gate 계층

| gate | 목적 | 통과 의미 |
|---|---|---|
| readiness proxy | 현재 검색 stack 이 제품 후보인지 | 본진 이식할 가치 있음 |
| random pressure | 랜덤 질의 분포에도 안정적인지 | template overfit 위험 감소 |
| query-log gold | 실제 사용자/운영자 질의에서 맞는지 | 제품 졸업 가능 |
| regression guard | 본진 변경 후 품질 유지 | 배포 가능 |

`productReadinessGate.py` 는 후보 품질을 본다. `productQueryLogGoldProbe.py` 는 실제 졸업 gate 다.

---

## 2. 현재 기준선

large corpus 기준:

- corpus: 57337 docs.
- product readiness: pass.
- random curatedDraft 300: readyRate 0.99.
- miss: 3.
- demo-ops ceiling: 301579 docs, 3 seeds × 100 rows, readyRate 0.9867, warm p95 157.9ms, max 173.9ms.
- known residual:
  - receipt-number-only filing 의 answer field 완성도 1건.
  - 제목/출처가 매우 비슷한 news 2건.

제품화 전 이 3건은 "차단 결함"은 아니다. query-log gold 에서 반복되면 차단 결함으로 승격한다.

---

## 3. 실제 query-log gold 계약

필드:

| target | 필요한 gold |
|---|---|
| filing | `rceptNo`/`docId` 또는 `corpName/stockCode + rceptDt + event/reportNm` |
| news | `docId` 또는 `url/link` 또는 `title` |
| noAnswer | `expectedAnswerable=false` |

공통:

- `query` 또는 `q`.
- `target`.
- `goldOrigin`.

`goldOrigin` 이 `sample`, `synthetic`, `stratifiedSynthetic`, `curatedDraft`, `operatorCuratedDraft`, `proxy` 면 제품 졸업 증거가 아니다. 실험에서만 `--allow-proxy-query-log` 로 통과시킨다.

---

## 4. 제품 졸업 기준

최소:

- rows >= 100, 권장 300.
- required target coverage: filing, news, noAnswer 모두.
- overall readyRate >= 0.9.
- filing docHit10 >= 0.9.
- filing memoryCitationTop3Exact >= 0.9.
- filing memoryAnswerReady >= 0.9.
- news exactHit10 >= 0.9.
- news targetSourceTop1 >= 0.9.
- news sourcePrecision10 >= 0.9.
- noAnswer negativeRejectRate >= 0.9.
- noAnswer falseAcceptRate <= 0.1.

제품 후보에서 제품 졸업으로 바꿀 때는 strict primary citation 을 별도 warning track 으로 유지한다. 같은 날짜 형제공시 때문에 strict exact 가 낮아져도 sourceRef set 과 report intent preference 가 맞으면 운영 품질에는 치명적이지 않다.

---

## 5. random pressure 기준

실제 로그가 쌓이기 전에는 multi-seed curatedDraft 로 압박한다.

권장:

- seed 5개 이상.
- seed 당 rows >= 300.
- filing/news/noAnswer 비율 유지.
- min readyRate >= 0.95.
- average readyRate >= 0.98.
- news sourcePrecision10 min >= 0.95.
- noAnswer falseAcceptRate max == 0.0.

이 gate 는 제품 졸업 증거가 아니라 overfit 감지용이다.

실험 runner:

```bash
uv run python -X utf8 tests/_attempts/searchCatalogDuckdb/productRandomPressureSweep.py --all-filing-files 64 --hf-extra-files 40 --panel-files 240 --news-rows 5000 --filing-gold-rows 140 --news-gold-rows 80 --no-answer-gold-rows 80 --seeds 20260615,20260616,20260617,20260618,20260619 --per-event 12 --news-samples 160 --candidate-pool 500 --rerank-window 120 --doc-pool 12 --source-pool 20 --top-chunks 6 --memory-snippet-chars 360
```

---

## 6. 본진 회귀 테스트 승격

본진 이식 시 최소 테스트:

- source intent hard isolation.
- receipt number anchor.
- news title anchor.
- no-answer wrong company/date/event/unknown/suffix trap.
- memory-card sourceRef top3.
- field evidence coverage.
- dataAsOf presence.
- search scope `auto/title/content/news/both` contract.

전수 `pytest tests/ -v` 대신 변경 파일과 search gate 중심으로 돌리고, L0~L1.5 경계 변경이면 Guard Index strict 를 추가한다.
