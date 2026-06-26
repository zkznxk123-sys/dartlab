# 02b · 포워드 전망 격상 — driver 기반 + 백테스트된 전망 (Forecast Uplift)

> 출처: 예측·재무모델링 직독 (`analysis/forecast/**` 22 파일 + `analysis/financial/_proformaCore.py` + `analysis/valuation/dcf.py` + `quant/benchmark/forecast.py`). 운영자 원칙 박제: **정직-스킵 = 무능. 엔진은 *진짜* 전방 전망을 모델링한다 (driver 기반·검증됨) — 순진 외삽도 스킵도 금지. 금지 = 날조 (방어 가능한 방법론·검증 없는 전망).** 백테스트된 방법론을 가진 전망은 분석이다. SSOT 를 개선한다 — 병렬 빌드 금지.
> 본 문서는 PRD §3 [8] 포워드뷰 · §8 게이트 5(백테스트된 전망)·8(미검증 확신 금지) 을 *코드 레벨*로 박는다. 02(밸류 격상)·02b(전망 격상)는 같은 driver 항등식을 공유한다 (g = 재투자율 × ROIC, ROIC→WACC fade).

---

## 1. SSOT 맵 (file:line)

전망은 **3 계층**으로 흩어져 있다. 본 격상의 SSOT 는 `analysis/forecast/` (L2) 이고, financial·valuation·story 는 소비자다.

### 1.1 매출 전망 본체 (L2 forecast)
| 역할 | 위치 | 핵심 |
|---|---|---|
| 4-소스 앙상블 진입 | `src/dartlab/analysis/forecast/_revenueForecastCore.py:40` `forecastRevenue()` | timeseries+consensus+roic+segment+backlog 가중평균. `forecastable` 게이트 = `:443-455` |
| 단일 메트릭 시계열 모델 | `src/dartlab/analysis/forecast/_forecastMetric.py:19` `forecastMetric()` | **OLS / cagr_decay / mean_revert 3-모델 자동선택** (`:145-177`). 매출 전망의 실제 엔진 |
| 마진 연동 이익 전망 | `_forecastMetric.py:211` `_marginLinkedForecast()` | 매출전망 × **최근 3년 가중평균 마진** (`:246-253`). 마진을 *고정* — 격상 핵심 표적 |
| 다중 메트릭 일괄 | `_forecastMetric.py:276` `forecastAll()` | revenue→OPM/NI 마진연동→OCF. DCF·시나리오 사전 단계 |
| ROIC 내재성장 | `_revenueForecastHelpers.py:54` `_fundamentalGrowth()` | **g = ROIC × 재투자율** (Damodaran, `:159`). *이미 존재* — 가중치 15% 에 묻혀있음 |
| 라이프사이클 분류 | `_revenueForecastHelpers.py:180` `_classifyLifecycle()` | high_growth/mature/transition/decline. fade 의 입력 |
| 앙상블 가중치 | `_revenueForecastHelpers.py:289` `_computeWeights()` + `:241` `_lifecycleWeightAdjustments()` | 구조변화 페널티 포함 |
| 3-시나리오 빌더 | `_revenueForecastSegments.py:342` `_buildScenarios()` | **bull/bear = base ± σ × lifecycleSpread × timeFactor** (`:377-395`). σ 는 과거 성장률 표준편차지 검증된 오차 아님 |
| 세그먼트 bottom-up | `_revenueForecastSegments.py:58` `_extractSegmentForecasts()` + `:161` `_segmentBottomUpGrowth()` | 부문별 forecastMetric 합산. 매출만, 마진 없음 |
| 수주잔고 선행 | `_revenueForecastSegments.py:213` `_computeBacklogSignal()` | B/R ratio → impliedGrowth. 건설/조선/방산 강신호 |
| OLS·구조변화 커널 | `src/dartlab/core/utils/ols.py:12` `ols()` · `:185` `detectStructuralBreak()` (Chow) · `:235` `coefficientOfVariation()` | 순수 Python, 외부 의존 0 |

### 1.2 Pro-forma 3-statement (L2 financial)
| 역할 | 위치 | 핵심 |
|---|---|---|
| 3-statement 빌더 | `src/dartlab/analysis/financial/_proformaCore.py:376` `buildProforma()` | revenueGrowthPath → IS/BS/CF 회계잠금 추정. 마진은 **비율 트렌드 경로** `_ratioForYear()` `:480` (선형 외삽) |
| 회사별 WACC | `_proformaCore.py:145` `computeCompanyWacc()` | Damodaran CAPM. *이미 회사별* — 02 가 DCF 에 배선 |
| 기준연도 스냅샷 | `_proformaCore.py:334` `_extractBaseYear()` | TTM 기반 base |
| financial 어댑터 | `src/dartlab/analysis/financial/_forecastCalcsRevenue.py:12` `calcRevenueForecast()` · `:106` `calcSegmentForecast()` | `forecastRevenue` → story dict. `forecastable=False` 전파 |
| financial 헬퍼 | `src/dartlab/analysis/financial/_forecastCalcsHelpers.py:90` `_runForecastRevenue()` | company → CompanyDataBundle → forecastRevenue (horizon=3 하드코딩) |

### 1.3 백테스트 인프라 (이미 존재 — 단 *prospective* only)
| 역할 | 위치 | 상태 |
|---|---|---|
| Forward test 저장/평가 | `src/dartlab/analysis/forecast/forwardTest.py` `saveForecast()`/`evaluate()`/`evaluateCalibration()` | **저장→실적 대기→사후평가**. 과거 윈도 백테스트 *아님* — ground truth 가 미래라 비어있음 |
| 캘리브레이션 메트릭 | `src/dartlab/analysis/forecast/calibrationMetrics.py` `computeBrierScore`/`generateCalibrationReport` | Brier·reliability bin. **방향확률 전용**, 매출 MAPE 백테스트 없음 |
| 시나리오 확률 보정 | `src/dartlab/analysis/forecast/calibrator.py:16` `calibrateScenarios()` | 외부 신호로 prior 재가중 |
| 가격 walk-forward (모범) | `src/dartlab/quant/benchmark/forecast.py:280` `forecastReturns()` + `:485` `forecastRuleFactory()` | **이미 walk-forward + conformal interval + OOS 검증** (`test_forecast.py` 35 케이스). 펀더멘탈 전망이 따라야 할 표준 |

### 1.4 DCF 소비자 (전망의 종착점)
| 역할 | 위치 | 핵심 |
|---|---|---|
| FCF 투영 | `src/dartlab/analysis/valuation/_dcfHelpers.py:122` `_projectFcf()` | `proformaFCF` 있으면 우선, 없으면 initialGrowth→tg blend |
| DCF 본체 | `src/dartlab/analysis/valuation/dcf.py:455-457` | **`initialGrowth = clamp(revCagr3Y, -5%, +15%)`** — 순진 CAGR 외삽 |
| 재투자 미연동 | `dcf.py:194-197` | `marginPath` 받고 **`pass`** — 성장에 재투자 안 묶임 (무에서 가치창조) |
| story 전망 블록 | `src/dartlab/story/builders/forecast.py:17` `proFormaHighlightsBlock()` · `:89` `forecastMethodologyBlock()` | 소스 가중치·가정 노출. 표시층 |

---

## 2. 현재 방법 + 왜 아마추어인가

### 2.1 실제로 무엇을 하는가 (코드 직독 요약)
`forecastRevenue` 는 4 소스를 가중평균하지만, **지배 소스인 `forecastMetric` 의 실체는 단일변량 시계열 외삽**이다 (`_forecastMetric.py:145-177`):
- `cv > 0.4` → **mean_revert**: 최근값 → 과거평균 선형 블렌드.
- `r² > 0.7 & |cagr| < 30` → **linear**: OLS 추세 연장.
- else → **cagr_decay**: 과거 CAGR → 섹터평균(기본 3%)으로 감속.

이익은 `_marginLinkedForecast` 가 **최근 3년 가중평균 마진을 그대로 곱한다** (`:246-253`) — 마진을 미래에 *고정*. pro-forma `_ratioForYear` 도 마진을 과거 트렌드로 *선형* 연장할 뿐 (`_proformaCore.py:480`). DCF 는 한술 더 떠 `revCagr 3Y 를 [-5,15] clamp` (`dcf.py:457`).

### 2.2 왜 아마추어인가 (4 결함, 코드 증거)
1. **driver 분해 없음 — 단일변량 외삽.** 매출을 "추세선"으로 본다. *왜* 성장하는지 (물량·단가·점유율·시장성장) 가 모델에 없다. `cagr_decay` 의 terminal=섹터평균 3% 는 임의값 (`_forecastMetric.py:143`). → PRD §8.5 위반("막연한 성장 금지").
2. **마진 고정.** `_marginLinkedForecast` 가 OPM 을 trailing 평균으로 고정 (`:248`). 영업레버리지(매출↑ 시 고정비 희석로 OPM 확대)·역레버리지를 못 잡는다. 마진은 비용구조의 *함수*인데 상수로 박았다.
3. **시나리오 밴드 = 통계 잡음, driver 아님.** bull/bear = base ± `과거성장 σ × lifecycleSpread(1.5~2.0) × (1+0.15·t)` (`_revenueForecastSegments.py:384`). σ 는 *과거 변동성*이지 *검증된 예측오차*가 아니다. PRD §5 "±10% 장난 금지" 위반 — 세 driver(성장·마진·WACC)를 움직여 만들어야 한다.
4. **자기 정확도 백테스트 0.** `forwardTest.py` 는 예측을 저장하고 *미래 실적*을 기다린다 — 과거 윈도 백테스트가 없어 **track record 가 영원히 비어있다**. `forecastable` 게이트(`_revenueForecastCore.py:452`)는 *입력 가용성*만 본다 (방법 정확도 아님). confidence high/medium/low 는 r²·소스 수로 *추정*할 뿐 실측 검증이 아니다. → PRD §8.8 위반("백테스트/민감도로 증명 후 탑재").

**판정**: 정직 스킵이 아니라 **방법이 약하고 검증이 없다.** 추측을 전망으로 분장.

---

## 3. 전문 driver 기반 방법 + 데이터 소스

핵심 전환: **"추세선 연장" → "동인 항등식 + mean-reversion fade + 영업레버리지 마진 + 검증된 밴드".** 이미 보유한 자산(`_fundamentalGrowth`·`computeCompanyWacc`·`detectStructuralBreak`·세그먼트·backlog)을 *지배 경로*로 승격하고, 외삽은 fallback prior 로 강등한다.

### 3.1 매출 driver 분해 (분해 가능한 곳)
우선순위 계단 — 위에서부터 데이터 있으면 채택, 없으면 다음:
1. **세그먼트 물량 × 단가** (제조·소비재): 세그먼트 매출 시계열 (`_extractSegmentForecasts`) 을 부문별 성장으로 분해, 가능하면 물량/단가 split (DART 주석 수량 공시 — `project_terminal_note_composition_cells` 셀). 데이터 소스: `company.segments.revenue` (axisPath).
2. **수주잔고 → 매출 전환** (건설·조선·방산): `_computeBacklogSignal` B/R ratio × 전환율 (이미 존재, `_revenueForecastSegments.py:304`). 강신호 섹터 가중↑.
3. **시장성장 × 점유율** (도출 가능 시): 섹터 GDP 탄성치 (`SectorElasticity.revenueToGdp`) × 회사 점유율 추세. 매크로 엔진 `macro/` 결합.
4. **재투자 묶인 내재성장** (항상 가능, 본 격상의 *기본 경로*): `_fundamentalGrowth` 의 `g = ROIC × 재투자율` (`_revenueForecastHelpers.py:159`). **이것을 외삽 대신 base growth 로**.

### 3.2 명시적 mean-reverting fade (분해 불가 구간)
flat trailing CAGR 폐기. 고성장은 **섹터/GDP 로 fade** — fade 파라미터를 *명시*한다:
```
g(t) = gTerminal + (g0 − gTerminal) × exp(−λ·t)
  g0        = 1순위 driver 성장 (3.1), 없으면 정규화 CAGR
  gTerminal = max(섹터 GDP 탄성 성장, 장기 실질GDP+인플레 ≈ 4~5% KR)
  λ (fade)  = lifecycle 별 — high_growth 0.35(빠른 수렴)·mature 0.7·transition 0.5·decline 0.5
```
fade 는 Damodaran 수렴 원칙 (초과성장은 경쟁으로 소멸). λ 와 gTerminal 은 **결과 dict 에 노출** (PRD §8.5 정량화). `cagr_decay` 의 임의 선형감속(`_forecastMetric.py:166-177`)을 이 지수 fade 로 교체.

### 3.3 마진 궤적 (비용구조 동학)
고정 마진 폐기. **영업레버리지 모델**:
```
OPM(t) = OPM_base + leverageBeta × (revGrowth(t) − revGrowthNormal)
  leverageBeta = ΔOPM / ΔRev 회귀 기울기 (과거 4~6년, ols.py 재사용)
                 = 고정비/변동비 split proxy. 매출 민감 OPM 탄성
  상·하한      = 과거 OPM min/max × 1.2 (역사적 범위 밖 외삽 차단)
```
데이터 소스: IS 시계열 매출·영업이익 (이미 series 에 있음). `leverageBeta` 산출 불가(< 4년·r² 낮음) 시 → 마진 *고정* fallback + 경고 (정직 경계). 무한 마진확대 방지 상·하한 필수.

### 3.4 시나리오 = driver 가정 (통계 밴드 아님)
bull/base/bear 를 **세 driver 를 명시적으로 움직여** 생성 — 각 가정 노출:
| driver | bear | base | bull |
|---|---|---|---|
| 매출성장 g0 | base − 1σ_driver | driver | base + 1σ_driver |
| fade λ | 빠른 수렴(×1.3) | base | 느린 수렴(×0.7) |
| 마진 leverageBeta | 0 (레버리지 무) | 추정 β | 1.5×β (레버리지 강) |
σ_driver 는 driver 입력의 불확실성 (세그먼트 분산·backlog 변동), **§4 백테스트 오차로 캡**. `_buildScenarios` 의 σ×spread×timeFactor(`_revenueForecastSegments.py:384`)를 driver 교란으로 교체. 각 시나리오는 "성장 X%·마진 Y% 가정" 문장 동반.

---

## 4. 백테스트 하니스 설계 (결정타)

**원칙**: track record 있는 전망 = 프로, 없으면 추측. `quant/benchmark/forecast.py` 의 walk-forward 를 *펀더멘탈 연간 전망*에 이식한다. 신규 모듈 `analysis/forecast/_revenueBacktest.py`.

### 4.1 핵심 — historical walk-forward (rolling origin)
```
for each company c, for each past origin year t (t = T−2 ... T−maxHorizon):
    seriesAtT = series 를 t 시점까지 절단 (lookahead 차단 — 핵심)
    fcst      = forecastRevenue(seriesAtT, horizon=2)   # t 에서 t+1, t+2 예측
    actual    = 실현된 t+1, t+2 매출 (series 에 이미 있음)
    record per (company, origin t, horizon h):
        ape   = |fcst[h] − actual[h]| / actual[h]
        dirHit = sign(fcst growth) == sign(actual growth)
        bandHit = bear[h] ≤ actual[h] ≤ bull[h]
```
**lookahead 차단**이 생명 — `seriesAtT` 는 t 이후 분기를 0 으로 잘라야 한다 (`getAnnualValues` 슬라이싱). consensus 소스는 백테스트 시 *비활성* (당시 consensus 재현 불가 → timeseries+roic+segment+backlog 만).

### 4.2 집계 — horizon × sector MAPE 분포
```
출력 BacktestReport:
  byHorizon:  {h1: {mape_median, mape_p90, dirAccuracy, bandCoverage, n}, h2: {...}}
  bySector:   {반도체: {mape_median, n}, 화학: {...}}
  overall:    {mape_median, dirAccuracy, bandCoverage90, nForecasts}
  baseline:   naive(전년동일)·CAGR 외삽 대비 skill = 1 − mape_method/mape_naive
```
bandCoverage = 실현치가 bull/bear 밴드 안에 든 비율 → **밴드가 정직한지** 검증 (90% 밴드면 ≈90% 들어와야). `forwardTest.evaluate` 의 MAPE·directionAccuracy·scenarioHit 로직(`forwardTest.py:243-266`)을 *과거 윈도*에 재사용 (이미 구현됨 — origin 절단만 추가).

### 4.3 데이터·실행
- 유니버스: 시계열 ≥ 6년 전상장사 부분집합 (백테스트는 long history 필요). 섹터 균형 샘플.
- 실행: 오프라인 배치 (`prebuild` 아님 — 검증 산출물은 SSOT 데이터 아니므로 테스트/리포트 메타). 결과는 `tests/_attempts/forecastBacktest/` 에서 졸업 후 `analysis/forecast/_revenueBacktest.py` + baseline JSON.
- 메모리: Company 200~500MB OOM 가드 — 순차 처리, 회사별 series 즉시 해제.

---

## 5. 구체 격상 (변경/추가 함수)

### 5.1 변경 (기존 SSOT 개선 — 병렬 빌드 금지)
| 파일:함수 | 변경 |
|---|---|
| `_forecastMetric.py:145-177` `forecastMetric` | `cagr_decay` 분기를 **§3.2 지수 fade** 로 교체. terminal=섹터평균 → gTerminal(GDP 탄성). λ·gTerminal 을 ForecastResult 에 노출 (신규 필드 `fadeParams`) |
| `_forecastMetric.py:211` `_marginLinkedForecast` | 고정 마진 → **§3.3 영업레버리지** `OPM(t) = OPM_base + β·Δg`. β 회귀(ols.py) + 역사적 상·하한. β 불가 시 고정+경고 |
| `_revenueForecastCore.py:191-233` 가중치 | driver(roic·segment·backlog) 가 *지배*, timeseries 외삽은 fallback prior 로 강등. `_ROIC_WEIGHT` 0.15→상향, driver 가용 시 외삽 floor 0.10 유지 |
| `_revenueForecastSegments.py:342` `_buildScenarios` | σ×spread 통계밴드 → **§3.4 driver 교란**. σ 는 §4 백테스트 p90 오차로 캡 |
| `_revenueForecastCore.py:443-455` `forecastable` 게이트 | 입력가용성 + **백테스트 통과 여부** 결합 (§6). 미달 시 forecastable=False *지만* mean-reversion prior 는 항상 반환 (스킵 금지) |
| `dcf.py:455-457` initialGrowth | clamp(CAGR) → `forecastAll` 의 driver 성장 경로 소비 (proformaFCF 우선은 이미 `_dcfHelpers.py:131`). 02 와 공동 |
| `_proformaCore.py:480` `_ratioForYear` | 마진 선형트렌드 → §3.3 레버리지 마진과 정합 |

### 5.2 추가 (신규)
| 신규 | 위치 | 역할 |
|---|---|---|
| `_revenueBacktest.py` | `analysis/forecast/` | §4 walk-forward 하니스 (`backtestForecast(company, maxHorizon=2)` + `aggregateBacktest(universe)`) |
| `fadeParams`·`leverageBeta`·`backtestMape` 필드 | `_revenueForecastTypes.py` `RevenueForecastResult` / `_forecastTypes.py` `ForecastResult` | driver 파라미터·검증 오차 노출 (PRD §8 정량화) |
| `_driverGrowth()` | `_revenueForecastHelpers.py` | §3.1 계단 (segment→backlog→market×share→roic) 단일 진입. 기존 헬퍼 조립 (재구현 0) |
| `backtest baseline JSON` | `tests/audit/_baselines/forecastBacktest.json` | horizon×sector MAPE 부채 원장 (회귀 가드) |

원칙: **재구현 0.** `_fundamentalGrowth`·`computeCompanyWacc`·`detectStructuralBreak`·`ols`·`forwardTest.evaluate`·세그먼트·backlog 전부 *기존 함수 조립*. 신규는 fade·레버리지·backtest origin-절단 *3 개 로직*뿐.

---

## 6. 졸업 게이트 (백테스트 합격선 + 불확실성 표면화)

전망이 리포트(PRD §3 [8])에 *들어가려면* 백테스트를 통과해야 한다. horizon 별 오차 한계:

| 게이트 | 합격선 (horizon=1 / horizon=2) | 근거 |
|---|---|---|
| G1 매출 MAPE median | ≤ 8% / ≤ 15% | sell-side 컨센서스 매출 1Y MAPE ≈ 5~10% 벤치. naive 외삽 대비 skill > 0 필수 |
| G2 방향 정확도 | ≥ 70% / ≥ 60% | 동전(50%) 대비 유의. `forwardTest.evaluate` directionAccuracy |
| G3 밴드 커버리지 | 80~95% (90% 밴드 기준) | 밴드가 *검증된 오차* 임을 증명. 너무 좁으면(<80%) σ 확대, 너무 넓으면(>95%) 무의미 |
| G4 baseline skill | mape_method < mape_naive (전 섹터 중앙값) | 외삽보다 나음을 *실측*. 1 섹터라도 역전 시 해당 섹터 외삽 fallback |

**밴드 = 검증된 오차** (§3.4 σ_driver 를 G3 backtest p90 으로 캡) — 임의 ±% 가 아니다. 미달 섹터는 confidence 강등 + 리포트에 "이 섹터 전망 검증 미달" 명시.

### 6.1 정직 경계 (스킵 금지, 그래도 답한다)
driver 모델조차 입력이 없는 경계 — **그래도 mean-reversion prior 를 준다**:
- **시계열 < 3년**: forecastMetric 이미 N/A 반환 — 대신 **섹터 GDP 탄성 성장 prior** + "history 부족, 섹터 prior 적용" 명시.
- **regime break** (`detectStructuralBreak` 양성): break 이후 구간만 학습 (이미 `_forecastMetric.py:125-132`) + confidence 강등 + "구조변화로 과거추세 신뢰 제한" (이미 경고).
- **백테스트 G1~G4 미달**: forecastable=False *표시* 하되, base mean-reversion 경로(g0=정규화CAGR→gTerminal fade)는 항상 출력. "방법 검증 미달 — 보수적 prior" 라벨.

→ 어떤 경우도 빈칸/스킵 0. PRD §8.6 "게으른 스킵 금지" + 운영자 "정직-스킵=무능" 충족.

---

## 7. 통합 (DCF + 포워드뷰 섹션 급전)

### 7.1 DCF 급전 (proformaFCF 계약)
이미 배선됨 — `_dcfHelpers.py:122 _projectFcf` 가 `proformaFCF` 우선 (`:131-137`). 격상 후:
```
forecastAll(series) → driver 매출경로 + 레버리지 마진
  → buildProforma(series, revenueGrowthPath=driver경로)  # _proformaCore.py:376
  → ProFormaYear.fcf 시계열                                # :601
  → dcf(series, proformaFCF=[yr.fcf ...])                  # _dcfHelpers.py:131 소비
```
**계약**: DCF 의 initialGrowth clamp (`dcf.py:455-457`) 는 proformaFCF 있으면 *우회*됨 → driver 경로가 자동 지배. 02(밸류)와 *동일 driver 항등식* 공유 (g=재투자율×ROIC, ROIC→WACC fade). 재투자 미연동(`dcf.py:194 pass`)은 proforma 가 capex·ΔNWC 를 회계로 잠그므로(`_proformaCore.py:528,597`) 자동 해소.

### 7.2 포워드뷰 섹션 급전 (리포트 [8])
`story/builders/forecast.py` 는 *표시*만 — 격상은 데이터 dict 풍부화:
- `calcRevenueForecast` (`_forecastCalcsRevenue.py:12`) 출력에 `fadeParams`·`leverageBeta`·**`backtestMape`(섹터별)** 추가 → `forecastMethodologyBlock` (`forecast.py:89`) 이 "이 방법은 과거 N년 백테스트 MAPE X% (방향 Y%)" 노출.
- `proFormaHighlightsBlock` (`forecast.py:17`) 의 성장경로에 fade 곡선·시나리오 driver 가정 동반.
- 랜딩 `/report` 포워드뷰: 같은 dict 소비 (TS contract `report.ts` scenario·driverTree 블록 — 03 문법). **track record 를 시각화** (MiniFinChart SSOT) = 차별화.

### 7.3 신뢰도 표면화
밴드(§3.4) = §4 백테스트 p90 오차 → "이 전망의 90% 구간은 과거 검증 오차 기반" 문장. confidence high/medium/low 를 *백테스트 통과 게이트*(§6)와 결합 — r² 추정이 아닌 실측 정확도.

---

## 8. 리스크

1. **백테스트 표본 부족.** 6년+ 시계열 전상장사 부분집합이라 섹터별 n 작을 수 있음 → bySector 신뢰 흔들림. 완화: n<10 섹터는 overall 로 묶고 "섹터 표본 부족" 표기. 게이트는 overall 우선.
2. **lookahead 누수.** origin 절단 실수 시 백테스트 정확도 과장 (가장 위험). 완화: `seriesAtT` 절단을 단위테스트로 강제 (t+1 데이터가 fcst 입력에 0건). consensus 소스 백테스트 비활성 필수.
3. **OOM (CLAUDE.md 가드).** 회사×origin×horizon 루프가 Company 다수 로드 → Polars Rust 힙. 완화: 순차+즉시해제, 병렬 agent ≤ 2, `tests/_attempts/` 에서 검증 후 본진.
4. **레버리지 β 과적합.** 4~6점 회귀라 β 불안정 → 마진 폭주. 완화: 역사적 OPM min/max×1.2 상·하한 (§3.3), r²<0.3 시 고정 fallback.
5. **fade λ 임의성.** lifecycle 별 λ 도 결국 가정 — "CAGR clamp 와 뭐가 다른가" 비판. 방어: λ 는 *노출*(투명)+ §4 백테스트가 λ 셋의 MAPE 를 실측 (G4) → 데이터가 λ 를 검증, 임의값이 아님.
6. **병렬 빌드 유혹.** "전망 전용 새 엔진" 만들고 싶을 수 있음 — *금지*. SSOT(`analysis/forecast/`) 개선만. 신규는 fade·레버리지·backtest 3 로직 + 필드 추가뿐, 나머지 조립.
7. **졸업 게이트 미통과 시 전체 블록.** G1~G4 미달이면 전망이 리포트에서 약해 보임 → "그냥 통과시켜" 압력 (`feedback_plan_score_not_signature` 사례). 방어: 미달=정직 라벨 + 보수적 prior 출력, 점수 인플레 금지.

---

> **요약 한 줄**: 단일변량 추세외삽 + 고정마진 + 통계밴드 + 백테스트0 (아마추어) → **driver 항등식(g=ROIC×재투자, segment/backlog/market×share) + 지수 fade(λ 명시) + 영업레버리지 마진 + driver 교란 시나리오 + walk-forward 백테스트(horizon×sector MAPE, lookahead 차단)** 로 격상. 기존 자산(`_fundamentalGrowth`·`computeCompanyWacc`·`forwardTest.evaluate`·세그먼트·backlog·ols)을 조립 — 신규 3 로직(fade·레버리지·origin-절단)뿐. 게이트 = G1 MAPE ≤8/15% · G2 방향 ≥70/60% · G3 밴드커버 80~95% · G4 baseline skill>0. 밴드 = 검증된 오차. 입력 없어도 mean-reversion prior — 스킵 0.
