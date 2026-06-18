# 02. 품질 Gate — 제품 후보와 제품 졸업을 분리

상태: v1.0 (2026-06-18)
범위: 제품화 전후의 필수 품질 기준.

---

## 1. Gate 계층

| gate | 목적 | 통과 의미 |
|---|---|---|
| readiness proxy | 현재 검색 stack 이 제품 후보인지 | 본진 이식할 가치 있음 |
| random pressure | 랜덤 질의 분포에도 안정적인지 | template overfit 위험 감소 |
| source/no-answer canary | source isolation 과 false accept 를 운영 전 차단하는지 | publish/activate 안전성 확인 |
| result contract audit | 결과 row 가 LLM/UI 근거 계약을 만족하는지 | 제품 표면으로 노출 가능 |
| query-log gold | 실제 사용자/운영자 질의에서 맞는지 | 제품 졸업 가능 |
| regression guard | 본진 변경 후 품질 유지 | 배포 가능 |

`productReadinessGate.py` 계열은 후보 품질을 본다. 본진 쪽 실제 졸업 gate 는 `src/dartlab/providers/dart/search/qualityGate.py` 와 `.github/scripts/search/evaluateSearchGold.py` 로 고정한다. source/no-answer canary 는 publish/local activation 전 차단 게이트이며, release graduation 증거는 아니다. artifact positive canary 는 `requireAnswerable=true` 로 생성해 source lane 만 맞는 빈 evidence 결과를 통과시키지 않는다. result contract audit 는 품질 점수가 아니라 제품 row 표면의 최소 계약을 막는 gate 다. productization status audit 는 이 증거들을 묶어 ops/release hard gate 로 판정하며, quality report 의 `releaseEligible=true` 를 그대로 믿지 않고 origin/review/coverage counts 를 다시 검사한다.

---

## 2. 현재 기준선

large corpus 기준:

- corpus: 57337 docs.
- product readiness: pass.
- random curatedDraft 300: readyRate 0.99.
- miss: 3.
- demo-ops ceiling: 301579 docs, 3 seeds × 100 rows, readyRate 0.9867, warm p95 157.9ms, max 173.9ms.
- direct-review release gate: 462947 docs full current, 106 real reviewed userLog rows, releaseEligible=true, blockers=[].
- direct-review coverage: filing 54 / news 20 / EDGAR 20 / noAnswer 12.
- direct-review metrics: overallReadyRate 1.0, docHit10 1.0, memoryCitationTop3Exact 1.0, newsSourcePrecision10 1.0, noAnswerFalseAcceptRate 0.0.
- known residual:
  - CAPEX/AI 데이터센터 사업보고서 2개 후보는 sourceHint mismatch 로 reviewable set 에서 제외했다. 현재 품질 수치에 몰래 포함하지 않는다.

제품화 전 proxy/curated miss 는 차단 결함이 아니었다. direct-review 이후의 신규 miss 는 miss ledger 에 기록하고 반복 유형이면 일반 정책으로만 승격한다.

2026-06-18 live runtime spot check 에서 `HBM 설비투자와 TC bonder 증설을 언급한 공시 원문` 은 본문 의미 질의로 분류되어 panel/allFilings HBM 근거가 top-5 에 들어왔고, `화성 지하도시에 상장사가 얼음광산을 매입했다` 는 후보 score 가 전부 confidence floor 아래라 `answerable=false`, `notAnswerableReason=lowConfidence` 로 차단됐다. 이 기준은 query별 mapper 가 아니라 본문 의미 rerank + low-confidence no-answer 정책이다.

2026-06-18 full query-log gold 는 `releaseEligible=true` 로 회복됐다. `overallReadyRate=0.9811`, `docHit10=0.9787`, `memoryCitationTop3Exact=0.9468`, `newsSourcePrecision10=1.0`, `noAnswerFalseAcceptRate=0.0` 이다. 본문/주석/위험요인 같은 정형 content 질의는 content lane 점수를 보존하고, `언급/다룬/수혜/증설/설비투자/전력/인프라` 같은 주제형 의미 질의만 body semantic rerank 를 탄다.

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
- `reviewStatus`.
- `expectedSourceRef` 또는 `expectedSourceRefs` 권장.

`goldOrigin` 이 `sample`, `synthetic`, `stratifiedSynthetic`, `curatedDraft`, `operatorCuratedDraft`, `proxy` 면 제품 졸업 증거가 아니다. 실험에서만 `--allow-proxy-query-log` 로 통과시킨다.

release graduation 에서는 `goldOrigin=real` 계열과 `reviewStatus=reviewed` 계열만 인정한다.

`runSearchQualityDrill.py` 가 만든 canonical rows 는 `goldOrigin=drillSynthetic`, `reviewStatus=drillReviewed` 다. 이 drill 은 raw log -> label -> canonical gold -> quality report -> miss ledger 도구 체인을 검증하지만, release graduation 에서는 `qualityProxyGoldRows:*` / `qualityUnreviewedGoldRows:*` blocker 로 남아야 정상이다.

raw 후보 수집:

```powershell
$env:DARTLAB_SEARCH_QUERY_LOG = "1"
uv run python -X utf8 -c "import dartlab; dartlab.search('삼성전자 대표이사 변경', topK=5)"
```

이 값이 `1` 이면 `{dartlab.dataDir}/search/queryLogRaw.jsonl` 에 candidate row 를 남긴다. 파일 경로를 직접 넣으면 그 경로에 쓴다. candidate row 는 `goldOrigin=userLog`, `reviewStatus=candidate` 이고 top sourceRef/source/answerability/dataAsOf 를 포함하지만, reviewer label 전에는 제품 졸업 증거가 아니다.

실행:

```powershell
uv run python -X utf8 .github/scripts/search/prepareSearchGold.py `
  --input data/search/queryLogRaw.jsonl `
  --label-template data/search/queryLogLabels.todo.jsonl `
  --out data/search/queryLogGold.draft.jsonl `
  --summary data/search/queryLogGold.draft.summary.json `
  --allow-proxy-query-log `
  --allow-missing-source-ref

uv run python -X utf8 .github/scripts/search/prepareSearchGold.py `
  --input data/search/queryLogRaw.jsonl `
  --labels data/search/queryLogLabels.reviewed.jsonl `
  --out data/search/queryLogGold.real.jsonl `
  --summary data/search/queryLogGold.summary.json `
  --min-rows 100 `
  --required-targets filing,news,noAnswer,edgar `
  --fail-on-ineligible

uv run python -X utf8 .github/scripts/search/evaluateSearchGold.py `
  --gold data/search/queryLogGold.real.jsonl `
  --out data/search/qualityReport.json `
  --miss-ledger data/search/missLedger.jsonl `
  --min-rows 100 `
  --required-targets filing,news,noAnswer,edgar `
  --fail-on-ineligible
```

`prepareSearchGold.py` 는 raw query log 와 reviewer label 을 합쳐 canonical JSONL 을 만든다. release graduation 용 운영 canonical path 는 `data/search/queryLogGold.real.jsonl` 이고, raw log 와 label source 는 같은 디렉터리의 `queryLogRaw.jsonl`, `queryLogLabels.reviewed.jsonl` 을 기본 운영 슬롯으로 둔다. GitHub Actions release gate 기본값은 repo에 고정한 `tests/fixtures/search/queryLogGold.real.jsonl` 이며, 운영 gold 를 새로 만들면 workflow `quality_gold` 입력으로 override 한다. answerable row 는 `expectedSourceRef` 또는 `expectedSourceRefs` 를 가져야 하며, noAnswer row 는 `expectedAnswerable=false` 로 보존한다.

---

## 4. 제품 졸업 기준

최소:

- rows >= 100, 권장 300.
- `realReviewedRows >= 100`.
- `goldOriginCounts` 가 real/userLog/operator 계열로 채워짐.
- `reviewStatusCounts` 가 reviewed/approved/accepted/gold 계열로 채워짐.
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

`docHit10` 과 `memoryCitationTop3Exact` 는 `answerable=True` 인 결과에서만 인정한다. sourceRef 가 맞아도 `missingDataAsOf`, `staleSource`, `facetMismatch:*` 같은 no-answer reason 이 붙은 row 는 release hit 가 아니다.

search runtime 은 후보를 반환하더라도 전체 후보군 score 가 confidence floor 아래면 `answerable=false` 로 내려야 한다. noAnswer gate 와 memory-card 생성은 이 플래그를 기준으로 false accept 를 판정한다.

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

## 6. 결과 row 계약 기준

검색이 정답 source 를 찾더라도 결과 row 가 `sourceRef`, `dataAsOf`, `snippet`, `answerable`, `fieldCards` 를 잃으면 LLM 이 자기 지식처럼 반복 사용할 수 없다. 따라서 release 후보 artifact 는 품질 점수와 별도로 result contract audit 를 통과해야 한다.

필수:

- 모든 row 는 `source`, `sourceRef`, `answerable` 을 가진다.
- release 후보는 `dataAsOf` 와 `snippet` 이 빈값이면 실패한다.
- `fieldCards` 는 parse 가능한 JSON/list 이고, 최소 1개 이상이어야 한다.
- 최소 1개 card 는 `sourceRef` 와 짧은 `evidence` 를 가진다.
- `answerable=False` row 도 source/no-answer reason 을 숨기지 않는다.

실행:

```powershell
uv run python -X utf8 .github/scripts/search/evaluateSearchResultContract.py `
  --query "유상증자" `
  --query "공시 말고 뉴스로 환율 기사" `
  --query "HBM 투자 계획" `
  --out data/search/resultContractReport.json `
  --min-rows 3 `
  --fail-on-error
```

precomputed result 를 쓰는 경우:

```powershell
uv run python -X utf8 .github/scripts/search/evaluateSearchResultContract.py `
  --results-json data/search/searchResults.sample.json `
  --out data/search/resultContractReport.json `
  --min-rows 10 `
  --fail-on-error
```

이 gate 는 실제 full-source artifact 에 대해 실행해야 운영 증거가 된다. synthetic/precomputed fixture 통과는 회귀 테스트 증거일 뿐이다.

---

## 7. source/no-answer canary 기준

source canary 는 실제 artifact publish 와 local active swap 전에 빠르게 막는 운영 안전장치다.

기본 pack 은 artifact 에서 자동 생성한다. `artifactCanary.py` 는 `main_meta.parquet` 의 source별 대표 row 와 no-answer trap 을 `sourceCanaryPack` 으로 만들고, `writeIndexManifest()` 가 manifest 에 기록한다. 이 pack 은 publish preflight 와 local activation 에서 실제 BM25 artifact 를 상대로 평가된다.

필수 row:

- news-only query 가 filing/panel 로 fallback 하지 않는지.
- filing-only query 가 news 로 fallback 하지 않는지.
- filing/panel/EDGAR row 는 가능하면 `expectedSourceRef` 가 topK 안에 들어오는지.
- news 자동 canary 는 특정 최신 기사 sourceRef 가 아니라 `news` lane 이 살아 있고 filing/panel 로 fallback 하지 않는지를 본다.
- `expectedAnswerable=false` trap 에서 answerable result 를 내지 않는지.
- productization status 는 canary report 가 valid 여도 allFilings/panel/edgar-panel/news source coverage 가 모두 통과했는지 별도로 본다.

실행:

```powershell
uv run python -X utf8 .github/scripts/search/evaluateSearchCanary.py `
  --canary data/search/sourceCanaryPack.jsonl `
  --out data/search/canaryReport.json `
  --fail-on-error
```

canary pack 은 작고 빠르게 유지한다. 최신 사건 3~5개를 월간으로 갱신하되, query-log gold 를 대체하지 않는다.

특정 뉴스 기사, 특정 EDGAR accession, 특정 공시 sourceRef 의 의미 품질은 canary 하나로 졸업시키지 않는다. 반복 가능한 운영 품질은 real query-log gold 와 miss ledger 에서 판단한다.

---

## 8. 본진 회귀 테스트 승격

본진 이식 시 최소 테스트:

- source intent hard isolation.
- query-log gold real/proxy/review status 차단.
- miss ledger failureType/policyCandidate 생성.
- receipt number anchor.
- news title anchor.
- no-answer wrong company/date/event/unknown/suffix trap. 회사명이 query 본문에 들어간 경우에는 `ListingResolver` 기반 stockCode facet 이 적용되어야 하며, 계열사/유사명 false accept 는 release blocker 다.
- memory-card sourceRef top3.
- field evidence coverage.
- dataAsOf presence.
- result contract audit.
- source/no-answer canary pack.
- search scope `auto/title/content/news/both` contract.

전수 `pytest tests/ -v` 대신 변경 파일과 search gate 중심으로 돌리고, L0~L1.5 경계 변경이면 Guard Index strict 를 추가한다.
