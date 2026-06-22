# 08. Valuation Report — 시뮬레이터 = 가치평가 엔진, 프로급 보고서 발간 계약

상태: PRD v0.4 (2026-06-13 다모다란 융합 + 자산 감사 + 적대 검증 / 2026-06-14 구현 정합: dcf 노드=proforma-FCFF[§1 ⑤·§2.3]·RNG=random.Random[§8]·금지어 lint 신설·CI배선 완료[§2.2·09 §10.1] / 2026-06-20 9인 패널 보강: Bridge Waterfall 시각 문법 SSOT[§3.4]·CRP+ERP_KR provenance[§2.3]·닻 2.5차원+세그먼트 닻 defer[§2.1] / 2026-06-20 16인 교차분야 천장 보강: 닻 시간축 expectations-revision[§2.1, vintage 반복평가]·닻 implied CAP↔01 §6.3(d) 봉합[§2.1]·기준선 앵커링 대칭 가드[§2.1, 03 §6.3(c) 재사용]·signal 라벨 2층화[§2.2]·규제 관할 표 KR primary→US secondary[§7]·필수고지 키 4종 존재 어서션[§7 ③]·ReportDock 거처 포인터[§5])
**지위: 발간 *계약* 문서 — 발간 모드는 `simulate/` 코어 졸업 *후*에 착수(§11 게이팅).** ★결정론 코어는 이미 졸업(4노드 DAG·공개 verb, 01 §5a) — 그러나 발간이 의존하는 **gate.py·reportDock·14키 ref 치환·렌더러 2개는 미구현**(금지어 lint 은 신설·CI배선 완료, 09 §10.1; 아래 ⚠ 표기). 코어 졸업 ≠ 발간 가동.

---

## 0. 결론

**시뮬레이터는 이미 가치평가 엔진이다.** 다모다란 "Narrative and Numbers"(story→drivers→numbers→value→story break)가 확정된 `simulate/`(L2.5) 아키텍처와 노드 대 노드 동형이고, 대응 leaf가 *전부 본진에 실재*한다(DCF 5변종·역DCF·RIM·실물옵션·SOTP·5시나리오 MC·thesisKillChain·publisher→blog). 따라서 "가치평가 보고서 발간"은 **새 엔진이 아니라 `SimulationResult`를 시간(Play)이 아닌 *논증 순서*(narrative→drivers→numbers→value→falsifier)로 펼친 정적 단면**이다. 새 계산 0, 새 verb 0 — `dartlab.simulate(mode="whatif")` → story가 `type="simulation"`으로 렌더.

"프로급"은 **품질 바**이지 유료 제품이 아니다(운영자 명시: "아직 pro 안 만든다, 그냥 프로급"). monetization·티어 분할 설계 없음.

---

## 1. 동형 확정 (덧붙임 아닌 같은 엔진 다른 각도)

| 다모다란 5단계 | `simulate/` 자료구조 (01) | 호출 leaf (2층 — §3.1) |
|---|---|---|
| ① Narrative (story) | `ScenarioSpec`/`ScenarioBranch` (02 §2.3-4) | — (가정 입력) |
| ② Story → drivers | `DriverNode`/`DriverSheet` (01 §5) | `transfer.transferMacroToFundamentals` |
| ③ 3P test (possible/plausible/probable) | DriverRegistry 6게이트 (02 §2B) | `calcMacroRegression`(pooled-panel OOS) |
| ④ Drivers → numbers | `DriverSheet` leaf 노드 | `buildProforma` (불가침) |
| ⑤ Numbers → value | ValuationBridge (02 §2.8) | **정적 가치평가** = `calcDFV`/`dFV`(quality-WACC 삼각검증). **시나리오 발간** = simulate `dcf` 노드(`registry._fnDcf` = proforma-FCFF, calcDFV 회피=scenario-coherence, §2.3) — 둘은 *2 정당 경로*, 발간은 후자 ref |
| ⑥ **현재가가 요구하는 믿음** | reverseDCF 닻 (§2) | **`reverseImpliedGrowth`+`computeGap`** |
| ⑦ Story break | `HypothesisNode`·`tripwireMonitor`·`DisagreementLedger` | `synth/thesisKillChain.py` |
| ⑧ Feedback loop open | AI `.ai` 평행 슬롯 + Brier | `ai/tools/lens.py`(신설)·`OutcomeLog`(MCP) |

다모다란 6단계 라이프사이클(startup→young→growth→mature growth→mature stable→decline)마다 story/number 균형·driver·multiple이 다르다 → DriverRegistry가 라이프사이클별 토글 카드 집합을 결정(young=TAM/share/survival, mature=FCF/multiple, **금융사=residualIncome/bankDFV leaf 스위치**(FCFF 부적합), cyclical=정규화 마진). AI lens가 단계 분류.

---

## 2. 적정주가(fair value) — 단일 목표가·rating 금지, reverseDCF 닻 + 조건부 범위

### 2.1 정의

> 적정주가 = 단일 점이 아니라 두 좌표의 **조건부 진술**:
> (A) **조건부 가치 범위** — bear/base/bull × P10/P50/P90 (시나리오 토글 파생)
> (B) **reverseDCF 닻** — 현재가가 *요구하는* 매출성장 g/영업마진 m/ROIC r. *예측이 아니라 시장이 priced-in 한 믿음의 해부*(Mauboussin Expectations Investing).

질문 전환: "미래 성장률이 얼마?"(추측·환각)→"시장이 박은 성장률이 plausible?"(판정·검증). **컨센서스 부재를 강점으로 뒤집는** 메커니즘. dartlab `reverseImpliedGrowth`(`priceImplied.py:27`)+`computeGap`(`:167`) 이미 실재, story `reverseImplied` 블록 이미 배선(`registry.py:854,890,914`) — 갭은 "보고서 *전면*으로 승격"이지 배선 아님.

> **★닻을 2.5차원으로(1차원 g 닻 확장):** 현 `reverseImpliedGrowth` 발간은 *implied 매출성장 g* 단일 좌표(1차원)다 — "시장이 박은 g 가 plausible?"는 강하나, 같은 가격이 *어떤 마진·자본효율 조합*을 요구하는지는 닫혀 있다. 2.5차원 = g 닻 위에 **required-operating-margin·required-ROIC 를 *최소 고정-입력* 형태로 동반 표시**한다(완전한 2D iso-value surface 아님 — '0.5차원'). 표기 = "현재가는 (g=X% 고정 시) 영업마진 m≥Y% *또는* ROIC r≥Z% 를 요구"처럼 한 변수 고정·나머지 1변수 함의를 짝으로 노출(`computeGap` 의 required-* 출력은 03 §6.2 Reverse DCF Gate 가 이미 required revenue growth/operating margin/ROC/reinvestment 를 명세 — 그 값을 발간 *전면*으로 끌어올림, 새 계산 0). **iso-value frontier**(g·m·r 자유조합이 같은 현재가를 만드는 *연속 곡면*, "여러 점이 같은 값" 시각화)는 후속 단계로 **defer 명시** — 곡면 샘플링·등가선 렌더는 닻 전면 승격(현 단계) 이후의 별도 작업(잠정 우선순위, 졸업 후 재검). 2.5차원은 required-* 짝-표기까지가 현 범위, frontier 곡면은 design.

> **★닻 시간축 — expectations revision 좌표(C, 새 계산 0 — vintage 반복평가):** 현 닻은 *한 asOf 시점* 의 정태 단면(현재가가 *지금* 요구하는 g/m/r)이다. 시뮬레이터는 이미 **vintage/asOf 스냅샷 기계**를 보유하므로(05 vintage 3축·`SimulationResult` asOf), `reverseImpliedGrowth`+`computeGap` 를 *마지막 N개 asOf 스냅샷*에 반복평가하면 새 계산 없이 **implied g·m·r 의 수정 궤적**(시장이 박은 기대가 분기마다 어떻게 옮겨갔는가)을 얻는다 — 닻에 **시간축(C 좌표)** 1행 추가. 라벨은 **2층화**한다:
> - **정태 라벨**(§2.2 리네임 후): `consistent / optimistic / pessimistic`(현재가 함의 vs 회사 과거범위 정합성).
> - **동태 라벨**(궤적 방향만, *중립*): `expectation-rising / falling / stable` — implied-g(또는 m/r) 가 N스냅샷에 걸쳐 오르는/내리는/평탄한 **방향 정보만**. over/under-reaction(과잉·과소반응)은 *인과 단정*이라 **금지** — "시장이 과잉반응했다"는 행동재무 판정을 발간하지 않는다. 대신 **정합성 갭**으로만 노출: "닻 implied-g 수정폭이 동기간 *펀더멘털 수정폭*(실현 매출·마진 revision)을 초과/미달" 이라는 *두 수정폭의 비교*(scenario≠forecast — 어느 쪽이 옳은지 단정 0, 갭을 DisagreementLedger 행으로). ⚠ **N-스냅샷 닻은 vintage fixture 가 닿는 종목부터** 실재 — vintage 스냅샷 미닿는 종목은 **정태 닻 단일**(궤적 행 부재)로 **defer 명시**(미구현을 구현으로 위장 금지, 02 세그먼트 census defer 와 동형). 잠정 — N(스냅샷 수)·수정폭 tol 은 졸업 데모서 재보정.

> **★닻 implied CAP 좌표(새 계산 0 — `computeGap` implied ROIC 의 fade 역산):** required-margin·required-ROIC 짝(2.5차원) 옆에 **implied CAP**(competitive advantage period — 현재가가 요구하는 *초과수익 지속연수*) 1좌표를 추가한다. 현재가가 함의하는 TV 에서 `ROIC → WACC` 로 fade 시킬 때 *얼마나 오래* 초과수익(`ROIC > WACC`)이 지속되어야 현재가가 정당화되는지를 역산해 **"현재가는 약 N년의 moat 지속을 가정"** 으로 노출(새 leaf 0 — `computeGap` 의 implied ROIC + terminal fade 산수). 이 implied-N 을 **01 §6.3(d) `checkValuationCoherence`(영구 초과수익 moat 라벨 강제)의 명시 moat/fade 가정과 cross-check** 한다 — 닻 implied-CAP(시장이 박은 지속연수) ≫ 명시 moat 가정(분석가가 박은 fade)이면 `SimulationResult.warnings 'market_implies_longer_moat_than_assumed'`(시장이 우리 가정보다 *더 긴* 해자를 priced-in). plausibility 는 **라벨만**(N 을 예측이 아니라 "*시장이 박은 가정의 해부*"로 — Mauboussin Expectations Investing 와 동축). ⟹ 닻(§2.1)과 01 §6.3(d) 를 **하나의 ROIC-spread 서사**로 봉합: (d)는 *우리* proforma 의 영구 초과수익 모순을 잡고, 본 implied-CAP 는 *시장가* 가 요구하는 초과수익 지속을 해부 — 같은 `ROIC−WACC spread` 의 공급·수요 양면. 잠정 — fade 곡선형·spread_tol 은 (d)와 공유, 졸업서 재보정. (⚠ 코드 정정: 01 §6.3(d)는 literal `capYears` 필드가 아니라 terminal `ROIC−WACC > spread_tol` + fade/convergence·명시 moat 라벨 기계강제 — implied-CAP 는 그 명시 가정을 *시장 함의 N년* 과 대조하는 것이지 별도 `capYears` 입력이 아님.)

> **★기준선 앵커링 대칭 가드(행동재무 — 닻을 재는 *자(尺)* 자체의 편향, 새 leaf 0):** §2.1 닻 plausibility 판정의 *기준선*(=회사 historical range·peer 범위)은 닻을 재는 자(尺)인데, **이 자 자체가 분석가 측 앵커링/recency 편향**을 품을 수 있다 — trailing-realized historical range 는 *과거가 미래의 닻* 이라는 가정이라, **구조 변곡**(신사업·세그먼트 진입·사이클 전환·peer lifecycle 사분위 전환)이 일어난 회사에서는 historical range 가 미래를 못 담아 시장 함의를 **"비현실적" 으로 오판**(market_implies_longer_moat 의 역방향 — 시장이 옳고 *우리 기준선*이 stale). 대칭 가드 = **닻이 historical 을 벗어남 = ① 비현실(시장 과열) *또는* ② 구조 변곡(기준선 stale), 둘을 단정 않고 *DisagreementLedger 행*으로** 남긴다(어느 쪽인지 발간이 정하지 않음, scenario≠forecast). 트리거 = peer lifecycle 사분위 전환·신세그먼트 존재 시 historical 비교를 **낮은신뢰 강등**(03 §6.2 Reverse DCF Gate 질문목록에 "기준선(historical range) 자체가 구조변곡 못담는 trailing anchor 인가" 1행 추가 — 03 소유, 본 절은 그 추가의 소비자). lifecycle 사분위 전환 판정은 **03 §6.3(c) lifecycle 불일치 게이트(`stage-mismatch`)** 의 사분위 비교 기계를 재사용(새 분기 0 — peer/target revenue CAGR·ROIC 사분위 동일 자료). (⚠ 코드 정정: 직전 라운드 백로그가 가리킨 "00 §6.4 R23 lifecycle dispatch" 는 실제로 00 §6.4 의 *ScreenerModal→PriceChart soft-swap 드릴다운*(R23)이고 lifecycle dispatch 가 아니다 — 진짜 lifecycle 사분위 dispatch 의 정본은 **03 §6.3(c) stage-mismatch** 다. 본 가드는 그 정본을 참조.)

> **★닻 분해 한계(시그니처 정밀화 — 전사 닻 실재, 세그먼트 닻 design):** 현 reverseDCF 닻은 **전사(consolidated) 단일 닻**이다 — "전사 현재가가 요구하는 g/m/r 가 회사 전체 historical range·peer 범위에서 plausible?"까지가 *실재*하고, 이 plausibility 판정은 지금 강제 가능하다. 그러나 다사업부 기업의 *진짜* 질문 — "*어느 세그먼트*의 implied 기대가 비현실적인가"(예: 전사 닻은 plausible 해 보여도 한 세그먼트에 비현실적 성장이 priced-in) — 은 **세그먼트 SOTP 닻**(부문별 sum-of-the-parts 역DCF)을 요구하며, 이는 세그먼트 분해 데이터(02 세그먼트 census 절이 census 하는 `NT_D871100` 세그먼트 셀, 메모리 segmentRnd coverage 2/10 = 데이터-부재 천장)가 **라이브된 *후*의 후속 단계로 defer**한다. ⟹ 시그니처 주장 정밀화 = **'전사 닻 실재(plausibility 강제 가능), 세그먼트 닻 design(세그먼트 census 라이브 후)'** — 둘을 하나로 뭉뚱그려 "닻이 세그먼트별 비현실성을 짚는다"고 쓰면 미구현을 구현으로 위장(확신오정렬, horizonMeaning 교훈). 세그먼트 닻은 잠정 후속, 졸업 AC 아님.

### 2.2 단일점·rating 차단 (적대검증 B-1·B-2 — 규제선 실제 구멍)

- **`signal` 필드 차단/리네임(B-1):** `reverseImpliedGrowth`의 `PriceImpliedRevenue.signal`이 `underpriced|overpriced|fair`(`priceImplied.py:23,222`)를 반환 — 이건 사실상 매수/매도 rating이다("underpriced"=한국어 "사라"로 직역). **발간 표면에서 `signal` 노출 금지**, "현재가 함의 vs 회사 과거범위 정합성(consistent/optimistic/pessimistic)"으로 리네임. 단 lint 은 *발간 표면 마크다운*만 스캔 — `priceImplied.py` 의 `signal` enum(leaf 정의)은 정당 사용이라 미스캔(§2.3·아래 §2.2 박스). **★라벨 2층화(정태+동태, §2.1 시간축 박스 동행):** 위 리네임은 **정태 라벨**(`consistent/optimistic/pessimistic` — 한 asOf 의 닻 vs 과거범위)이고, N-스냅샷 vintage 닻이 닿는 종목에는 **동태 라벨**(`expectation-rising/falling/stable` — 방향만, 중립)을 *짝으로* 노출한다(SSOT = §2.1 "★닻 시간축" 박스). 동태도 over/under-reaction 인과 단정 금지 — *정합성 갭*(닻 수정폭 vs 펀더멘털 수정폭)으로만. vintage 미닿는 종목은 정태 단일(동태 행 defer).
- **★`computePriceTarget` rating·단일목표가 차단(B-1', 평가 P0):** `pricetarget.py`의 `weighted_target`(단일 목표가)+`signal: strong_buy/buy/hold/sell/strong_sell`(`_classifySignal:644`)도 동일 금지 출력 — **§2.3 어댑터가 두 필드를 drop**하고 P10~P90 분포+reverseDCF 닻만 발간. 금지어 lint = **발간 표면(frontmatter `reportType: simulation` 마크다운) 한정** — leaf src 3파일(`priceImplied`/`_valuationOther`/`pricetarget`)은 `_isSimulationReport()` 가 `.py` 를 영원히 False 로 막아 미스캔(=leaf 의 정당한 `signal`/`weighted_target` 안 잡음, CI red 0). 그 3파일 값의 발간 누출은 §2.3 어댑터(weighted_target/signal drop)가, 마크다운에 쓴 매수/목표가 어휘는 lint 가 차단 — 책임 다른 두 메커니즘. 09 P12.
  > **★구현 정합(2026-06-14):** 발간 표면 한정 금지어 lint = `tests/audit/valuationPublishLint.py`(+companion `test_valuationPublishLint.py`) **신설·CI배선 완료**(`tests/run.py:140` fast 게이트 `--strict`, green no-op·6 unit PASS 실측). 스캔 대상이 발간 표면(frontmatter `reportType: simulation` 마크다운)뿐이라 leaf src `.py` 는 영원히 미스캔(=leaf 의 정당한 `signal`/`weighted_target` 사용 안 잡음, CI red 0). 발간 표면 0파일이라 현재 green no-op — 표면 ship 시 자동 발화. 정본 명세=09 §10.1 T1. **잔여=T2 발간 표면 신설(Phase 6).**
- **priceP50 단독 금지(B-2):** `PriceSimulationResult.priceP50`/`perShare`(02 §2.8-9) 단독 표시는 목표가로 읽힌다. **발간 게이트 기계 규칙: perShare/P50 단독 출력 시 build fail — 항상 P10·P90 + reverseDCF 닻 동반.** 무료 공개 발간이 더 위험(불특정 다수).
- `verdict`(저평가/적정/고평가) = 조건부 *분류*이지 Buy/Sell *rating* 아님 — 단 §7 가드로 강제.

### 2.3 leaf (전부 실재 — 단 ★computePriceTarget rating 정면충돌, 어댑터 필수)

범위(A): `calcDFV`(`dFV.py:56`, 4엔진 통합 quality-WACC)·`computePriceTarget`(`pricetarget.py:460`, 5시나리오×proforma×DCF + `_monteCarloPriceDistribution` P10~P90). 닻(B): `reverseImpliedGrowth`+`computeGap`. WACC: `computeCompanyWacc`(`_proformaCore.py:145`)+`calcQualityWACC`. **한국기업 CRP 토글**을 DriverCard로(지정학 악화→CRP +1.5pp).

> **★평가 정정 — `+1.5pp` CRP 매직상수 provenance 라벨(자기-적발 비대칭 해소):** §2B 가 `SECTOR_ELASTICITY`(35키 inline·seed/CI 0)·`WACC×0.5`(`transfer.py:111-127`)를 `elasticity_prior_unvalidated`·`default:no-wacc` 접두로 라벨 적발하면서, 같은 종류의 무출처 손튜닝 상수인 `+1.5pp CRP`는 본 절이 라벨 없이 통과시키는 비대칭이 있었다. 정정 — **CRP DriverCard 도 `elasticity_prior_unvalidated`(또는 `crp_prior_unvalidated`) provenance + `SimulationResult.warnings`에 `country risk premium defaulted — geopolitical stress assumption(honest-gap)`** 강제(§2B.3 A2 흡수 ⓐⓑ 접두 규율과 동형). `+1.5pp`는 검증된 추정이 아니라 **'지정학 stress 시나리오 가정'으로만** 라벨(scenario≠forecast). 잠정값(졸업 데모서 재보정) — held-out 검증 0이라 proven 아님.
>
> **★ERP_KR 합성식 명세(매직상수→해체 가능 구조):** 단일 `+1.5pp` 손튜닝 대신 ERP 를 분해 가능 형태로 박는다(Damodaran country-risk 방법): `ERP_KR = ERP_mature + CRP_KR`, 여기서 `CRP_KR = sovereignDefaultSpread_KR × (σ_equity / σ_bond)`(default-spread × 상대 주식 변동성, Damodaran 합성). `ERP_mature`(US 성숙시장 기준 base ERP)·`sovereignDefaultSpread_KR`(KR 국가 신용 default spread)·`σ_equity/σ_bond`(KR 주식/국채 상대 변동성)는 각각 ref 동반 입력 — 셋 다 무출처면 카드 `warnings=["erp_components_unsourced"]`. **`+1.5pp` 는 이 합성식의 *지정학 stress 가산항*(stress 시 CRP_KR 위에 얹는 시나리오 토글)으로만 잔존**하고, base ERP_KR 자체는 합성식이 산출(매직상수 1개 → 출처-추적 3입력). 합성식 *형* 은 지금 박고, 컴포넌트 값/캘리브레이션은 졸업 데모서 ref 확정(잠정 — 현재 ERP_mature·spread·σ 비율 모두 placeholder).

> **★평가 P0 정정 — computePriceTarget는 "거의 선구현"이 아니라 금지 출력 반환체다:** `computePriceTarget`은 P10~P90 분포 외에 **`weighted_target: float`(단일 목표가) + `signal: strong_buy/buy/hold/sell/strong_sell`(`_classifySignal:644` = 매수/매도 rating)**을 함께 반환한다 — 00·§2가 가장 강하게 금지한 바로 그것. §2.2 금지어 lint 은 *어느 `.py` 도 안 잡는다*(발간 표면 마크다운 한정) — `weighted_target`/`signal` 의 발간 누출 차단은 lint 이 아니라 발간 어댑터의 *필드 drop* 책임이다. ⟹ 발간에 그대로 쓰면 안 되고, **발간 어댑터(P10/P50/P90 분포 + reverseDCF 닻만 추출, `weighted_target`·`signal` 필드 drop)**를 거친다. 졸업 AC = "calc 직접호출 0"과 **동급으로 "rating/단일목표가 필드 누출 0"** 명문화. (~80% 재사용 자평은 실재하나 *그대로는 못 씀* — 어댑터가 추가 작업.)
> **★구현 정합(2026-06-14):** deterministic core의 dcf 노드(`registry._fnDcf`)는 **proforma-FCFF**를 쓰고 `calcDFV`를 의도적으로 회피(외부 proforma 무시→scenario-coherence 깨짐, 09 P3). 발간 ⑤ Numbers→value도 *시나리오 일관성*을 위해 simulate dcf 노드(proforma-FCFF) 결과를 ref로 받아야지 calcDFV/computePriceTarget을 재호출하면 SSOT 분열(§1 ⑤ 표는 정적 가치평가용 calcDFV — scenario 발간과 구분).

---

## 3. 프로급 보고서 구성 — 12블록, 2층 leaf, story 렌더

### 3.1 2층 leaf SSOT (적대검증 A-1·A-3 — 핵심 정정)

가치평가 호출은 **2층**이다: `analysis/valuation/`(순수 수학 leaf) ← `analysis/financial/valuation.py`+`_valuation*.py`(`calc*` 회사-바인딩 래퍼: series/shares/price fetch) ← story. **simulate는 `analysis/financial/`의 `calc*` 래퍼를 호출**(순수 leaf 직접 아님) — 그래야 company 바인딩(`_getSeriesAndShares`·`_fetchPriceContext`)을 재구현하지 않는다(0줄 보장). 중앙 적정주가 leaf = `calcDFV`(삼각검증), **`fullValuation`은 deprecated(docstring "calcDFV 우선")라 fallback으로 강등**.

### 3.2 12블록 (괄호=기존 story 블록/leaf, 대부분 재사용)

1. Thesis/Narrative (ScenarioSpec+assumptionLedger) 2. Environment Snapshot (02 §5.1) 3. **DriverGraph→Profit Bridge waterfall (★신규 렌더러 2개)** 4. Proforma IS/BS/CF (`buildProforma`) 5. DCF range (`dFV`/`priceTarget` 블록) 6. Relative (`valuationSynthesis` 블록) 7. **Reverse 닻 (`reverseImplied` 블록 — 상단 승격)** 8. Sensitivity (`sensitivityGrid`) 9. Robustness (walk-forward, replay 모드) 10. Falsifier (`thesisKillChain`) 11. Assumptions ledger (각 행 status+falsifier+ref) 12. Provenance (셀 ref+sourceRef+latestAsOf, 결손 0대체 금지).

신규 렌더러 단 2개: `businessDriverBridgeBlock`(02 §5.3)·`profitBridgeBlock`(02 §5.4) — builders.py 확장(새 모듈 0). story type 11→12(`type="simulation"`). **이 두 렌더러의 bridge waterfall 시각 문법(시작/부유/착지 바·점선 근사·빗금 missing·4단 캐스케이드·부호색 중립)은 §3.4 가 SSOT.**

### 3.3 역할분리 + 14키 ref 치환 매트릭스 (적대검증 D-3 = 졸업 AC)

story는 렌더만(헌법 "자체 계산 0"). 현 registry가 `calcDcf(company,...)`를 *직접 호출*(`:897`)하는데, 융합 후 **valuation 14키(`_CORE_KEYS`, registry `:848-863`) 전수를 `SimulationResult` ref 읽기로 치환**(키→필드 매트릭스 명시). 일부만 치환하면 story가 계산 트리거를 유지 → 헌법 회색지대. **졸업 AC = "simulation type 보고서에 calc 직접호출 잔존 0".**

### 3.4 Bridge Waterfall 시각 문법 (블록3 = `businessDriverBridgeBlock`·`profitBridgeBlock` 렌더러 명세)

블록3(§3.2 #3)의 두 신규 렌더러가 출력하는 **bridge waterfall** 의 시각 문법을 박는다(개념=다모다란 story→drivers→numbers, propagation 을 *눈에 보이는 폭포*로). 새 차트 라이브러리 0 — `builders.py` 확장이 SVG/CSS 도형(AuditStrip RUN_COLORS·HonestyFooter 기존 컴포넌트 *확장*, 재발명 금지)으로 그린다. **이 절이 시각 문법 SSOT, 00 §6.3(Bridge Waterfall 화면 구성)은 본 명세를 포인터 참조.**

**(1) 폭포 골격 — 시작 바 → 부유 driver 바 → 착지 바.** 한 bridge(예: 매출→영업이익)는 좌→우로:
- **시작 바**(전기 매출, 바닥 anchor): x축 baseline 에서 올라온 *전체 높이* 회색 기준 바(`--dl-line-strong #2a3142` fill, muted). "어디서 출발했는가"의 고정 닻.
- **부유(floating) driver 바**: 각 driver 효과를 *떠 있는* 바로 — 직전 누적 top 에서 시작해 +상승(위로)·−하강(아래로). 바닥에 붙지 않음(앞 바의 끝이 다음 바의 시작 = waterfall 불변).
- **착지 바**(당기 영업이익): 마지막 driver 누적 후 다시 baseline 까지 내린 *전체 높이* 회색 결과 바. 시작 바와 같은 muted 톤(둘 다 *수준값*, 가운데는 *변화값*).

**(2) 각 부유 바 = driver 라벨 + delta 숫자 + ref 점 + ledger 클릭.** 바 위/아래에 `{driver명}` + `{+/−delta}`(단위·기간 동반, 02 §2.5 단위강제), 바 모서리에 **ref 점**(작은 채워진 원 = valueRef/tableRef 존재 표식, 결손이면 점 없음). **클릭 → AssumptionLedger 해당 행 하이라이트**(05 cross-panel highlight bus 재사용, 05 근거 인벤토리 cross-link — 새 배선 0, 기존 highlight bus 에 bridge-bar→ledgerRow id 매핑만 추가).

**(3) 시각 규율 — 점선 '근사' + 빗금 'missing'(0대체 시각화 금지).** 05 시각 인코딩 SSOT(실선=검증 fan / 점선=미검증 prior fan)와 *일관*:
- **미검증 elasticity 유래 효과 바**(provenance `elasticity_prior_unvalidated`·`crp_prior_unvalidated`·`default:no-sector`, §2.3·§2B.3): **점선 테두리 + '근사' 배지**(amber `#fb923c` 11px, HonestyFooter Tier3 active-경고 톤). 검증된 pooled-OOS transfer 유래 바만 실선.
- **결손 driver**(데이터 부재): **0 높이 바가 아니라 'missing' 빗금(hatch) 바** — baseline 폭만큼 자리는 차지하되 사선 빗금 패턴 + `missing`/`blocked`/`partial` 라벨(`--dl-line #1b2130` 빗금). **0 으로 그려 "효과 없음"으로 위장 금지**(missing≠0 불변, 05 fan band None 끊김과 동형 — 결손을 0 추정으로 위장하지 않는 시각화).

**(4) 4단 캐스케이드 — 매출→이익→FCF→가치 세로 연결.** 4 bridge(매출 / 영업이익 / FCF / 가치)를 *세로로 쌓고*, 각 bridge 의 착지 바 → 다음 bridge 의 시작 바를 **세로 연결선**(faint `--dl-line`)으로 잇는다(한 폭포의 결과가 다음 폭포의 입력 = propagation 가시화). reference path = 03 §8 Premortem propagation 예시(원재료→COGS→마진→OI→FCFF→DCF→가격)와 1:1 — 그 텍스트 화살표 체인을 그대로 세로 폭포로 시각화한 것. 캐스케이드 어느 단이라도 missing 빗금/근사 점선이 끼면 *하류 전 단이 그 라벨을 상속*(불확실 전파 명시).

> **★부호색 중립(인과 단정 가드 — 호재/악재 금지):** 시나리오 투영/bridge delta 의 부유 바는 **증가=시안 계열(`#22d3ee`)·감소=중립 회색(`--dl-line-strong`/`#8b94a3`)** 으로 *부호만* 표기 — 녹/적('좋다/나쁘다')으로 칠하지 않는다. 시나리오는 forecast 가 아니고 "마진 하락 = 악재"는 인과 단정이라(00 §3·§7 추천 금지), 부호는 방향 정보지 가치 판정이 아니다. (실현·과거 수익 표면은 기존 `--up #34d399`/`--dn #f0616f` 관례 유지 가능 — 단 투영 폭포에는 적용 금지. 시작/착지 *수준* 바는 muted 회색.)

**색·바 방향·연결선·라벨 위치 명세(고정):**

| 요소 | fill/테두리 | 방향·위치 | 라벨 |
|---|---|---|---|
| 시작 바(전기 수준) | `--dl-line-strong #2a3142` muted, 실선 | baseline→전체높이, 좌단 | "전기 {지표}" + 값+ref점 |
| 착지 바(당기 수준) | `--dl-line-strong #2a3142` muted, 실선 | baseline→전체높이, 우단 | "당기 {지표}" + 값+ref점 |
| 부유 바 +증가(검증) | 시안 `#22d3ee`, 실선 | 직전 top→위로 floating | driver명+`+delta`+ref점, 바 위 |
| 부유 바 −감소(검증) | 중립 회색 `#8b94a3`, 실선 | 직전 top→아래로 floating | driver명+`−delta`+ref점, 바 아래 |
| 부유 바(미검증 prior) | 동상(시안/회색), **점선 테두리** | 동상 floating | + '근사' amber `#fb923c` 11px 배지 |
| 부유 바(결손 driver) | **빗금 hatch** `--dl-line #1b2130` | baseline 폭 자리만(0높이 금지) | "missing/blocked/partial" 라벨 |
| waterfall 연결선(바간) | faint `--dl-line #1b2130` 점선 | 앞 바 끝→다음 바 시작 수평 | — |
| 캐스케이드 연결선(bridge간) | faint `--dl-line` | 착지 바→다음 시작 바 세로 | — |
| ref 점 | 채워진 작은 원(focus 시 `#22d3ee`) | 바 모서리 | 결손=점 없음 |

**ASCII 와이어프레임(매출→영업이익 bridge 1단, 부호색 중립):**

```text
값
│  ┌────┐                                              ┌────┐
│  │전기│  ┌╌╌╌┐                                       │당기│
│  │매출│  ┊+물량┊(시안)  ┌────┐                       │영업│
│  │수준│  └╌╌╌┘ ▲       │−원가│(회색)  ▒▒▒▒▒          │이익│
│  │muted        │       │  ▼  │       ▒물류▒(missing) │muted
│  │(회색)│ ●ref  └╌╌╌╌╌╌╌┘ ●ref  ▒빗금▒ (라벨)  ●ref  │(회색)
│  └────┘                          └ 0높이 아님          └────┘
└──────────────────────────────────────────────────────────── 기간
   ▲시작 바      ▲점선=근사(미검증)   ▲빗금=결손      ▲착지 바
   (●=ref 점, 클릭→ledger 행 하이라이트 / 점선 테두리=elasticity_prior_unvalidated)
```

세로 4단 캐스케이드는 위 1단 폭포를 **매출 / 영업이익 / FCF / 가치** 4개 세로로 쌓고 착지→시작 세로 연결선으로 이은 형태(03 §8 propagation chain = 세로축). 잠정 — 바 폭·간격·애니메이션 타이밍(Play 시간순 갱신 시 05 §3 #4 ReportDock bridge 동기)은 졸업 데모서 눈검수 재보정.

---

## 4. 발간 표면 (적대검증 A-2·E-2)

- **정적 blog:** `story/publisher.py::publishReport`(`:27`)→`_buildFullReport`(`:118`, 면책 자동삽입 `:169`)→`blog/05-company-reports/{순번}-{코드}-{명}/index.md`→landing `company-reports` 카테고리(`posts.ts:15`)→GH Pages. **publisher 선례는 `story/publisher.py` 단독**(`credit/publisher.py`는 *미존재* — A-2 환각 삭제).
- **기존 company-reports 충돌 규약(E-2):** 같은 카테고리에 기존 6막 리포트와 시뮬 리포트가 공존하면 혼란. **`reportType` 메타(또는 서브카테고리)로 구분 + asOf 표시** 필수. 충돌 미설계로 같은 카테고리 재사용 금지.
- **terminal `?sim=`:** URL 공유=Play 결정론 척추. 단 현 terminal에 replay 상태기계·ReportDock 둘 다 부재(§5가 채움).
- **viewer AskDrawer:** 결정론 Tier0 답 안 "이 회사 시나리오 보기" 링크(공개 AskDrawer 회귀 금지 준수).

---

## 5. ReportDock — 단일 valuation 모드로 시작 (적대검증 C-2·B-3)

> **★거처 SSOT 포인터:** ReportDock 거처·셸 결정(좌패널 교체 패턴·셸 토폴로지·StrategyDock 선례 흡수)은 **05 ReportDock SSOT(StrategyDock 패턴) 준수** — 08 은 ReportDock 의 *valuation 모드 콘텐츠 계약*만 소유하고, 셸·거처 본문 결정은 05 가 소유한다(SSOT 분열 차단). 본 절은 05 가 정한 셸 위에 얹히는 valuation 단면 명세다.

세 보고서(가치평가·백테스트·시뮬)는 같은 검증 골격 공유(RunSpec·provenance·assumption ledger·quality gate·면책·look-ahead 차단). 그러나 **백테스트·시뮬 모드는 둘 다 미존재 → 2-mode 추상화 선투자는 YAGNI.** ReportDock은 **valuation 단일 모드로 시작**, backtest/sim 모드는 그 엔진 졸업 시 추가. ReportDock은 landing 측 *셸*(렌더만, 계산기 아님). 백테스팅 PRD([[project_terminal_backtesting_prd]])와 교차참조.

**금지어 lint(B-3):** "백테스팅 PRD와 SSOT 공유"는 거짓(백테스트 모드 미존재) → **본 작업이 `tests/audit/valuationPublishLint.py` 투자권유 금지어 lint 를 신설·CI배선 완료**(발간표면 한정 green no-op, 09 §10.1), 백테스팅이 나중에 import. 의존 방향: 본 작업이 선행 정의자.

---

## 6. 프로급 품질 체크리스트 (= "전문가급" 라벨의 정의, 발간 게이트)

전 항목 PASS여야 발간(`thesisKillChain.premortemQualityGate` + 03 Gate Matrix). ⚠ **부분 기계 강제**: 금지어 lint(§2.2·§7)는 **신설·CI배선 완료**(09 §10.1, 발간 표면 ship 즉시 자동 강제), 그러나 gate source(01 §6.3 `gate.py`)는 여전히 *미구현*(fatal③ AI-lens phase) → 그 항목만 발간 모드 착수(§11) 시 사람-체크.
1. ☐ 단일 목표가 부재 — 범위로만 (§2) 2. ☐ reverseDCF 닻 노출 + 충돌 판정 (03 §6.2) 3. ☐ 최소 3시나리오 (bear/base/bull) 4. ☐ 모든 숫자→ref 5. ☐ 모든 가정→falsifier 6. ☐ terminal 규율 통과 (g≤Rf, reinvest=g/ROC, ROC→WACC 수렴 or 명시 moat) 7. ☐ 결손=결손(0대체 0건) 8. ☐ provenance asOf 일치(look-ahead 0) 9. ☐ DisagreementLedger 노출 10. ☐ qualityGateStatus 표시 11. ☐ 라이프사이클 인지(young/mature/금융/cyclical leaf 분기) 12. ☐ 면책+금지어 가드 통과.

"전문가급" = **방법 엄밀함**(독점 데이터 아님). 컨센서스 부재(감사 확정) → "방법 투명성" 라벨이 적절하다. AI 3-티어(advanced/onDevice/deterministic)는 *기능 가용성*(어디서 도나)이지 과금 아님 — 공개 GH Pages=결정론 reverseDCF+3시나리오 토글(WebGPU 열화·숨김 금지), 로컬=multiStageDcf·thesisKillChain 전체·특수경로.

---

## 7. 법적 불가침선 (가드 — 문구·UI·테스트)

> **★규제 관할 표(발간표면 → primary 법역 → secondary 법역, 새 파일 0):** 현 §7 한 줄은 *US 권위*(Lowe v. SEC·Advisers Act·FINRA)로만 안전을 정당화하는데, **현 발간표면은 한국어·한국기업·GH Pages** 라 1차 관할은 **한국 자본시장법**이다 — US 권위로만 정당화하면 *확신오정렬*(엉뚱한 법역으로 안전 선언). 관할을 명시:
>
> | 발간표면 | primary 법역 (현재) | secondary 법역 (영문/EDGAR 해금 시 *추가*) |
> |---|---|---|
> | 한국어 · 한국기업 · GH Pages | **자본시장법 · 유사투자자문업** — 불특정·비개별 일반분석물(impersonal)은 *미신고 허용경계* | (영문/EDGAR 해금 시) **SEC Marketing Rule · FINRA 2210/2241** |
>
> 핵심 = **한국 유사투자자문업의 "비개별성"(불특정 다수 대상·개별 자문 아님) 요건과 US Publisher's Exclusion 의 "impersonal" 요건은 *동일 축*** 이다 — 한 가드(개별화·점추천·운용 금지)가 양 법역을 동시에 충족. 따라서 아래 안전/위험 4행은 **양 법역 공통요건**으로 읽는다(어느 한쪽 권위에 종속 아님). ⚠ 데이터락 정정: 영문/EDGAR 발간은 시뮬레이터에서 *데이터 해금* 사안(EDGAR 본문은 §4 viewer 에서 외부 untrusted 데이터로만 소비, 발간표면은 KR 한정)이며, **영문 발간이 열리는 순간 규제표면은 KR→US 가 *추가*(둘 다 적용, KR 대체 아님)** 된다. (직전 백로그가 "09 ④ US lock 옆"이라 했으나 09 ④는 실제로 *BC 위임 별도 commit* 외과 단위이고 별도 "US lock §④"는 09 에 부재 — 본 표가 관할 정본, 09 는 데이터 청산만 소유.)

**한 줄:** dartlab은 *impersonal·일반·재현·반증가능 분석 도구*(Publisher's Exclusion, Lowe v. SEC; **한국 유사투자자문업 비개별성 동일축**)로 남는다. 개별 재무상황 *적응*·점 추천 *발행*·자금 *운용* 순간 Advisers Act/FINRA(US) 및 유사투자자문 신고의무(KR) 본체로 넘어간다.

**안전/위험 4행 = 양 법역(KR 비개별성 · US impersonal) 공통요건** — 한 가드가 둘을 동시 충족:

| 안전 | 위험(가드 차단) |
|---|---|
| 회사 단위 조건부 시나리오 | 사용자 포트폴리오 맞춤 최적화 |
| 사용자가 가정 토글 | dartlab이 "이 가정 쓰라" 개인화 추천 |
| reverseDCF 함의 노출 | 단일 target + Buy/Hold/Sell rating, `signal` 노출 |
| 확률가중 bear/base/bull | "예상 수익률 N%" 약속 |

가드 구현(테스트 강제): ① **금지어 lint(`valuationPublishLint.py`, 신설·CI배선 완료, 발간 표면 마크다운 한정 — `_BANNED` 6패턴 실측)**(매수의견/매도의견·적극매수·비중확대/축소, strong buy/sell·buy/sell rating, underpriced/overpriced, 목표주가 점추정(NNNNN원), 예상수익률 약속(NN%), 개인화 어휘("귀하의 포트폴리오/상황"·회원님) → 발간 마크다운에서 차단; leaf src 는 미스캔. ⚠"추천"·"검증된전략"·bare Buy/Hold/Sell 단독 어휘는 현 6패턴 미포함 — 위 RISK 표(line 110~113)는 규제 *의도*, lint 은 이 6패턴만 실제 강제) ② 대체 어휘 강제("조건부 perShare 범위"/"현재가 함의"/"시나리오 분석"/"반증 조건") ③ **필수고지 *존재* 기계강제(필수고지 키 4종 표 — 산문 대신 박제, 아래)** ④ FINRA 2241 형식 차용(rating 미발행이라 본체 비적용, 형식만: reasonable basis=panel ref+ledger / valuation method 명시=어느 leaf / risks=falsifierLedger). 네 규제가 *모두* 같은 것(criteria/assumptions 노출+risk 명시+reasonable basis)을 요구 → 가정-노출이 곧 규제 안전 + 전문가급.

> **★③ 면책 산문 → 필수고지 키 4종 표 + *존재* 어서션(규제 red 차단, 새 파일 0 — 기존 가드 확장):** 현 `valuationPublishLint.py` 는 *금지어 negative-scan* 만 한다(`_BANNED` 6패턴 — *없어야 할 것*). 그러나 **있어야 할 고지가 누락**되면 금지어 0건이라 lint green 이어도 *규제 red*(SEC Marketing Rule·FINRA 2210 은 hypothetical 한정고지·가정노출·반증·산정방법을 *요구*) — negative-only lint 의 false-green 구멍. ⟹ 같은 guard 에 **고지-*존재* 어서션**을 additive 로 추가한다(새 파일 0 — `valuationPublishLint.py` 확장): `reportType: simulation` 발간표면에 아래 4키가 *모두 present* 아니면 `--strict` red.
>
> | 필수고지 키 | 내용 | 규제 근거 | 현 상태 |
> |---|---|---|---|
> | (a) `hypothetical` | hypothetical/scenario 한정고지 — "scenario analysis, *not a forecast*" | SEC Marketing Rule·FINRA 2210 hypothetical performance | ⚠ 신설(현 lint 미검사) |
> | (b) `asOf+ledger` | asOf 기준시점 + assumptions ledger 링크 노출 | criteria·assumptions 노출 요건 | ⚠ 신설 |
> | (c) `falsifier` | falsifier(반증 조건) 노출 — `thesisKillChain` ledger 링크 | risks 명시(FINRA 2241 risks) | ⚠ 신설 |
> | (d) `valuationMethod` | 산정방법 라벨 — 어느 leaf(어느 DCF/닻)로 산정했는지 | reasonable basis·valuation method 명시 | ⚠ 신설 |
>
> 구현 = `valuationPublishLint.py` 에 `_REQUIRED_DISCLOSURE` 4키 정규식 + `_assertPresence(md)` (4키 중 하나라도 미매치 시 `[FAIL] 필수고지 누락` → `--strict` exit 1). **`publisher.py:169` 면책 emit 구조 = 4키 명세** — 현 `disclaimer` 단일 산문(line 169, generic "투자 권유 아님" + "자동 생성"[⚠ 별건: 주체중립 위반, 본 백로그 범위 밖])을 `reportType: simulation` 발간 시 **4키를 모두 emit** 하는 구조로 명세(a hypothetical 한정 + b asOf·ledger 링크 + c falsifier 링크 + d valuationMethod 라벨). T1↔T2 자동발화 계약(09 §10.1 FIX-2)과 동형 — publisher emit 키 ↔ lint 매치 키 바이트 동일. ⚠ **현재 미구현(design + 졸업 AC)** — 현 `valuationPublishLint.py` 는 금지어 6패턴만 실측, 존재 어서션·`publisher.py` 4키 emit 은 T2 발간표면 신설(Phase 6) 동행 신설. 졸업 AC = **"reportType:simulation 발간표면에 4키 고지 누락 0(금지어 0 + 고지 4/4 동시)"**. 잠정 — 4키 정규식·publisher emit 형식은 T2 표면 ship 시 실측 확정.

---

## 8. 재현성 (적대검증 F-1)

- 같은 입력→같은 출력. 순수함수 DAG(01 §0). 현 결정론 코어(`simulate/`)는 **난수 0** — 같은 회사·시나리오·asOf면 노드별 inputsHash byte-identical(메모이제이션은 후속). RunSpec(03 §4.1)=scenario+drivers+asOf+vintage+fee/slippage.
- **선결 kill-test — ✅ 완료(09 P1, 2026-06-14): 전역 `random.seed` 2곳(`pricetarget.py:278`·`_simMonteCarlo.py:145`)→로컬 `random.Random(seed)`**(stdlib·pyodide 안전, **numpy/PCG64 아님**) + `:205` 덮어쓰기 버그 → 연도별 cumprod. *레거시 MC 경로* 한정 — `simulate/` 코어엔 MC 노드 부재.
- **★브라우저 패리티 정정(F-1):** 레거시 MC는 stdlib `random.Random`(Mersenne) — JS RNG와 다른 알고리즘이라 TS byte-패리티 자동 보장 *안 됨*. **결정론 path는 엔진이 사전계산, 브라우저는 *드러내기만*(RNG 미사용)** — 05 Play 전제와 일관. MC 노드가 후속에 생기면 분포통계 패리티(±ε)만(01 §12). **AI lens(`.ai` 슬롯)는 비결정론 → fact 미승격·재현성 보증 밖(hypothesis 라벨), 보고서 면책에 명시.**

---

## 9. 거처·계약 (새 verb 0)

leaf=L2 SSOT 불변(`analysis/valuation/*`·`analysis/financial/calc*`·`buildProforma`·`computeCompanyWacc`). simulate(L2.5)가 `calc*` 래퍼 호출, story(L3)가 렌더. 가치평가=`simulate(mode="whatif")`의 한 읽기 방식, 새 톱레벨 verb 없음. 신설 총량(좁음): builders 렌더러 2개 + story `type="simulation"` + 금지어 lint 1개 + landing `ReportDock` 셸(valuation 단일 모드). _attempts 졸업 후 본진. 덕지덕지 금지(reverseDCF·fairValueRange·thesisKillChain·publisher 재발명 금지 — 조립).

---

## 10. 신설 vs 재사용

**재사용(~80%):** DCF 5변종·역DCF·RIM·실물옵션·SOTP·5시나리오 MC·`computePriceTarget`(§5.6 선구현)·`buildProforma`·story 조립기 11타입+100+렌더러+업종 템플릿+6막·publisher→blog 가동·thesisKillChain·`judgeQuarter`+OutcomeLog(Brier 기반).
**신설:** `simulate/` 묶음(0줄)·`ai/tools/lens.py`·렌더러 2개·금지어 lint·ReportDock 셸·역DCF 보고서 전면 승격. **불가(후속):** 거시 미래경로 투영(AR/VAR, `macro/`에 부재 — preset 의존).

---

## 11. ★우선순위 게이팅 (적대검증 C-1 — 가장 중요)

`src/dartlab/simulate/` 결정론 코어(sheet/transfer/registry/run/entry)·`dartlab.simulate`/`Company.simulate` verb 는 **이미 졸업·실재**(01 §5a, `ac3905fd9`). **미구현 = 발간 의존부**(렌더러 2개·14키 ref 치환·ReportDock·gate.py·T2 발간표면). 보고서 발간 단면을 그 의존부보다 앞세우는 것은 우선순위 역전 — 코어는 섰으나 발간 단면은 아직. 순서:

1. **Phase 0 ✅ 완료(09 P1):** MC seed kill-test — 전역 `random.seed`(`_simMonteCarlo.py:145`·`pricetarget.py:278`)→로컬 `random.Random(seed)`(stdlib, numpy/PCG64 아님) + `:205` cumprod(`test_horizon_widens_cone`).
2. **simulate 코어 _attempts 졸업**(01 §15) — DriverSheet·DriverRegistry·`SimulationResult` 실측 확정.
3. **그 후에야** 본 08의 보고서 모드(렌더러 2개·14키 ref 치환·ReportDock·lint)를 착수.

07 통합 로드맵상 시뮬레이션은 시퀀스 4번(지수→이벤트레일→백테스팅→시뮬). 본 08은 그 4번의 *발간 단면*이므로 **시뮬 코어와 동기**, 단독 선행 금지.

---

## PRD 반영 (이 문서 외 삽입)

- 01 §1 사실정정: reverseImplied 이미 배선(`registry.py:854`) + 2층 valuation SSOT(`analysis/financial/calc*`←`analysis/valuation/`) + `fullValuation` deprecated.
- 01 §4 외과추출: 신설 builders 2개 행 추가.
- 03 §9: "발간 게이트"(금지어 lint·면책 확장·FINRA 2241 형식·priceP50 build-fail).
- 00 §5: "Valuation Report = simulate 발간 단면" 1줄.
- 00 §6.3(Bridge Waterfall 화면): bridge waterfall *시각 문법 SSOT = 08 §3.4* 포인터 1줄(시작/부유/착지 바·점선 근사·빗금 missing·4단 캐스케이드·부호색 중립 — 00 은 화면 배치, 08 §3.4 는 시각 문법).
- README: 문서지도에 08 추가.
