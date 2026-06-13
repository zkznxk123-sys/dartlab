# 09. Architecture Consolidation — 시뮬레이터-앵커 부채 원장 + 외과 청산 시퀀스

상태: PRD v0.3 (2026-06-13 SSOT 5종 감사 + 클린 아키텍처 / 2026-06-14 구현 정합: P1·P3·P13 ✅·P14 위치·금지어 lint 3파일 내부 일관화[§7·§8]·recordForecast/models dead chain 정직표기[§0 #5·P9] / **★2026-06-14 §10 신규: 4 Fatal 빌드 티켓 — 100점 해제 완전 실행 스펙**[fatal①~④ 파일·시그니처·테스트게이트·phase·의존·CI안전·동시세션 비충돌, 코드 실측 정본+verdict requiredFix 반영])
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
- 신규 테스트: `tests/architecture/{test_simulate_leaf_ssot,test_no_duplicate_dcf,test_no_duplicate_regression,test_axis_ssot,test_story_no_self_calc}.py`, `tests/audit/`(admission critical-t+Holm·**금지어 lint = `tests/audit/valuationPublishLint.py`+`test_valuationPublishLint.py` 신설**[§10.1 — leaf src 미스캔, 발간 표면 한정. ⚠§P12 의 "3파일" 은 leaf *소스* 위치 참조용일 뿐 스캔 대상 아님; `_valuationOther.py` 는 `analysis/**financial**/` 에 실재, `analysis/valuation/` 아님 — 경로 표기 정정]), `tests/_attempts/scenarioSimulator/mcSeedReproKill.py`
- **★fatal 빌드 티켓 신규/수정 파일(§10 SSOT, 절대경로)**: 신설 `tests/audit/valuationPublishLint.py`·`tests/audit/test_valuationPublishLint.py`(①T1) / `src/dartlab/simulate/{ledger,admission,gate}.py`·`tests/simulate/{test_ledger,test_admission,test_gate}.py`·`src/dartlab/ai/tools/lens.py`(③ T-B) / `.github/workflows/driverDecay.yml`·`tests/analysis/forecast/{__init__,test_forwardTestWrite}.py`(②P9e/f). 수정 `tests/run.py`(①1줄), `core/dataConfig.py`·`analysis/valuation/_crossRegressionIo.py`·`analysis/valuation/crossRegression.py`(★FIX-1 _MODEL_CACHE_DIR re-export)·`analysis/forecast/forwardTest.py`(②), `simulate/{entry,registry,run,transfer,sheet}.py`·`synth/scenario.py`·`tests/simulate/{test_verb,test_run}.py`(③T-A1·④). **04-progress-ledger.md = 편집 금지(동시세션).**
- 엔진 SSOT(불가침): `analysis/financial/_proformaCore.py`·`_signalsMacroSensitivity.py:244`, `analysis/valuation/dcf.py:46`, `synth/distress/*`
- UI 새 토폴로지: `ui/packages/surfaces/src/terminal/charts/{PriceChart.svelte,chartState.svelte.ts}`, `ui/packages/contracts`

---

## ★10. 4 Fatal 빌드 티켓 — 100점 해제 (코드 실측 정본, 2026-06-14)

> 객관 평가 천장 ≈8.5 의 원인 = §0~§9 가 "문서가 기계강제를 주장하나 코드 부재"인 4 지점. 본 절은 각 fatal 을 *재명명이 아닌 실제 빌드 티켓*(파일·시그니처·스키마·테스트게이트·phase·의존·CI안전·동시세션 비충돌)으로 박제한다. **코드=정본, 옹호 금지.** ⚠ 동시세션이 엔진 코드(`simulate/registry.py·run.py·sheet.py`) + `04-progress-ledger.md` 활발 편집 중 — 본 절의 모든 티켓은 "엔진 트랙이 실행" 전제이며 `04` 는 절대 편집하지 않는다(충돌 회피). 실측 재검증 일자: 2026-06-14.

### 10.0 빌드 표면 실측 요약 (4 fatal 의 정확한 코드 위치)

| fatal | 코드 실측(2026-06-14) | 지금 빌드 | CI red 위험 |
|---|---|---|---|
| ① 투자권유 금지어 lint 미존재 | `tests/audit/valuationPublishLint.py` 0건. leaf 가 금지어 **정당 사용**: `priceImplied.py:222/224` `signal="underpriced"/"overpriced"`, `pricetarget.py:450/454` `"strong_buy"/"strong_sell"`+`:89 weighted_target`. 스캔 표면 `story type="simulation"` = `reportTypes.py REPORT_TYPES` 12키에 **미존재**(11키 실측+추가). ⚠`_valuationOther.py` 는 `analysis/**valuation**/` 아닌 `analysis/**financial**/_valuationOther.py` 에 실재(§P12 의 "3파일" 경로 표기 부정확 — 그러나 lint 는 src 미스캔이라 무관) | T1=**예**(표면 한정 lint 스켈레톤, 표면 0파일=green no-op) / T2=**아니오**(발간 표면 신설=BLOCKED) | T1=없음(src 미스캔). 발간표면 없이 src 전역 스캔 시 즉시 red |
| ② recordForecast/models dead chain | `forwardTest.py` 함수 = generateKey/saveForecast/loadRecords/evaluate/evaluateCalibration (`recordForecast` **0건**). `_FORWARD_TEST_DIR=Path.home()/.dartlab/forward_tests`(:13, ephemeral). `savePanelModel`→`_MODEL_CACHE_DIR=Path.home()/.dartlab/models`(`_crossRegressionIo.py:16`, **`crossRegression.py:19,36` 에서 import+`__all__` 재노출**). `DATA_RELEASES` 에 `models`/`forwardTest` 키 **0건**. `recordGrade`=`credit/monitoring/history.py:22` 실재(cron 0건) | P9a/b/c/f=**예** / P9d(HF)·P9e(cron body)=**아니오**(fatal③ admission 의존) | MEDIUM — `_MODEL_CACHE_DIR` 제거 시 smoke gate red(아래 FIX) |
| ③ gate/ledger/admission 미존재 | `simulate/{gate,ledger,admission}.py` 3파일 Glob **0건**. `ai/tools/lens.py` **0건**. `sheet.py` `NodeValue.ai` 슬롯 정의되나 `evaluateSheet` 가 안 채움(det만) | T-A(ai-독립: ledger honest-gap·admission 통계 primitive·gate det/block 분기·NodeValue.frozenInputs 동결)=**예** / T-B(ai-종속: gateUsable ai/fork·collectForks·grounding a/b·Brier)=**아니오**(lens 선행) | LOW(신설 3파일 dartlab import 0). HIGH 충돌(registry.py 핵심) |
| ④ US 비전 vs 코드 모순 | `entry.py:111` `market != "KR"` ValueError 실재. `scenario.py:94 PRESET_SCENARIOS_US`(5개)+`:229 SECTOR_ELASTICITY`(35키=KR23+US12) 실재, `getPresetScenarios:146` US 분기(`:206`)+silent KR fallback(`:207`). `getPresetScenarios("KR")` 하드코딩 = `registry.py:256·459` + `run.py:264`. `transfer.py:114 fxChangePct=(fx-BASELINE_FX)/BASELINE_FX*100`+`:127 adjustedWacc=baseWacc+rateChange*0.5`(전역 KR 상수). EDGAR `sector/sectorParams` EXEMPT(`company.py:3955`). `test_verb.py:46` US→ValueError 잠금 | **예**(US 프리셋·elasticity·market 판별 전부 실재) | LOW — 단 transfer baseline·test_verb 동일 commit 미동행 시 red |

### 10.1 fatal① — 발간 표면 한정 투자권유 금지어 lint (P12 실행 명세)

**2개 독립 티켓.** SSOT 룰 = `08-valuation-report.md §2.2·§5 B-3·§7`.

**T1 — 발간 표면 한정 lint 스켈레톤 [지금 빌드 가능].** 스캔 대상을 발간 표면(frontmatter `reportType: simulation` 마크다운)으로 *한정* → leaf `.py` 영원히 비매치(CI red 0). 표면 0파일이면 green no-op, 표면 ship 시 자동 발화 = "스켈레톤-now, active-on-surface".
- **신설**: `tests/audit/valuationPublishLint.py`(미러 = `noViewerChangeSummary.py` 의 `argparse --strict`/`_scan`/`return 1·0` 구조 — 단 companion test 는 net-new, 그 파일엔 test 부재).
  - `_scanSurface(root: Path) -> list[tuple[Path,int,str,str]]` — 발간 표면 파일만 수집(파일·행·위반어·사유).
  - `_isSimulationReport(md_path: Path) -> bool` — frontmatter `reportType: simulation`(따옴표 유/무) 매치 = **스캔 게이트**. `.py` 영원히 False(= leaf 안전 핵심).
  - `main() -> int` — `argparse --strict`(위반 시 exit1; 기본 exit0).
  - `SURFACE_ROOTS = (REPO_ROOT/"blog"/"05-company-reports",)` — **src 미포함**.
  - `_BANNED: tuple[tuple[re.Pattern,str],...]` — §7 ①~② 도출: 매수/매도 rating(한/영)·`underpriced/overpriced` 누출(→consistent/optimistic/pessimistic)·단일 목표가(범위 비동반)·예상수익률 약속·개인화 추천. 출력 사유에 §7 ② 대체어휘 동봉.
- **수정 1줄**: `tests/run.py GATES["lint"].cmd`(:130-139, 현 9-tool `&&` 체인) 끝에 `&& python -X utf8 tests/audit/valuationPublishLint.py --strict`. ★CI 동결 안전 검증: `test_runEntrypoint.py:153 len(GATES)==30`·`:161 {fast:17,full:6,nightly:7}` 는 게이트 수·tier 만 동결, cmd *문자열 내용* 미검사 → &&체인 추가는 drift 아님(noScriptsDir/checkSilentFail 등 이미 동일 패턴, :132-138).
- **테스트게이트**: `tests/audit/test_valuationPublishLint.py` 신설. **★FIX-1(필수): 모듈 상단 `pytestmark = pytest.mark.unit`**(test_cleanup_calls.py:15·test_namingConsistency.py:11 컨벤션) — 없으면 test-fast `-m 'unit and not requires_data'`(run.py:185) 에서 조용히 제외돼 표면봉합.
  - `test_lint_greenNow`: blog/ simulation 0건 → `main()==0`(현 119 index.md 중 `reportType` 키 자체 0건 실측).
  - `test_lint_catchesBannedInSimReport(tmp_path)`: tmp `reportType: simulation`+"목표주가 95000원"/"매수의견" → 위반≥1, `--strict` exit1.
  - `test_lint_ignoresNonSimReport(tmp_path)`: `reportType` 없는 6막 md 에 underpriced 넣어도 `_scanSurface()==[]`(발간표면 한정 증명).
  - `test_lint_ignoresLeafSource`: `_isSimulationReport(priceImplied.py)==False`(src .py 비매치 회귀가드).
  - **★FIX-3(권장)**: `test_lint_collectsCleanSimReport` — tmp `reportType: simulation`+깨끗 본문 → `_scanSurface` 수집됨 + 위반==[](0파일 green 과 N파일-위반0 green 분리 검증).
- **★FIX-2(필수, T1↔T2 자동발화 계약)**: `_isSimulationReport` 매치 키 = T2 publisher 가 emit 하는 키와 **바이트 동일**(`reportType: "simulation"`). 현 publisher.py:141-157 frontmatter 는 `reportType` 자체 부재(119 index.md 전수 0건 실측) → T2 가 정확히 동일 키를 emit 하기 전엔 영영 0파일. T1 docstring + T2 의존목록에 이 키 동일성을 명시 고정.
- **phase**: T1=지금(발간 phase 무관, 독립 머지 green). **buildable-now, 선결 의존 0.**

**T2 — 발간 표면 신설(story type=simulation) [BLOCKED].** T1 이 실제로 스캔하려면 발간 표면 ship 선결. fatal① 범위 밖이나 활성 선결.
- 차단: (1) SimulationResult ref 14키 치환(`registry.py` 핵심 = **엔진트랙 회피**) (2) 렌더러 2개(businessDriverBridgeBlock·profitBridgeBlock, `builders.py`) (3) `reportTypes.py REPORT_TYPES` simulation 12번째 키(현 11키 실측) (4) `publisher.py` frontmatter `reportType:"simulation"`+면책 확장("hypothetical scenario analysis, not a forecast", §7 ③).
- **phase**: Phase 6(발간, 코어 졸업 후 — §7 시퀀스). **story 트랙이 실행**, fatal① 설계자는 T1만. T1↔T2 독립 — T1 단독 머지 green, T2 머지 즉시 T1 자동 발화(코드 수정 0).

### 10.2 fatal② — forwardTest write 체인 + models HF chain (P9 실행 명세, 6 sub-ticket)

> `data/` 전체 gitignored(`.gitignore:41`) — `data/credit/` 는 HF-only(git ls-files=0). 모든 write redirect 는 `data/` 대상, git 추적 0, HF 만 배포(credit recordGrade 패턴 동일). HF 업로드 SSOT = `pipeline/hfUpload.py uploadCategoryToHf`(repoFor/retryHfCall/증분).

- **P9a [지금]** `core/dataConfig.py DATA_RELEASES` 에 2키 추가(`DATA_CATEGORY_ALIASES`:253 앞): `"models":{"dir":"models","label":"driver pre-fit artifact","public":False}`, `"forwardTest":{"dir":"forwardTest","label":"forward-test 예측+사후평가(Brier ledger)","public":False}`. flat(nested 없음), 신규 top-level HF dir(충돌 0). CI: LOW(dict 키 추가, `.get`-graceful 리더 무영향, news drift test 무관).
- **P9b [지금, P9a 의존]** ephemeral→`data/` redirect via 호출시 resolver(module-const 아님, `DARTLAB_DATA_DIR` env override):
  - `_crossRegressionIo.py`: `def _modelDir()->Path: return Path(os.environ.get("DARTLAB_DATA_DIR") or "data")/DATA_RELEASES["models"]["dir"]`. `saveModel:73·loadModel:133·savePanelModel:187·loadPanelModel:241` 의 `_MODEL_CACHE_DIR`→`_modelDir()`. **★FIX-1(CI red 하드 블로커): `crossRegression.py:19` 가 `_MODEL_CACHE_DIR` import + `:36 __all__` 재노출** → 심볼 삭제 시 `import dartlab` smoke gate red. 해법 = `_MODEL_CACHE_DIR = Path.home()/".dartlab"/"models"` deprecated default 로 **유지**(call-time 은 `_modelDir()` 사용) OR `crossRegression.py` import+`__all__` 동시 갱신. **crossRegression.py 를 touched-files 에 추가 필수.**
  - `forwardTest.py`: `def _forwardTestDir()->Path` 동형. `saveForecast:112·loadRecords:171·evaluateCalibration:374/376` 의 `_FORWARD_TEST_DIR`→`_forwardTestDir()`. CI: MEDIUM — forwardTest 테스트 grep 0건(무회귀), docstring path 예시는 리터럴 유지(`feedback_no_docstring_auto_sweep`).
- **P9c [지금, P9b 의존]** `recordForecast` 신설(thin facade, 새 저장 메커니즘 0 — ForwardTestRecord+saveForecast 재사용):
  `def recordForecast(*, stockCode:str, horizon:int, projected:list[float], scenarios:dict[str,list[float]], sourcesUsed:list[str], assumptions:list[str], version:str="v3", directionProbability:float|None=None, directionPredicted:str|None=None) -> Path` → `saveForecast(ForwardTestRecord(...))`. **정정(코드-truth)**: §P9 "OutcomeLog 박제" 는 부정확 — `OutcomeLog`(`ai/memory/outcomeLog.py`)는 per-code 마크다운 AI-결정 로그지 숫자 forecast 저장소 아님. forecast 저장소 = ForwardTestRecord/saveForecast. recordForecast(write)+`evaluate:182`(채점, 이미 완비)+`evaluateCalibration:320`(Brier 집계, 이미 완비)로 루프 닫힘 — 평행 OutcomeLog hop 추가 금지(덕지덕지). scenario≠forecast 보존(이미 산출된 projected 만 저장, shock 로직 0). **★FIX-2(in-session 블로커): `lint_camelcase_ast.py --hook` PostToolUse(`.claude/settings.local.json`)가 public def docstring 없으면 exit2 차단** → recordForecast 에 ≥1줄 docstring 필수(docstring4Section 4섹션 hook 은 CI 미배선, 1줄로 충분).
- **P9d [BLOCKED-by③]** HF 업로드 배선: `uploadCategoryToHf("models"/"forwardTest")` 재사용(새 코드 0). HF repo = panel repo(`HF_REPO`) 재사용(models JSON ~1파일/사). **★FIX-3(메커니즘 정정): flat 카테고리 full-folder fallback 은 `*.parquet`+`*.arrow` 만 glob(hfUpload.py)** → `.json` 0파일 업로드(조용히). 해법 = 호출자가 `changedFiles=[<json>]` 명시 전달(`:81` extension-agnostic 분기) OR flat fallback 에 `.json` glob 추가.
- **P9e [PARTLY BLOCKED]** `.github/workflows/driverDecay.yml` quarterly cron(`0 18 1 */3 *`, concurrency `hf-models-push` cancel:false, `permissions contents:read`, `HF_TOKEN` secret, **workflow_run 트리거 금지**). **★MONITORED_WORKFLOWS 등록 필수**(`.github/scripts/ops/monitorPipeline.py`, `project_gather_pipeline_overhaul` — 새 scheduled = 등록 강행, silent-swallow 회귀 가드). forwardTest decay job body = BLOCKED(admission.evaluateAll/DriverCard 미존재=fatal③). **★FIX-4(credit 과대표기 정정)**: credit 은 "fully unblocked" 아님 — `DATA_RELEASES` credit 키 0건+HF 업로드 0건+`history.py:13 Path("data/credit")` 하드코딩(DARTLAB_DATA_DIR 무시). 닫으려면 신 카테고리+`.json`-upload fix+(선택)env-aware path 필요(단순 cron 배선 아님).
- **P9f [지금, P9a/b/c 의존]** `tests/analysis/forecast/test_forwardTestWrite.py` 신설(`__init__.py` 동반 — dir 미존재 실측). **게이트명 정정: §P9 `test_outcomelog_roundtrip`→`test_forwardTestWrite_roundtrip`**(OutcomeLog 오표면). `@pytest.mark.unit`+`monkeypatch.setenv DARTLAB_DATA_DIR=tmp`(repo data/ 무오염):
  - `test_recordForecast_writes_to_data_dir`(tmp/forwardTest/{code}.json, NOT home)·`test_recordForecast_roundtrip`·`test_savePanelModel_redirect`·`test_evaluate_closes_loop`(rec.evaluation has mape/scenarioHit)·`test_dataReleases_models_category`(`DATA_RELEASES["models"]["dir"]=="models"`·`repoFor("models")==HF_REPO`·`hfBaseUrl("models").endswith("/models")`).
  - 실행: `bash tests/test-lock.sh tests/analysis/forecast/test_forwardTestWrite.py -m unit -v`(OOM 가드, pytest 전수 금지).
- **phase**: 09 Phase 4. **슬라이스 P9a+P9b+P9c+P9f = "Phase-4-EARLY write primitives"**(registry/admission 무관, 엔진 트랙과 충돌 0 — `dataConfig.py`(L0)+`_crossRegressionIo.py`+`forwardTest.py`+`crossRegression.py`(L2 leaf)+신규 tests). P9d/P9e cron body = admission(fatal③) 동반 착륙.

### 10.3 fatal③ — simulate/{gate,ledger,admission}.py (AI lens phase, 2-트랙)

**핵심 판정: 3파일은 동일 phase 아님.** `gateUsable` 의 ai/fork 분기·`DisagreementLedger.collectForks`·`groundingCheck(a)(b)` 는 `node.ai`(NodeValue)가 채워져야 의미 — 채우는 주체 = `ai/tools/lens.py`(미존재) = **선결 차단(T-B)**. 그러나 `admission` 통계 primitive·`ledger` honest-gap 수집·`gate` det/block 분기·NodeValue.frozenInputs 는 ai 무관 순수함수 = **지금 빌드(T-A)**. 이 분리가 100점 핵심 — "gate 전체 한 번에"는 ai 슬롯 없는 dead 코드 = ≤8.5 천장 재발.

**T-A [지금 빌드 가능, ai-독립]** (신설 3파일 모두 dartlab import 0=stdlib+numpy, L2.5 born-clean, import_direction 자동통과):
- **T-A1 NodeValue.frozenInputs 인터페이스 동결**(OQ8 척추): `sheet.py NodeValue` 에 `frozenInputs: tuple[tuple[str,str],...] = ()` append(frozen hashable 유지, 기본 ()=무회귀). `evaluateSheet` 가 fn 반환 frozenInputs→`_freezeInputs`(`tuple((k,_normalize(v)) for k,v in sorted(d.items()))`)→NodeValue 적재. ⚠ `registry._macroFrozen:459`/`run._marginPathFromSnapshot:264` 우회 **삭제는 엔진트랙 phase4 와 라인 겹침** → **본 티켓은 형상만 동결, 삭제 실행은 엔진트랙 위임**. **★FIX(형상 미결 — 동결 전 엔진트랙 삭제 착수 불가)**: frozenInputs 를 '정규화 str 튜플(해시 동등)'로 동결하면 다운스트림이 wacc/shares 를 float 로 다시 읽을 때 str→float 역파싱 필요(rev 노드가 `frozenInputs[gdp/rate/fx]` 직접 읽기 전제와 충돌). 적재 형상을 해시용 str vs 수치 소비용 float 중 무엇으로 동결할지 §1.b/§5b 에 명시 필요(한 필드 두 용도 양립 불가) — **권장: 이중필드 또는 `_normalize` 가 수치 보존하도록 계약 고정.**
- **T-A2 `simulate/ledger.py`**: `@dataclass(frozen=True) LedgerRow(nodeId·kind:Literal["gap","stale","fork"]·detValue·aiValue·gap·provenance·refs·resolution)`+`DisagreementLedger(rows)`. `collectGaps(result:SimulationResult)->DisagreementLedger`(ai-독립: partial→gap, asOf≠latestAsOf→stale). `collectForks(sheet:DriverSheet)->tuple[LedgerRow,...]`(**T-B 까지 inert: ai=None sheet→()**, 결정론 무영향). 명명 `*Graph/*Loop/*Kernel/*Dag` 금지(no-graph-regression 통과), docstring 영어(`checkAgentBoundary.py:160` 한국어 "회귀 가드" substring SRC 전역 스캔 회피).
- **T-A3 `simulate/admission.py`**(순수 primitive 4종, numpy 만): `criticalT(nTrials, *, core=False)->float`(core=HLZ 3.0, exploratory=√(2lnN))·`holmStepDown(pValues, alpha=0.05)->tuple[bool,...]`(진짜 step-down, Bonferroni degenerate 회피 — `multipleTesting.py` 와 byte-다름)·`participationRatio(corrMatrix)->float`((Σλ)²/Σλ², eigvalsh, T-독립, denoiseRMT 대체)·`stabilitySelection(...)->tuple[tuple[str,...],float]`. 4함수 `*, tier:str="pooled"` 키워드+`tier=="firmRefine"→ValueError`(§2B.9). `evaluateAll`/DriverCard 오케스트레이션 = DriverRegistry phase(본 티켓 제외, stub 도 금지). **★FIX(clutter 정직)**: T-A 에서 4 primitive 는 unit 테스트만 있고 live caller 0(`feedback_always_check_clutter` 소지) → born-clean primitive 정당화를 명시하거나 admission 신설을 DriverRegistry phase 로 묶어 caller 동시 졸업 권장.
- **T-A4 `simulate/gate.py`**(ai-독립 분기만): `_isStrongDet(provenance)->bool`(preset:/elasticity:/transfer:/proforma:/dcf:=약함, ols:R²+adj/OOS/df=강함; **현 4노드 전부 약함 → strong 분기 dead, 정직**). `gateUsable(node,snapshot)->Literal["det","ai","fork","block"]`(ai-독립 라이브: det.value None→block, ai None→det; ai/fork/grounding 분기=T-B). `groundingCheck` 는 (a)refs실재·(b)수치범위 가 aiNV 의존이라 전체 T-B 배치(부분 분리=clutter).

**T-B [선결 차단]** ai/tools/lens.py 선행: (1) `lens.py` 신설(L4, `annotateNodes(sheet,*,onlyForkGap=True)->None` fork/gap 노드 .ai 만, 전수 금지) (2) evaluateSheet lens 경로 물리분리 (3) gateUsable ai/fork·collectForks·grounding(a)(b)·Brier(fatal② recordForecast 닫힘 후) 활성.

- **테스트게이트**: `bash tests/test-lock.sh tests/simulate -m "unit" -v`. T-A1 `test_nodeValue_carries_frozenInputs`+기존 무회귀 / T-A2 `test_collectGaps_marks_partial`+`test_collectForks_inert_on_det_only` / T-A3 `test_holm_not_bonferroni`+`test_criticalT_core_3_0`+`test_participationRatio_t_independent`+`test_tier_guard_blocks_firmRefine` / T-A4 `test_gateUsable_block_on_none`+`test_gateUsable_det_when_no_ai`+`test_isStrongDet_preset_is_weak`. T-B(후속) `test_gateUsable_fork_on_strong_disagreement`(lens 졸업 후).
- **★FIX(과대표기 정정)**: 테스트게이트가 'docstring4Section(4섹션 hook) preflight 27게이트 강제'로 적었으나 코드 실측 = `docstring4Section.py` 는 `tests/run.py GATES` 미등록+어떤 hook 도 미바인딩 → 4섹션 누락이 CI red 직접 유발 안 함(engine-add/graduation 규율일 뿐). 게이트 목록에서 'hook 강제'를 'engine-add 규율'로 정정.
- **phase**: 09 Phase 5(본진 `simulate/`+`ai/tools/lens.py`). T-A2/A3/A4 신설은 registry import 확장 불필요(run.py 의 ledger.collectGaps 배선 1줄=엔진트랙 위임) → 엔진트랙과 라인 0 겹침. **충돌 유일점 = T-A1**(sheet.py NodeValue + registry/run 우회삭제) → 형상만 동결.

### 10.4 fatal④ — US 시장 해금 (Phase A, 지금 빌드 가능, 정공법=transfer baseline)

> 표면 보고서의 "프리셋 와이어링만"보다 1단계 깊은 블로커: `transfer.py` 전역 KR 상수(`BASELINE_FX`/`BASELINE_RATE`)를 US 프리셋에 그대로 먹이면 거짓 충격. **단 magnitude 정정(아래 FIX) — ~0 붕괴 아님.**

- **수정1 `synth/scenario.py`**: `getMacroBaseline(market:str="KR")->tuple[float,float]`(=(baselineRate,baselineFx); KR=(2.5,1470.0) US=(5.0,1.0)) 신설+`US_BASELINE_RATE=5.0`/`US_BASELINE_FX=1.0` 상수(기존 `BASELINE_*` BC 유지, 삭제금지).
- **수정2 `simulate/transfer.py`**: `transferMacroToFundamentals(..., *, baselineRate:float, baselineFx:float)` / `transferRevenuePath(..., *, baselineRate:float, baselineFx:float)` — 전역 `BASELINE_*` 참조 제거, 키워드 주입. **★FIX(doctest red 회피)**: `transfer.py:66-72·167-172` doctest 가 키워드 없이 호출 → 키워드를 **KR default 부여**(`baselineRate=BASELINE_RATE, baselineFx=BASELINE_FX`)로 BC+doctest 값 보존(필수화는 doctest TypeError red). 정공법.
- **수정3/4 `registry.py`/`run.py`**: `buildSnapshot` 반환 dict **끝에** `market`/`baselineRate`/`baselineFx` 3키 append(`market=getattr(company,"market","KR")`, merge 충돌 최소). `_macroFrozen(macroNv,horizon,market)`→`getPresetScenarios(market)`(`:459` 'KR' 제거). `_marginPathFromSnapshot`(`run.py:264`)도 market+baselineRate/baselineFx 수신(2번째 transfer 호출=감사 rev 노드와 발산 방지). **★FIX(시그니처 정합)**: `_fnRevPath` 는 `getPresetScenarios` 직접 호출 아님 — `_macroFrozen` 경유. `_marginPathFromSnapshot` 시그니처에 baselineRate/baselineFx pass-through 추가 명시.
- **수정5 `entry.py:108-115`**: `market not in ("KR","US")→ValueError`. (drivers/lens/mode 인자 추가 금지 = no-graph-regression). **★FIX(가드 비대칭)**: `Company.simulate`(`providers/dart/company.py:2070`)는 `runScenario(self)` 직접 호출(entry 가드 우회) → 실제 US-정합 게이트 = `buildSnapshot` 의 `snap["market"]` threading 이지 entry 가드 아님. EDGAR Company 엔 simulate 메서드 부재(`company.py:3955` EXEMPT) → `Company("AAPL").simulate` 는 AttributeError. G-A4/G-A6 은 top-level verb + runScenario 만 exercise(Company.simulate on US 안 함) 명시.
- **수정6 `tests/simulate/test_verb.py:46-58`**: `test_simulate_guards_non_kr`(US→ValueError match="KR") **교체 필수(동일 commit)** → `test_simulate_accepts_us_market`+`test_simulate_rejects_unknown_market`. 누락 시 entry 완화로 즉시 red.
- **테스트게이트**: `bash tests/test-lock.sh tests/simulate/ -m "unit" -v`. G-A1 `test_us_market_snapshot_baseline`(macro.provenance=="preset:baseline", rev>base) / **G-A2 `test_us_fx_no_false_shock`**(US baselineFx=1.0,fx=1.0→fxChangePct==0.0, 전역 1470 결합 끊김) / **★FIX(WACC 동등 가중 — G-A2b 추가)**: `test_us_wacc_no_inflation`(US baseline waccPath[0]==snap["baseWacc"], +1.25pp 없음 — baselineRate threading 증명; WACC 왜곡이 FX 보다 material) / G-A3 `test_kr_path_unchanged`(KR rev[0] byte 불변) / G-A4/G-A5(doctest) / G-A6(realData,serial,skip-tolerant AAPL). **★FIX(magnitude 정정, 정직성 결함 ~70배 과대)**: 티켓이 "fxChangePct≈-99.9%→US 매출 ~0 붕괴" 반복하나 코드 실측 = `revFxEffect = revenueToFx*fxChangePct/1000` → 연 매출 배수 0.986(Semis revToFx=0.5) ~ 0.996(US 실제 DEFAULT_ELASTICITY revToFx=0.2). 매출 ~0 아님, ~0.4~1.4%/yr drift(3yr ~0.97). transfer baseline 버그는 실재·5번째 수정이 정답이나, '틀린 숫자 ≈0/매출경로 붕괴' 프레이밍은 거짓 — 'subtle multi-% drift + WACC inflation(+1.25pp/yr, dcfPerShare 가 더 material)'로 재기술.
- **정직 한계(옹호 금지)**: ① US 시뮬 Phase A = 항상 DEFAULT_ELASTICITY(EDGAR sector/sectorParams EXEMPT + SIC→GICS 리졸버 부재) — US 12 elasticity 키는 코드 실재하나 도달경로 0 → Phase A 미사용, "US=DEFAULT 근사" docstring 명시, 가짜 sector 매핑 금지. ② US baseWacc=10/terminalGrowth=3 default(KR 비대칭, Phase C). ③ US 프리셋=무출처 정적 상수(seed/CI 0, folk-stat) — "검증된 Fed DFAST" 과대 라벨 금지.
- **phase**: Phase A(지금 빌드, 결정론 한정). fatal①②③ 의존 0 = **fatal④ 단독 해소 = 천장 상승 즉시 가능 1건.** Phase B(US SIC→GICS sector 리졸버)/Phase C(US sectorParams) 후속 독립.
- **동시세션**: `transfer/scenario/entry/test_verb` 4파일 먼저 빌드(엔진트랙 Phase4 와 거의 비충돌) → `registry/run` 은 Phase4 최신 위 rebase 로 market 라인만 얹기. **★수정2+3+4+6 = transfer 시그니처 변경 동반이라 단일 commit 필수**(import 깨짐 방지) + `test_run.py:69-83 _snapshot` 헬퍼에 3키 추가 동일 commit(누락 시 전 unit 테스트 KeyError red).

### 10.5 규율 점검 (전 티켓 공통)

scenario≠forecast(lint·recordForecast·gate 전부 예측 안 함) ✓ / 결손0(gate block·ledger honest-gap, 0 대체 금지) ✓ / look-ahead(recordForecast forecastDate=now UTC, evaluate vs later actual; admission 통계만) ✓ / rating금지(fatal① 핵심 목적) ✓ / no-graph-regression(`*Loop/*Graph/*Kernel` 신설 0, agent.py 본체 불변, 순수 함수/자료구조) ✓ / L2 cross금지(simulate L2.5 import 0, tests/audit L2 아님) ✓ / 졸업게이트(lint=tests/audit 도구 도메인 정당; simulate 신설=졸업한 코어 동급 확장; recordForecast=기존 엔진 복구) ✓ / preflight(lint 게이트 &&체인=수 불변 30 동결) ✓.
