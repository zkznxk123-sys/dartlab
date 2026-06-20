# 02. Assumption and Simulation Method

상태: PRD (§2B = v0.4 DriverRegistry / 본문 §1·§2.1~2.9·§3~7 = v0.1 방법, 아래 정정 우선)
범위: 가정 장부, vintage 처리, 이벤트 정규화, 손익 전파, 가치평가, 주가 민감도, 미세 절차 + §2B driver 수렴/확장

> **★구현 정합(2026-06-14):** §2B.5 item 4 models HF dead chain = "1줄" 과소평가 정정 → 4단 신설 작업(`recordForecast` 부재 확인). §2B.10 firm-level t-stat None 명시. §2B.11 작은 표본 수치 게이트(min-T 12분기·min pooled-N 60·holdout-k 4·Sobol S_T 0.05) + look-ahead 코드 강제 위치 신설. admission.py/eval gate는 미구현 — §2B 게이트 공식은 *설계*.

> **★v0.2 정정(2026-06-13) — 본문 v0.1 용어보다 우선:**
> - **mode enum 통일**: 본문 §2.3의 `historicalReplay`/`walkForward`/`futureWhatIf` → 정본 = **`replay`/`walkforward`/`whatif`**(01·README·05). 한쪽 폐기, `whatif`가 SSOT.
> - **회귀 4중**(본문이 암시한 것보다 1개 더, 09 §0): +`analysis/financial/macroExposure.py:88 calcMacroSensitivity`. `calcMacroSensitivity` **동명 3곳**(`_signalsMacroSensitivity.py:105`·`macroExposure.py:88`·`_predictionSynthesis.py:77`) disambiguate.
> - **forwardTest는 write 함수 *부재*(신설 필요)** — credit은 write 함수 존재(cron 배선만 부재). §2B.5 decay 게이트 참조.
> - driver 수렴/확장의 정본 메커니즘 = **§2B DriverRegistry**(pooled-panel transfer 1차, factor-zoo 규율). 본문 §2.6 BusinessDriverEstimate는 그 자료구조 측면.

---

## 1. 핵심 개념

이 시뮬레이터의 기본 단위는 예측값이 아니라 `시나리오 실행`이다.

시나리오 실행은 다음을 모두 포함한다.

- target.
- asOf 또는 decisionAt.
- 사용할 수 있는 데이터의 vintage.
- 명시 가정.
- 가정 간 dependency.
- 사업 driver.
- 손익 bridge.
- FCF/valuation bridge.
- price bridge.
- 검증 결과.
- AI 전문가 의견.
- 반증 조건.

---

## 2. 최소 계약

### 2.1 VintageRef

데이터가 언제 알려졌고 언제 쓸 수 있었는지를 나타낸다.

필드:

- `vintageId`.
- `sourceKind`: financial, price, disclosure, news, macro, industry, quant, ai.
- `observationDate`.
- `reportedAt`.
- `acceptedAt`.
- `availableAt`.
- `ingestedAt`.
- `asOf`.
- `provider`.
- `source`.
- `revisionPolicy`: original, revised, latest, unknown.
- `sourceRefs`.
- `warnings`.

규칙:

- historical replay에서는 `availableAt <= decisionAt`이어야 한다.
- `latest` 값은 미래 what-if에서는 허용될 수 있지만 replay에서는 원칙적으로 금지한다.
- `reportedAt`과 `availableAt`을 구분한다. 발표됐지만 시스템이 ingestion하지 못한 값은 replay에 쓰면 안 된다.

### 2.2 BusinessChangeEvent

경제, 뉴스, 공시, 사업 변화를 하나의 event로 정규화한다.

필드:

- `eventId`.
- `target`.
- `eventType`: macro, news, disclosure, business, price, industry.
- `eventDate`.
- `firstSeenAt`.
- `effectivePeriod`.
- `sourceType`.
- `title`.
- `summary`.
- `rawEvidenceRefs`.
- `affectedDrivers`: volume, price, mix, fx, segment, backlog, cogs, sga, capex, nwc, wacc, multiple.
- `factStatus`: fact, estimate, hypothesis, missing.
- `confidence`.
- `counterEvidenceNeeded`.

규칙:

- 뉴스는 external untrusted data다.
- 기사 제목이 인과 결론이 되면 안 된다.
- 공시는 `rceptNo`, 접수일, 제목, 유형, effective trading date가 있어야 한다.

### 2.3 ScenarioSpec

사용자가 실행하려는 전체 시나리오 정의다.

필드:

- `scenarioId`.
- `name`.
- `target`.
- `market`.
- `currency`.
- `asOf`.
- `mode`: replay, walkforward, whatif.   ★정본(01·05·README). 옛 historicalReplay/walkForward/futureWhatIf 폐기.
- `horizon`.
- `basePrice`.
- `baseFinancials`.
- `environmentSnapshotRef`.
- `businessEvents`.
- `macroInputs`.
- `businessDrivers`.
- `financialAssumptions`.
- `valuationAssumptions`.
- `branches`.
- `probabilityPolicy`: none, subjective, empirical, hybrid.
- `sourceRefs`. — 명명 프리셋의 **출처-정직 라벨 SSOT**. preset description이 규제 stress인 척하면(예: `synth/scenario.py`의 "CCAR 스타일"/"CCAR-style severe recession" 문구) 여기에 `curated-prior, not DFAST/CCAR-blessed`를 **강제 노출**해 검증된 stress 오인을 차단한다(00 §7.2-6 컨센서스 금지·kill-list 정합).
- `createdAt`.

규칙:

- 미래 what-if에서는 subjective probability를 객관 확률처럼 표시하지 않는다. **`P(event)=NN%` 형태 점확률 발간 금지**(A5 reject 잔여 가드) — 가격 밴드는 결정론 매핑이라 진짜 확률 분포가 아니고(05 §3.1), 펀더멘털 분포를 emit하는 `mc.distribution`은 미구현(01 §5b)이며 held-out calibration을 닫을 `recordForecast` write-end가 부재(09 §17)다. 점확률을 박으면 un-calibrated folk-stat(메모리 horizonMeaning: 3점·CI0·seed0 금지)의 재발이다. 표시 시 `run.warnings`에 `subjective_probability_not_objective` 표면화. 미래 격하(reject→defer) 선결 3조건 = `mc.distribution` 라이브 + `recordForecast` write-end + held-out Brier calibration 통과, 그 후에도 점확률이 아닌 *조건부 펀더멘털 진술*("이 가정 하 매출이 X 넘는 분포 비율")로만.
- branch는 중첩 가능하지만 같은 driver가 중복 반영되면 overlap warning이 필요하다.
- **명명 프리셋 흡수(A1, absorb-as-defer)**: baseline/adverse 등 명명 시나리오는 이미 `_fnMacroPath → getPresetScenarios("KR")`로 1급 소비되며 `provenance=preset:{scenarioId}`로 출처 태깅됨(01 §5a) — **새 라이브러리 자료구조·카탈로그 패널·`version`/`falsifier` 필드 신설 0**(falsifier는 AssumptionLedgerRow 레벨에만 존재, 시나리오로 끌어올리면 SSOT 분열). 실제 KR 프리셋명 = baseline/adverse/china_slowdown/rate_hike/semiconductor_down이며 "severe" 단일 명칭은 코드에 없다(권위 환각 가드). 흡수할 단 하나의 다듬기 = `DriverCard.warnings`의 `elasticity_prior_unvalidated`가 명명 프리셋 결과 `SimulationResult.warnings`에도 실리도록 전파(현재 미배선, §2B.5 forwardTest write-end dead chain이라 active 승격 자체 불가 = 졸업 AC와 동일 선결).

### 2.4 ScenarioBranch

if 조건 하나 또는 조건 묶음이다.

필드:

- `branchId`.
- `parentBranchId`.
- `label`.
- `condition`.
- `assumptionRefs`.
- `dependencyRefs`.
- `activationRule`.
- `weight`.
- `exclusiveGroup`.
- `overlapGroup`.
- `status`.

예:

- 환율 +8%.
- ASP +3%.
- 수출 물량 -5%.
- 원재료 가격 -7%.
- peer multiple -10%.

### 2.5 AssumptionLedgerRow

가정 하나의 장부 row다.

필드:

- `assumptionId`.
- `scenarioId`.
- `branchId`.
- `category`: macro, revenue, cost, workingCapital, capex, tax, valuation, price, event.
- `claim`.
- `baseValue`.
- `scenarioValue`.
- `rangeLow`.
- `rangeHigh`.
- `distribution`.
- `unit`.
- `period`.
- `source`: user, engine, ai, imported.
- `evidenceRefs`.
- `counterEvidenceNeeded`.
- `falsifier`.
- `affectedDrivers`.
- `sign`.
- `probability`.
- `status`: fact, estimate, hypothesis, missing, rejected.
- `lastCheckedAt`.

규칙:

- 숫자 가정은 단위와 기간이 없으면 invalid다.
- AI source row는 반드시 검토 상태를 가진다.
- 반증 조건이 없는 핵심 가정은 gate에서 실패한다.

### 2.6 BusinessDriverEstimate

사업 driver로 변환된 추정이다(가정 장부 측면 — 사용자/엔진 입력 row). **실행 노드 입자도(driverId, scenarioId, periodKey 3중 좌표 + NodeValue.vector)의 SSOT는 01 §5**다. 본 자료구조는 그 입력이지 실행 노드 자체가 아니다.

필드:

- `driverId`.
- `target`.
- `segment`.
- `driver`: volume, price, mix, fx, backlog, capacity, rawMaterial, labor, logistics, rnd, depreciation.
- `baseValue`.
- `deltaPct`.
- `deltaAmount`.
- `elasticity`.
- `lag`.
- `duration`.
- `projectedImpact`.
- `sourceRefs`.
- `assumptionRefs`.
- `status`.
- `warnings`.

### 2.7 ProfitEstimate

손익과 현금흐름 추정이다.

필드:

- `estimateId`.
- `scenarioId`.
- `period`.
- `scenarioLabel`.
- `revenue`.
- `grossProfit`.
- `operatingIncome`.
- `netIncome`.
- `eps`.
- `cfo`.
- `capex`.
- `fcf`.
- `grossMargin`.
- `operatingMargin`.
- `netMargin`.
- `taxRate`.
- `shareCount`.
- `workingCapitalDelta`.
- `driverRefs`.
- `executionRef`.
- `qualityFlags`.

> **★qualityFlags producer 결선(orphan 필드 해소, R17):** `ProfitEstimate.qualityFlags`는 *producer가 명시되지 않은 orphan 필드*였다. 정본 producer = **`quality.baseline` 노드**(결정론 회계품질 측정 노드) — baseline actual 단면에서 cashConversionGap forensic·Sloan accrual·receivable-led growth 등 결정론 신호를 산출해 `qualityFlags`를 채운다(09 §0 #6 forensic 7모델 leaf 호출 일원화, 새 산출 0). **역할 분리**: (1) **결정론 측정 = `quality.baseline` 노드**(숫자·flag 산출, AI 무관) (2) **AI Accounting lens(§3.13 step 4·03 §7 Accounting lens) = 해석·반증만**(quality.baseline의 flag를 *읽어* 해석하고 반증 시나리오를 제시하되 *새 회계 숫자를 만들지 않는다*, 00 §3 원칙 5 "AI가 만든 숫자는 공식 fact가 아니다"). projected 단면은 위 R17 §3.9대로 forensic 신호 아님 — quality.baseline 노드는 baseline 단면에서만 forensic flag를 켠다.

### 2.8 ValuationBridge

손익과 현금흐름을 가치평가로 전파한다.

필드:

- `valuationId`.
- `scenarioId`.
- `method`: fcffDcf, relative, residualIncome, reverseDcf.
- `nopat`.
- `reinvestment`.
- `fcff`.
- `salesToCapital`.
- `rocPct`.
- `reinvestmentRatePct`.
- `riskFreeRatePct`.
- `erpPct`.
- `beta`.
- `costOfEquityPct`.
- `afterTaxCostOfDebtPct`.
- `waccPct`.
- `terminalGrowthPct`.
- `terminalValueSharePct`.
- `enterpriseValue`.
- `netDebt`.
- `equityValue`.
- `shares`.
- `perShare`.
- `marketCap`.
- `upsidePct`.
- `reverseDcf`.
- `sensitivityGrid`.
- `blockers`.
- `sourceRefs`.

### 2.9 PriceSimulationResult

최종 가격 민감도 결과다.

필드:

- `simulationId`.
- `runId`.
- `scenarioId`.
- `branchId`.
- `basePrice`.
- `priceP10`.
- `priceP50`.
- `priceP90`.
- `bearPrice`.
- `baseScenarioPrice`.
- `bullPrice`.
- `fundamentalReturn`.
- `factorReturn`.
- `eventReturn`.
- `interactionAdjust`.
- `overlapPenalty`.
- `totalReturn`.
- `componentReturns`.
- `priceBridge`.
- `qualityGateStatus`.
- `warnings`.
- `dateRef`.
- `executionRef`.
- `sourceRefs`.

---

## 2B. Driver 수렴·확장 메커니즘 — DriverRegistry (v0.2, 데이터 폭발 → bounded if)

데이터(거시·지수·뉴스·공시·customs)는 계속 추가·확장된다. 각 데이터가 새 if/driver가 되면 시나리오 if 수가 폭발한다. 운영자 직관("데이터 종류별 과거 백테스팅 → 미래 투영")은 정확히 자산가격 연구의 **factor zoo** 문제(Harvey·Liu·Zhu: 발표 팩터 300+, 대부분 거짓발견)와 동형이고, 그 규율이 답이다. 단 **dartlab 실제 표본이 작아(분기 6~36, 연간 4~8) 대형 표본 기법을 그대로 못 쓴다** — 이 부정합 해소가 품질의 척추다(적대검증 치명상 4).

### 2B.0 결론

**driver는 코드 `if`가 아니라 `simulate/registry.py`가 소유하는 *데이터 카드(DriverCard)*다. 새 데이터는 카드 1줄 등록으로 들어오고 코드 분기는 0개 는다. 카드는 6단계 입장 게이트를 통과해야 `active`가 되어 시나리오 sheet 엣지가 된다. 수렴 = 후보가 늘수록 입장 허들이 자동 상승하는 게이트, 확장 = 모든 데이터가 동일 카드·동일 게이트를 타는 단일 파이프라인. if 상한 = 시리즈 수가 아니라 검증된 축 수(현재 6~8).** 01 §0(L2.5 `simulate/`·det/ai 평행·순수함수 DAG)을 0줄 바꾸지 않고, 본 절이 driver가 *어떻게 자격을 얻는가*를 채운다.

> **★엔진계약-차원 쌍둥이(데이터 자동흡수 ↔ 계약 자동인식).** DriverRegistry 의 "데이터=카드 1줄, 코드 분기 0"은 *데이터* 차원의 자동흡수 선례다. 그 *엔진계약* 차원 등가물 = simulate 노드가 호출하는 외부 leaf 의 시그니처·반환 shape drift 를 잡는 순방향 binding 게이트(`test_simulate_leaf_binding`, 09 §6·§0 6행 표). 운영자 급소("엔진이 변환되면 simulate 수동변경 순환")의 정본 해법으로, leaf 계약이 *BC-additive* 로 늘면(선택인자·superset 반환) subset 단언이 자동 통과(코드 분기 0), *깨지면*(제거/rename/arity 변경) CI red 로 단일 노드 fn 지목. **단 binding 을 별도 선언 카드로 승격하는 것은 현 4노드(외부 leaf 6표면) 단계엔 중복 — `registry.py` 호출부+체크인 baseline 으로 충분, 카드화는 노드 N>~8 superset 일 때 조건부 졸업**(`feedback_always_check_clutter` — 강함은 깎아서).

### 2B.1 ★표본 결정 — pooled-panel 우선 (치명상 4 해소, 가장 중요)

회사별 분기 OLS(`calcMacroRegression`, T=6~36)는 stability selection·Bai-Ng IC·purged walk-forward에 **표본이 근본적으로 부족**하다(T=20에서 purge+embargo 후 train fold 3~4분기 → 3변수 OLS 자유도 0). 대형 기법 이름만 빌리면 거짓발견을 *못 막는* 게이트가 된다(horizonMeaning folk-stat 함정과 동형). 정공법:

- **driver transfer는 pooled-panel(섹터 횡단면)이 1차 SSOT.** 섹터 내 회사 분기 재무를 풀로 합치면 `T × 기업` 횡단면이 stability selection·다중검정·OOS를 점근에 근접시킨다. dartlab `valuation/crossRegression.fitPanel`(within-estimator·기업 고정효과)·`scan.scanMacroBeta`(전종목)가 정확히 이 자리 — **단 pre-fit cron이 dead라(grep 0건) 활성화 신설 필요.** driver = "섹터 공통 transfer + 기업 고정효과", T=20 회사별 취약 베타가 아니라. 단 pooled-panel 은 *기업 이질성의 정밀도*만 사고, 섹터 macro-transfer β 자체는 여전히 공통 시간변동(T=6~36)으로만 식별된다 — 모든 기업이 매 t 같은 macro shock 을 보므로 유효 독립관측은 firms×quarters 가 아니라 ≈T 다(Moulton/clustered-SE). 따라서 macro β 의 SE/t 는 cluster-robust-by-time(Driscoll-Kraay 또는 블록) SE 로 계산하며, t-자유도는 pooled-N 이 아니라 유효 time-DoF(≈T)다. 이 SE 처리는 §2B.10 이 추가하는 scanMacroBeta t-stat/SE 산출(및 G1' t-bar)에 박제하며 새 추정기는 추가하지 않는다.
- **★β 이질성 정직 경계(pooled-panel이 식별하는 것의 한계, R19).** within-estimator pooled-panel은 **섹터 공통 기울기 β_s + 회사 고유 절편 α_i**만 식별한다 — 회사 *고유 기울기* β_i(회사별 macro 민감도)는 작은 표본(T=6~36)에서 비식별이다(고정효과는 절편 이질성만 흡수, 기울기 이질성은 firm-level 자유도 부족으로 못 가른다). 따라서 충격 전파 *크기*는 **섹터 평균**이다 — 어떤 회사가 섹터 평균보다 cyclical하거나 defensive하면 그 편차를 pooled-β로 못 잡는다. 강제 라벨 = `beta=sector-average, firm slope unidentified`(회사별 고유 민감도를 안다고 위장 금지, "확신오정렬 > 정렬실패" 차단).
- **식별가능 관측 modifier로 기울기 부분 복원(R19).** β_i를 직접 추정하진 못해도, *공시 실측 노출 metric*은 섹터 β를 회사로 modulate하는 식별가능 정보다 — `exportRatio`(수출 비중 → fx·글로벌 수요 노출)·`fixedCostRatio`(고정비 비중 → operating leverage)·`netDebtToEquity`(레버리지 → 금리 노출). 이 modifier를 섹터 β에 *곱해* 기울기의 *관측가능 부분*만 복원한다(잔여 β_i는 여전히 미식별 라벨). 거처 = `DriverCard.transferSpec.modifierRefs`(§2B.3a TransferSpec 필드 확장 — 노출 metric의 VintageRef 목록, 추정기 신설 0·공시 실측값 곱셈만). modifier가 결손이면 섹터 평균 그대로 + `modifier_unavailable` 라벨.
- **회사별 베타는 *정제*로만.** `calcMacroRegression`은 `nObs ≥ 임계`이고 OOS holdout 통과 시에만 pooled 값 위에 회사 편차를 얹는다(라벨). 미달이면 pooled 섹터 transfer 사용(provenance hierarchy: pooled+회사확증 > pooled > preset 무출처).
- **T<40 회사 단위에서는 stability selection·Bai-Ng IC 금지.** 회사 단위 OOS = leave-last-k holdout만. per-company E(V) bounded 주장 철회. 대형 기법은 pooled-panel 차원에서만.
- **★firm-level t-stat 부재(치명 정정 — 01 §1 #7과 동일 사실):** `scanMacroBeta`(scan/macroBeta.py:113)는 연간 컬럼만 쓰고 ≥4개 요구 → 성장률 obs = 3개, `_quickOLS:343` k=4 적합 → df = N−k ≤ −1. firm-level에서 SE·t-stat이 *수학적으로 존재하지 않는다*. "회사 회귀 N~13"은 *연간 기준 실제 N=3*로 한 단계 더 낙관이었다. 정정 3택 중 admission.py 강제: ① firmRefine 게이트 nObs≥12를 *분기* 기준으로 명시(연간 불가 — T=12분기≈3년), 또는 ② macroBeta가 분기 매출을 쓰도록 leaf 확장 명시, 또는 ③ ★G1' t-stat은 firmRefine에서 *계산 자체 금지*(pooled-panel에서만 valid t), firmRefine은 leave-last-k point-forecast hitrate만(§2B.9 tier 가드가 강제).

### 2B.2 6단계 입장 게이트 (admission)

`simulate/admission.py`(신설, 순수함수)가 leaf를 *감싼다*(leaf 불가침):

- **G0 prior + family 등록:** 경제적 사전 있는 후보만 검정 패밀리에 넣고 시도 수 N을 정직히 등록(사전등록 ledger — forking-paths 차단). **N = driver family 의 누적 DISTINCT 사전등록 trial 수** — vintages/sectors 횡단으로 시도-후-기각된 모든 distinct (series × transform × lag) 가설, `DriverCard.admission.nTrials`에 persist(G0 ledger 가 SSOT). 전 시장 카탈로그(130)는 over-counting 이라 기각하되, *per-prefit active pool*(under-counting, ~13)도 아닌 누적 distinct-trial. nTrials 는 NEW 가설이 family 에 들어올 때만 monotone 비감소(이미 등록된 driver 를 새 vintage 로 재적합하는 것은 N 증가 아님 — 아니면 새 탐색 0인데 G1' t-bar 가 시간 따라 무한 인플레, §2B.9 self-strangle). lag1/2가 상관-only면 N에 안 곱함(코드 정합).
- **G1 OOS transfer 유의성:** in-sample R²≥0.3을 **purged+embargoed walk-forward OOS 부분 R²**(pooled-panel)로 교체. 거시 driver는 IS→OOS 붕괴가 가장 심하므로(Goyal-Welch) 가장 엄격히.
- **G1' 다중검정 t-bar:** 보정 후 `|t| > √(2·ln N)`(N = G0 누적 distinct-trial `nTrials`, §2B.0)(또는 core driver는 Harvey-Liu-Zhu `t>3.0`). core(척추 6축)=step-down Holm(FWER), exploratory(뉴스·customs)=BHY-FDR(driver 상관 허용). **신설 정직 계상**(치명상 2): `multipleTesting.haircutSharpe`는 Sharpe·일별수익 시그니처라 직접 호출 불가 + Holm이 degenerate(rank-1=Bonferroni) → critical-t 공식 + 진짜 step-down Holm을 `admission.py`에 **독립 구현**(호출 아닌 신설).
- **G2 stability selection:** subsample 선택빈도 ≥ π_thr, E(V) ≤ q²/((2π−1)p) — *p가 늘어도 거짓발견 기대 bounded*. **pooled-panel에서만**(T<40 회사 단위 금지). effective-N은 denoiseRMT 아니라(T>N 위반, 치명상 3) 후보 상관행렬 participation ratio `(Σλ)²/Σλ²`(T-독립)로 추정 — 신설.
- **G3 차원 라우팅:** 6축 흡수(기본, 새 if 0) / block factor 응축(customs HS 17 → 교역 block 1개) / 신축(예외, IC+직교+지속 4게이트, pooled 증거). **6축 SSOT 정정**(경상): `predictionSpace` 6축(businessCycle/interestRate/fxRate/commodity/sentiment/liquidity) ≠ `exogenousAxes` 6축(commodity/production/demand/financial/domestic/fx) — 서로 다른 분류다. `exogenousAxes.axis` 필드를 **라우팅 SSOT로 확정**하고 predictionSpace 축을 거기 매핑.
- **G4 횡단면 robustness:** value-weight + 극단치 winsorize + 최소표본(Hou-Xue-Zhang microcap 가드 — 소형·저유동·소표본 슬라이스에서만 빛나는 driver 거부).
- **G5 쇠퇴 강등 (2채널, R22):** driver 자격은 매 vintage 갱신하되 *두 종류*의 쇠퇴를 본다 — 점오차 drift와 coverage drift는 다른 실패다(점추정은 맞아도 밴드 폭이 틀릴 수 있고, 그 역도 성립).
  - **채널A (기존) 점오차 drift**: `forwardTest` per-driver 오차 스트림에 Page-Hinkley/ADWIN drift → `active→dormant`(재적합) / 누적 실패 → `retired`. forwardTest 적재 cron 신설(현재 dead, §2B.5 #4).
  - **채널B (신규) coverage drift**: `LiveScore.rollingCoverage`(최근 k분기 명목-vs-경험 포함율)가 **90% 명목밴드를 3분기 연속 < 0.80**이면 σ 재추정 트리거 → 최근 윈도 잔차 재적합(regime 층화 유지). 재추정 후에도 미달이면 `calibState='under-dispersed'` + fan을 **점선·회색 강등**(05 §시각 인코딩 SSOT 미검증 표기) + `SimulationResult.warnings`에 `coverage_below_nominal` append.
  - **★silent 확대 금지(핵심 정직 가드)**: coverage가 낮다고 *조용히 σ를 키워* 명목 coverage에 맞추면 사후적합(post-hoc overfit, horizonMeaning "확신오정렬" 재현)이다. 재추정한 σ는 **held-out 검증을 통과한 σ만 승격**(§2B.11 acceptance threshold·§3.7 fan σ 확대도 검증 σ만). 검증 미통과 σ는 강등 라벨로만 표면화하고 active로 안 올린다.

### 2B.3 DriverCard 자료구조 + 생애주기

`candidate → (G0~G4) → dormant ⇄ active → (G5) → retired`. 데이터 추가 = `candidate` 카드(코드 0줄). 카드 필드: `driverId·sourceRef(VintageRef)·axis·tier(core|exploratory)·transferSpec{leaf,lag,transform}·admission{state,nTrials,oosPartialR2,adjustedTStat,selectionFreq,eVBound,sTotal}·liveScore{directionHitRate,driftStat,lastCheckedAt}·warnings`. 동일 데이터 종류 무관 동일 카드·동일 게이트 → **if 폭발이 코드 분기 폭발이 아니라 후보 풀 통계 필터링으로 전환**(손 큐레이팅 0).

> **★active 진입 선결(write-end 게이트):** `forwardTest` write 끝단(recordForecast + data/models persistence + driverDecay cron, §2B.5 item 4)이 라이브가 되기 *전까지* `DriverCard.state` 는 **dormant 가 상한**이다 — 어떤 카드도 `active` 로 승격될 수 없다. 1회성 admission(G0~G4 prefit OOS)은 in-sample 시점 결정이라 시간축 silent degradation 을 막지 못하고, `active→retired`(G5)만이 누적 false discovery 를 bound 하는데 그 G5 의 쇠퇴 스트림(forwardTest)이 없기 때문이다(factor-zoo). write-end 라이브 후에만 active 승격 허용. **새 게이트가 아니라 기존 candidate→active 전이의 precondition.**

> **★A2 흡수(Bloomberg MAC3 충격 전파, absorb-as-defer):** *결정론 단일-충격 캐스케이드*(macro→rev→proforma→dcf, preset scenario 주입)는 이미 본진 졸업(`096e84c43`)되어 `simulate/transfer.py`(L2.5-OWNED 엣지, leaf 0줄)가 소유 = **already-have**(01 §4, 신규 항목 추가 0). MAC3 대비 갭이 가장 날카로운 자리 = MAC3는 포트폴리오 팩터 재평가/순간 재평가에 멈추지만 우리는 회사 pro-forma·시간 replay까지 내린다. A2가 더하는 *진짜 신규* = **임의/다중 사용자 충격 주입 UX**(유가+20%·금리+100bp 자유 주입)인데, 이것은 미검증 magic-constant β(`SECTOR_ELASTICITY` 35키 inline·seed/CI 0, WACC×0.5 하드코딩 `transfer.py:111-127`)를 *침묵 증폭*한다. 따라서 이 신규 부분은 위 write-end 게이트(DriverRegistry pooled-β admission 라이브) + warning 실배선 *후로* defer한다. 그 전까지 모든 충격 결과에 강제: ⓐ provenance `elasticity_prior_unvalidated`·`default:no-sector`/`default:no-wacc` 접두, ⓑ `SimulationResult.warnings`에 `sector elasticity defaulted — approximation(honest-gap)`(01 §5a footnote·§3 silent 값-대체 표면화 계약을 졸업 AC에서 **실배선**으로 승격), ⓒ 라벨은 `transfer`(전달) 고정(cause 금지, §2B.5 #1)·fan band 필수·scenario≠forecast·overlap penalty(§3.11, 다중충격 UX와 **동시 신설** 선결).

### 2B.3a DriverCard 자료구조 스펙 (형 수준 — admission.py/DriverRegistry 구현자용, 재조사 0)

위 프로즈 필드 목록을 형 수준으로 박는다(새 결정 0, 전부 §2B.2~2B.5에서 이미 정해진 타입):

```python
@dataclass(frozen=True)
class TransferSpec:
    leaf: str                # "calcMacroRegression"|"scanMacroBeta"|...
    lag: int                 # 0|1|2
    transform: str           # "level"|"yoy"|"diff"
    modifierRefs: tuple[str, ...] = ()  # R19 §2B.1 — 공시 실측 노출 metric VintageRef
                                        # (exportRatio·fixedCostRatio·netDebtToEquity)
                                        # 섹터 β 곱셈 modulate, 결손 시 ()=섹터 평균 그대로

@dataclass(frozen=True)
class Admission:
    state: Literal["candidate","dormant","active","retired"]
    nTrials: int             # G0 누적 distinct-trial (§2B.0)
    oosPartialR2: float | None
    adjustedTStat: float | None     # cluster-robust, 유효 time-DoF (§2B.1)
    selectionFreq: float | None     # G2 stability selection π
    eVBound: float | None           # G2 Meinshausen-Bühlmann E(V)
    sTotal: float | None            # G3/C Sobol S_T (데모 보정, OQ11)
    poolKey: str                    # 적합 풀(IndustryGroup or 승격 Sector, OQ2)

@dataclass(frozen=True)
class LiveScore:
    directionHitRate: float | None
    driftStat: float | None         # 채널A 점오차 drift: Page-Hinkley/ADWIN (G5)
    rollingCoverage: float | None   # R22 — 최근 k분기 명목-vs-경험 포함율(밴드 안에 든 실현 비율)
    pitDriftStat: float | None      # R22 — 채널B coverage drift 통계(rollingCoverage 90%밴드 이탈)
    lastCheckedAt: str              # vintage asOf

@dataclass(frozen=True)
class DriverCard:
    driverId: str
    sourceRef: str           # VintageRef
    axis: str                # exogenousAxes.axis — tier 는 여기서 파생(저장 안 함, OQ7)
    transferSpec: TransferSpec
    admission: Admission
    liveScore: LiveScore
    warnings: tuple[str, ...]       # "pooled_N_below_floor"·"elasticity_prior_unvalidated"·"revisedDataBias"
```
- **state 머신**: `candidate →(G0~G4)→ dormant ⇄ active →(G5)→ retired`. ★active 진입 선결 = write-end 라이브(§2B.3 dormant 상한).
- **tier 미저장**: `tier = "core" if axis in {6 exogenousAxes 문자열값} else "exploratory"`(파생, OQ7). `EXOGENOUS_AXES` 명명 상수 없음 → 파생집합(`{ind.axis for ind in indicators}`, exogenousAxes.py:461) 참조.
- **persist 스키마**: `data/models/driverPanel.json` = `{poolKey → {driverId → asdict(DriverCard)}}`. `loadDriverPanel`/`saveDriverPanel`(§2B.7) ↔ DATA_RELEASES `"models"`(09 §10.2 P9a). 입자도 = **per-sector(pooled grain) + 회사 override**(전사 복제 회피) — pooled transfer 가 섹터 공통이고 회사는 편차 라벨(§2B.1)이므로.

### 2B.4 수렴 3층 요약

- **A 입장:** earn-your-keep 게이트(2B.2). 후보가 늘수록 허들 √(ln N) 자동 상승. seed=`calcMacroRegression` top-k + `multipleTesting` + `forwardTest`(미배선 → admission이 결선).
- **B 차원 붕괴:** N 시리즈 → 6~8 축(Stock-Watson diffusion index). 새 데이터는 raw if가 아니라 축 loading. transfer 계수는 pooled 베타에서 **학습**(predictionSpace `3.0/2.0/1.5/0.5` 손튜닝 마법상수 교체), 축 *level 정의*는 curated 고정(folk-stat 회피). seed=`predictionSpace`(6축)+`exogenousAxes`(라우팅)+`shrinkage`(축 공분산 안정화).
- **C 민감도 가지치기:** Morris(스크리닝)→Sobol S_T(factor fixing)→tornado(노출 정렬). S_T≈0 driver는 토글 제거. shock 크기는 **학습 베타에서**(하드코딩 -5pp/-15% 교체). 다축 조합은 CIB로 self-consistent만. seed=`scenarioSensitivity`(3-shock+breakdownPoint)+`sensitivityAnalysis`(WACC×성장 격자).

### 2B.5 정직 경계 (잔존 거짓발견 + vintage 편향)

1. **입장 driver = 인과 아닌 검증된 통계적 연관.** 엣지는 "transfer(전달)"로만 라벨, "cause" 금지. scenario≠forecast 불가침(driver는 거시→기업 민감도만, 거시 미래경로는 preset).
2. **vintage 편향**(치명상 5): macro/gov는 latest-revised만(original 부재) → OOS R²가 **상방 편향**("가장 엄격"이 "가장 낙관"). 보정 = OOS 게이트 임계를 더 보수적으로 + 카드 `revisedDataBias` 플래그 강제 + 개정 적은 시리즈(FX·금리 > GDP) 우선.
3. **seed 정직 계상**(치명상 2·3·6, "6/7 기존" 폐기): 신설 = ① admission critical-t + 진짜 step-down Holm(haircutSharpe 재사용 불가 — `multipleTesting.py:88-92` Holm 브랜치가 `0.05/nTests`=Bonferroni byte-identical degenerate, 시그니처가 sharpe·일별obs라 partial-R²/t 직접 못 받음) ② participation-ratio effective-N `(Σλ)²/Σλ²`(numpy.linalg.eigvalsh, T-독립 — denoiseRMT는 `shrinkage.py:207` `T<=N` error라 단일회사 분기 사용 불가) ③ `scanMacroBeta` t-stat/SE 확장(`_invertMatrix4` 이미 (XtX)⁻¹ 계산, residual σ² 추가 — 단 ★N=3 df≤0 firm-level에선 t-stat 정의불가, pooled에서만 valid) ④ crossRegression/forwardTest pre-fit cron(dead 활성화 = 실build). 재사용 = predictionSpace 6축·scenarioSensitivity·scan 프리빌드·exogenousAxes 라우팅.
4. **★models HF dead chain — 다단 신설 작업(치명, "1줄" 과소평가 정정 2026-06-14)**: 실측: `_crossRegressionIo.py:16` `_MODEL_CACHE_DIR = Path.home()/.dartlab/models`(ephemeral), `savePanelModel`(**`:144` def**, `:187`은 mkdir 라인)→`~/.dartlab/models/panel_latest.json`. `core/dataConfig.py` DATA_RELEASES에 'models' 카테고리 **부재**(grep 0건 확인). **`recordForecast`는 src 전체에 존재하지 않음**(grep 0건 — `recordGrade`만 credit에 실재). ⟹ forward-test 루프는 **write 끝단이 통째 비어 있다.** "1줄 추가"는 *심각한 과소평가*(04 자체가 이를 '치명'으로 명시) — 실제 작업 4단:
   - **(a) DATA_RELEASES 'models' 카테고리 신설** `{"dir":"models","label":"driver pre-fit 적합 artifact","public":True}`("새 카테고리 = 한 줄" 메커니즘 정합 — *이 한 줄은 4단계 중 가장 작은 조각*).
   - **(b) `savePanelModel`/`saveDriverPanel`을 `data/models/`로 리다이렉트** + **`recordForecast` 함수 신설**(현재 부재 — OutcomeLog 박제 + actual 채점 stub). 둘 다 코드 신설이지 배선이 아니다.
   - **(c) 파이프라인 스테이지 + cron** — `prebuildData._uploadScan` 동형 `_uploadModels`로 HF push(driverPrefit step에 *반드시* 동반) + `driverDecay.yml`(분기, forwardTest persistence) 신설.
   - **(d) HF repo** — models 카테고리 repo 결정(panel repo 재사용 vs 신규).
   > 이 dead chain이 닫히기 전까지 **Brier-score 규율과 factor-zoo admit/retire 사이클은 강제 불가능한 주장**이다(01 §6.3 Brier·§2B.9 tier 가드의 write 의존). 100점 차단 항목.
5. **★credit/forwardTest persistence 비대칭(정정)**: '둘 다 동일 적재'는 틀림. `credit/monitoring/history.py:26 recordGrade`→`data/credit/history/{code}.json`(repo-relative, HF 배포 가능 — *cron만 부재*). `forwardTest.py:83 saveForecast`→`~/.dartlab/forward_tests/`(ephemeral). → forwardTest 출력도 `data/`(또는 HF)로 리다이렉트해야 driverDecay cron이 의미. recordGrade는 경로 OK·cron만 신설.

### 2B.6 거처·공개 계약

레지스트리·게이트 = `simulate/`(L2.5, 01 §0). 신설 2파일(`registry.py`·`admission.py`) + scanMacroBeta t-stat 확장 + 사전적합 cron. leaf(`calcMacroRegression`·`crossRegression.fitPanel`·`forwardTest`·`scenarioSensitivity`)는 호출. 별도 verb 없음 — `dartlab.simulate(...)` 하나에 흡수, 카드는 결과 provenance ref로 노출(public-contract-only). `ai/` 밖 순수 자료구조(no-graph-regression 면제), `*Graph/*Dag` 명명 금지, `_REGRESSION_KEYWORDS` 한국어 substring 회피. AI lens는 카드 transferSpec·축 라우팅을 *제안*, 백테스트·forwardTest가 *반증*(01 §6 det/ai 평행 = "AI 검증장치"). **본 §2B가 driver 수렴/확장의 SSOT — 01 §6은 게이트 공식·N 계상을 재서술하지 않고 여기를 포인터로만 참조**(SSOT 분열 차단, `feedback_always_check_clutter`).

### 2B.7 end-to-end 데이터 추가 배선 — 자동/수동 경계 (★운영자 핵심 요구)

신규 데이터(customs HS / gov 지수 / 뉴스) 1종 추가 시 정확한 호출 체인:

```
[수동 2곳, 미동기화] 운영자: ① source catalog(fred/catalog.py CATALOG 또는 ecos/catalog.py)에 CatalogEntry 1줄 — buildMacroData.buildFred/buildEcos 가 getAllEntries()/getAllIds()로 *실 fetch 하는 유일 소비처*. ② exogenousAxes.py(gather/mapping/, L1)에 ExogenousIndicator(seriesId, source, label, axis)+tier(라우팅 SSOT). 두 레지스트리는 코드상 미연결(자동 동기화 0) — exogenousAxes 에만 등록 시 gather 가 fetch 안 해 driverPrefit 이 빈 시리즈를 받는 silent 실패(실증: 현재 exogenousAxes fred-source 19개 중 14개가 fred 카탈로그 부재로 미수집). 코드 분기 0.
   ▼ (자동) gather cron 이 *catalog* 등록분을 raw parquet → HF push (기존 sync; exogenousAxes 미참조 — ①번 catalog 등록이 전제)
   ▼ (자동) dataPrebuild.yml 증분 → prebuildData.py → scan finance.parquet → _uploadScan → HF dart/scan/
   ▼ (자동) ★신설 step driverPrefit.py(.github/scripts/prebuild/, **주간 prebuild-full 경로만**=일 cron `0 17 * * 0`, 증분 prebuild-scan 아님 — OQ6: scanMacroBeta 연간 컬럼이라 분기 증분 재적합은 같은 design matrix 재계산 낭비; 입력=finance.parquet+macro 캐시 재사용):
         섹터별 CompanyFeatures 풀 → fitPanel → PanelModel → scanMacroBeta(t-stat 확장본, pooled에서만 valid t)
         → candidate DriverCard[] → admission.evaluateAll(G0~G4) → active/dormant(★write-end 라이브 전엔 dormant 상한, §2B.3)
         → saveDriverPanel(★data/models/, ~/.dartlab/ 아님) → _uploadModels → HF models/  [★DATA_RELEASES 'models' 1줄]
   ▼ (자동) 소비: simulate/registry.py loadDriverPanel()(HF resolve) → active 카드만 sheet 엣지
   ▼ (자동) ★신설 cron driverDecay.yml(분기, 실적 vintage 갱신):
         forwardTest.saveForecast(★data/로 리다이렉트) + evaluate(record, actual)
         + per-driver 오차 → DriverCard.liveScore + admission.decayGate(Page-Hinkley) → active⇄dormant⇄retired
         + credit.recordGrade도 동일 적재(경로 OK, cron만 신설)
   ▼ (수동, 예외만) 신축(neonatal axis): G3 routeAxis='neonatal' + 4게이트(IC+직교 corr<0.3+지속 2분기+pooled OOS) 통과 시 운영자가 _AXIS_ROUTE에 승인
```

**자동/수동 경계**: 자동 = gather sync·scan 프리빌드·driverPrefit·candidate 생성·admission 게이트·forwardTest decay(전부). 수동 = ① source catalog + exogenousAxes 2곳 등록+axis ② tier 지정 ③ 신축 승인(예외). 데이터 1종 = **2곳 수동 등록**(source catalog + 라우팅), 코드 *분기* 0개(admission 게이트·prefit 은 데이터 종류 무관 자동).

**6축 라우팅 SSOT 확정**: `ExogenousIndicator.axis`(commodity/production/demand/financial/domestic/fx — `gather/mapping/exogenousAxes.py:34`) = 라우팅 SSOT. predictionSpace 6축(businessCycle/interestRate/fxRate/commodity/sentiment/liquidity) = *소비 축*이라 별개 → `_AXIS_ROUTE: dict[str,str]` 매핑 신설(production/demand/domestic→businessCycle, financial→interestRate, fx→fxRate, commodity→commodity; sentiment/liquidity는 exogenous 미존재→preset 유지).

### 2B.8 수렴 증명 — if 상한이 시리즈 수와 독립 (Stock-Watson diffusion index)

**active edge 상한 = 검증된 축 수(6~8), 시리즈 수 N과 독립.** N개 외생 시리즈가 추가돼도 G3 routeAxis가 대부분을 6축 중 하나에 흡수(`absorb`) — 새 시리즈는 raw if가 아니라 *축 추가 loading*(diffusion index에 더 많은 관측 = 추정 정밀도↑, 차원↑ 아님). block 응축이 두 번째 안전판(customs HS 17→교역 block 1). 신축만 +1 차원인데 4게이트+수동 승인이라 통과율 극저 → **dN/d(시리즈)→0, active edge는 6~8에 점근.** 정직 경계: '축 정의 curated 고정' 전제 위에서만 성립(2B.4-B). 축을 데이터 주도로 자동 신설하면 folk-stat 재현(horizonMeaning 함정) → 신축만 4게이트+수동. ★단 k≤6 / 6~8축 수렴은 S_T 컷오프(§2B.11)가 held-out 데모서 보정된 *후에만* 닫힌 bound — 그 전까지 본 절은 proven bound 아닌 design target.

### 2B.9 tier 가드 강제 (folk-stat 차단 — requiredFix)

T<40 회사 단위 자유도 0 folk-stat 재현 차단: admission.py가 **tier 컨텍스트로 게이트 호출을 강제 분기**한다. `tier=="firmRefine"`에서 `stabilitySelection`(G2)·`purged walk-forward`(G1)·`criticalT`/`holmStepDown`(G1')·`participationRatio`(corr가 T=3~12 노이즈) 호출 시 **즉시 ValueError raise**(`pooled-panel only` 게이트). firmRefine은 leave-last-k holdout만. (horizonMeaning '확신오정렬>정렬실패' 재현 방지.)

### 2B.10 scanMacroBeta 스키마 회귀 가드 (requiredFix)

t-stat/SE 컬럼 추가는 **append-only** + `_emptyDf()`(macroBeta.py:393) 동반 갱신 강제. scan('macroBeta') 공개 소비처가 있으므로 기존 컬럼(gdpBeta/rateBeta/fxBeta/rSquared/nObs/confidence) *불변* + gdpTStat/rateTStat/fxTStat/stdErr append. `_emptyDf` 미갱신 시 스키마 불일치. ★firm-level은 N=3·df≤−1이라 t-stat 수학적 부재(§2B.1) — t-stat 컬럼은 **pooled-panel 산출분에만 채워지고 firm-level 행은 None**(honest-gap, 0/거짓 t 금지). **★pooled cluster-robust t 산출 위치 핀**: scanMacroBeta 자체엔 pooled 경로 없음(연간 firm-level only, macroBeta.py:113) → pooled t 는 `crossRegression.fitPanel`(within-estimator)에 Driscoll-Kraay/block SE(유효 time-DoF≈T)로 산출 후 stockCode/sector 머지로 scanMacroBeta 표 pooled 행에 채움(scanMacroBeta 에 새 pooled 분기 추가 아님 — fitPanel 산출분 머지). 모듈 경로(정확): `src/dartlab/quant/factor/multipleTesting.py`·`shrinkage.py`(analysis/valuation/ 아님), `src/dartlab/analysis/valuation/crossRegression.py`.

### 2B.11 작은 표본 규율의 수치화 + look-ahead 코드 강제 (requiredFix — 방법론 차단 항목)

작은 표본·look-ahead 규율이 *산문으로만* 존재하면 강제되지 않는다. admission.py·evaluateSheet 신설 시 다음 수치/코드 게이트를 박제한다(미정 시 방법론은 ≤8 천장):

> **★잠정값 경고:** 아래 여섯 수치(min-T 12·pooled-N 60·holdout-k 4·Sobol S_T 0.05·embargo window 1분기·purge gap = label horizon 2분기)는 *잠정값* — un-calibrated, seed/CI=0, 아직 discipline 보장이 아니다(졸업 데모서 held-out 재보정). 현 단계 = design target.

- **min-T (베타 사용 하한)**: 분기 기준 `T ≥ 12`(≈3년) 미만이면 회사별 베타 *사용 자체 금지* → pooled-panel transfer로 폴백(연간 컬럼 금지 — 연간이면 성장률 obs = N−1 = 3, df 음수, §2B.1). firm refine은 그 위에 *라벨*로만.
- **min pooled-N (횡단면 풀 하한)**: pooled-panel 적합은 `섹터 내 기업수 × 유효 분기 ≥ 60`(예: 기업 10 × 분기 6) 미만이면 카드 `admission.state=dormant` + `warnings=["pooled_N_below_floor"]`. ✅ **풀 경계 규칙(OQ2 결정)**: IndustryGroup(sub-sector) 기본 → pooled-N<60 이면 부모 WICS-11 Sector 승격 → 여전히 <60 이면 DEFAULT_ELASTICITY+warnings(`_resolveSectorKey`(_valuationHelpers.py:55) 2층 구조 재사용, 새 코드 0). 경계 *임계값*만 데모(IG풀 vs 승격이 leave-last-k=4 OOS partial-R²로 갈리는 지점, 04 §5 OQ2). 단 pooled-N≥60 은 *기업-수준 응답 이질성*의 하한일 뿐 — macro-β t-stat 의 자유도는 pooled-N 이 아니라 유효 time-DoF(≈T)를 쓴다(common-shock 독립관측 ≈T, §2B.1).
- **holdout-k (leave-last-k)**: firm refine OOS = `leave-last-k, k=4분기`(최근 1년 홀드아웃). pooled OOS = purged+embargoed walk-forward(§2B.2 G1). full-sample parameter selection 금지(03 §4.3).
- **embargo window + purge gap (walk-forward leakage 차단, 잠정값)**: pooled purged walk-forward는 train/test 경계에서 *두 종류*의 leakage를 막는다 — ⓐ **purge gap = label horizon(2분기 잠정값)**: train 끝과 test 시작 사이에 label horizon만큼 분기를 *제거*(label이 미래 2분기를 보므로 train 마지막 label이 test 구간을 들여다보는 누수 차단), ⓑ **embargo window = 1분기(잠정값)**: test 직후 1분기를 다음 train fold에서 *제외*(serial-correlation 잔류 누수 차단). 두 값 전부 held-out 재보정 라벨. 시그니처(09 §10.3 admission primitive와 형제, walk-forward 파라미터화만 — deflatedSharpe/pbo primitive 시그니처는 09 담당):
  ```python
  def purgedWalkForwardFolds(timeIndex, *, nFolds, embargoQuarters=1, purgeQuarters) -> tuple[tuple[Idx, Idx], ...]
  ```
  (`purgeQuarters` = label horizon 주입, 기본값 미부여 = 호출자가 horizon 명시 강제. 반환 = fold별 `(trainIdx, testIdx)` — test 직전 `purgeQuarters` 제거 + test 직후 `embargoQuarters` 제외.)
- **Sobol S_T 컷오프(OQ11)**: factor admission/격자 토글 유지 임계 = `S_T ≥ 0.05`(총효과 5% 미만 driver는 토글 제거 → k≤6 보장, 01 §13b). 데모 전 잠정값, 졸업에서 재보정.
- **look-ahead 코드 강제 — 3표면 완성(admission.py/walk-forward 순수 가드, Company 생성 0, R18b)**: 규칙은 03 §3에 있으나 *코드 단언이 없다*. firm financial vintage assert 1표면만으로는 universe/param leakage를 못 막는다 → 다음 *3표면* 모두에 assert를 박는다(전부 import-only·numpy·Company 0줄 = 09 §6 형제 패턴, Polars-OOM 안전):
  - **(표면 1, 기존) firm financial vintage assert**: replay 모드 진입 시 `buildSnapshot`의 asOf 라벨이 모든 NodeValue.asOf로 전파(이미 구현)되고 `admission`/`buildSnapshot`이 `availableAt <= decisionAt` *assert*를 거는 가드 신설(현 `entry.py`/`registry.py`는 asOf 라벨만 들고 assert 부재).
  - **(표면 2, 신규) universe as-of assert**: walk-forward fold의 `decisionAt`에 *그 시점 멤버십*만 포함한다 — `listing.asOf(decisionAt)` membership 단언(상장폐지사도 그 시점까지는 포함 = **survivor-only 금지**, 03 §4.2 #5·#6 survivorship 가드의 코드 강제). ★코드 실측: 현 `dartlab.listing()`(`_listingDispatch.py:34`)은 **as-of 인자 부재**(현재 멤버십만 반환, `**kw` 패스스루) — survivor-only가 *구조적으로* 위험. 정공법 = listing에 as-of 표면 추가(survivor-only fallback 금지) 또는 fold 구성 시 그 시점 가용 universe parquet vintage 직독. as-of 도달 전엔 walk-forward `survivor-only(blocked)` 라벨 강제(침묵 진행 금지).
  - **(표면 3, 신규) param-selection 격리 assert**: fold의 *train 내부서만* param을 선택한다 — 선택에 쓴 `timeIndex ⊆ train idx` 단언, full-sample 선택을 detect하면 `ValueError`(03 §4.3 "full-sample parameter selection 금지"의 코드 강제·§2B.11 holdout-k full-sample 금지와 정합). `purgedWalkForwardFolds`(위 holdout-k 시그니처)가 반환한 `trainIdx`만 param 후보 timeIndex로 허용.
  - 신호→체결 = `t종가 → t+1시가` 매핑은 backtest 경로(suite/03)에서 강제.
- **held-out 졸업 acceptance threshold (전부 재보정 라벨, R15-b)**: DriverRegistry가 `design`에서 *본진 active*로 승격하려면 단일 섹터 held-out 데모가 다음을 *전부* 통과해야 한다(하나라도 미달 = `DriverCard` dormant 상한 + 발간 BLOCKED, §2B.3 write-end dormant 상한과 동형). 전부 *잠정값* — 졸업 데모서 재보정, 현 단계 design target:
  - **direction Brier < 0.25**(driver→방향 적중의 사후채점, 무정보 0.25 기준 — recordForecast write-end 라이브 후에만 측정 가능, §2B.5 #4).
  - **calibration MAE < 0.1**(예측 신뢰도 vs 실현 빈도 정합, horizonMeaning folk-stat 교훈: CI0 금지).
  - **DSR > 0 & PBO < 0.5**(deflated Sharpe 양수 + probability of backtest overfit 절반 미만 — 05 §5 walk-forward·09 admission primitive).
  - **seed × 3 CI 부호 안정**(3 seed 재실행서 β/방향 부호 불변 — horizonMeaning seed0 금지의 직접 대응, "확신오정렬 > 정렬실패" 차단).

---

### 2B.12 Proof-of-Method 졸업 게이트 (design→proven 단일 분기점, R15)

DriverRegistry pooled-panel transfer가 *세계수준 방법*이라는 주장은 held-out 데모 전까지 미검증이다(8b "design target → proven wedge 승격 단일 분기점"). 본 절은 그 분기점을 *게이트 순서*로 박는다 — 통과 전엔 DriverRegistry가 `design` 라벨이고 `rev.path`는 fallback 경로만 쓴다.

**(a) 단일 섹터 held-out 데모 게이트 (DriverRegistry 본진 졸업 선결)**

DriverRegistry를 `src/dartlab/simulate/registry.py` active 경로로 졸업시키기 *전에*, 단일 섹터(반도체 또는 화학 — pooled-N≥60 충족 가능성 高)에서 held-out 데모를 통과해야 한다:

- **pooled-panel β가 leave-last-4Q OOS에서 GDP-beta 단순모델 대비 partial-R² 개선**(개선 없으면 pooled-panel transfer가 단순 1-beta보다 나을 근거 0 → §2C volume/price fallback과 동급으로 강등).
- **S_T 가지치기 k≤6 수렴**(§2B.8 design target이 데모서 실제로 닫히는지 — Sobol S_T 컷오프 §2B.11이 보정된 후의 실측 k).
- **잠정 4수치(min-T 12·pooled-N 60·holdout-k 4·S_T 0.05) 재보정**(데모 실측으로 design target → proven 승격).

통과 전 상태: **DriverRegistry `state='design'`**, `rev.path`(`_fnRevPath`)는 `SECTOR_ELASTICITY` + provenance `elasticity_prior_unvalidated` 경고만(09 §10.4 fxChangePct transfer baseline 경로) — pooled-β active 승격 0. 즉 §2B.3 "write-end 라이브 전 dormant 상한"과 *직교*하는 두 번째 선결: write-end는 *시간축 decay* 게이트, 본 데모는 *방법 자체의 OOS 우월성* 게이트. 둘 다 통과해야 active.

**(b) held-out acceptance threshold (§2B.11에 박음)**

위 (a)의 통과/미달 판정 기준 = §2B.11 말미 'held-out 졸업 acceptance threshold' 4항(direction Brier<0.25·calibration MAE<0.1·DSR>0&PBO<0.5·seed×3 CI 부호안정). 하나라도 미달 = **DriverCard dormant 상한 + 발간 BLOCKED**(03 §9.3 A7 공개 리더보드 dormant 상한·05 §3 fan σ 점선 강등과 동형). 본 절은 그 threshold를 졸업 게이트의 *합격선*으로 결선한다(SSOT = §2B.11, 본 절은 포인터).

**(c) write-end = 졸업 게이트 0번 (§2B.5 #4 승격)**

§2B.5 item 4의 *models HF dead chain*(recordForecast 신설 + forwardTest `data/` 리다이렉트 + driverDecay cron, 09 §10.2 P9)을 **본 졸업 게이트의 0번 단계로 승격**한다 — (a) held-out 데모는 *write-end가 라이브여야* direction Brier·calibration·seed CI를 측정할 저장소(ForwardTestRecord/recordForecast, 09 §10.2 P9c)가 생기기 때문이다. 게이트 순서:

```
게이트 0 (write-end 라이브)  → 게이트 (a) held-out 데모  → (b) threshold 합격  → DriverRegistry active 졸업
   §2B.5 #4 / 09 P9              단일 섹터 OOS                §2B.11 4수치              본진 registry.py
```

게이트 0이 닫히기 전엔 (a)~(b)가 *강제 불가능한 주장*(09 §10.2 "Brier 규율은 강제 불가")이라, write-end를 0번으로 못 박는 것이 100점 차단 항목의 정직 인정이다.

---

## 2C. Driver Coverage Census — 정직 천장 (비전↔가용 거리, 새 추출능력 약속 0)

00 §5.3 Business Driver Bridge는 11 driver(volume/price/mix/fx/backlog/capacity/rawMaterial/labor/logistics/rnd/depreciation, §2.6 `BusinessDriverEstimate.driver` enum)가 *모두* 이벤트→손익으로 전파되는 비전을 그린다. 그러나 driver별 *결정론 추출 경로*의 실제 coverage는 driver마다 천차만별이고, 어떤 driver는 경로 자체가 부재다. 이 거리를 숨기면 8b의 "텍스트→driver 매핑 커버리지 미실증"(가장 큰 위협 ①)이 침묵 낙관으로 재현된다. 본 절은 그 거리를 *행 단위로 박제*하고, coverage<임계면 시뮬레이션이 스스로 'honest-gap'을 외치게 계약한다. **새 driver 추출 능력 약속 0 — 가진 능력의 천장을 정직 표면화할 뿐**(메모리 segmentRnd 2/10·incomeExpense 66.9% 천장과 동형).

### 2C.1 Census 표 (★실측치 = 잠정값, 본진 졸업 데모서 KOSPI200 전수 재측정)

> **★coverage% 잠정 경고:** 아래 coverage%는 `tests/_attempts`(segmentRnd·incomeExpense) 소표본 실측에서 *유추*한 잠정값이다 — KOSPI200 전수가 아니고 held-out 검증도 0. 졸업 데모서 KOSPI200 실측으로 재보정한 *후에만* proven. 현 단계 = design target + 능력 천장의 정직 라벨.

| driver | 추출 leaf (코드 정본) | 데이터 소스 (주석/사업보고서 섹션/XBRL 태그) | KOSPI200 coverage% (잠정) | 결손 fallback | 라벨 |
|---|---|---|---|---|---|
| volume | (경로 부재 — 분해 leaf 0) | 사업보고서 "생산·판매 실적" 표(비정형, XBRL 미태깅) | **0%** | 섹터 1-beta GDP 근사(매출성장 통째) | `blocked` — volume/price 분해 불가 |
| price (ASP) | (경로 부재 — 분해 leaf 0) | 동상, ASP는 회사별 표기 비표준 | **0%** | 섹터 1-beta 근사 | `blocked` — volume/price 분해 불가 |
| mix | `_noteCellsFromPanel("NT_D871100")`(세그먼트 주석, `_revenueSelect.py`) | 영업부문 주석(IFRS 8), XBRL `NT_D871100` | **2/10 ≈ 20%**(segmentRnd 실측 — 축-태깅 vs 행-라벨 인코딩이 가름) | 회사 전체 proxy(세그먼트 없음 라벨) | `partial` — XBRL 인코딩 의존 |
| fx | `transfer.py` fxChangePct(`:114`) + 거시 transfer | 환율 거시 시리즈(gather) + 노출 metric(공시 exportRatio) | **노출 metric 결손 시 섹터 평균**(§2B.1 β 이질성) | 섹터 평균 pass-through(회사 노출 미식별 라벨) | `partial` — 노출 metric 결손 시 direction-unknown 위험(§3.5) |
| backlog | 수주잔고 공시(수주 계약 체결/변경) | 단일판매·공급계약 공시(rceptNo) + 정기보고서 backlog 표 | 업종 편중(조선·플랜트 高, 소비재 0) | backlog 항목 없음 라벨 | `partial` — 업종 의존 |
| capacity | 사업보고서 "생산능력·가동률" 표 | 정기보고서 비정형 표(XBRL 미태깅) | 낮음(가동률 숫자 자체 결손 多) | 상한 미적용 라벨 | `partial` — 비정형 표 파싱 |
| rawMaterial | 비용성격별 주석 Tier1(원재료비) | 비용성격 주석(IFRS) + 사업보고서 "주요 원재료" | **Tier1 ≈ 53.4%**(incomeExpense 판관비명세 도달) | CF 비현금 Tier2(13.5%) → ratio Tier3(blocked) | `partial`/`blocked` — tier별(§3.8) |
| labor | 비용성격별 주석 Tier1(인건비/급여) | 동상 비용성격 주석 | Tier1 ≈ 53.4%(rawMaterial 동반) | Tier2/Tier3 강등 | `partial`/`blocked` — tier별 |
| logistics | 비용성격별 주석 Tier1(운반비) | 동상 | Tier1 부분(운반비 별도 표기 회사만) | Tier2/Tier3 강등 | `partial` |
| rnd | 2-tier: IS `select`(연구개발비) → SG&A 주석 `NT_D834310` | IS 본문 + R&D 주석(XBRL `NT_D834310`) | **6/10 ≈ 60%**(segmentRnd 실측) | IS 본문만(주석 결손 라벨) | `partial` — 2-tier |
| depreciation | CF 비현금 가산 + 비용성격 주석 | CF 본문(감가상각비 가산) + 주석 | 비교적 높음(CF 본문 표준) | 주석 결손 시 CF만 | `partial` |

### 2C.2 driverCoverage 표면화 계약 (SimulationResult.warnings 동일 채널)

위 census를 *런타임에 강제*한다 — `rev.path`(`_fnRevPath`, registry.py)/`transfer`(transferRevenuePath) 노드 결과에 **`driverCoverage` 필드**(= `(분해 성공 driver 수) / (시도 driver 수)`)를 부착하고, 이를 `SimulationResult.warnings` *동일 채널*로 표면화한다(별도 채널 신설 0 — run.py:100 `warnings: tuple[str,...]` + :227·229 honest-gap 패턴 재사용, "결손 0 대체 없음" §3 silent 값-대체 표면화 계약과 정합).

- coverage가 driver별 임계 미만이면 `SimulationResult.warnings`에 **`segment/mix 분해 불가 — 섹터 1-beta 근사(honest-gap)`**(또는 해당 driver의 census 라벨)를 *강제 append*. base revenue absent / shares unavailable honest-gap(run.py:227·229)과 동형 메시지 규약.
- volume/price처럼 coverage 0%(경로 부재) driver는 분해를 *시도조차 안 하고* 매출성장을 통째로 섹터 1-beta 근사로 폴백 — provenance `default:no-volume-price-split`. 이는 "volume과 price를 합쳐서 하나의 성장률로만 두지 않는다"(§3.7 주의)의 *능력 한계* 정직 라벨이지 규칙 폐기가 아니다(분해 가능한 회사는 여전히 분리).
- `driverCoverage` 필드 추가는 §2B.10 scanMacroBeta 가드와 동형 **append-only**(기존 SimulationResult 9필드 불변 + driverCoverage append) — 09 §0 표 #4 `transferRevenuePath` 3-tuple arity 동결(`test_simulate_leaf_binding`)을 깨지 않도록, driverCoverage는 transfer 노드의 *반환 tuple 확장이 아니라* registry 노드가 NodeValue provenance로 부착(arity 불변).

### 2C.3 정직 경계 (능력 천장 ≠ 설계 갭)

- **새 추출 능력 약속 0.** 본 절은 volume/price 분해 leaf를 *신설하겠다는 약속이 아니다* — 그 경로는 데이터(비정형 생산·판매 실적 표)가 막혀 있고(segmentRnd 2/10·incomeExpense 66.9% 천장이 같은 데이터-부재 벽), 약속하면 8b honest caution("새로움≠검증")의 재현이다. coverage%를 *정직 표면화*하는 것이 산물이지 coverage%를 *올리는* 것이 본 절 약속이 아니다.
- coverage 천장은 **SYSTEM(데이터 도달) 한계지 PLAN(설계) 갭이 아니다**(09 §10 축 분리와 동형) — census 표가 닫혀 있으면 설계는 완전하고, coverage%는 데이터 진행률로만 추적한다.
- driver coverage가 낮다고 시뮬을 *차단*하지 않는다 — fallback(섹터 1-beta·회사 proxy)으로 *계속하되 honest-gap 라벨*. 차단은 base revenue/shares 같은 척추 결손(blocked status, 05 §7)에 한정.

---

## 3. 미세 절차

### 3.1 Step 0. 실행 의도 고정

1. mode를 선택한다(정본 enum = replay/walkforward/whatif).
   - replay (과거 시점 복원).
   - walkforward (fold 학습·검증).
   - whatif (미래 가정).
2. target을 확정한다.
3. horizon을 확정한다.
4. currency와 market을 확정한다.
5. 기준 가격을 확정한다.
6. `asOf` 또는 `decisionAt`을 확정한다.
7. 실행 목적을 기록한다.
   - 실적 민감도.
   - 이벤트 영향.
   - macro scenario.
   - valuation sanity.
   - 과거 검증.

산출물:

- `ScenarioSpec` draft.
- `RunSpec` draft.

### 3.2 Step 1. 데이터 vintage freeze

1. 재무제표 latest period를 고정한다.
2. 공시 접수일과 사용 가능일을 고정한다.
3. 뉴스 firstSeenAt과 ingestedAt을 고정한다.
4. 가격 기준일과 거래 가능일을 고정한다.
5. macro 지표의 observation date, release date, revision policy를 고정한다.
6. 산업/peer 데이터 기준일을 고정한다.
7. 각 데이터에 `VintageRef`를 붙인다.

차단 조건:

- historical replay에서 `availableAt > decisionAt`.
- latest revised macro를 과거 시점에 사용.
- 재무제표 공시 전 수치를 사용.
- 뉴스가 실제 ingestion 전인데 사용.

### 3.3 Step 2. baseline snapshot

1. IS에서 revenue, COGS, SG&A, operating income, net income을 읽는다.
2. BS에서 cash, debt, receivables, inventory, payables, equity를 읽는다.
3. CF에서 CFO, capex, FCF proxy를 읽는다.
4. ratios에서 margin, leverage, turnover, cash conversion을 읽는다.
5. price에서 current price, market cap, shares, liquidity를 읽는다.
6. valuation baseline을 읽는다.
7. industryBadge, dcrBadge, peer context를 붙인다.

산출물:

- `BaseFinancialSnapshot`.
- `BaseMarketSnapshot`.
- `BaseQualityFlags`.

### 3.4 Step 3. environment snapshot

1. macro regime을 판정한다.
2. rates, FX, liquidity, inflation, credit spread를 수집한다.
3. sector index와 peer return을 수집한다.
4. factor exposure 후보를 수집한다.
5. 뉴스 압력을 계산한다.
   - event velocity.
   - source breadth.
   - firstSeenAt.
   - disclosure alignment.
   - price lead/news lead.
6. 회사의 macro sensitivity를 불러온다.
7. macro scenario override가 있으면 명시적으로 적용한다.

산출물:

- `EnvironmentSnapshot`.
- `MacroShockVector`.
- `EventPressure`.

### 3.5 Step 4. 이벤트 정규화

1. 공시, 뉴스, 지표, 가격 움직임, 산업 변화를 후보 event로 모은다.
2. 중복 event를 합친다.
3. 각 event에 `factStatus`를 붙인다.
4. event가 닿는 driver를 제안한다.
5. AI가 event 해석을 보조하되, 숫자와 결론은 ref 기반으로 검증한다.

예:

- 원달러 환율 상승: `fx`, `price`, `cogs`, `wacc`.
- 신규 수주 공시: `backlog`, `volume`, `capacity`, `workingCapital`.
- 원재료 가격 하락: `cogs`, `grossMargin`, `inventory`.
- 금리 하락: `wacc`, `multiple`, `interestExpense`.

**★driver 매핑 부호는 회사 노출이 결정한다 (event→driver는 후보집합만, R19):**

위 예의 `이벤트 → driver` 매핑은 *부호·크기를 확정하지 않는다* — 결정론으로 제안하는 것은 **후보 driver 집합**(어디에 닿는가)뿐이고, *부호와 크기*는 회사의 공시 실측 노출 metric에서 파생한다(§2B.1 modifier·DriverCard.transferSpec.modifierRefs).

- 예: "원달러 환율 상승 → `fx` driver"는 후보 집합 제안이다. 부호는 회사 노출이 가른다 — 수출 비중 高(`exportRatio` 큰) 회사면 호재 방향, 원재료 수입 비중 高면 마진 악화 방향. **노출 metric이 결손이면 `direction-unknown` 라벨**(부호 미확정) — "fx상승=호재"식 *고정 부호 오매핑*을 교정한다(03 §7.3 DisagreementLedger 예 "Macro lens는 환율 상승을 매출 긍정으로 보지만 Accounting lens는 원재료 수입 비중 때문에 마진 악화 경고"의 결정론 토대).
- 즉 event→driver 후보집합 = 결정론 제안(부호 0), driver 부호·크기 = 노출 metric 파생(modifier), 둘 다 결손이면 `direction-unknown(partial)`. AI는 이 후보집합·부호를 *해석*하되 새 부호를 만들지 않는다(00 §3 원칙 5).

산출물:

- `BusinessChangeEvent[]`.

### 3.6 Step 5. 가정 장부 작성

1. 사용자 가정을 row로 만든다.
2. engine이 제안한 가정을 row로 만든다.
3. AI가 제안한 가정은 `source=ai`, `status=hypothesis`로만 둔다.
4. 각 가정의 단위, 기간, 범위, evidence, falsifier를 채운다.
5. 가정 간 dependency를 연결한다.
6. 중복 또는 충돌 가정을 찾는다.

차단 조건:

- 단위 없는 숫자.
- 기간 없는 성장률.
- ref 없는 fact 주장.
- 반증 조건 없는 핵심 가정.

산출물:

- `AssumptionLedger`.
- `DisagreementLedger` 초기 row.

### 3.7 Step 6. 매출 bridge

1. base revenue를 고정한다.
2. segment별 historical revenue를 읽는다.
3. volume driver를 적용한다.
4. price driver를 적용한다.
5. mix driver를 적용한다.
6. FX translation과 transaction exposure를 분리한다.
7. backlog가 있으면 매출 전환률을 적용한다.
8. capacity constraint가 있으면 상한을 적용한다.
9. channel/customer concentration이 있으면 집중도 risk를 붙인다.
10. revenue scenario를 bear/base/bull로 만든다.

기본 식:

```text
projectedRevenue
= baseRevenue
  * (1 + volumeDelta)
  * (1 + priceDelta)
  * (1 + mixDelta)
  * (1 + fxTranslationDelta)
  + backlogConversionImpact
  + newBusinessImpact
```

주의:

- volume과 price를 합쳐서 하나의 성장률로만 두지 않는다.
- 세그먼트 데이터가 부족하면 회사 전체 proxy와 산업 proxy를 구분한다.
- 매출 증가가 매출채권과 재고 증가로만 나타나면 cash quality flag를 붙인다.

**★quality-adjusted revenue prior(과거 매출성장을 미래 volume prior로 쓰기 전 신뢰도 강등):**

과거 매출성장이 *진짜 수요*가 아니라 채널 밀어내기·외상 확대로 만들어졌으면(receivable-led growth), 그 성장률을 미래 volume prior로 그대로 쓰면 안 된다. 강제:

- baseline `receivable growth − revenue growth > 10pp`(잠정 임계, 졸업 재보정 — 03 §5.3 "매출보다 매출채권이 훨씬 빠르게 증가" 경고와 동일 metric)면, **과거 매출성장을 미래 volume prior로 쓸 때 신뢰도를 강등**한다 + **fan σ를 확대**(under-dispersion 방지 — §2B.11 잠정 σ는 검증된 σ만 승격이므로, 여기 확대는 *보수적 확대*지 사후적합 아님, §2B.5 #2 vintage 편향 보정 정신과 정합).
- 강등은 `provenance='revenue_prior_quality_adjusted'` + `SimulationResult.warnings`에 `receivable-led growth — volume prior downweighted, fan widened` append.
- 이 metric은 이미 03 §5.3 Revenue Quality·00 §4.3 Phase 4 완료 기준("receivable growth minus revenue growth가 표시된다")에 있는 결정론 지표 재사용 — 새 leaf 0.

**★회계품질 forensic 신호 → fan σ *하방 비대칭* 전파 (FQ2 결선 — quality.baseline 노드 ↔ mc.distribution σ):**

위 receivable-led growth 는 fan σ 를 *대칭* 확대하나, 회계품질 적신호의 본질은 **하방 위험**이다(과대계상된 이익은 *아래로* 정정되지 위로 가지 않는다 — Sloan accrual anomaly). 따라서 quality.baseline 노드(01 §5b·09 §0 #7~8 `scanQuality`·`buildEvidenceForensicsMemo`)의 forensic flag 가 fan σ 를 *어느 방향으로* 키우는지 명시한다(elasticity 미검증엔 경고 전파하면서 회계 적신호엔 채널 미부여였던 비대칭 해소):

- **트리거**: `quality.baseline` 의 `accrualRatio`(Sloan 발생액)·`cfToNi`(현금전환)가 **섹터 하위 분위**(예: accrualRatio 상위 quintile = 고발생액, cfToNi 하위 quintile = 저현금전환)면 저품질 이익으로 판정.
- **비대칭 σ 가중(모수 연극 회피 — empirical-quantile 위 가중)**: mc.distribution(01 §5b R12) 의 *하방 분위(P5/P25)만* 추가 확대, **상방 분위(P75/P95)는 불변**. 가우시안 σ 한 스칼라를 키우는 대칭 확대(대칭 = 상방 위험도 같이 키워 비현실적)가 아니라 — held-out 잔차의 *하방 꼬리만* 재가중하는 비대칭 분위 가중(01 §5b R12 empirical-quantile 분포라 분위별 가중이 자연). 펀더멘털 하방 truncation·마진 floor 의 비대칭(01 §5b R12-(2) 영업레버리지 하방꼬리 empirical-quantile)과 같은 메커니즘.
- **provenance·warnings**: `provenance='downside_skew_low_earnings_quality'` + `SimulationResult.warnings` 에 `low earnings quality (accrual/cfToNi) — downside fan widened`(§2C.2 driverCoverage·R9 receivable-led 와 *동일 채널*, 03 §5 producer-leaf 매트릭스 G8 결선).
- **silent 사후적합 금지**: 하방 확대 폭도 §2B.11 acceptance threshold 를 통과한 **held-out 검증 σ만 승격**(§2B.2 G5 silent 확대 금지·§3.7 검증 σ만 정신과 정합) — "회계 나쁘니 막연히 더 넓힌다"는 임의 상수 금지, 하방 가중 크기는 저품질 섹터의 *실현 하방 오차*로 보정한다(잠정값, 졸업 데모서 재보정).
- **결손 처리**: accrualRatio·cfToNi 산출 입력 결손이면 가중 적용 안 함 + `status='partial'`(0 대체 금지, 무근거 확대 금지). 회계품질 측정=결정론 quality.baseline 노드, AI Accounting lens=해석·반증만(§3.13·§2.7 역할분리 일관 — AI 가 σ 를 못 키움).
- **거처**: 본 비대칭 전파는 mc.distribution(01 §5b 후속) 합류 시 와이어링하는 *설계*다 — quality.baseline 노드 미구현이라 현 4노드 코어엔 미배선(planScore 직결, write-end·노드 졸업 후 active).

### 3.8 Step 7. 비용과 영업이익 bridge

1. COGS ratio baseline을 고정한다.
2. SG&A ratio baseline을 고정한다.
3. 고정비와 변동비를 가능한 범위에서 분리한다.
4. raw material, labor, logistics, depreciation, R&D, marketing driver를 적용한다.
5. 매출 변화에 따른 operating leverage를 적용한다.
6. one-off 비용과 recurring 비용을 분리한다.
7. 영업이익과 영업이익률을 계산한다.

기본 식:

```text
grossProfit = revenue - costOfSales
operatingIncome = grossProfit - sga
operatingMargin = operatingIncome / revenue
```

driver 식:

```text
costOfSales
= revenue * baseCogsRatio
  + rawMaterialImpact
  + logisticsImpact
  + laborImpact
  + fxCostImpact
  + inventoryValuationImpact
```

```text
sga
= baseFixedSga
  + revenue * variableSgaRatio
  + rndImpact
  + marketingImpact
  + allowanceImpact
```

주의:

- 비용성격별 주석이 없으면 `partial`로 둔다.
- 감가상각은 현금비용이 아니지만 영업이익에는 영향을 준다.
- R&D는 비용 처리와 자본화 여부를 AI 회계 lens가 검토한다.

**★base margin 정규화 게이트(시나리오 base가 one-off에서 출발하는 것 차단):**

시나리오 base의 마진이 *직전 분기 우연한 one-off*(일회성 충당금·재고평가손·소송비·자산처분익)에서 출발하면 전체 fan이 잘못된 닻에 매인다. 강제 절차:

1. **일탈 탐지**: baseline operating/gross margin이 직전 `N분기 median ± 2σ`(N=8 잠정값, 졸업 데모서 재보정)를 벗어나면 `one-off 의심 flag`를 단다. median·σ는 기존 `core/ratios`(마진 시계열) + `analysis/financial/insight/_earningsQualityCalcs`(이익품질 시계열)에서 *결정론 도출* — **새 leaf 0**(이미 마진 시계열 산출하는 함수 재사용, §4 "기존 함수 재사용" 정합).
2. **정규화 base 강제**: flag가 서면 시나리오 base를 직전 median(또는 one-off 제거 normalized margin)에서 출발하도록 강제한다. one-off가 든 분기 그대로 base로 쓰지 않는다.
3. **불가 시 정직 라벨**: 시계열이 짧아(분기 < N) median/σ 산출 불가면 정규화 못 함 → `provenance='margin_baseline_unnormalized(partial)'` + `SimulationResult.warnings`에 `margin baseline not normalized — one-off risk(partial)` append(§2C.2 driverCoverage와 동일 채널). 침묵 진행 금지.

**★COGS 분해 가용 tier 명시(원재료/인건비 토글의 능력 한계):**

§2C.1 census의 rawMaterial/labor/logistics가 손익 bridge에서 *어느 tier*로 들어오는지 명시한다(토글 활성화 게이트):

- **Tier1 — 비용성격별 주석(≈ 53.4%, incomeExpense 실측 잠정값)**: 원재료비·인건비·운반비를 주석에서 직접 읽음 → 원재료/인건비 driver 토글 *활성*.
- **Tier2 — CF 비현금 가산(+13.5%, 누적 ≈ 66.9% 천장)**: 비용성격 주석 결손 시 CF에서 감가상각 등 비현금만 분리 → 부분 토글(원재료/인건비 직접 분해 불가, 라벨).
- **Tier3 — ratio만(blocked)**: 주석·CF 모두 결손 시 COGS ratio만 → **원재료/인건비 driver 토글 비활성화 + `cogs decomposition unavailable — ratio only(blocked)` 라벨**. Tier3에서 원재료 토글을 활성으로 보여주면 능력 없는 분해를 약속하는 침묵 낙관(8b honest caution).

### 3.9 Step 8. 3-statement와 FCF bridge

1. operating income에서 tax를 적용해 NOPAT을 만든다.
2. depreciation, amortization을 더한다.
3. capex를 뺀다.
4. working capital delta를 반영한다.
5. CFO 기반 FCF와 NOPAT 기반 FCFF를 대조한다.
6. 차이가 크면 cash conversion flag를 붙인다.

기본 식:

```text
nopat = operatingIncome * (1 - taxRate)
reinvestment = capex + deltaNwc
fcff = nopat - reinvestment
```

대조 식:

```text
fcfProxy = cfo - capex
cashConversionGap = fcff - fcfProxy
```

주의:

- BS는 stock, IS/CF는 flow다.
- 분기와 연간을 섞으면 안 된다.
- YTD와 Q를 혼동하면 gate 실패다.

**★baseline vs projected 회계품질 구분 (cashConversionGap forensic 판정의 적용 범위, R17):**

`cashConversionGap = fcff - fcfProxy`(위 대조 식)의 *forensic 해석*은 단면마다 의미가 다르다 — 이 구분을 라벨로 강제하지 않으면 projected 단면의 항등식 잔차를 회계 부정 신호로 오독한다.

- **baseline actual 단면 = forensic valid**: 실제 공시 CFO와 NI/FCFF의 괴리는 진짜 회계품질 신호다(03 §5.3 "CFO가 순이익을 따라오지 못함"·09 §0 #6 Sloan/Beneish forensic). 여기서만 cashConversionGap을 *forensic 판정*으로 쓴다.
- **projected 단면 = forensic 신호 아님 (provenance/warnings 강제)**: `buildProforma`의 projected CFO는 **cash-plug 산물**이다 — proforma는 CFO를 직접 추정하지 않고 항등식(BS·IS·CF 닫힘)으로 *역산*한다(코드 실측: `_proformaCore.py`에 CFO 직접 산출 0). 따라서 projected `cashConversionGap`은 cash-plug가 CFO를 항등식으로 강제해 **신호가 죽는다**(0에 수렴하거나 plug 잔차만 반영). projected 단면은 `provenance='proforma_cash_plug — identity-closed, not forensic'` + `SimulationResult.warnings`에 `projected cashConversionGap is identity-check not forensic signal` append. **projected의 진짜 cash-quality는 cashConversionGap이 아니라 driver 가정 자체**(매출채권/재고 회전 가정·운전자본 delta 가정, §3.7 quality-adjusted revenue·§3.9 step 4 working capital delta)에서 본다.
- 이 구분은 §3.13 step 4 accounting lens가 baseline에서만 forensic 판정을 내리도록 역할을 가른다(아래 R17 역할 분리).

### 3.10 Step 9. valuation bridge

1. FCFF DCF를 만든다.
2. WACC를 계산하거나 ref 기반으로 입력한다.
3. terminal growth를 제한한다.
4. sales-to-capital, ROC, reinvestment rate 정합성을 확인한다.
5. relative valuation으로 peer multiple sanity를 확인한다.
6. reverse DCF로 현재 가격이 요구하는 성장률, 마진, ROC를 계산한다.
7. terminal value share가 과도하면 flag를 붙인다.

기본 식:

```text
growth = reinvestmentRate * roc
enterpriseValue = presentValue(fcff) + presentValue(terminalValue)
equityValue = enterpriseValue - netDebt
perShareValue = equityValue / shares
```

제약:

- terminal growth는 장기 무위험금리 또는 명시된 보수적 상한을 넘어서는 안 된다.
- ROC가 WACC보다 낮은데 높은 성장을 주면 value destructive flag가 필요하다.
- reverse DCF 요구치가 산업과 회사 historical range를 벗어나면 plausibility가 낮아진다.

### 3.11 Step 10. price bridge

가격 결과는 손익 변화와 시장 변화가 섞여 만들어진다. 이 둘을 분리해서 보여준다.

기본 log return bridge:

```text
rFund = deltaLn(epsOrFcfPerShare) + deltaLn(targetMultiple)
rFactor = marketBeta * marketShock
        + sum(factorBeta_i * factorShock_i)
        + sum(macroBeta_j * macroShock_j)
rEvent = sum(eventImpact_k * decay_k)
rTotal = wFund * rFund
       + wFactor * rFactor
       + wEvent * rEvent
       + interactionAdjust
       - overlapPenalty
priceScenario = basePrice * exp(rTotal)
```

기간별 가중 원칙:

- 단기: event와 factor 비중이 높다.
- 중기: 손익과 multiple 비중이 높다.
- 장기: FCF, reinvestment, ROC, terminal assumptions 비중이 높다.

주의:

- 같은 macro shock이 multiple과 factor에 동시에 들어가면 overlap penalty를 둔다.
- R²가 낮은 beta는 shrink하거나 warning을 붙인다.
- event impact가 통계적으로 약하면 가격 bridge에서 보조 정보로만 둔다.

**★driver 공분산을 fan band 분산에 1차 반영 (추가 추정기 0, R21b):**

driver들을 *독립*으로 처리해 fan band를 만들면(각 driver σ를 단순 합) 상관된 충격의 분산을 과소·과대 추정한다(03 §4.3 factor exposure·§3.12-5 독립 처리 금지). 정공법 — pooled-panel 적합이 *이미 산출하는* residual로 공분산을 추정한다(추가 추정기 0):

- **Σ 추정 = `fitPanel` residual outer-product**(`crossRegression.fitPanel`이 잔차를 이미 산출 → `Σ = E[ε εᵀ]` outer-product, 새 추정기 0). MC noise를 독립 가우시안이 아니라 **Σ Cholesky로 상관 샘플링**(driver 충격이 상관 구조를 따라 함께 움직임).
- **ill-conditioned 보호**: Σ가 ill-conditioned(작은 표본 → 거의 특이행렬)면 대각 shrink(Ledoit-Wolf류 또는 단순 대각 가산) + `SimulationResult.warnings`에 `driver covariance shrunk — small-sample(partial)` append. shrink는 §2B.2 G2 participation-ratio·shrinkage 재사용(새 leaf 0).
- **curated prior 부호 제약 유지**: §3.12-5 '독립 처리 금지'는 *부호 알려진 쌍*(예 fx↑↔cogs↑ 원재료 수입 자연헤지)은 curated prior 부호 제약을 유지한다 — Σ 추정이 작은 표본서 그 부호를 뒤집으면(우연 잔차) prior 부호를 *우선*(추정 Σ보다 경제 prior). 자연헤지 쌍은 음의 상관을 강제 유지(과대 fan 방지).
- **σ provenance 시각 규율 정합**: Σ 기반 fan은 §2B.5 #2·05 §시각 인코딩 SSOT(검증 σ=실선 / 미검증 elasticity prior=점선·회색)를 따른다 — Σ가 pooled-OOS residual(검증)이면 실선, prior 합성이면 점선.

### 3.12 Step 11. 시나리오 range 생성

1. bear/base/bull 값을 만든다.
2. 또는 P10/P50/P90 값을 만든다.
3. 가정 분포가 있으면 sampling을 사용할 수 있다.
4. 분포가 없으면 deterministic sensitivity grid를 우선한다.
5. 상관관계가 불명확하면 독립 가정으로 처리하지 않는다. **★미식별 시 보수적 *확대*(R21b)**: driver 간 상관을 Σ로도 prior로도 식별 못 하면(둘 다 결손), 독립 가정보다 *넓은* 밴드를 쓴다 — 미식별 상관을 독립으로 두면 동방향 충격의 분산을 *과소* 추정해 band가 좁아지고 거짓 정밀이 된다. 행동규칙 = 미식별 상관은 보수적 worst-case 상관(동방향 가정)으로 band를 *확대* + `correlation unidentified — band widened(conservative)` 라벨. "독립 처리 금지"의 *방향*은 항상 확대(좁히기 금지, §2B.11 under-dispersion 금지와 정합).
6. probability 없는 branch는 가중 평균하지 않는다.

산출물:

- `PriceSimulationResult`.
- `SensitivityGrid`.
- `ScenarioFan`.

### 3.13 Step 12. AI 전문가 검토

1. macro lens가 환경 가정을 검토한다.
2. event/news lens가 이벤트 인과와 timing을 검토한다.
3. business lens가 driver mapping을 검토한다.
4. accounting lens가 손익과 현금흐름 품질을 검토한다.
5. valuation lens가 DCF와 reverse DCF를 검토한다.
6. quant lens가 backtest, beta, factor, overfit을 검토한다.
7. skeptic lens가 가장 취약한 가정을 깨본다.

각 lens는 같은 형식으로 답한다.

- `claim`.
- `supports`.
- `counterEvidence`.
- `missingEvidence`.
- `tripwire`.
- `confidence`.
- `status`.

### 3.14 Step 13. gate와 최종 상태

1. evidence coverage를 확인한다.
2. vintage integrity를 확인한다.
3. fact/estimate/hypothesis 구분을 확인한다.
4. 경제적 정합성을 확인한다.
5. 회계 품질을 확인한다.
6. valuation sanity를 확인한다.
7. backtest robustness를 확인한다.
8. AI disagreement를 확인한다.
9. 반증 조건을 확인한다.
10. 최종 상태를 결정한다.

상태:

- `usable`: 핵심 증거와 gate가 충분하다.
- `usableWithGaps`: 사용할 수 있지만 결손과 취약점이 명확하다.
- `blocked`: 핵심 숫자 또는 vintage가 부족하다.
- `rejected`: look-ahead, ref 누락, 계산 모순 등으로 사용할 수 없다.

---

## 4. 과거 replay 절차

1. replay target과 event를 고른다.
2. `decisionAt`을 고정한다.
3. 당시 available data만 불러온다.
4. 당시 기준 ScenarioSpec을 생성한다.
5. 사용 가능한 feature와 사용할 수 없는 feature를 분리한다.
6. 당시 시점의 assumption ledger를 만든다.
7. 손익과 가격 range를 생성한다.
8. 실제 이후 실적과 가격을 outcome으로 붙인다.
9. 가정별 error를 계산한다.
10. 실패 원인을 분류한다.

실패 원인 분류:

- macro 가정 실패.
- event 해석 실패.
- revenue driver 실패.
- margin driver 실패.
- cash conversion 실패.
- valuation multiple 실패.
- factor shock 실패.
- data vintage 오류.
- overfit.

---

## 5. walk-forward 절차

1. universe를 as-of 기준으로 고정한다.
2. train window와 test window를 정의한다.
3. fold별로 feature와 parameter를 다시 학습한다.
4. fold별 ScenarioSpec을 생성한다.
5. fold별 결과를 저장한다.
6. 비용, slippage, benchmark를 적용한다.
7. DSR/PBO 또는 유사 과최적화 경고를 계산한다.
8. 성과보다 assumption stability를 먼저 본다.

필수 경고:

- 표본 수 부족.
- fold 간 불안정.
- 특정 regime에만 작동.
- 비용 반영 후 소멸.
- benchmark 대비 설명력 없음.
- post-selection risk.

---

## 6. 미래 what-if 절차

1. 현재 asOf snapshot을 만든다.
2. 사용자 가정을 받는다.
3. AI가 누락 가정 후보를 제안한다.
4. 사용자가 채택한 가정만 scenario에 반영한다.
5. branch dependency를 만든다.
6. 반증 조건과 tripwire를 채운다.
7. bridge를 실행한다.
8. gate를 통과한 결과만 표시한다.
9. 결과를 추적 지표 목록으로 남긴다.

추적 지표 예:

- 다음 분기 매출.
- 영업이익률.
- 수주잔고.
- ASP.
- 원재료 가격.
- 환율.
- DSO.
- CFO/NI.
- peer multiple.
- WACC proxy.

---

## 7. 출력 문장 원칙

허용:

- "이 가정이 맞으면 base case에서 영업이익률은 2.1%p 개선된다."
- "현재 가격은 base case 대비 더 높은 margin 지속을 요구한다."
- "이 결과는 원재료 가격 가정과 sales-to-capital 가정에 가장 민감하다."
- "공시 전 replay에서는 이 매출 driver를 사용할 수 없으므로 결과가 blocked다."

금지:

- "이 종목은 오른다."
- "검증된 전략이다."
- "AI가 목표주가를 산출했다."
- "뉴스가 호재이므로 매수."
- "결손값은 0으로 처리했다."

