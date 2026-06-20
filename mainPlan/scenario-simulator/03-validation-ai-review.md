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
| G16 | Calibration | fan band coverage·PIT 균등성·skill>0 vs baseline (§4.4) | usableWithGaps / blocked |
| — | (전 게이트 메타-enum) | 게이트의 *blocking source* 가 미배선(소스부재) | **design(소스부재) → 강제 미검증 워터마크** |

> **★'실패 시 상태' enum 확장 — `design(소스부재)`(R-fc, 적대 레드팀):** 위 표 마지막 행은 *게이트별*이 아닌 *전 게이트 공통 메타-상태*다. 한 게이트의 통과 조건이 코드로 박혀 있어도, 그 판정을 먹이는 source(`SimulationResult→gate`·`recordForecast→calibScore`·`ledger.py→DisagreementLedger`·`recordForecast→공개 Brier`)가 *미배선*이면 그 게이트는 rejected/blocked/usableWithGaps 중 어느 것도 emit할 수 없다 — 판정할 입력 자체가 없다. 이 경우 상태는 **`design(소스부재)`** 로 기계 라벨하고, 해당 게이트를 소비하는 *모든 표면*에 **미검증 워터마크를 강제 + usableWithGaps 상한**으로 강등한다(fail-closed: 검증 못 한 게이트를 통과로 위장 금지). `design` 은 '통과'가 아니라 '대기'다(G16 box·02 §2B.3 DriverCard dormant 상한과 동형) — 아래 결선표가 각 소비 표면의 blocking source 를 핀한다.

> **★design 게이트 ↔ 소비 표면 fail-closed 결선표(R-fc, 적대 레드팀 — 새 파일 0·새 표면 0):** 각 소비 표면이 *어느* 게이트(=blocking design source)에 매여 ship 하는지, 그 source 가 미배선(`design`)인 동안 표면이 *무엇을 강제*하는지를 핀한다. 이 표가 없으면 "코어 졸업했으니 발간도 ship" 식 우선순위 역전(08 §11)이 게이트별로 새어 들어온다. 졸업 AC = **각 표면이 자기 blocking source 미배선 동안 미검증 워터마크 + usableWithGaps 상한을 기계 강제** (source 라이브 후에만 워터마크 해제).

| 소비 표면 | blocking design 게이트 (source) | source 미배선 시 강제 (fail-closed) | source 라이브 조건 |
|---|---|---|---|
| 05 Play fan band | G16 Calibration (`recordForecast`→calibScore) | 모든 fan '캘리브레이션 미검증' 라벨 + σ 점선·회색(05 §3.1·§4.4 동일 채널) + usableWithGaps 상한 | `recordForecast` write-end + N≥8분기 (§4.4) |
| 08 발간 보고서 | G15 Output Safety (`gate.py`→SimulationResult) + 발간 게이팅(08 §11) | 발간 모드 착수 차단 + 사람-체크 라벨(08 §11 부분 기계 강제) | `gate.py` 배선 + 발간 표면 ship(T2, 본문 §2 G15) |
| DisagreementLedger (§7.3) | G14 AI Review (`ledger.py`→lens 산출) | 내부 노출만 + '미검증·hypothesis' 워터마크, 발간 표면 비노출(§9.3) | `ledger.py`+`lens.py` 배선(§9.3 A7 dormant 상한) |
| 공개 Brier 리더보드 (§9.3) | G16 Calibration (`recordForecast`→공개 Brier) | 발간 금지(§9.3) + 내부 DisagreementLedger·rationale만 | write-end 라이브 + N분기 + held-out·seed/CI 강제(§9.3) |

> 워터마크 SSOT 분열 차단: 위 '강제' 컬럼의 *시각·카피*는 본 표가 소유하지 않는다 — 미검증 워터마크 카피 = `05 §11 상태 카피 매트릭스`, 점선·회색·해치 시각 = `05 §3.1`+`05 §10`. 본 표는 *어느 게이트가 어느 표면을 막나(fail-closed 결선)* 만 소유한다(03 = gate semantics).

> **★카피 SSOT 포인터(R14):** 위 표는 *게이트 판정 로직*(통과 조건·상태 enum)의 SSOT다. **각 실패 행이 사용자에게 어떻게 보이는가(상태 라벨 문구·색·점선·워터마크 카피)는 본 표가 소유하지 않는다 — 실패 상태→초보 평어 카피·복구 안내의 SSOT = `05 §11 상태 카피 매트릭스`, 시각 채널(점선·색·해치·워터마크) = `05 §3.1 fan σ provenance` + `05 §10 시각 인코딩 SSOT` 를 준수한다.** 03 = 무엇이 막히나(gate semantics), 05 = 막힌 것을 어떻게 정직하게 표시하나(copy/visual semantics). 한 게이트 상태 문구를 03·05 양쪽에 복제하지 않는다(SSOT 분열 차단, `feedback_always_check_clutter`). G16(Calibration)의 미검증 라벨 채널은 §4.4 가 σ 점선 규율(05 §3.1·01 §5b A6 흡수)을 *동일 채널*로 재사용한다 — 새 시각 토큰 0.

> **★G16 상태 정직(planScore 직결, design):** G16 의 통과 조건(§4.4)은 *지금* 박지만, 게이트 자체는 `recordForecast` write-end 라이브 + N≥8분기 누적 후에야 **active** 다(§4.4). 그 전까지 G16 은 항상 `미검증`(캘리브레이션 표본 부재)을 emit 하고 모든 fan 에 '캘리브레이션 미검증' 라벨을 강제한다 — 게이트가 *없는* 것이 아니라 *대기* 상태다(02 §2B.3 DriverCard dormant 상한과 동형). 게이트 공식은 코드 빌드 전이라 *설계*이며, planScore(설계 완전성)에 직결하되 systemScore(빌드)에는 미반영.

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

> **★#5·#7 코드 강제 격상(R18-G3, design — 산문→assert):** #5(universe membership as-of)와 #7(parameter selection log)은 *산문 점검*이면 강제되지 않는다. 둘은 02 §2B.11 look-ahead 코드 강제(`buildSnapshot` asOf 전파 + replay 진입 시 `availableAt <= decisionAt` assert)와 **결선**해 다음 두 가드로 격상한다(졸업 AC, write-end 라이브 후 활성). ⓐ **survivorship 가드(#5·#6)** = replay/walk-forward 유니버스를 *decisionAt 시점 상장 종목*으로 고정하되 **상장폐지사를 폐지 시점까지 포함**(생존자만 남긴 유니버스 = look-ahead 의 변종, 사후 생존 정보 누설). pooled-panel 적합·peer 풀 구성 양쪽에 동일 적용. ⓑ **post-selection peeking 차단 assert(#7)** = parameter selection 이 test-window 데이터를 *보지 않았다*를 코드로 단언 — full-sample parameter selection 금지(§4.3·§4.4 PIT/skill 채점이 학습창에 오염되면 무의미). selection log 는 `RunSpec.parameterSelectionLog` 에 trial·창·선택근거를 persist(02 §2B.0 nTrials ledger 와 동일 forking-paths 차단 원리). **현재 `entry.py`/`registry.py` 는 asOf 라벨만 들고 두 assert 모두 부재**(02 §2B.11 실측) → 본 격상은 admission/buildSnapshot 신설 시 박는 *설계*다.

### 4.3 과최적화 경고

다음이면 성과 해석을 제한한다.

- regime 하나에서만 작동.
- 비용 반영 후 alpha 소멸.
- benchmark와 구분 어려움.
- factor exposure가 대부분 설명.
- fold 간 parameter가 불안정.
- 반복 탐색 후 최선 결과만 선택.
- PBO/DSR 또는 대체 지표가 weak.

### 4.4 Forecast Calibration (연속 fan chart 전용 — design)

> **★범위 분리(혼동 차단):** 본 절은 **연속 fan chart**(rev/OI/FCF·가격 밴드 — `P5..P95`)의 *분포 캘리브레이션* 전용이다. **Brier score 는 이진(또는 다항) 사건 확률에만 정의되는 별개 채점**으로(예: "tripwire 발화 여부", "특정 이벤트 발생 여부"), 본 절의 연속 분포 채점과 **명시 분리**한다 — 09 §10·01 §6.3 의 Brier 규율(det-vs-ai 노드별 사후채점)은 이진 사건 표면에, 본 §4.4 는 연속 fan 표면에 적용한다. 둘을 한 지표로 섞지 않는다.

연속 fan 이 "정직한 fan"이려면 *벌어진 폭이 실제 불확실성을 맞혀야* 한다 — cosmetic 가우시안 폭(통계적 연극, 01 §5b A6)을 walk-forward held-out 으로 반증한다. 모든 채점은 **purged + embargoed walk-forward**(§4.2 #3·§2B.2 G1, look-ahead 차단)에서만 산출한다.

**(a) Coverage(밴드 적중률).** 명목 90% 밴드(P5~P95)면 held-out 실현치가 밴드 안에 떨어진 *경험 비율*이 0.85~0.95(=|empirical−nominal|≤tol, tol≈0.05 *잠정값·졸업 데모서 재보정*). 밴드가 너무 좁으면 적중률<0.85(과신), 너무 넓으면>0.97(과소확신·무용).

**(b) PIT 균등성(probability integral transform).** 각 held-out 시점 t 에서 `u_t = F_t(actual_t)`(예측 CDF 에 실현치를 통과) → 캘리브레이션이 완벽하면 `{u_t}` 가 **Uniform[0,1]**. KS 또는 χ²(bin=5) 균등성 검정 `p>0.1`(*잠정 임계·재보정*). 비균일 패턴 = 진단: U 모양=과신(꼬리 과소), ∩ 모양=과소확신, 한쪽 쏠림=편향. **10-bin PIT 히스토그램**을 진단 산출로 emit(숫자 1개로 숨기지 않음).

**(c) CRPS / pinball(분포 전체 채점).** 단일 점이 아니라 *분포 전체*를 채점 — CRPS(continuous ranked probability score) 또는 분위별 pinball/quantile loss 를 P5..P95 전 분위에서 평균. 점추정 금지 척추와 정합(단일 점 채점 거부, 분포 채점).

**(d) Skill score(baseline 대비).** `skill = 1 − CRPS_model / CRPS_baseline`(또는 pinball 비). `skill ≤ 0` = 모델이 단순 baseline 을 *못 이김* = **예측력 없음**. baseline 정의(§4.4-baseline 아래).

**(e) 캘리브레이션 robustness — prior/임계 sensitivity(design — 새 게이트 아닌 `calibScore` 2회 더 산출).** (a)~(d) 의 calibState(over/under-dispersed/통과) 판정이 *잠정 prior·임계의 함수*면 그 판정은 robust 하지 않다 — prior 를 살짝 바꾸면 통과↔미달이 뒤집히는 fan 은 "캘리브레이션 통과"가 우연이다(베이지안 prior sensitivity). 졸업 데모서 (a)~(d) 를 **두 섭동에서 재산출**한다(새 노드·새 게이트 0, 분위 함수 재호출만):
- **(i) elasticity prior ±50%(또는 off)**: σ 를 먹이는 elasticity prior(02 §2B.4·transfer.py `SECTOR_ELASTICITY`)를 ±50% 흔들거나 prior-off(검증 σ 만)로 두 번 더 채점.
- **(ii) 잠정 임계 ±1단계**: §2B.11 잠정값표의 acceptance 임계(coverage tol 0.05·PIT p 0.1·skill 등)를 ±1단계 흔들어 재채점. **임계 목록은 §2B.11 잠정값표를 재사용**(복제 0 — 본 절은 그 표를 *읽어* 섭동만 함).

calibState 가 두 섭동에서 **뒤집히면** `SimulationResult.warnings` 에 `calibration_prior_sensitive` 표면화 + fan 점선·회색(05 §3.1 σ provenance 동일 채널 — 새 토큰 0); **불변이면** `calib:robust` 라벨. 이것은 §10 #11(`skill ≤ 0` = baseline 못 이김)의 **대칭** — #11 이 *약한 baseline 을 못 이긴* fan 을 막고, (e)는 *prior 운에 기댄* 통과를 막는다. 둘 다 "통과처럼 보이나 실은 우연" 회피.

**(f) Posterior predictive 꼬리 진단(design — 분위 함수 재사용·새 노드 0, 베이지안 PPC).** (a)~(d) 의 PIT/coverage/CRPS 는 *전역* 캘리브레이션 — 분포 *전체*의 평균 적중은 보지만 **국소 꼬리 오적합**(아래 꼬리만 너무 얇음)은 못 잡는다. posterior predictive check 를 더한다: `mc.distribution`(01 §5b)이 emit 한 예측분포에서 replicated `y_rep` 의 **검정통계**를 뽑아 held-out 실현치의 동일 통계와 비교한다.
- **검정통계 3종**: ⓐ 하방 σ 비대칭(§3.7 forensic 하방비대칭이 분포에 *실제로* 반영됐는지 — 회계 적신호가 σ 를 하방으로 키웠다면 y_rep 하방 꼬리가 두꺼워야), ⓑ fat-tail kurtosis, ⓒ Ljung-Box(잔차 자기상관).
- **판정**: 관측 통계가 y_rep 분포 안에서의 위치(posterior predictive p값)가 **극단(p<0.05 또는 p>0.95)** 이면 `SimulationResult.warnings` 에 `ppc_tail_misfit` 표면화(전역 PIT 가 통과해도 국소 꼬리는 빗나감). 이로써 §3.7 의 하방 비대칭 전파가 *말로만*이 아니라 *분포에 실제 반영됐는지* 검증된다(R12 mc.distribution '측정된 비모수 예측분포'·01 §5b 와 한 결). **상태(design)**: `mc.distribution` 노드 미구현(4노드 코어 미포함) → PPC 는 그 노드 합류 후 분위·검정통계 함수만 추가(새 노드 0).

**실패 판정(과신·과소확신 *대칭*).** 90% 밴드 coverage<0.70(체계적 과신 — 밴드가 현실의 30%+ 를 놓침, 너무 좁음) = **blocked** + `calibState='under-dispersed'`. **coverage>0.97**(과소확신 — 밴드가 너무 넓어 정보가치 0, *밴드를 무한히 넓혀 coverage 를 채우는 회피*) = **usableWithGaps** + `calibState='over-dispersed'` + fan '밴드 과대·정보가치 낮음' 라벨. 그 외 mild miscalibration(coverage 0.70~0.85·PIT p<0.1·skill 미미)은 **usableWithGaps** + fan 에 '캘리브레이션 부분미달' 라벨. ★under-dispersion(좁음=과신)만 막고 over-dispersion(넓음=무용)을 안 막으면 "밴드를 키워 coverage 통과" 라는 §2B.2 silent 확대 회피가 캘리브레이션 게이트로 새므로 *대칭 enum* 으로 양방향 강등.

**표본 가드(folk-stat 회피, horizonMeaning 교훈).** **회사 단위 캘리브레이션 금지**(T<40 — held-out 분기가 한 자릿수면 coverage/PIT 가 잡음). **pooled-panel 섹터 횡단면**으로 채점(섹터 내 회사×분기 풀) + **bootstrap CI**(점추정 metric 금지·CI 동반) + **seed 고정**(재현). seed/CI=0 인 "3점 성공"은 §10 #11 으로 차단(horizonMeaning §8 정정 교훈).

**게이트 활성 조건(design·정직 라벨).** G16 은 `recordForecast` write-end 가 라이브(02 §2B.5 dead chain — `recordForecast` src 부재, grep 0건) + **N≥8분기 누적** 후에야 **active**. 그 전까지 게이트는 모든 fan 에 **'캘리브레이션 미검증' 라벨을 강제**하고 — σ 점선·회색 근사 fan(05 §3.1·§4.4 위 동일 채널)으로 그려 검증된 실선 fan 과 정직하게 가른다. 게이트 공식·임계는 코드 빌드 *전 지금* 박는다(planScore 직결, systemScore 미반영).

**메커니즘(design).** `recordForecast` 저장분 = `{asOf, projected, p5, p25, p50, p75, p95}`(예측 시점·분위 frozen) → N분기 후 실현 `actual` 을 asOf 키로 join → 위 (a)~(d) 를 산출해 `calibScore`(coverage·pitP·crps·skill 묶음) emit. recordForecast 자체가 부재라 본 join·채점 파이프는 write-end 라이브 후 졸업 AC.

**★fitProvenance 단일 field(R-mlops, ML 시스템·MLOps — field-append, BC default=None):** `recordForecast` 저장분에 `fitProvenance` 1 field 를 추가한다(스키마 *행 추가*, BC: 미배선 구간 `None`):

```text
fitProvenance = {
  driverPanelAsOf:  str,   # 적합에 쓴 driverPanel 의 asOf (02 §2B.7 data/models/driverPanel.json)
  driverPanelHash:  str,   # blake2b(driverPanel 직렬화) — 같은 적합분 식별
  codeSha:          str,   # git describe — 적합 코드 버전
  macroVintageId:   str,   # 적합 시 macro snapshot vintage (03 §3.5 releaseDate/dataAsOf)
}
```

이 지문이 *드리프트 게이트 발화*(02 §2B.5 driverDecay·Page-Hinkley)를 두 원인으로 **라벨 분해**한다 — `driverPanelHash` 가 *같은* 구간 안에서 calibScore 가 열화하면 `regime`(같은 적합분이 변한 시장에서 진다), `driverPanelHash`/`codeSha` 경계에서 점프하면 `refit`(재적합 경계의 불연속)이다. 라벨은 별도 채널이 아니라 `SimulationResult.warnings` 동일 채널(`drift_regime` / `drift_refit_boundary`)로 표면화(01 §5b elasticity_prior_unvalidated 와 같은 튜플 — 새 채널 0). 이 분해 없이는 "예측력 열화"가 *시장 변화*인지 *우리가 모델을 갈아끼운 인공물*인지 못 가른다(factor-zoo 의 시간축 false discovery 와 직교).

**★reproSeed 감사 항(02 §2B.3a admission 결선):** `admission.py` 통계 primitive(critical-t·Holm step-down·participation-ratio·bootstrap CI §4.4 표본 가드)에 **명시 `seed` 인자를 강제**(전역 RNG 의존 금지 — 09 P1 의 `random.Random(seed)` 로컬화 원리를 prefit 통계로 확장). `reproSeedAudit` GATES(09 §10 reproducibility 게이트)에 **'prefit 전역 RNG 0' 항** 추가 — 같은 `asOf` 입력이면 `driverPanelHash` 가 byte-identical(같은 asOf → 같은 driverPanel 재현)임을 단언. 전역 RNG 가 prefit 경로에 새면 같은 asOf 가 다른 panel 을 내 fitProvenance 지문이 무의미해진다(folk-stat seed=0 회귀 차단, horizonMeaning §8 교훈). 본 항은 admission/recordForecast 신설 시 박는 *설계*이며, 임계·seed 목록은 §2B.3a 와 한 결.

#### §4.4-baseline. 명시 baseline 정의 (skill 채점·R-skill SSOT)

skill score(§4.4-d)·§10 #11 이 비교하는 **명시 baseline**을 박는다(권위 환각 차단 — "baseline 보다 낫다"는 baseline 을 명명해야 검증 가능).

| 표면 | baseline | 정의 |
|---|---|---|
| 가격 fan | random-walk(drift 0) | `price_{t+h} ~ price_t`(마틴게일), 분산은 historical vol scaling |
| 가격 fan(보조) | analyst consensus target | 외부 컨센서스 목표가(있으면)를 점앵커로, 밴드는 추정치 분산 |
| 펀더멘털 fan(rev/OI/FCF) | **seasonal-naive(floor)** | `x_t ~ x_{t-4}`(작년 동분기, T≥5분기 가용 시) — 분기 매출/이익 계절성의 정직 floor |
| 펀더멘털 fan(rev/OI/FCF) | persistence | `x_{t+h} ~ x_t`(직전 분기 유지) |
| 펀더멘털 fan(보조) | AR(1) | `x_{t+h} = c + ρ·x_t + ε`(1차 자기회귀, in-sample 적합 후 OOS) |
| 펀더멘털 fan(보조) | consensus estimate | 외부 컨센서스 추정치(있으면) |

> **★seasonal-naive 가 펀더멘털 floor 인 이유(R-ts, 시계열 계량):** persistence baseline `x_{t+h} ~ x_t` 는 *분기 데이터에 계절적으로 순진*하다 — 분기 매출/이익은 강한 계절성(연말 성수기·반기 패턴)을 가지므로 작년 동분기 `x_{t-4}` 가 직전 분기 `x_t` 보다 거의 항상 더 센 baseline 이다. seasonal-naive 를 floor 에서 빼면 우리 모델이 *약한 baseline 을 이겨* skill>0 이 나오는 **낙관 편향**(§10 #11 회귀)이 생긴다. 따라서 §4.4-d skill 은 **random-walk / persistence / seasonal-naive 중 *가장 센* baseline 대비** 채점한다(가장 약한 것이 아니라 — 불공정 비교 차단). seasonal-naive 는 T≥5분기일 때만 가용(작년 동분기 1점 필요), 미달이면 persistence 로 폴백 + `seasonal_baseline_unavailable(partial)` 라벨.

baseline 도 동일 walk-forward held-out 에서 같은 분위로 채점한다(불공정 비교 차단). consensus baseline 은 데이터 부재 시 `missing`(0 대체 금지) — random-walk·persistence·seasonal-naive·AR(1) 가 항상 가용한 floor baseline(단 seasonal-naive 는 T≥5분기 조건부).

> **★§3.8 base margin 정규화 — 계절조정 결선(R-ts):** 02 §3.8 base margin 정규화 게이트(one-off 일탈 탐지)의 `N분기 median ± 2σ` 는 *계절 미조정* 이면 계절 변동을 one-off 로 오탐한다(성수기 마진 상승을 일회성 flag). 정규화는 **YoY(전년 동분기 대비) 또는 분기-계절조정 후 median/σ** 로 산출한다 — 같은 분기끼리 비교하면 계절 성분이 상쇄돼 진짜 one-off 만 남는다. 계절조정 불가(T<5분기 또는 분기 라벨 결손)면 `margin_baseline_not_deseasonalized(partial)` 라벨 + 미조정 median/σ 로 폴백(침묵 진행 금지, 02 §3.8 item 3 정직 라벨과 동일 채널).

**자료구조 핀(design):** `ScenarioFan`(02 §3.12 산출물)에 `baselineSkill: float | None` 필드 추가 — §4.4-d 의 skill score 를 fan 단위로 persist(None=캘리브레이션 미검증 또는 baseline 데이터 부재). **`skill ≤ 0` 노드는 `NodeAudit.status = "no_skill_vs_baseline"`**(현 ok/partial 에 추가) + 시각은 **점선·회색**(σ provenance 미검증 fan 과 동일 시각 채널, 05 §3.1 — 새 토큰 0) → "baseline 못 이긴 fan"을 신뢰 결론으로 위장 금지. 이 필드·enum 은 fan 표면 ship(05 Play) 시 기계 강제 표면이며, 그 전엔 *설계*다.

---

## 5. 회계와 손익 품질 검증

> **★신호→producer leaf 매트릭스(R3, design — 점검 리스트의 leaf 바인딩):** 아래 5.1~5.3 의 점검·경고 항목은 *산문 리스트*면 어느 엔진이 그 숫자를 만드는지 추적 불가다. 각 품질 신호를 **producer leaf**(그 신호를 산출하는 L2 SSOT 함수)에 바인딩해 — simulate quality 노드가 그 leaf 를 *호출*만 하고 자체 계산 0 임을 강제한다(09 §1 앵커 원리 동형). 이 표는 09 §0 simulate↔leaf 결합 표면 전수표의 **7번째 행 후보**(quality 노드 합류 시 `_EXPECTED_BINDINGS` 추가)이며, 01 §5b 후속 노드(quality 노드가 simulate DAG 에 합류할 때)와 결선한다. **현재 simulate 코어 4노드에 quality 노드는 미포함**(01 §5b) → 본 바인딩은 *설계*이며, 합류 시 leaf 호출+포장으로만 와이어링한다(점검 항목 정보는 5.1~5.3 에 보존).

| 품질 신호 | producer leaf (L2 SSOT) | 실측 위치 | 게이트 연결 |
|---|---|---|---|
| CFO/NI (현금전환) | scan `quality` 빌더 → `cfToNi` | `scan/builders/edgar/scan.py:189 _scanQuality`(필드명 실측 = `cfToNi`, 백로그 표기 `cfoToNi` 정정) | G8 Cash Quality |
| accrual ratio (Sloan 발생액) | scan `quality` → `accrualRatio` + crossStatement | `scan.py:211`·`analysis/financial/crossStatement.py:339`·`_earningsQualityCalcs.py:229` | G8 |
| 매출채권성장 − 매출성장 | `buildEvidenceForensicsMemo._revenueCashBridge` | `synth/evidenceForensics.py:350` → `receivableGrowthMinusRevenueGrowth`(`:370`) | G8·§5.1 경고 |
| earnings quality(quintile) | `_earningsQualityCalcs` (Sloan quintile) | `analysis/financial/_earningsQualityCalcs.py:229` | G8 |
| 매출-OCF bridge(분기별) | `buildEvidenceForensicsMemo` cashBridge | `synth/evidenceForensics.py:140 cash_rows` | G7 Profit·§5.3 |
| margin 신호(원가율·판관비율) | proforma/financial leaf | `analysis/financial/` (proforma 경유, 09 §0 #1 `buildProforma`) | G7·§5.2 |
| **scope 정렬(연결/별도)** | `_buildFinanceSeries(scope=…)` → panel `fs_div` 컬럼 | `providers/dart/company.py:3922`·`providers/edgar/company.py:1737` `_buildFinanceSeries(scope='consolidated')` + `core/schemas.py:84 fs_div: Series[str]`(panel SSOT) | **G1 Vintage**(scope 혼동=look-ahead 변종, §3.2) |

> **★scope 정렬 producer-leaf 바인딩(R-kifrs, K-IFRS 회계 의미론 — 비대칭 해소):** R3 가 CFO/NI·accrual·매출채권성장을 leaf 에 바인딩하면서 **scope 만 산문**(§3.2 "연결/별도 scope 혼동"·§5.1 "연결/별도 scope" 점검·§6.3(d) normalize 3곳)에 남긴 비대칭을 해소한다 — 플랜 자신의 R3 원리("산문 리스트면 어느 엔진이 그 숫자를 만드는지 추적 불가")를 scope 에는 미적용했었다. scope 는 단일 신호가 아니라 *전 신호의 정렬 축*(연결 매출과 별도 매출을 섞으면 모든 quality 신호가 오염)이라 게이트 연결이 G8 이 아니라 **G1 Vintage**(scope 정렬은 vintage integrity 의 일부)다. ★**코드 정정(code-as-truth)**: 백로그의 producer 표기 `scanQuality.scope` + `_getSeriesAndShares fs_div` 는 코드와 어긋난다 — (1) `scan/financial/quality.py` 에 `scope` 필드 **부재**(grep 0건), (2) `_getSeriesAndShares`(`_valuationHelpers.py:104`)는 `fs_div` 인자가 없고 `_buildFinanceSeries(freq="Y")`를 *scope 인자 없이* 호출(기본 `scope="consolidated"` 묵시 채택). 진짜 scope producer = **`_buildFinanceSeries(scope=…)`**(DART/EDGAR 양쪽 `scope` 키워드 인자 실재) + panel 의 **`fs_div`** 컬럼(`core/schemas.py:84` Pandera Series, panel SSOT). peer normalize(§6.3(d))의 scope 정렬도 **동일 `fs_div` 컬럼을 소비**해 SSOT 분열을 차단한다(연결/별도 정렬을 §5 와 §6.3 가 각자 재정의하지 않음).

> 바인딩 규율: quality 노드는 위 leaf 의 **반환을 읽기만** 하고 발생액·CFO/NI·scope 선택 식을 `simulate/` 안에 재정의하지 않는다(`test_simulate_leaf_ssot` 동형 가드, 09 §6). 신호가 결손이면 `NodeAudit.status=partial` + None(0 대체 금지). 합류 시 09 §0 표 7행으로 baseline 박제 + 01 §5b 표에 quality 노드 행 추가(둘 다 *설계*, quality 노드 빌드티켓 09 §10 동반).

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

#### PeerSelection 방법론 (R11, design — "단순 평균 금지"의 회귀-조정 강제)

위 경고("단순 평균으로만 사용"·"다른 stage")를 *산문 금지*가 아니라 **명세된 절차**로 강제한다. peer 비교가 정직하려면 peer 가 *비교 가능*해야 하고(성장·마진·ROIC·레버리지 통제), 통제 안 한 단순 평균은 stage-mismatch 를 숨긴다.

**(a) 후보 풀.** 동일 `IndustryGroup`(sub-sector)에서 1차 선정 — `_resolveSectorKey`(`analysis/valuation/_valuationHelpers.py`, OQ2 §2B.11 pooled 풀 경계와 **동일 2층 재사용**, 새 코드 0)를 그대로 쓴다. peer 수 부족(예: <5) 시 부모 **WICS-11 Sector**로 승격(pooled-N 폴백과 동형). 풀 구성은 **decisionAt 시점 멤버십**(§4.2 #5 survivorship 가드 — 상폐사 폐지 시점까지 포함).

**(b) 회귀-조정(핵심 — 단순 평균 금지를 회귀로 인코딩).** 각 peer multiple(EV/EBIT·P/E·EV/Sales)을 `multiple ~ f(revenue growth, margin, ROIC, leverage)` **cross-sectional 회귀**로 적합(`crossRegression.fitPanel` 실재, `_crossRegressionFit.py:136`) → 회귀로 조정된 multiple(target 의 펀더멘털을 회귀식에 대입한 fitted multiple)만 비교에 쓴다. **단순 산술평균·중앙값 단독 금지** — peer 가 평균보다 빠르게 성장하거나 마진이 높으면 그 프리미엄을 회귀가 흡수한다. **★자유도 가드(folk-stat 차단 — 02 §2B.9 firm-level df≤0 가드와 동형):** `peer N − 회귀변수수(4) < floor`(잠정값 ≥8 여유)면 **회귀-조정 금지** → (e) fitted multiple 대신 통제 안 한 peer P25/P50/P75 분포 + `'regression-adjustment skipped — insufficient peer DoF'` 라벨 폴백. (a)의 'peer<5 → WICS-11 승격'은 *풀 크기*만 보고 회귀 *자유도*를 안 보므로, 승격 후에도 DoF 부족하면 fitted multiple 을 발간하지 않는다(자유도 0 근방 회귀는 spurious 과적합 — `_quickOLS` df≤0 folk-stat 재현). 졸업 AC: **'peer DoF 부족 시 fitted multiple 발간 0건'**.

**(c) lifecycle 불일치 게이트.** peer 와 target 의 revenue CAGR·ROIC 가 **다른 사분위**면 `stage-mismatch` 라벨 + 해당 peer 가중 하향(또는 풀 제외). 성장기 peer multiple 을 성숙기 target 에 적용하는 confound 차단(§5.1 lifecycle 차이 점검의 정량화).

**(d) normalize.** accounting scope(연결/별도) 정렬 + multiple 분모(EBIT·매출·이익)에서 **일회성 항목 제거**(§5.2 일회성 조정과 결선) — 분모가 일회성으로 부풀면 multiple 이 거짓 저평가로 읽힘.

**(e) 출력.** peer **조정 multiple 의 P25/P50/P75**(단일 점 금지·분포 — 점추정 척추 정합) + **target percentile**(조정 후 분포 내 위치) + **DCF range cross-check**. relative valuation 의 함축가치가 §6.1 DCF range 와 **어긋나면 `DisagreementLedger` 행**(§7.3) 추가 — 두 가치평가 경로의 불일치를 숨기지 않는다(usableWithGaps, 단정 금지).

> **상태(정직):** PeerSelection 절차는 `crossRegression.fitPanel`·`_resolveSectorKey` 실재 leaf 를 호출하는 *설계*다. relative valuation 노드는 simulate 코어 4노드에 미포함(01 §5b reverseDcf 와 같은 후속) → 합류 시 leaf 호출+포장으로 와이어링하고 회귀·정렬을 `simulate/` 안에 재정의하지 않는다(09 §6 앵커 가드).

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

### 8.1 Reverse Stress (결정론 역탐색 — 새 노드 0, sensitivity grid 역읽기, design)

위 1~8 은 *가정 → 결과* forward propagation 이다. Reverse stress 는 그 방향을 **뒤집어** — *결과가 깨지는 가정 임계*를 역산한다(리스크 관리 reverse stress 기법: "얼마나 틀려야 깨지나"). 새 탐색 노드를 만들지 않고 **02 §3.12 item 4 의 deterministic sensitivity grid 를 역방향으로 읽는다** — grid 가 이미 (driver shock 격자 → perShare/NodeAudit) 매핑을 산출하므로, 그 격자 셀에서 다음 임계를 *역으로* 찾는다:

- **닻-붕괴 임계**: `perShare` 가 reverseDCF 닻(현재가가 요구하는 implied value, 08 §2·03 §6.2) *아래로* 내려가는 가장 가까운 driver 값.
- **NodeAudit incoherent 임계**: `NodeAudit.status` 가 ok→partial/incoherent 로 뒤집히는(예: terminal growth 제약 위반·negative spread·CFO/NI 정합 붕괴, §6.1·§5.3) 가장 가까운 driver 값.

산출 = **`ReverseStressLedger`** 행: `{driverId, breakingThreshold(붕괴 임계값), currentValue, breakDistance(=|threshold − current| 또는 상대거리)}`. 05 §6.1 Assumption Ledger 밀도표에 **`break-distance 오름차순` 정렬키 1개** 추가(가장 *깨지기 쉬운* 가정이 위로 — 새 컬럼·새 패널 0, 기존 정렬가능 표의 정렬키 항목만). break-distance 작은 행 = "이 가정이 조금만 틀려도 닻이 깨진다" = premortem 1순위.

> **인과 단정 금지(정직 가드):** ReverseStressLedger 의 "이 가정이 임계 도달 시 perShare < 닻"은 **조건부 산수**(sensitivity grid 역읽기의 결정론 사실)지 *예측·확률·발생 가능성*이 아니다. "임계 도달 확률 NN%"·"닻 깨질 것"은 금지(02 §121 P(event) 점확률 발간 금지와 정합) — 임계까지의 *거리*만 정직히 표면화하고, 그 거리가 가까운지/먼지의 판단은 사용자 몫(scenario≠forecast 척추). **상태(정직):** sensitivity grid 노드(`scenarioSensitivity` leaf)는 simulate 코어 4노드에 미포함(01 §5b 후속) → ReverseStressLedger 는 그 grid 합류 후 역읽기로 와이어링하는 *설계*이며, grid 셀 위에서 임계 역산만 한다(새 계산 leaf 0).

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

> **★AI lens 발간 규제지위(R-reg, 발간 관할-규제 정합 — defer 조건 1줄):** 위 A7 흡수는 AI lens 가 *내부* hypothesis 라벨까지만 노출함을 박았으나, **A7 공개 리더보드/rationale 가 라이브되어 *발간 표면*으로 나가는 순간의 규제 고지**는 미명세였다. defer 조건에 한 줄을 더한다 — **A7 공개 발간 시 면책 4키(08 §7 rank23 — hypothetical·criteria·assumptions·falsifier)에 AI-rationale 전용 고지 1키를 추가**: ⓐ AI rationale 은 *hypothesis* 이며 fact 로 미승격, ⓑ 비결정론이라 *재현성 보증 밖*(08 §8 F-1: AI lens `.ai` 슬롯 = byte-parity 제외), ⓒ 비교 *baseline 명시*(§4.4-baseline — 어느 baseline 대비 Brier 인지). 이 1키는 면책 4키와 *동시 표시*(SEC Marketing Rule·FINRA 2210 hypothetical performance 의 'criteria/assumptions 노출' 요건을 AI 산출에도 충족). 발간 표면 ship 전엔 *설계*(`lens.py`/`gate.py` 미배선, 위 fail-closed 결선표 DisagreementLedger 행과 동형).

> **★고지 채널 분리(05 §12 온보딩 ↔ 상존 고지 — 본 03 의 cross-ref 지시):** 위 AI-rationale 고지·면책 4키는 **발간/캔버스 상존 고지**(05 §2 "가정 하의 가상 경로 · 투자권유 아님 · [conf:30]" 워터마크·08 §7 면책)이지 *온보딩 1회성 고지*가 아니다 — 둘은 별개 채널이다. 05 §12 온보딩 절(휘발·dismiss·재방문 skip)에 "**온보딩 고지 skip 이 상존 고지(05 §2 캔버스 워터마크·면책 4키+AI-rationale 1키)를 끄지 않는다**" 1줄을 더해야 한다(온보딩을 건너뛴 사용자도 상존 고지는 항상 본다 — 규제 고지는 dismiss 불가). *05 는 본 패널 owner 밖*이라 본 항은 05 §12 owner 에게 cross-ref 지시로 남긴다(03 = 규제지위 SSOT, 05 = 표시 채널).

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
11. 명시 baseline(가격=random-walk·펀더멘털=seasonal-naive[floor]/persistence/AR(1)·analyst-consensus, §4.4-baseline — 펀더멘털은 *가장 센* baseline 대비) 대비 `skill ≤ 0`(예측력 없음)인 예측을 신뢰 결론으로 표시함 — baseline 못 이긴 fan 은 `NodeAudit.status="no_skill_vs_baseline"`(§4.4-d)·점선 회색 시각 강제. seed/CI 0 인 "3점 성공"을 캘리브레이션 통과로 표시하는 것도 동일 위반(folk-stat, horizonMeaning §8 교훈).

