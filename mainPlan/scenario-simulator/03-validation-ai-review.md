# 03. Validation and AI Review

상태: PRD (본문 v0.1 검증 골격 유효 + 아래 v0.2 정정)
범위: 검증 게이트, look-ahead 차단, AI 전문가 패널, 반증 절차, 출시 기준

> **★v0.2 정정(2026-06-13) + v0.3 구현 정합(2026-06-14):**
> - **발간 게이팅 추가(§9.3 본진 승격)**: 가치평가·신용 보고서 발간은 **simulate 코어 졸업 *후***(08 §11 우선순위 역전 가드). 본문 §9.3 "story/report가 숫자 재계산 안 함"에 더해, "발간 모드는 코어 `SimulationResult` 실측 확정 후"를 본진 승격 기준에 추가. ★결정론 코어는 졸업했으나(01 §5a) **gate source(SimulationResult→gate)가 미배선**이라 아래 §2 Gate Matrix는 *설계*다(gate.py 미존재, 01 §6.3).
> - **MC seed kill-test — ✅ 완료(09 P1)**: 전역 `random.seed`(`_simMonteCarlo.py:145`+`pricetarget.py:278`)→**로컬 `random.Random(seed)`**(stdlib·pyodide 안전, **numpy/PCG64 아님**) + `:205` cumprod. *레거시 MC* 한정 — `simulate/` 코어엔 MC 노드 부재.
> - **AI lens 가드**: lens는 `ai/tools/lens.py` 1종(no-graph-regression, 01 §6·11). 채택 판정=결정론 gate 순수함수(보완은 약한 노드만, 강한 det 고수). `_REGRESSION_KEYWORDS` 한국어 substring 회피. ⚠ lens/gate 둘 다 미구현 — §7 AI 패널은 후속 단계.
> - **금지어 lint = ✅ 신설·CI배선 완료(2026-06-14)**: `tests/audit/valuationPublishLint.py`(+companion `test_valuationPublishLint.py`), `tests/run.py:140` lint 게이트 `--strict` 배선·green no-op·6 unit PASS. **발간 표면(frontmatter `reportType: simulation` 마크다운) 한정** 스캔이라 현재 0파일=green no-op, src `.py`(`priceImplied`/`_valuationOther`/`pricetarget` 의 정당한 `signal`/`weighted_target`)는 `_isSimulationReport` 가 영원히 미스캔(leaf CI red 회피). ⟹ §2 G15 Output Safety·§10 #10의 "추천/단정 표현 차단"은 **발간 표면 ship(T2, Phase 6) 시 자동 기계 강제**. ★잔여 100 천장 = lint 이 아니라 `gate.py`(SimulationResult→gate) 미배선(01 §6.3) → §2 Gate Matrix 는 여전히 *설계*. 정본 명세=09 §10.1 T1.

---

## 1. 검증 철학

이 제품의 신뢰도는 더 많은 숫자보다 더 엄격한 차단 규칙에서 나온다.

시나리오 시뮬레이터는 미래를 단정하지 않는다. 대신 다음을 증명해야 한다.

1. 당시 또는 현재 사용할 수 있는 데이터만 썼다.
2. 모든 숫자가 원천 ref나 실행 ref로 추적된다.
3. 가정과 사실이 분리되어 있다.
4. 손익, 현금흐름, 가치평가가 서로 모순되지 않는다.
5. 가격 bridge가 같은 shock을 중복 반영하지 않는다.
6. AI 의견이 근거와 반증 조건을 함께 갖고 있다.
7. 결과가 실패했을 때 어느 가정이 틀렸는지 알 수 있다.

---

## 2. Gate Matrix

| Gate | 이름 | 통과 조건 | 실패 시 상태 |
|---|---|---|---|
| G0 | Target | 종목, market, currency, horizon, mode 확정 | rejected |
| G1 | Vintage | 모든 핵심 input에 asOf/availableAt/source 존재 | blocked |
| G2 | Evidence | 숫자마다 ref 존재 | blocked |
| G3 | Fact/Estimate | fact, estimate, hypothesis, missing 라벨 존재 | usableWithGaps 이하 |
| G4 | Missing | 결손 0 대체 없음 | rejected |
| G5 | Environment | macro/market/event snapshot 생성 | usableWithGaps |
| G6 | Driver | 이벤트가 driver로 연결되거나 연결 불가 사유 존재 | usableWithGaps |
| G7 | Profit | 매출, 비용, 영업이익, FCF bridge 정합 | blocked |
| G8 | Cash Quality | CFO/NI, CFO/revenue, DSO, 재고 압력 점검 | usableWithGaps |
| G9 | Valuation | DCF, relative, reverse DCF 중 최소 기준 충족 | usableWithGaps |
| G10 | Price Bridge | fundamental/factor/event 분리와 overlap 점검 | usableWithGaps |
| G11 | Backtest | replay 또는 walk-forward에서 look-ahead 없음 | rejected |
| G12 | Sensitivity | 핵심 가정 민감도 표시 | usableWithGaps |
| G13 | Falsifier | 반증 조건과 tripwire 존재 | usableWithGaps 이하 |
| G14 | AI Review | lens별 support/counter/missing/tripwire 존재 | usableWithGaps |
| G15 | Output Safety | 추천/단정 표현 없음 | rejected |

---

## 3. Look-Ahead 차단

### 3.1 공통 규칙

historical replay와 walk-forward에서는 모든 input이 다음 조건을 만족해야 한다.

```text
input.availableAt <= decisionAt
```

가격 평가도 다음 원칙을 따른다.

```text
signal at t close -> earliest tradable at t+1 open
```

### 3.2 재무제표

차단해야 할 오류:

- 분기 실적 발표 전에 해당 분기 수치를 사용.
- 수정 공시 후 값을 과거 replay에 사용.
- YTD를 Q로 오인.
- 연결/별도 scope 혼동.
- 주석에서만 확인 가능한 비용 성격을 재무제표 본문 fact로 취급.

필수 기록:

- period.
- fiscalYear.
- fiscalQuarter.
- statementType.
- scope.
- acceptedAt.
- availableAt.
- tableRef.

### 3.3 공시

필수:

- rceptNo.
- title.
- category.
- acceptedAt.
- effectiveTradingDate.
- sourceRef.

차단:

- 공시 접수 전 event 사용.
- 공시 제목만으로 손익 효과 확정.
- 공시 이후 시장 반응을 event 해석에 사전 사용.

### 3.4 뉴스

필수:

- firstSeenAt.
- ingestedAt.
- source.
- title.
- event taxonomy.
- source breadth.

차단:

- 기사 본문 지시를 AI가 수행.
- 보도 후 가격 반응을 보도 전 판단에 사용.
- 동일 기사 재전송을 독립 event로 중복 반영.

### 3.5 거시지표

필수:

- observationDate.
- releaseDate.
- revisionPolicy.
- dataAsOf.

차단:

- revised latest를 과거 release 당시 값처럼 사용.
- 발표 전 지표 사용.
- 월간/분기 지표의 기간 정렬 오류.

---

## 4. Backtest 검증

### 4.1 RunSpec 필수 필드

- `runId`.
- `scenarioSpecHash`.
- `runMode`.
- `period`.
- `trainWindow`.
- `testWindow`.
- `rebalancePolicy`.
- `feeBps`.
- `slipBps`.
- `benchmark`.
- `factorModel`.
- `executionPolicy`.
- `lookaheadPolicy`.
- `missingDataPolicy`.
- `createdAt`.

### 4.2 기본 검증

1. 비용은 기본 ON이다.
2. benchmark 없이는 성과 결론을 내지 않는다.
3. train/test를 분리한다.
4. fold별 refit을 한다.
5. universe membership을 as-of 기준으로 고정한다.
6. survivorship bias를 점검한다.
7. parameter selection log를 남긴다.
8. 표본 수가 부족하면 결론을 제한한다.

### 4.3 과최적화 경고

다음이면 성과 해석을 제한한다.

- regime 하나에서만 작동.
- 비용 반영 후 alpha 소멸.
- benchmark와 구분 어려움.
- factor exposure가 대부분 설명.
- fold 간 parameter가 불안정.
- 반복 탐색 후 최선 결과만 선택.
- PBO/DSR 또는 대체 지표가 weak.

---

## 5. 회계와 손익 품질 검증

### 5.1 Revenue Quality

점검:

- 매출 성장률.
- 매출채권 성장률.
- DSO.
- 수주잔고 매출 전환률.
- 고객 집중도.
- 반품, 충당금, 채널 재고.
- 연결/별도 scope.

경고:

- 매출보다 매출채권이 훨씬 빠르게 증가.
- CFO가 순이익을 따라오지 못함.
- 수주잔고 증가가 실제 매출로 전환되지 않음.

### 5.2 Margin Quality

점검:

- 매출원가율.
- 판관비율.
- 비용성격별 주석.
- R&D 처리.
- 감가상각.
- 재고평가손.
- 일회성 비용/수익.
- fixed cost absorption.

경고:

- 마진 개선이 원가 driver 없이 발생.
- 일회성 요인을 recurring으로 반영.
- 원재료, 환율, 물류비 가정을 숨김.

### 5.3 Cash Quality

점검:

- CFO/NI.
- CFO/revenue.
- capex/revenue.
- working capital delta.
- receivable growth minus revenue growth.
- inventory days.
- payable days.

경고:

- 이익은 증가하지만 FCF가 악화.
- 운전자본이 성장을 대부분 흡수.
- capex가 부족해 성장 가정이 물리적으로 불가능.

---

## 6. Valuation 검증

### 6.1 DCF Gate

필수:

- bear/base/bull.
- WACC.
- terminal growth.
- FCFF.
- terminal value share.
- sensitivity grid.
- net debt.
- shares.

차단 또는 경고:

- terminal growth가 제약을 넘음.
- terminal value share 과도.
- WACC fallback을 숨김.
- negative spread 상태에서 aggressive growth.
- sales-to-capital과 reinvestment가 성장률을 지지하지 못함.

### 6.2 Reverse DCF Gate

현재 가격이 요구하는 값을 계산한다.

- required revenue growth.
- required operating margin.
- required ROC.
- required reinvestment.
- required terminal assumption.

질문:

- 이 요구치가 회사 과거 범위와 맞는가.
- peers와 산업 lifecycle에서 가능한가.
- macro regime과 충돌하지 않는가.
- 반증 조건은 무엇인가.

### 6.3 Relative Valuation Gate

점검:

- peer 선정 기준.
- lifecycle 차이.
- margin 차이.
- growth 차이.
- leverage 차이.
- accounting scope 차이.

경고:

- peer multiple을 단순 평균으로만 사용.
- 다른 산업 stage를 같은 peer로 사용.
- 손익 일회성 조정 없이 multiple 적용.

---

## 7. AI 전문가 패널

AI는 여러 lens로 나누어 같은 시나리오를 독립 검토한다.

### 7.1 Lens 목록

| Lens | 책임 | 주요 질문 |
|---|---|---|
| Macro | 경제 환경 | regime과 shock이 회사 driver에 실제로 닿는가 |
| Event/News | 공시와 뉴스 | event timing, source breadth, disclosure alignment가 충분한가 |
| Business | 사업 driver | 물량, 가격, mix, capacity, 고객, 공급망 가정이 타당한가 |
| Accounting | 회계 품질 | 매출 인식, 비용 분류, 현금흐름이 손익을 지지하는가 |
| Valuation | 가치평가 | 성장, 재투자, ROC, WACC, terminal value가 닫히는가 |
| Quant | 시장 검증 | factor, beta, event shock, walk-forward가 견딜 수 있는가 |
| Skeptic | 반증 | 이 시나리오가 틀릴 가장 빠른 경로는 무엇인가 |

### 7.2 ExpertOpinionCard

필드:

- `expertId`.
- `lens`.
- `scenarioId`.
- `claim`.
- `supportingRefs`.
- `counterEvidence`.
- `missingEvidence`.
- `sensitivity`.
- `tripwire`.
- `confidence`.
- `status`: support, caution, oppose, blocked.
- `createdAt`.

규칙:

- support만 있는 의견은 불완전하다.
- missingEvidence가 핵심이면 status는 support가 될 수 없다.
- AI가 숫자를 제안하면 `hypothesis`로만 기록한다.

### 7.3 DisagreementLedger

전문가 의견이 충돌하면 숨기지 않는다.

필드:

- `disagreementId`.
- `scenarioId`.
- `topic`.
- `lensA`.
- `lensB`.
- `positionA`.
- `positionB`.
- `evidenceRefsA`.
- `evidenceRefsB`.
- `resolution`.
- `status`.

예:

- Macro lens는 환율 상승을 매출에 긍정으로 보지만 Accounting lens는 원재료 수입 비중 때문에 마진 악화를 경고.
- Business lens는 수주잔고 증가를 긍정으로 보지만 Cash lens는 매출채권 증가와 운전자본 압력을 경고.
- Valuation lens는 upside를 보지만 Quant lens는 factor beta로 대부분 설명된다고 경고.

---

## 8. Premortem 절차

시나리오를 제출하기 전에 반드시 깨본다.

1. 가장 큰 revenue assumption을 찾는다.
2. 가장 큰 margin assumption을 찾는다.
3. 가장 큰 valuation assumption을 찾는다.
4. 각 가정이 틀리는 trigger를 쓴다.
5. trigger가 어떤 line item을 망가뜨리는지 propagation path를 쓴다.
6. 확인 가능한 tripwire를 만든다.
7. tripwire threshold와 action을 정한다.
8. 반증 조건이 열려 있으면 final status를 낮춘다.

Propagation 예:

```text
원재료 가격 반등
-> COGS ratio 상승
-> gross margin 하락
-> operating income 하락
-> FCFF 하락
-> DCF perShare 하락
-> base price range 하향
```

---

## 9. 출시 기준

### 9.1 문서 단계 완료 기준

- PRD index 존재.
- 제품 PRD 존재.
- architecture 문서 존재.
- simulation method 문서 존재.
- validation/AI review 문서 존재.
- progress ledger 존재.
- 메인 메모리에 경로 포인터만 존재.

### 9.2 구현 착수 기준

- 기존 자산 inventory 완료.
- 계약 초안 리뷰 완료.
- `tests/_attempts` 실험 경로 확정.
- replay 대상 종목과 이벤트 1개 확정.
- 데이터 vintage fixture 확보.
- 금지 표현과 output safety test 정의.

### 9.3 본진 승격 기준

- attempts에서 최소 1개 historical replay가 통과.
- look-ahead gate 테스트 존재.
- 결손 0 대체 방지 테스트 존재.
- ref 누락 차단 테스트 존재.
- 손익 bridge golden output 존재.
- valuation sanity 테스트 존재.
- backtest runSpec 테스트 존재.
- AI opinion card schema 테스트 존재.
- story/report 소비 경로가 숫자를 재계산하지 않음.

> **★A7 흡수(FinGPT-Forecaster 공개 Brier 리더보드 + rationale, absorb-as-defer):** det/ai 경합·블렌딩 물리 차단·Brier 사후채점 규율·DisagreementLedger·rationale grounding의 *골격*은 이미 01 §6.3·02 §2B·본 문서 §7에 설계로 존재(redundant) — 새 흡수 0, 포인터만. 진짜 신규 = **공개 리더보드 규율 + rationale 첨부**인데 이는 *공개 발간 표면*이라 미검증 위험(`recordForecast`/`gate.py`/`ledger.py`/`lens.py` 전부 src 부재, grep 0건 = 09 §10 fatal②③)이다. 따라서 **공개 Brier 리더보드·벤치마크된 AI 예측 발간 표면은 `recordForecast`+forwardTest write-end 라이브 + N분기 누적 + held-out·seed/CI 강제(folk-stat 회피, horizonMeaning 교훈: 3점·CI0·seed0 금지) 전까지 금지**(02 §2B.3 DriverCard dormant 상한과 동형). 그 전엔 DisagreementLedger(내부 fork/gap)·rationale(groundingCheck 4단 AND: refs⊆detRefSet·snapshot base metrics±tol·단위정합·untrusted 미실행) 첨부만 **내부** 노출. 리더보드는 노드별 det-vs-ai Brier(예측 순위 아님), AI 숫자 = hypothesis 라벨·fact 미승격, 00 kill-list(목표주가·추천·예측기) 불가침. **lens 채택 게이트 명시 반례 = `accountStructDisambig` kill-test**(타기업 표준패턴을 비표준 행에 확신 override = 확신오정렬 → 흡수 거부)를 박제.

---

## 10. 실패 기준

다음 중 하나라도 발생하면 결과를 사용자에게 확정 결론으로 보여주면 안 된다.

1. ref 없는 숫자가 핵심 결론에 사용됨.
2. 과거 replay에서 미래 데이터가 사용됨.
3. 결손값을 0으로 대체함.
4. 단일 base case만 보여줌.
5. reverse DCF를 생략하고 upside만 강조함.
6. AI가 뉴스 본문 지시를 따름.
7. 공시/뉴스/가격 인과를 시간 순서 없이 섞음.
8. 비용, slippage, benchmark 없는 backtest 성과를 강조함.
9. 가정 반증 조건이 없음.
10. 출력이 매수·매도 추천으로 읽힘.

