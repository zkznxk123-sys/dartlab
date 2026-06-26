# 02 · 능력 엔진 격상 — 종합 index

> 6 전문 에이전트가 각 SSOT 를 직독. 상세 = [02a](02a-valuation-uplift.md) · [02b](02b-forecast-uplift.md) · [02c](02c-segment-economics.md) · [02d](02d-quant-moat.md) · [02e](02e-credit-wiring-macro.md). 본 문서 = 종합·의존그래프·게이트 원칙.

## 0. 관통하는 발견 — "이미 다 있는데 꺼져 있다"

모든 능력에서 동일 패턴이 나왔다: dartlab 은 프로 기계를 **이미 소유**하고 있고, 다만 (a) 게이트로 꺼져 있거나 (b) 가중치에 묻혀 있거나 (c) 라이브 미배선이다. → 격상 = 대부분 **de-gate + 배선 + 검증**, 처음부터 빌드 아님. "능력부족"의 실체 = *능력 부재가 아니라 조립이 아마추어*.

## 1. 엔진별 요약

| 엔진 | SSOT | 핵심 결함 | 격상 (대부분 de-gate) | 졸업 게이트 |
|---|---|---|---|---|
| **밸류에이션** (02a) | `analysis/valuation/` + `analysis/financial/_valuationDeep*` | 프로 레버를 *이미 보유*(bottom-up WACC `computeCompanyWacc`·Hamada β·implied ERP·reverse-DCF `priceImplied.py`·재투자항등식·7룰 consistency) 하나 주경로 `calcDFV`→`_calcTwoStageDcf` 가 **게이트로 꺼둠**. reverse-DCF 는 `wacc=10` 하드코딩 미배선 | ~80% de-gate + 20% 신규(fade·reverse 배선). 신규 모듈 `_dFVDrivers.py` 4함수(reinvestmentPath·driverScenarios·triangulateWeighted·reverseDcfExhibit). `multiStageDcf:194-197` `pass`→재투자조정 FCFF | G1 단위항등 · **G2 백테스트**(20 KR사 implied FV vs t+12M 실현가, 방향 >55%·중앙오차 무회귀) · G3 민감도(TVshare<0.80·p90/p10<3) · G5 consistency≥70 |
| **전망** (02b) | `analysis/forecast/` (`_revenueForecastCore`·`_forecastMetric`) | driver 분해 없는 추세외삽 · 마진 *고정* · 시나리오=과거 σ 잡음 · **자기 백테스트 0**(`forwardTest.py` 는 prospective 라 track record 영원히 빈칸). 격상자산은 이미 존재(`_fundamentalGrowth` g=ROIC×재투자가 15% 가중에 묻힘·quant walk-forward+conformal 가 모범) | 신규 3로직(fade `g(t)=gT+(g0−gT)e^−λt`·영업레버리지 마진·origin 절단) + 신규 `_revenueBacktest.py`(rolling-origin walk-forward, lookahead 차단) | G1 MAPE≤8/15% · G2 방향≥70/60% · G3 밴드커버 80~95% · G4 baseline skill>0 |
| **세그먼트** (02c) | `_revenueSegment.py:127`·`_revenueSelect.py:91`·`panel/cell.py:224`(axisPath) | 공시 매출은 진짜 추출. 단 `hasOpIncome:213` 게이트로 **부문 마진 미공시 시 조용히 drop** | 연결 OI 를 부문 배분(매출가중 floor + **peer 부문 벤치마크 reconcile** + 자산집약 tilt) → *범위* 라벨(`marginSource=derived`). SOTP: `damodaranL15.py:1242` 스텁 → `calcOperatingSegmentSotp` | 공시사(005930·051910 등) 대상 백테스트: 마진 MAE≤5%p·커버≥80%·Spearman ρ≥0.6 통과해야 마진 *값* 노출, 아니면 방향/믹스만 |
| **정량 moat** (02d) | (신규) `analysis/financial/moat.py` — 기질은 존재(ROIC−WACC 스프레드 `calcRoicTimeline`·마진CV `profitability.py`·재투자·peer 백분위·HHI) | 벽 아님. 기존 `calcMoatProxy:113` 은 5y평균 스칼라+WACC 8% 하드코딩(지속성·내구성 미측정) | 5성분 시계열 → logical-AND 등급(wide/narrow/none, `noComposite`): 초과수익 지속성·마진CV·점유궤적·증분ROIC·자본장벽. 측정불가(switching/network/brand)는 `unmeasured[]` 명시(prose 금지) | cohort 평균회귀 백테스트(`tests/_attempts/quantMoat/`): wide 코호트가 none 대비 ROIC fade 저항하는가(T+3) |
| **신용 라이브배선** (02e P1) | `credit/`(79사 검증)·`ai/tools/creditBadge.py:20 getDcrBadge`(dCR packet 이미 빌드) | 엔진은 강한데 **라이브 미배선** — /report 는 4축 브라우저 비율만. dCR 20등급·7축·forward PD 미노출 | **권장 = prebuild publish**(credit 를 `finance.json` 에 임베드 — `macroExposure` 가 이미 그렇게 함 `buildFinanceJson.py:324`). 엔진 0-변경 → 79사 검증 보존. ⚠ *운영자 승인 필요 결정*(§04) | panel-availability parity(finance.json vs `credit(code)` byte동일) + 79사 회귀 보존 |
| **매크로 민감도** (02e P2) | `macro/macroExposure.py`(`calcMacroSensitivity`) | n≈3-5 연간 → R²<0.20 자동 차단(`:121`). 너무 얕음 | 분기 히스토리(~4x obs, nObs≥8) + 다변량 OLS(VIF) + **계층 sector-pooled-beta fallback**. 실패 시 sector 폴백, 스킵 0 | out-of-sample β-stability(70/30 time split, sign-flip<20%) |

## 2. 의존 그래프 — 밸류에이션이 허브

```
신용 grade ──(Kd 스프레드)──▶ 밸류에이션 WACC (02a §4.4)
ROIC ───────(g=재투자×ROIC)──▶ 전망(02b) · moat fade(02d)
세그먼트 OI ─(부문 multiple)──▶ SOTP(02c→02a)
매크로 β ───────────────────▶ 포워드뷰(02b)
```

→ **밸류에이션(02a)을 먼저 격상**해야 신용·ROIC·세그먼트가 꽂힐 자리가 생긴다(Phase 순서 = 04).

## 3. 검증 게이트 공통 원칙 (날조 금지 선)

각 엔진은 **백테스트/민감도 졸업 게이트 통과 후에만** 리포트에 탑재. "약하게 추정하고 단정" = 게이트 미통과 = 탑재 금지. 게이트는 방어 스캐폴딩이 아니라 *능력이 진짜인지의 증명*. 정직 boundary 도 *모델*로 처리 — 입력 없으면 sector prior/mean-reversion 으로 폴백하지 *조용히 스킵하지 않는다*.

## 4. 공통 리스크

- **메모리**: 백테스트 다회 load → OOM. fixture module-scope·직렬 load(CLAUDE.md OOM 가드).
- **이중계산**: 신용 grade 를 WACC Kd 와 신용섹션에 동시 쓸 때 Fernandez single-count.
- **외부 fetch fallback**: WACC 무위험금리·peer 가 외부 의존 시 가정 명시(honest-skip 아닌 named-assumption).
- **L2↔L2 cross-import**: moat(02d)가 industry 입력 필요 → L3 가 주입(L2 cross 금지 가드).
