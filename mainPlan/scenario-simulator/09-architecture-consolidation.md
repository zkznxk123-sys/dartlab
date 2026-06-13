# 09. Architecture Consolidation — 시뮬레이터-앵커 부채 원장 + 외과 청산 시퀀스

상태: PRD v0.3 (2026-06-13 SSOT 5종 감사 + 클린 아키텍처 / 2026-06-14 구현 정합: P1·P3·P13 ✅·P14 위치·금지어 lint 3파일 내부 일관화[§7·§8]·recordForecast/models dead chain 정직표기[§0 #5·P9])
지위: 08(발간 단면)과 자매 — **정합성 단면**. 부채 청산은 simulate 코어 졸업과 인터리빙(§7), 실행은 운영자 go 후.

---

## 0. 결론 + 평가 정정 (Glob+Read 재검증으로 grep 감사의 사각 교정)

**시뮬레이터를 옳게 지으면 정리(cleanup)는 별도 잡일이 아니라 귀결이다.** simulate가 "모든 시뮬 숫자 = 정확히 하나의 SSOT leaf 호출"을 lint로 강제하면, 중복 구현(DCF 5중·회귀 4중·WACC 4진입·축 6×6 이중화·distress 이중)이 "simulate가 부를 수 없는 죽은 코드"로 자동 노출되어 외과 제거된다. 신용은 새 엔진 0의 solvency 뷰(§4). 실행은 빅뱅 금지·census 단조감소·byte-identical·무중단(§3·§7).

**감사가 PRD 너머로 발견한 신규 사실 7건 — 단 PRD 평가가 코드 재검증으로 3건을 정정:**
1. **DCF는 5중**(PRD 01은 "3중"): `multiStageDcf`(본체)·`dcfValuation`·`scenarioSim._scenarioDCF`·`_simScenario` 인라인·`pricetarget._dcfFromProforma`+`_monteCarloPriceDistribution`. WACC≤TG 보정상수 3종 상이(`tg+0.05`/`max(lastWacc-2,0.5)`/`max(wacc-2,1.0)`).
2. **매출-거시 회귀 4중**(PRD 02는 "3중"): +`analysis/financial/macroExposure.py:88 calcMacroSensitivity`(단변량). OLS 엔진 3종(`_invertMatrix4`/`_predictionMath._invertMatrix`/`core/utils/ols.olsMulti`).
3. **`calcMacroSensitivity` 동명 3곳**: `_signalsMacroSensitivity.py:105`(섹터탄성)·`macroExposure.py:88`(외생회귀)·`_predictionSynthesis.py:77`(lazy proxy). public-contract 혼란.
4. **calibrator dead 안의 dead**: `calibrateScenarios`는 src 호출 0(dead), 그 안 `_adjust("optimistic",...)`의 `optimistic` 키는 SCENARIO_PROBABILITIES 부재 → 항상 no-op.
5. **★정정(평가): forwardTest vs credit 분리.** forwardTest는 **write 함수 자체 부재**(`recordForecast`/`runForwardTest`/`saveRecords` src 0건 — 신설 필요). credit은 **write 함수 존재**(`monitoring/history.py:22 recordGrade`·`scoring/migration.py:93 buildTransitionMatrix`)하나 **cron 배선만 없음** + `data/credit/` 부재(작업량 차이 큼 — credit=배선 1줄, forwardTest=함수 신설). 설계가 둘을 conflate한 것을 평가가 정정.
6. **distress 이중구현**: `synth.distress`(merton/chs/survival, L1.5 중립 SSOT, 깨끗) vs `analysis/financial/insight/_distressModels.py`(822줄, Altman/Ohlson/Beneish/Sloan/Piotroski/Merton/Audit 7모델). "부실 판정"이 credit(CHS+notch)·analysis(7모델)·quant(alphas) 3곳 각자. zone 라벨 파일마다 재정의.
7. **story 헌법 실질 위반 2모듈**: `sixAct.py`(`_GRADE_TO_SCORE`·가중치로 6막 레이더 점수 자체 산출, landing hero radar 데이터원)·`narrative.py`(`company.select` 9곳 + 자체 `_yoy()`로 YoY 인과 재계산). builders/summary/dashboard는 깨끗.

**★정정(평가) — 설계 §0의 사실 오류 3건(거짓 정정 전파 차단):**
- **P14 위치 오류:** `qualityGate.py`는 **미존재**(Glob 0). 실제 `scripts/` 위반자 = `skills/measureProgress.py:68-69`(`_BASELINE_DIR=_REPO/"scripts"/"audit"`) + `core/observability/mapping_ledger.py:22` stale docstring.
- **P13 — ✅ docstring 정정 완료(2026-06-14):** `SECTOR_ELASTICITY` 실측 **35키(KR 23 + US 12, `scenario.py:229` inline)** — 설계 "36"·이전 정정 "11" **둘 다 오류**(평가가 짚은 "정정이 새 오류를 박음"; 11은 US 12키 누락). `getElasticity` 9섹션 docstring 전체가 **가짜 데이터 파이프라인이었음**: Guide "2010~2024 KR 11업종 패널 회귀"(미존재 회귀)·Requires/Prerequisites "`data/synth/sectorElasticity.json` 로드"(파일 미존재, 값은 모듈 inline)·Freshness "연1회 회귀 업데이트"(가짜)·TargetMarkets "KR 11/US 별도필요"(실제 35키 inline). **"확신 오정렬 > 정렬 실패"의 교과서.** → Guide/Requires/Prerequisites/Freshness/TargetMarkets honest 라벨 + 35키 명시로 정정 완료(`synth/scenario.py` docstring). 잔여 = Example 실제값 동기화(코어 구현 시).
- **금지어 lint 범위:** `underpriced/overpriced`가 `priceImplied.py:23,222` + `_valuationOther.py`, **★+ `pricetarget.py` `weighted_target`/`signal:strong_buy~strong_sell`(평가 P0, 중추 함수 — 설계가 놓침)** = **3파일**. lint 범위에 셋 다(signal enum·단일목표가 필드 차단).

**★워크스페이스 변동(이 세션 중 실측):** mainPlan 리팩토링이 이 세션 동안 단계-4b~5로 진척 → **터미널 전체가 `landing/src/lib/terminal/` → `ui/packages/surfaces/src/terminal/`로 이동**(commit ff9099ba0). `landing`엔 `terminal-shell/{routeLoad,terminalShell}.ts`만 잔존. **PRD의 모든 `landing/.../terminal/...` UI 경로는 stale** — 새 SSOT = `ui/packages/surfaces/src/terminal/`(charts/PriceChart.svelte·chartState.svelte.ts 실재) + 포트 = `ui/packages/contracts`. 엔진 측(`src/dartlab/*`) 경로는 불변. 본 09는 엔진 중심이라 영향 미미하나, 05(Play)·06(지수)는 새 토폴로지로 재기반 필수.

---

## 1. 시뮬레이터-앵커 원리

### 1.1 메커니즘 (한 문장)

**simulate는 노드 평가를 "L2 공개 계약 호출 + 결과 포장"으로만 정의하고, `simulate/` 안에 어떤 수학(DCF/WACC/OLS/terminal value/`random.gauss`)도 *정의*될 수 없게 lint(`test_simulate_leaf_ssot.py`)로 금지한다.** 그 결과 모든 시뮬 숫자가 정확히 하나의 L2 SSOT leaf에 닿고, 중복 구현은 죽은 코드로 노출되어 외과 제거된다. 노드는 얇은 어댑터(L2 leaf 호출 + NodeValue 포장)지 계산 본체가 아니다(01 §5).

### 1.2 각 중복의 정본 SSOT 확정표

| 중복군 | 실측 N | 정본 SSOT (단 하나) | 나머지 수렴 | simulate 노드 |
|---|---|---|---|---|
| DCF 순수수학 | **5** | `valuation/dcf.py:46 multiStageDcf` | `dcfValuation`·`_scenarioDCF`·`_simScenario`인라인·`_dcfFromProforma` → DAG `value` 노드가 `calcDFV`(상층 래퍼) 1회 호출로 흡수 | `proforma→value` |
| 회사-바인딩 가치평가 | 2층 | `financial/_valuationDeep.py calcValuationSynthesis` ← `dFV.py:56 calcDFV` | simulate는 **상층 calc\* 래퍼만** 호출(company 바인딩 0줄 재구현) | `value` |
| WACC | 4진입 | base=`_proformaCore.py:145 computeCompanyWacc`, 조정=`qualityWACC.calcQualityWACC` | `_getBaseWACC` `_estimateWacc` 우회·`discountRate or 10.0` 3폴백·`calcDFV.py:226 wacc_effect=0.12` 곱셈근사 → sensitivity 노드 실제 그리드 | `wacc`(base+quality) |
| 매출-거시 회귀 | **4**(+OLS 3) | 단일사=`_signalsMacroSensitivity.py:244 calcMacroRegression`, 횡단면=`scan.scanMacroBeta`(scan 위임), OLS엔진=`core/utils/ols.olsMulti` 단일 | `macroExposure.calcMacroSensitivity` 폐기, `_invertMatrix4`/`_invertMatrix`→olsMulti. crossRegression(펀더멘털 팩터모델)=**별개 SSOT 유지** | `macro.beta`(단일사)+scan(universe) |
| 차원축 | 2(6×6) | driver 정의=`gather/mapping/exogenousAxes.py`(라우팅 SSOT), state 뷰=`predictionSpace._normalize*` | predictionSpace 6축 정의·`impactOn` 마법상수(3.0/2.0/1.5/0.5) **귀결 소멸**(driver=raw 변화율이면 환산상수 불필요) | `driver.card` |
| distress 판정 | 2(synth vs 7모델) | `synth.distress.{merton,chsModel,survival,chsFeatures}`(L1.5 중립) | analysis 7모델·quant alphas는 **호출 일원화**(deletion 아닌 재사용). zone enum 1곳 | `solvency`(§4) |
| scenario/forecast | 5 | simulate `SimulationResult` 1객체의 mode 차이 | scenarioSim 수동봉합·인라인 DCF → DAG 흡수 자연소멸 | mode={whatif,replay,walkforward} |

### 1.3 transfer 마법상수 2층 소멸

transfer = 현재 2층 마법상수(SECTOR_ELASTICITY 탄성치 × `impactOn` 환산상수 3.0/2.0/1.5/0.5). simulate가 driver를 **raw 변화율**(exogenousAxes)로 두고 transfer 계수를 **pooled-panel β**(02 §2B.1)로 학습하면 환산상수가 구조적으로 불필요. SECTOR_ELASTICITY는 노드 provenance(`preset:`/`pooled-β:R²=`)로 라벨되고 가짜 docstring 6섹션도 정직해짐(§5, P13).

---

## 2. 우선순위 부채 원장 (심각도 S × simulate 의존도 D)

D=3=코어 척추(이걸 안 풀면 simulate 못 짐) / D=1=독립.

| # | 위치 | 문제 | 정본·정리방향 | 검증 | S×D | 게이트 |
|---|---|---|---|---|---|---|
| **P1** ✅ **완료(2026-06-14)** | `_simMonteCarlo.py:145`·`pricetarget.py:278` 전역 `random.seed`+`:205` 덮어쓰기 | Play 결정론·URL공유·TS패리티 붕괴 | **구현: ① 전역 seed→로컬 `random.Random(seed)`**(`fe9e66c0a`, stdlib·외부의존0·pyodide안전 — numpy PCG64는 simulate 엔진이 jumpable stream 필요 시 재방문) **② `:205` `=`→연도별 cumprod**(`ad112b171`, `*=` 단순수정은 **평균경로 소실이라 기각**, cumRevFactor×(1+revNoise)·margin random-walk·mean path 보존) | ✅ `test_horizon_widens_cone` kill-test PASS(옛 cv h1≈h3 버그 증명→cone 확대), MC 30 PASS | 9 | **P0** |
| **P2** | lazy-proxy 4파일(`_simScenario:35`·`_simMonteCarlo:36`·`_simHistorical:34`·`simulation:240`) | no_import_evasion·양방향 cycle | `_applyMacroShock`→`simulate/transfer.py` 이사, `_extract*`→`_simExtract.py` | `test_import_direction` 함수내부 import AST 확장 | 9 | **P2** |
| **P3** ★정합 정정(구현) | DCF 5중+WACC 4진입 | TV/exit/FCF<0 폴백 silent 발산 | **시나리오 DCF = `registry._fnDcf` proforma-FCFF**(구현 `096e84c43` — ★`calcDFV` 회피: calcDFV는 외부 proforma 무시→scenario-coherence 깨짐) / 정적 가치평가 = `calcDFV`(삼각검증). 둘은 *중복 아닌 2 정당 경로* — census 5→**2**(proforma-FCFF·calcDFV)로 정정, 나머지 3(`_scenarioDCF`·인라인·`_dcfFromProforma`)만 흡수 | `test_no_duplicate_dcf` census 5→2 단조 | 9 | **P3** |
| **P4** | 회귀 4중+OLS 3+동명 3 | 같은 OLS 3구현 | calcMacroRegression+scanMacroBeta+olsMulti, macroExposure 폐기, crossRegression 별개유지 | `test_no_duplicate_regression` census | 9 | **P4** |
| **P5** | 축 이중화 predictionSpace↔exogenousAxes | 매크로 축 2 SSOT·impactOn 마법상수 | exogenousAxes=driver SSOT, predictionSpace=state 뷰 | `test_axis_ssot` | 6 | **P4** |
| **P6** | distress 이중 7모델+zone 산재 | 부실판정 3엔진 각자 | `synth.distress`, analysis 7모델·quant 호출 일원화, zone enum 1곳 | lint-imports: solvency leaf→synth.distress+credit.scoring만 | 6 | **P5(credit)** |
| **P7** | distress 입력 actual 단면 | CHS/Merton/survival 전부 actual, proforma 0줄 | `chsFeatures.extractChsFeatures` proforma 주입(본체 0줄) | 졸업 골든(actual 재현+proforma 신규) | 6 | **P5(credit)** |
| **P8** | story `sixAct`·`narrative` 자체계산 | 헌법 위반·YoY·grade→score 중복 | analysis calc 재사용 | `test_story_no_self_calc`(AST `company.select`·`_yoy` 0) | 4 | **P6** |
| **P9** | ★forwardTest **write 함수 부재**(신설) / credit transition **cron만 부재**(배선) | Brier ledger 영구 빈 | forwardTest=`recordForecast` 신설+OutcomeLog / credit=`recordGrade` cron 배선 | `test_outcomelog_roundtrip` | 4 | **P4(G5)** |
| **P10** | multipleTesting 미배선+t-stat 미산출 | β 우연유의 거를 장치 0 | `admission.py` critical-t+진짜 Holm 독립구현, scanMacroBeta t-stat 추가(leaf 확장) | `test_admission_gate` | 6 | **P4** |
| **P11** | crossRegression pre-fit cron 0+calibrator dead+dead-branch | loadModel 영구 miss·optimistic no-op | DriverRegistry G0~G5 결정·"재활성 or 정직폐기" 졸업판정·optimistic 키 제거 | `vulture` baseline | 2 | **P5(졸업)** |
| **P12** ★범위 확대(평가) | `signal` underpriced/overpriced(`priceImplied.py:23,222`+`_valuationOther.py`) **+ ★`pricetarget.py` `weighted_target`(단일 목표가)+`signal:strong_buy/buy/hold/sell/strong_sell`(`_classifySignal:644`)** = **3파일** | 사실상 매수/매도 rating — pricetarget.py는 08 §2.3이 채택한 *중추* 함수인데 기존 lint이 놓침(평가 P0) | 발간 표면 제거→"consistent/optimistic/pessimistic" + pricetarget.py는 발간 어댑터(P10/P50/P90만 추출, weighted_target/signal drop) | 금지어 lint 신설(**3파일**, signal enum+weighted_target 필드 차단) | 3 | **P6(발간)** |
| **P13** ✅ docstring 정정 완료(2026-06-14) | getElasticity provenance 날조(회귀패널·json 로드 단정, 실제 inline)+업종수 오기(문서 36/11, 실측 **35=KR 23+US 12**) | folk-stat을 검증된 양 위장 | "inline 하드코딩 prior 무출처(seed/CI 0)" 정직표기·**35키 통일**·json 로드 주장 제거(✅ `synth/scenario.py`)·Example 실제값(잔여=코어 구현 시) | `docstring9Section.py` AC "데이터 정합" | 2 | **Phase −1(부분 완료)** |
| **P14** | ★`skills/measureProgress.py:68-69` `scripts/audit`(NOT qualityGate.py) | CLAUDE.md scripts/ 금지 | `tests/audit/_baselines/` 이동 | `noScriptsDir.py` | 1 | **선행(무관)** |
| **P15** | publisher fossil docstring(`story/publisher.py`·`credit/_calcsAdvanced.py:187,282`) | 미존재 모듈 참조 | fossil 정정(story/publisher.py 단독) | `stale_references.py` | 1 | **선행(무관)** |

P1~P4(S×D=9)=코어 척추. P14·P15=즉시 청산(무위험). P5~P10=코어 옳게 지으면 함께 풀림.

---

## 3. 외과적·게이트 실행 (빅뱅 금지)

4개 외과 단위: ① **born-clean 병행 신설**(simulate 소비처 0 출발, 기존 무손상) ② **byte-identical golden**(삼성/카카오/현대 2~3사, MC는 분리 — 결정론만 byte-identical, MC는 분포통계 패리티 ±ε) ③ **census baseline 단조감소**(DCF 5→1·회귀 4→2, PR마다 한 호출처만) ④ **BC 위임 별도 commit**(`analyst.py:322-347` `__getattr__` 4엔트리 + capability 카탈로그 동반).

**숨은 회귀 표면(협소 검증 금지):** ① `analyst.py:322-347` 모듈경로 문자열 강결합 ② MCP "0건 거짓" — `engineCall.py` 카탈로그 동적 dispatch. **불가침:** `buildProforma`/`_proformaCore.py`·`calcMacroRegression`·공개 시그니처(BC re-export).

`tests/_attempts/scenarioSimulator/` 졸업 8단계(01 §15) + ⑤에 calibrator optimistic dead-branch 명시 제거 추가.

---

## 4. 신용 = simulate solvency 뷰 (새 엔진 0)

### 4.1 동형
가치평가 뷰(08, simulate mode="whatif")와 노드 대 노드 동형. 신용(distress/survival/scorecard)은 같은 driver→proforma 투영을 **지급능력 렌즈**로 본 단면.

### 4.2 leaf SSOT (조립, 재발명 금지)
distress 수학=`synth.distress.{merton,chsModel,survival,chsFeatures}`(이미 L1.5 중립, credit↔analysis 공유=**이미 정합**). 등급=`credit.scoring.gradeTable.mapTo20Grade`. 7축=`credit.engine.evaluateCompany`.

### 4.3 일점 수술 (P7)
CHS/Merton/survival은 **이미 회사 비의존 순수함수**(`calcCHS(netIncome=,totalLiabilities=)`) → 본체 0줄. 바꿀 곳=**feature 추출기 1개**: `chsFeatures.extractChsFeatures`에 `proformaStatement` 주입 + `_calcCHSAdjustment` actual/proforma 분기. 정당성: `creditScenarioBlock`(builders.py:6060)+`calcCreditScore(overrides={"debtRatio":150})`가 **이미 가정 교체로 등급 재산출** — 빠진 건 "override가 임의 dict 아닌 동일 DAG proforma 단면에서 자동 도출"되는 배선뿐.

### 4.4 가치평가(08)와 공통/차이
| | 가치평가 | 신용=solvency |
|---|---|---|
| 공통 | 동일 driver→proforma→leaf, SimulationResult 단면, `synth.distress` 공유, `story/publisher.py` 발간 | (좌동) |
| collapse | proforma **WACC 할인**→주당가치 | 동일 proforma **임계 대비 비율/hazard**→등급/PD |
| horizon read | P10~P90 범위 | **survival curve**(시점별 pSurvival)+dCR 등급 궤적 |
| 금융사 | residualIncome/bankDFV 스위치 | 5축(`_engineFinancial`) — 둘 다 "금융사=별도 leaf" 통일 |

**이미 부분 흡수:** dFV가 `_dFVCalcs.py:312 _applySurvivalAdjustment`로 CHS PD를 fair value 반영 → 가치평가가 이미 신용 일부 흡수. solvency 뷰=그 역방향(같은 PD를 등급으로 collapse).

### 4.5 story 렌더
기존 8 credit 블록(`creditMetrics/Score/History/PeerPosition/Flags/Narrative/Audit/Scenario`) 재사용. ReportDock credit mode는 P7 졸업 후. `auditCredit`은 `externalGrades.json` 부재 시 silent None → "데이터 없음" structured 반환 정정.

---

## 5. 클린코드·9섹션 docstring 기준

엔진 만질 때만(함수단위). **일괄 sweep 금지**(`feedback_no_docstring_auto_sweep`). simulate 신설 코드는 baseline 0 출발 + `docstring9Section.py --strict --baseline simulateDocstring9Section.json` 게이트. 최소 4섹션 hook 강제, full 9=사람용 8 + LLM Specifications 1(6 sub-keys). **simulate 특수:** `SeeAlso`/`Dataflow`가 "이 숫자가 닿는 L2 SSOT leaf" 명시 → docstring이 §1 계약의 사람-읽기 표면. §11 키워드 회피(한국어 "회귀 가드" substring). **격상 시 데이터-docstring 정합 정정 AC**(P13: getElasticity 가짜 6섹션·업종 11·Example 실제값). 격상 대상(4→9, LLM Spec 누락): `_valuationDcf`·`_valuationOther`·`calibrator`·`forwardTest`·`scenarioSim`·`calcMacroSensitivity/Regression`·`predictionSpace`·`qualityWACC`·`computePriceTarget`·`crossRegression.fit*`·`scanMacroBeta`.

---

## 6. 거처·계약 (계약 먼저, 코드 나중)

**Phase 1 계약 동결(코드 0줄):** ① `test_import_direction.py LAYER_OF`+`LAYERS`에 `simulate:2.5`(SINK_HELPERS·STRICT_L0_L15 미추가) ② importlinter Contract `layers` story 아래 simulate + 신규 forbidden(`source=[analysis,credit,macro,quant,industry] forbidden=[dartlab.simulate]`=역방향 차단). 단 import-linter는 continue-on-error 가시화 도구, **진짜 강제=pytest** ③ L2 cross 이중룰 정합: credit이 analysis import 아니라 **둘 다 simulate DAG 구독**(공통 transfer는 simulate/synth로 올림) ④ guard census L2.5 규칙 추가(full census).

**신규 강제 계약 3종:** `test_simulate_leaf_ssot.py`(simulate 안 DCF/WACC/회귀/`random.gauss` 정의 0)·`test_no_duplicate_{dcf,regression}.py`(census 단조)·`reproSeedAudit.py` GATES(simulate 전역 seed 0).

**준수:** no-graph-regression(`DriverNode`/`DriverSheet`, `*Graph/*Dag` 금지, AI=`ai/tools/lens.py` 1종, agent.py 불변)·public-contract-only(`dartlab.simulate(...)` verb 1개, universe로 횡단면 흡수)·panel wide 불가침(동결 snapshot만).

---

## 7. 실행 Phase 시퀀스 (코어 졸업 ⨉ 부채 청산 인터리빙)

- **Phase −1 (즉시·무위험·simulate 무관):** P14(`measureProgress.py:68-69` `scripts/`→`tests/audit/_baselines/`)·P15(publisher fossil docstring)·**✅ P13 부분 완료(getElasticity provenance 날조 docstring 정정·35키 명시, 2026-06-14)**·죽은코드(`_loadMacroAligned` 등). 검증=`stale_references.py`·`vulture`. 독립 commit.
- **Phase 0 (kill-test) — ✅ 완료(2026-06-14):** P1 전역 seed→**로컬 `random.Random(seed)`**(`fe9e66c0a`, numpy PCG64 아님 — stdlib·pyodide안전·동작무변경, jumpable stream은 엔진 필요 시 재방문), `:205` →**연도별 cumprod**(`ad112b171`, `*=` 단순수정은 평균경로 소실이라 기각). 검증=`test_horizon_widens_cone` kill-test PASS(옛 cv h1≈h3 버그 증명→cone 확대) + MC 30 PASS.
- **Phase 1 (계약 동결, 코드 0줄):** §6 레이어·importlinter·census 3종을 현 baseline(DCF=5·회귀=4)으로 동결(이후 감소만).
- **Phase 2 (졸업 ②③):** P2 transfer 적출+`_extract*` 하강→lazy-proxy 4파일 소멸. 2~3사 byte-identical 골든.
- **Phase 3 (졸업 ④) — ✅ 부분 완료(2026-06-14):** ✅ DAG dcf 노드 `registry._fnDcf` = proforma-FCFF(`096e84c43`, calcDFV 회피=scenario-coherence). 잔여 = census 5→2 단조(나머지 3 DCF 경로 흡수)·wacc 노드 `computeCompanyWacc` 통합·노드 입자도 실측 확정.
- **Phase 4 (회귀 수렴+게이트):** P4 macroExposure 폐기·OLS→olsMulti·동명 disambiguate. P5 exogenousAxes=driver SSOT. P10 admission.py+scanMacroBeta t-stat. P9 forwardTest recordForecast 신설+OutcomeLog / credit cron 배선.
- **Phase 5 (졸업 ⑤⑥⑦⑧ + 신용):** 덕지덕지(봉합·calibrator dead-branch 제거·중복 단일화). P11 crossRegression/calibrator 재활성 or 정직폐기. 9섹션 docstring. 본진 `simulate/`+`ai/tools/lens.py`. P6+P7 신용(extractChsFeatures proforma 주입 일점 수술, 7모델 호출 일원화, zone enum 1곳). 검증=engine-add 5점+skill-os-add 4단계+lint-imports.
- **Phase 6 (발간, 코어 졸업 후):** P8 story sixAct/narrative 자체계산 외과이전. **P12 금지어 lint 신설(3파일** — `priceImplied.py`+`_valuationOther.py`+`pricetarget.py`; **현재 미존재** — `tests/audit/`에 매치 0건, 2026-06-14 실측). builders 렌더러 2개+`type="simulation"`+14키 ref 치환(가치평가)+credit 14키. ReportDock valuation→credit mode. `reportType`+`asOf` frontmatter(company-reports 충돌 해소). **UI 측은 새 `ui/packages/surfaces/src/terminal/` 토폴로지** 기준.
- **Phase 7 (잔여 9섹션 격상, 만질 때만):** §5 격상 대상 함수단위. P13 데이터 정합.

---

## 8. 종합

5종 감사가 PRD 01/02/08 v0.2를 코드로 확증, 7개 신규 사실 추가, PRD 평가가 Glob+Read로 그 중 3건(P14 위치·P5 credit/forwardTest 분리·P13 업종11+가짜 docstring)을 정정. 앵커 원리(`test_simulate_leaf_ssot`)가 중복을 구조적으로 청산, 신용은 `extractChsFeatures` proforma 주입 일점 수술로 새 엔진 0의 solvency 렌즈. 실행은 Phase −1→7로 census 단조감소·byte-identical·무중단 외과 1단위씩. **워크스페이스: 터미널이 `ui/packages/surfaces/src/terminal/`로 이동 — UI 경로 전수 재기반(05/06) 필요, 엔진 경로 불변.**

### 산출/정정 대상 (절대경로)
- 신규(본 문서): `mainPlan/scenario-simulator/09-architecture-consolidation.md`
- 정정: `01`(§15 "3→5중"·§1 가짜 docstring), `02`(§2B "3→4중"·동명3·forwardTest write 부재), `04`(v0.1→v0.2 전면), `08`(§3.3 신용 14키·§5 credit mode), `00`(§5 1줄), `README`(09 추가)
- 신규 테스트: `tests/architecture/{test_simulate_leaf_ssot,test_no_duplicate_dcf,test_no_duplicate_regression,test_axis_ssot,test_story_no_self_calc}.py`, `tests/audit/`(admission critical-t+Holm·**금지어 lint 3파일** `priceImplied`+`_valuationOther`+`pricetarget` — 현재 미존재, 신설 필요), `tests/_attempts/scenarioSimulator/mcSeedReproKill.py`
- 엔진 SSOT(불가침): `analysis/financial/_proformaCore.py`·`_signalsMacroSensitivity.py:244`, `analysis/valuation/dcf.py:46`, `synth/distress/*`
- UI 새 토폴로지: `ui/packages/surfaces/src/terminal/charts/{PriceChart.svelte,chartState.svelte.ts}`, `ui/packages/contracts`
