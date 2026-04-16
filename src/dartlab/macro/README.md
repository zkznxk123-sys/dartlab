# Macro

시장 레벨 매크로 분석 엔진 — **L2 분석 엔진**. Company 없이 경제 환경을 해석한다.

> **1.0.0 리팩토링 이후**: macro는 **dict만 반환하는 도구**다. 보고서 조립은 review(L3)의 책임.
> 기존 `macro/narrative.py`, `mbuilders.py`, `mcatalog.py`, `report.py`, `charts.py`는
> `review/macro/`로 이동되었다. `dartlab.macro.report()` 대신 review 경유로 호출.

6막 서사 구조는 review가 가진다 (`review/macro/`). macro 엔진은 12축 데이터 계산만 담당.

## 6막 구조

```
1막: "경제는 어디에 있나"     cycle, inventory
 ↓ 국면이 기업이익의 맥락 제공
2막: "왜 여기에 있나"         corporate, trade
 ↓ 실물 상태가 정책을 결정 (테일러 룰)
3막: "정책은 뭘 하고 있나"    rates
 ↓ 정책금리가 금융상태를 결정 (ECB 전파 1단계)
4막: "금융 시스템은 괜찮나"   liquidity, crisis
 ↓ 금융상태가 자산/심리를 결정 (금융가속기)
5막: "시장은 어떻게 반응하나"  assets, sentiment
 ↓ 현재가 미래의 기반
6막: "앞으로 어떻게 되나"     forecast, scenario
```

학술 근거: FOMC 성명서, ECB 전파 메커니즘, Bernanke 신용채널(1995), Dalio 부채사이클, Goldman/IMF 보고서 구조.

## 호출 계약

```python
import dartlab
dartlab.macro()                                    # 가이드 — 6막 + 12축
dartlab.macro("사이클")                             # 1막: 국면 진단
dartlab.macro("금리")                               # 3막: 정책 대응
dartlab.macro("시나리오", "2008 금융위기")           # 6막: 시나리오
dartlab.macro("종합")                               # 전체 종합
```

## 노트북

[![marimo](https://marimo.io/shield.svg)](https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo/06_macro.py)
[![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/06_macro.ipynb)

---

| 항목 | 내용 |
|------|------|
| 레이어 | L2 |
| 진입점 | `dartlab.macro()`, `dartlab.macro("사이클")` |
| 소비 | gather(L1) — FRED/ECOS, scan finance.parquet |
| 생산 | ai(L3)가 매크로 환경 판단에 소비, review 6막에 macroCycle 블록으로 소비 |
| 구조 | **6막 인과 서사** + 12축 (사이클/재고, 기업집계/교역, 금리, 유동성/위기, 자산/심리, 예측/시나리오, 종합) |

## 호출 계약 (4엔진 통일 패턴)

```python
import dartlab

# 1. 무인자 → 가이드 DataFrame (act | actLabel | axis | label | description)
print(dartlab.macro())

# 2. 축별 분석
dartlab.macro("사이클")                              # 1막: 4국면
dartlab.macro("기업집계")                            # 2막: 이익/Ponzi
dartlab.macro("금리")                                # 3막: 정책 대응
dartlab.macro("위기")                                # 4막: 신용/유동성 + historicalContext
dartlab.macro("심리")                                # 5막: 공포탐욕
dartlab.macro("예측")                                # 6막: 침체확률
dartlab.macro("시나리오", "2008 금융위기")            # 6막: 시나리오
dartlab.macro("시나리오", "신용 충격", severity="severe")
dartlab.macro("종합")                                # 전체 종합

# 공통 파라미터
dartlab.macro("사이클", market="KR")                 # 한국
dartlab.macro("사이클", as_of="2022-01-01")          # 백테스트
dartlab.macro("사이클", overrides={"hy_spread": 600}) # 시뮬레이션
```

다른 분석 엔진(analysis/quant/credit/scan)도 동일 패턴: 무인자 → 가이드, "축이름" → 분석.

## macro → review 모듈 매핑

macro 는 review 6막 매크로 섹션(6-7)에 11축 종합 데이터를 제공한다.
`dartlab.macro("종합")` **1회 호출**로 11축 전부 가져온 뒤, 각 builder가 해당 부분만 추출.

| review 블록 | 소스 | 서사 내용 |
|---|---|---|
| macroEnvironment | summary 전체 | 종합 판정 + 축별 기여도 + 자산배분 시사점 |
| macroCycle | summary["cycle"] | 경기 사이클 4국면 + 전환 시퀀스 + **Bridgewater 4 Quadrant** + 섹터 전략 |
| macroRates | summary["rates"] | 금리 방향 + 수익률곡선 + 실질금리 + **ACM 텀프리미엄** + **CP 팩터** |
| macroLiquidity | summary["liquidity"] | 유동성 regime + FCI (Hatzius 실증 가중치) + 신용스프레드 |
| macroSentiment | summary["sentiment"] | 공포탐욕 + VIX + **JLN 실물 불확실성** + VIX-JLN 괴리 |
| macroForecast | summary["forecast"] | 침체확률 + LEI + Sahm + **Growth-at-Risk 5th%** |
| macroCorporate | summary["corporate"] | 전종목 이익사이클 + Ponzi비율 + 레버리지 |
| macroTrade | summary["trade"] | 교역조건 + 수출이익 함의 (KR만) |
| macroFlags | summary 전체 | 위기 신호 + **EBP 침체 신호** + **신용사이클 경고** + 경고/기회 집계 |
| valuationBand | calcValuationBand(company) | PER/PBR 정규분포 밴드 현재 위치 |

## 설계 원칙

- **Company 불필요** — 종목코드 없이 동작 (macro 자체). 단 review 연동 시 company.market 참조
- **macro ↛ analysis** — 같은 L2지만 상호 import 금지. 해석 조합은 AI(L3)의 몫
- **numpy만** — Hamilton RS, Kalman DFM, Nelson-Siegel, GaR 분위회귀, CP 팩터 전부 numpy 직접 구현. 외부 통계 라이브러리 0
- 3계층: L0(core/finance 순수함수) → L1(gather 수집) → L2(macro 분석축)
- 공통 헬퍼: `_helpers.py`의 `get_gather`, `fetch_latest`, `fetch_series_list`, `collect_timeseries` — 중복 코드 제거, 로깅 통합
- **as_of/overrides 관통** — 전체 11축에 백테스트(`as_of`) + 시나리오(`overrides`) 지원

## API

```python
import dartlab

# ── 6막 순서 ──
# 1막: 경제는 어디에 있나
dartlab.macro("사이클")               # 4국면 + Bridgewater 4Quadrant
dartlab.macro("재고")                 # ISM 재고순환

# 2막: 왜 여기에 있나
dartlab.macro("기업집계")             # 전종목 이익/Ponzi/레버리지
dartlab.macro("교역", market="KR")    # 교역조건 + 수출이익 선행

# 3막: 정책은 뭘 하고 있나
dartlab.macro("금리")                 # 금리 + Nelson-Siegel + ACM + CP

# 4막: 금융 시스템은 괜찮나
dartlab.macro("유동성")               # M2 + FCI + NFCI
dartlab.macro("위기")                 # Credit-to-GDP + GHS + Minsky + 역사적 맥락

# 5막: 시장은 어떻게 반응하나
dartlab.macro("자산")                 # 5대 자산 + Cu/Au + 금 3요인
dartlab.macro("심리")                 # 공포탐욕 + VIX + JLN

# 6막: 앞으로 어떻게 되나
dartlab.macro("예측")                 # LEI + 침체확률 + Sahm + Hamilton RS
dartlab.macro("시나리오", "2008 금융위기")  # 역사적 충격 재현 (110개 프리셋)
dartlab.macro("시나리오", "신용 충격", severity="severe")
dartlab.macro("시나리오")              # 시나리오 목록 가이드

# 종합
dartlab.macro("종합")                 # 6막 전체 + 40전략 + 포트폴리오

# 공통 파라미터
dartlab.macro("사이클", overrides={"hy_spread": 600, "vix": 35})  # 시뮬레이션
dartlab.macro("금리", as_of="2022-01-01")                          # 백테스트
```

---

## 축별 가이드

### 사이클 (cycle)

4국면: 확장 → 둔화 → 침체 → 회복. 투자 의사결정의 출발점.

| 키 | 의미 | 활용 |
|---|---|---|
| `phase` | expansion/slowdown/contraction/recovery | 자산배분의 뼈대 |
| `confidence` | high/medium/low | low = 전환기 = 가장 중요 |
| `transition` | 전환 시퀀스 | 국면 전환 임박 신호 |
| `sectorStrategy` | 업종별 overweight/neutral/underweight | 섹터 로테이션 |
| `quadrant` | **Bridgewater 4 Quadrant** — reflation/goldilocks/stagflation/deflation | Growth×Inflation 2×2 체제 → 자산군 overweight/underweight. Dalio (2018) |

주의: HY + 장단기차 동시 악화 → 침체 강화. VIX 단독 급등은 일시적 가능. KR은 CLI 의존(느림).

### 금리 (rates)

금리 방향 + DKW 분해 + Nelson-Siegel + BEI/실질금리 4분면 + **ACM 텀프리미엄** + **CP 채권리스크프리미엄**.

| 키 | 의미 | 활용 |
|---|---|---|
| `outlook.direction` | cut/hold/hike | 가장 중요한 방향 |
| `expectation.spread2yFf` | 2Y-FF 스프레드 | 음수 = 시장이 인하 기대 |
| `decomposition` | 명목 = 실질 + BEI + 기간프리미엄 | 금리 원천 분해 (US만) |
| `yieldCurve` | Nelson-Siegel β0(Level)/β1(Slope)/β2(Curvature) | 수익률곡선 형태 |
| `realRateRegime` | tightening/reflation/goldilocks/deflation | BEI×실질금리 4분면 |
| `employment/inflation` | 고용/물가 상태 | 금리 방향의 근거 |
| `termPremium` | **ACM Term Premium** — Adrian, Crump, Moench (2013) JFE | 압축(<0)=리스크 선호, 상승(>1)=경기 우려. NY Fed 일일 공개 |
| `bondRiskPremium` | **Cochrane-Piazzesi Factor** — CP (2005) AER | 선도금리 tent-shaped 팩터 → 채권 초과수익 R²=0.44. 경기역행적 |

### 자산 (assets)

5대 자산 + 금 3요인 + Cu/Au + VIX 구간.

| 키 | 의미 |
|---|---|
| `assets` | 자산별 방향 + 해석 |
| `goldDrivers` | 금 = f(실질금리, 달러, 안전자산). 어느 요인이 지배적인지 |
| `copperGold` | Cu/Au ratio. 상승 = 산업수요 확대, 하락 = 안전자산 선호 |
| `vixRegime` | complacent/normal/anxious/fear/panic + 분할매수 차수 |

### 심리 (sentiment)

공포탐욕 0-100 + ISM 자산배분.

| 키 | 의미 |
|---|---|
| `fearGreed.score` | 0-100. <25 극단공포(매수), >75 극단탐욕(경계) |
| `ismAllocation` | ISM >55 risk-on, <50 risk-off |
| `vixRegime.buySignal` | 0/1/2/3 분할매수 차수 |
| `macroUncertainty` | **JLN Macro Uncertainty** — Jurado, Ludvigson, Ng (2015) AER. 실물 불확실성 (VIX와 다름). <0.8 낮음, >1.2 극단. VIX-JLN 괴리 시 금융/실물 불일치 |

### 유동성 (liquidity)

M2 + 연준 B/S + 신용스프레드 + NFCI + 자체 FCI (Hatzius 2010 실증 가중치).

| 키 | 의미 |
|---|---|
| `regime` | abundant/normal/tight |
| `nfci` | Chicago Fed 금융상태지수 (US, 주간, FRED 직접) |
| `fci` | 자체 FCI — GS 방식 5변수 z-score (US+KR) |
| `capexPressure` | HY 스프레드 → 설비투자 압력 |

FCI 구현: `fci = w₁z(정책금리) + w₂z(장기금리) + w₃z(HY) + w₄z(-주가) + w₅z(환율)`
가중치 (Hatzius et al. 2010 impulse response 기반 교정):
- US: 정책금리 0.25, 장기금리 0.20, **스프레드 0.30** (가장 큰 GDP 영향), 주가 0.15, 환율 0.10
- KR: 정책금리 0.25, 장기금리 0.20, 스프레드 0.25, 주가 0.15, **환율 0.15** (수출 의존 반영)
**한국 FCI — 오픈소스 최초**: 기준금리 + 국고3Y + 회사채AA + USDKRW.

### 예측 (forecast)

LEI + 침체확률 + Sahm Rule + Hamilton RS + GDP Nowcast + **Growth-at-Risk**.

| 키 | 의미 |
|---|---|
| `recessionProb` | Cleveland Fed 프로빗 침체확률 (0-1). >0.3 경계 |
| `lei` | Conference Board LEI 복제. expansion/caution/recession_warning |
| `sahmRule` | 실업률 3M MA - 12M 최저 MA. ≥0.5%p 침체 신호 |
| `hamiltonRegime` | 2-regime Markov Switching. contraction 확률 |
| `nowcast` | GDP 실시간 추정 (DFM Kalman) |
| `growthAtRisk` | **Adrian, Boyarchenko, Giannone (2019) AER**. FCI → GDP 성장률 조건부 분위회귀 (5th/25th/50th/75th/95th). GaR 5th = worst-case GDP. tail_risk high = 하방 꼬리 리스크 확대. IMF 공식 도구, 20+ 중앙은행 사용. numpy IRLS 직접 구현 |

### 위기 (crisis)

Credit-to-GDP gap + GHS + Minsky 5단계 + Koo BSR + Fisher + **EBP** + **신용사이클 4단계**.

| 키 | 의미 |
|---|---|
| `creditGap` | BIS 신용/GDP 갭. >10%p 최고 경고, CCyB 0-2.5% |
| `ghsScore` | 3년 신용팽창+자산급등 → 위기확률. 정상 7%, 위험 40% |
| `minskyPhase` | displacement→boom→overtrading→discredit→revulsion |
| `kooRecession` | 민간 금융잉여 + 저금리 = 대차대조표 침체. 재정 확대 필수 |
| `fisherDeflation` | DSR + CPI + NPL → 부채-디플레이션 악순환 위험 |
| `krHousingStress` | 한국 아파트가격 YoY + 가계부채 (KR만) |
| `recessionDashboard` | 프로빗+LEI+ISM+신용+스프레드 종합 |
| `excessBondPremium` | **Gilchrist & Zakrajšek (2012) AER**. HY 스프레드에서 기대부도분 제거한 잔차. EBP>1.0 = 12개월 내 침체 강한 신호. HY 스프레드보다 우월한 예측력 |
| `creditCycle` | **Verdad 신용사이클 4단계** — expansion(팽창)/peak(정점)/contraction(수축)/trough(저점). HY OAS + Senior Loan Officer + Charge-off Rate 조합. Greenwood-Hanson-Jin (2019) |

### 재고 (inventory)

ISM 재고순환 4국면 + 자산배분 바로미터.

| 키 | 의미 |
|---|---|
| `inventoryPhase` | active_restock(회복) → passive_restock(확장) → active_destock(수축) → passive_destock(바닥) |
| `ismBarometer` | ISM 수준별 주식/금리 시사점. <55+하락 = 인상종결 |
| `ismAllocation` | risk-on / neutral / risk-off |

### 기업집계 (corporate)

전종목 재무제표 → 이익사이클, Ponzi비율, 레버리지. scan/finance.parquet 기반.

| 키 | 의미 | 실측 (2025 DART) |
|---|---|---|
| `earningsCycle` | 전종목 영업이익 YoY | 2023 -30.9% → 2024 +38.6% → 2025 -19.5% |
| `ponziRatio` | ICR<1 기업 비중 (Minsky 취약) | 2021 16.8% → 2025 32.8% |
| `leverageCycle` | 부채비율 중간값 | 2023 70.4% → 2025 88.6% |

### 교역 (trade) — KR 전용

교역조건 + 대용치 + 수출이익 선행 + 양국 선행지수.

| 키 | 의미 |
|---|---|
| `termsOfTrade` | 수출물가/수입물가 비율 |
| `totProxy` | 환율YoY - 유가YoY (투자전략 12) |
| `exportProfit` | 교역조건 + 수출량 → 수출기업 이익 선행 |
| `leadingRelativeStrength` | US LEI vs KR CLI → 환율 방향 |

### 종합 (summary)

10축 + 40전략 + 포트폴리오 매핑.

| 키 | 의미 |
|---|---|
| `overall` | favorable/neutral/unfavorable |
| `score` | 종합 점수 |
| `contributions` | 축별 점수 기여도 |
| `allocation` | 주식/채권/금/현금 % (regime × phase 매핑) |
| `strategies` | 40개 전략 active/direction/strength/confidence |

---

## 시나리오 + 백테스트

### 시나리오 시뮬레이션 (overrides)

모든 축의 `_fetch_*` 데이터를 직접 교체하여 "만약 X가 바뀌면?" 시뮬레이션.

```python
baseline = dartlab.macro("종합")
scenario = dartlab.macro("종합", overrides={"hy_spread": 600, "vix": 35})
# scenario["score"] < baseline["score"]  → 위기 환경에서 점수 하락 확인
```

### 백테스트 (as_of)

전체 축에 `as_of` 파라미터 → gather 시계열을 해당 날짜까지만 사용.

```python
past = dartlab.macro("사이클", as_of="2022-01-01")
# 2022년 1월 시점의 데이터만으로 사이클 판별
```

### walk-forward 프레임워크

```python
from dartlab.core.finance.macroBacktest import walkForwardBacktest
result = walkForwardBacktest("2005-01-01", "2024-01-01", stepMonths=3)
# result.precision, result.recall — NBER 침체 기준 적중률
```

---

## 포트폴리오 매핑

`portfolioMapping.py` — regime × phase → 자산배분 가중치.

| 종합 판정 | 주식 | 채권 | 금 | 현금 |
|----------|------|------|---|------|
| favorable + expansion | 70% | 20% | 5% | 5% |
| favorable + recovery | 60% | 25% | 5% | 10% |
| neutral | 50% | 30% | 10% | 10% |
| unfavorable + slowdown | 30% | 40% | 15% | 15% |
| unfavorable + contraction | 20% | 40% | 20% | 20% |

미세 조정: 극단공포 → 주식 +10%p(역투자), FCI 긴축 → 채권 +5%p, Minsky 과열 → 금 +5%p.

---

## 축 조합 가이드

| 질문 | 보는 축 | 판단 기준 |
|------|---------|----------|
| 경기 침체가 오나? | forecast + cycle + crisis | 프로빗 >30% + 둔화/침체 + Minsky 과열 이후 |
| 금리는 어떻게 되나? | rates + forecast + liquidity | 인하기대(2Y-FF 음수) + LEI 하락 + 유동성 긴축 |
| 한국 수출은? | trade + inventory + corporate | ToT 악화 + 적극감축 + 이익수축 |
| 지금 주식 사도 되나? | sentiment + cycle + crisis | F&G <25 + 회복기 + 위기점수 낮음 |
| 금융위기 가능성? | crisis + liquidity + corporate | Gap>10 + GHS>50 + Ponzi>30% |
| 환율 방향은? | trade + assets + rates | 양국 선행지수 + 달러인덱스 + 금리차 |

---

## 방법론 상세

### Hamilton Regime Switching (1989)

GDP 성장률이 2개 국면(확장/침체)을 오가는 Markov Switching 모델.

수학: `y_t = μ_{s_t} + φ·y_{t-1} + ε_t`, s_t ∈ {0,1} Markov chain.
추정: Hamilton 필터(forward) → Kim smoother(backward) → EM 반복.
구현: `regimeSwitching.py` — numpy 직접, 539줄. EM maxIter=100.
출력: filteredProbs, smoothedProbs, currentRegime, currentProb, params.
한계: 사후 판별에 강하지만 실시간 전환점 2-3분기 지연.

### Kalman DFM GDP Nowcasting (Banbura 2011)

여러 월간 지표에서 공통 팩터를 추출하여 GDP 실시간 추정.

수학: 관측 `y_t = Λf_t + e_t`, 상태 `f_t = Af_{t-1} + η_t`. Kalman 필터 predict-update.
추정: PCA 초기화 → Kalman 필터/스무더 → EM 반복 (Λ, A, Q, R 갱신).
구현: `nowcast.py` — numpy 직접, 387줄. 결측(NaN) 자동 처리.
한계: 동일 주파수만. 혼합 주파수(주간+월간+분기) 미지원.

### Nelson-Siegel 수익률곡선 (1987)

수익률곡선 전체를 3팩터로 분해.

수학: `y(τ) = β₀ + β₁[(1-e^{-τ/λ})/(τ/λ)] + β₂[(1-e^{-τ/λ})/(τ/λ) - e^{-τ/λ}]`
- β₀ = Level (장기 수준), β₁ = Slope (기울기, -β₁ = 장단기차), β₂ = Curvature (곡률)
추정: λ grid search (0.3~6.0) + OLS.
구현: `yieldCurve.py` — numpy 직접. 입력: DGS1~DGS30 8개 만기.
활용: Slope가 음수(역전) → 침체 예고. 기존 T10Y3M 스프레드보다 정교.

### Cleveland Fed 프로빗 (Estrella-Mishkin 1996)

10Y-3M 스프레드 → 12개월 내 침체 확률.

수학: `P(recession) = Φ(α + β·spread)`, α=-0.5333, β=-0.6330 (하드코딩).
구현: `regimeSwitching.py` — `math.erf`로 CDF 직접 구현.
실적: 지난 8번 미국 침체 전부 사전 감지. 리드타임 6-18개월 편차.

### Sahm Rule (2019)

실업률 3개월 이동평균 - 12개월 최저 3개월 이동평균.

수학: `sahm = MA3(current) - min(MA3, past 12 months)`. ≥0.5%p → 침체.
한계: 2024년 0.57%p 도달했으나 실제 침체 없음 (false positive). 단독 의존 금지.

### BIS Credit-to-GDP Gap (2014)

신용/GDP 비율과 장기 트렌드의 편차. Basel III 공식 지표.

수학: `gap = actual - trend`. trend = 단측 HP 필터(λ=400,000).
구현: `crisisDetector.py` — EMA 재귀 근사 (`alpha = 1/(1+√λ)`).
활용: gap >2%p → CCyB 발동, >10%p → 최고 경고.

### GHS 금융위기 예측 (2022 Journal of Finance)

3년간 신용 팽창 + 자산가격 급등 동시 → 위기 확률 급등.

근거: 42개국 1950-2016 실증. 정상 ~7%, 동시 발생 ~40%.
구현: `crisisDetector.py` — 신용 3Y 변화 + 자산 3Y 수익률 복합 스코어.

### Minsky 5단계 (Kindleberger-Minsky)

displacement → boom → overtrading → discredit → revulsion.

정량화: creditGap(boom), HY<300+VIX<15(overtrading), HY>600(discredit), DXY급등(revulsion).
구현: `crisisDetector.py` — 점수 기반 판별, 최고 점수 단계 선택.

### Koo Balance Sheet Recession (2009)

민간 금융잉여(저축-투자) + 저금리 = 대차대조표 침체. 금리 인하 무효, 재정 확대 필수.

구현: `crisisDetector.py` — FRED W987RC1Q027SBEA(저축), GPDI(투자), GDP.

### Fisher Debt-Deflation (1933)

과잉 부채 → 디스트레스 매각 → 물가 하락 → 실질 부채 증가 → 악순환.

구현: `crisisDetector.py` — DSR(TDSP) + NPL(DRSFRMACBS) + CPI YoY 조합.

### FCI 금융환경지수 (Hatzius 2010)

여러 금융 변수를 하나의 지수로 합성.

구현 2가지:
1. NFCI 직접 소비 — FRED `NFCI` (Chicago Fed 105변수 DFM, 주간)
2. 자체 FCI — GS 방식 5변수 z-score. `fci.py`. **Hatzius (2010) impulse response 기반 가중치 교정 완료.**

### Bridgewater 4 Quadrant (Dalio 2018)

Growth × Inflation 2×2 → 4체제: reflation(리플레이션) / goldilocks(골디락스) / stagflation(스태그플레이션) / deflation(디플레이션).
입력: ISM PMI - 50 (성장), CPI YoY 모멘텀 (인플레). 각 체제별 자산군 overweight/underweight 매핑.
구현: `quadrant.py`. Ilmanen (2011) "Expected Returns" Ch.17 참조.

### Growth-at-Risk (Adrian, Boyarchenko, Giannone 2019 AER)

FCI → GDP 성장률의 조건부 분위회귀. 5th percentile = worst-case 성장률.
**IMF 공식 도구, 20+ 중앙은행 사용.** 금융 긴축기에 5th percentile이 급락 → 하방 꼬리 리스크 확대.
구현: `growthAtRisk.py` — IRLS(Iteratively Reweighted Least Squares) numpy 직접. scipy 불필요.
입력: NFCI (또는 자체 FCI) 시계열 + GDP 성장률 시계열. horizon=4분기.

### Excess Bond Premium (Gilchrist & Zakrajšek 2012 AER)

회사채 스프레드 = 기대 부도 프리미엄 + EBP(잔차). EBP는 신용시장 투자심리.
EBP > 1.0: 12개월 내 침체 강한 신호. HY 스프레드 단독보다 예측력 우월.
구현: `excessBondPremium.py` — HY OAS - BAA-10Y spread(부도 프리미엄 근사)로 EBP 근사.
Fed가 원본 EBP를 CSV로 직접 공개 (향후 직접 소비로 전환 가능).

### Dalio Debt Cycle Phase + Policy Lever Status (Dalio 2018)

Big Debt Crises Part 1 템플릿의 6단계 enum (`earlyBoom` / `lateBoom` / `topBubble` /
`deflationaryDepression` / `beautifulDeleveraging` / `reflationary`) + 정책 4 레버
(monetary / fiscal / credit / fx) 소진도 (spare|partial|maxed, 합계 0~12).
L0 SSOT: `core/finance/crisisDetector.py::dalioDebtCyclePhase`,
`dalioPolicyLeverStatus`. `dartlab.macro("위기")` 결과 dict 에
`debtCyclePhase` / `policyLeverStatus` 키로 노출. GHS 위기점수에는
`regime` 플래그 (deflation|inflation) 동반.

### Dalio Beautiful Deleveraging 내부 4단계 + Regime Variant (Dalio 2018 Part 1 세부)

`beautifulDeleveraging` 상태일 때 `subPhase` 필드에 내부 순서 4단계 추가 판정:
- **austerity** (긴축) / **defaultRestructuring** (디폴트) / **moneyPrinting** (화폐발행) / **wealthTransfer** (재분배)

`regimeVariant` 필드에는 환율/기축통화/외화부채 기반으로 **deflationary** vs
**inflationary** 분기. L0: `core/finance/crisisDetector.py` 내부 통합 (`_beautifulDeleveragingSubPhase`, `_dalioRegimeVariant`).

### Dalio Part 2 Detail Case Matching (Weimar / Great Depression / Subprime)

3 상세 사례의 연도별 매크로 시그니처와 현재 상태를 코사인 유사도로 비교해
가장 근접한 stage + 진행 경로 힌트를 반환. L0: `core/finance/dalioCaseMatch.py`.
데이터: `core/data/dalioDetailCases.json`. `dartlab.macro("위기")` 결과에
`dalioCaseMatch` 키로 노출.

### Dalio Part 3 48 Case Compendium Matching

48 big debt cycle cases 중 현재 상태와 가장 가까운 5개 + archetype 분포
(deflationary vs inflationary). L0: `core/finance/dalio48Match.py`. 데이터:
`core/data/dalio48Cases.json` (현재 20+ subset, 확장 여지).
`dartlab.macro("위기")` 결과에 `dalio48Match` 키.

### Reinhart-Rogoff Crisis Type Classification (R&R 2009)

4 위기 유형 (banking / currency / inflation / sovereign_debt) + boundary case
(stagflation). 현재 매크로 시그널을 유형별 임계치와 비교해 multi-label 분류,
"triple crisis" (banking + currency + debt) 판정. 역사 DB 매칭 병행.
L0: `core/finance/rrCrisisDB.py`. 데이터: `core/data/rrCrises800y.json` (주요 21
에피소드 수록). `dartlab.macro("위기")` 결과에 `crisisType` / `rrMatch` 키.

### Verdad Credit Cycle (Greenwood-Hanson-Jin 2019)

신용사이클 4단계: expansion(팽창) → peak(정점) → contraction(수축) → trough(저점).
구현: `creditCycle.py` — HY OAS + Senior Loan Officer Survey(`DRTSCLCC`) + Charge-off Rate(`CORCCACBS`).
trough에서 역발상 매수, peak에서 리스크 축소.

### Cochrane-Piazzesi Factor (2005 AER)

5개 선도금리의 tent-shaped 선형 결합 → 단일 팩터. 이 팩터로 채권 초과수익률 R²=0.44.
경기역행적: 불황기에 팩터 상승 → 기대 초과수익 상승 → 장기채 매수 기회.
구현: `bondRiskPremia.py` — Table 2 계수 하드코딩 `γ = [-2.14, 0.81, 3.00, 0.80, -2.08]`.
입력: DGS1~DGS5에서 선도금리 계산.

### JLN Macro Uncertainty (Jurado, Ludvigson, Ng 2015 AER)

132개 시계열의 예측 오차 공통 변동을 추출 → 실물 불확실성 측정.
VIX(옵션 내재 = 금융 변동성)와 근본적으로 다름 — JLN은 실물 예측 불확실성.
FRED 시리즈 `WLEMUINDXD` 1개로 직접 소비. VIX-JLN 괴리 감지.

### ACM Term Premium (Adrian, Crump, Moench 2013 JFE)

국채 수익률 = 기대 단기금리 경로 + 텀프리미엄. NY Fed가 일일 업데이트로 공개.
텀프리미엄 < 0: 리스크 선호, 채권 수요 강. > 1.5: 경기 불확실성/인플레 우려.
FRED 시리즈 `THREEFYTP10` 직접 소비 (계산하지 않고 공식 데이터 사용).

---

## 백테스트 결과 (실제 FRED 데이터, 2000-2024)

### Cleveland Fed 프로빗 — 3/3 침체 사전 감지

| 침체 | 감지 | 리드타임 |
|------|------|---------|
| 2001년 (닷컴) | ✅ | 2-8개월 전 |
| 2007년 (GFC) | ✅ | 7-16개월 전 |
| 2020년 (코로나) | ✅ | 5-8개월 전 |

"12개월 이내 침체 시작" 예측 성능 (월간, 300관측):

| 임계값 | precision | recall | FPR | F1 |
|--------|-----------|--------|------|-----|
| 0.10 | 33.1% | **100%** | 30.3% | 49.7% |
| 0.15 | 39.2% | 97.4% | 22.6% | 55.9% |
| **0.20** | **45.5%** | **89.7%** | 16.1% | **60.3%** |
| 0.25 | 41.3% | 66.7% | 14.2% | 51.0% |
| 0.30 | 38.3% | 46.2% | 11.1% | 41.9% |
| 0.40 | 17.2% | 12.8% | 9.2% | 14.7% |

**최적: 임계값 0.20에서 recall 90%, precision 46%, F1 60%.** 임계값 0.10이면 recall 100%(모든 침체 감지)이지만 FP 많음. 0.20이 가장 균형.
3번의 침체를 전부 사전 감지. FP는 금리 역전 후 침체까지 6-18개월 지연 구간에서 발생.

### Sahm Rule — 3/3 트리거 (후행)

| 침체 | 트리거 | 시차 |
|------|--------|------|
| 2001년 | ✅ | 후행 4개월 |
| 2007년 | ✅ | 후행 2개월 |
| 2020년 | ✅ | 후행 2개월 |

Sahm은 침체 시작 후 2-4개월에 트리거 — **확인 지표**(선행 아님).

### 금리역전 (10Y-3M < 0) — 3/3 선행

| 침체 | 역전 시점 | 리드타임 |
|------|---------|---------|
| 2001년 | 2000-07 | 8개월 |
| 2007년 | 2006-08 | 16개월 |
| 2020년 | 2019-05 | 9개월 |

수익률곡선 역전은 가장 일관된 선행지표 — 8-16개월 선행.

### Nelson-Siegel 현재 상태 (2026-04-04)

```
β0(Level) = 5.32, β1(Slope) = -1.60, β2(Curvature) = -1.84
→ 실효 기울기 +1.60%p — 가파른 정상 (경기 확장/인플레 기대)
RMSE = 0.052 (피팅 우수)
```

### 침체확률 → S&P500 12개월 수익률

| 조건 | 12M 후 S&P500 평균 | 관측 수 |
|------|-------------------|---------|
| 침체확률 ≥30% | **+21.9%** | 19 |
| 침체확률 <10% | +5.2% | 35 |

**역설적 결과**: 침체확률이 높을 때 주식이 더 올랐다. 이유: 금리 역전 후 12개월은 대부분 침체 직전 + 금리 인하 기대 → 자산 반등. 이것은 "금리 역전 = 즉시 매도" 전략이 틀렸다는 실증이다.

### 금리역전 → S&P500 12개월 수익률

| 조건 | 12M 후 S&P500 평균 | 관측 수 |
|------|-------------------|---------|
| 10Y-3M < 0 (역전) | **+20.9%** | 20 |
| 10Y-3M > 1.5%p (정상) | +4.5% | 18 |

역전 후 12개월은 대부분 주식 상승 구간이다. 침체는 역전 후 8-16개월에 오고, 시장은 이미 반영. 역전은 "지금 팔아라"가 아니라 "12-18개월 후에 대비하라"가 맞다.

### 자체 FCI 현재 상태

```
FCI = -0.55 (완화)
요소: 정책금리 -0.27, 장기금리 -0.51, 신용스프레드 -0.80, 주가 -2.00, 환율 +1.20
→ 주가 강세 + 스프레드 안정이 완화를 주도. 달러 강세만 긴축 방향.
```

### 기업집계 실측 (2021-2025, DART 2745종목)

| 연도 | 영업이익 합계 | YoY | Ponzi비율 | 부채비율 중간값 |
|------|-------------|-----|----------|-------------|
| 2021 | 108.5조 | — | 16.8% | 72.3% |
| 2022 | 105.4조 | -2.9% | 25.8% | 71.9% |
| 2023 | 72.8조 | **-30.9%** | 25.3% | 70.4% |
| 2024 | 100.9조 | +38.6% | 32.4% | 74.1% |
| 2025 | 81.2조 | -19.5% | **32.8%** | **88.6%** |

2023년 반도체 불황으로 이익 30% 급감. 2024년 회복했으나 2025년 재하락.
Ponzi비율 32.8% — **상장기업 3분의 1이 영업이익으로 이자를 감당 못 함**.
레버리지 88.6% — 2023년 대비 18%p 급등.

---

### Hamilton Regime Switching (2000-2024, 분기 GDP)

- 수렴: 17회, 0.14초 (maxIter=50)
- μ_expansion=3.01, μ_contraction=2.50
- 2001년 침체 구간: contraction 확률 평균 **99.7%**
- 2007년 GFC: 23.0% (분기 데이터 한계)

### 성능 (축별 호출 시간)

| 축 | 시간 | 비고 |
|---|---|---|
| 사이클 | 4.8s | FRED 6개 시리즈 |
| 금리 | 5.3s | FRED 9개 + Nelson-Siegel 8개 |
| 예측 | 7.5s | LEI + Hamilton EM + Kalman DFM |
| 종합 | 8.2s | 10축 + 40전략 + 포트폴리오 |
| 교역 | 0.4s | ECOS 5개 (KR) |

대부분 FRED/ECOS API 대기 시간. Hamilton EM 자체는 0.14초.

재현: `uv run python -X utf8 scripts/macro_backtest.py`

---

## 40개 투자전��

summary 축에서 40개 전략의 활성/비활성을 실시간 판별. 각 전략에 `strength`(0-1)과 `confidence`(high/medium/low).

### 경기순환 (6개): 1, 6, 7, 8, 9, 16
### 선행지수/교역조건 (7개): 5, 10, 11, 12, 14, 15, 31
### 금리/통화정책 (10개): 4, 17, 19, 20, 22, 28, 30, 34, 37, 40
### 환율/달러 (6개): 3, 23, 24, 25, 27, 38
### 물가/신용 (6개): 13, 18, 32, 33, 35, 36

상세: `core/finance/strategyRules.py` — `evaluateStrategies()` 함수.
ops 이전 버전에 40개 전략 전체 테이블이 있으므로, 여기서는 그룹만 명시.

---

## 코드 품질

| 지표 | 수치 |
|------|------|
| L2 모듈 | 12개 파일, ~2,400줄 |
| L0 순수함수 | **19개 파일**, ~5,700줄 (+5 신규: quadrant, growthAtRisk, excessBondPremium, creditCycle, bondRiskPremia) |
| 단위 테스트 | 38개 (test_macro_l0.py) |
| bare except (L2) | **0개** (구체적 예외 + logging) |
| bare except (_helpers) | 6개 (의도적 — httpx/Polars 포함 전체 포착, log.debug) |
| getDefaultGather 호출 | 8회 (24→8 최적화) |
| 공통 헬퍼 | 8개 (fetch_latest, fetch_yoy, collect_timeseries 등) |
| as_of 실제 동작 | 11/11축 |
| overrides 실제 동작 | 11/11축 |

---

## 관련 코드

| 경로 | 역할 |
|------|------|
| `src/dartlab/macro/` | 11축 + 종합 + 헬퍼 + spec |
| `src/dartlab/macro/_helpers.py` | 공통 fetch 헬퍼 8개 + as_of/overrides 지원 |
| `src/dartlab/core/finance/regimeSwitching.py` | 프로빗 + LEI + Sahm + Hamilton RS |
| `src/dartlab/core/finance/nowcast.py` | Kalman DFM Nowcasting |
| `src/dartlab/core/finance/yieldCurve.py` | Nelson-Siegel |
| `src/dartlab/core/finance/crisisDetector.py` | Credit-to-GDP + GHS + Minsky + Koo + Fisher |
| `src/dartlab/core/finance/macroCycle.py` | 사이클 + Cu/Au + BEI 분해 |
| `src/dartlab/core/finance/fci.py` | 자체 FCI (US + KR, Hatzius 2010 실증 가중치) |
| `src/dartlab/core/finance/quadrant.py` | **Bridgewater 4 Quadrant** — Growth×Inflation 체제 (Dalio 2018) |
| `src/dartlab/core/finance/growthAtRisk.py` | **IMF Growth-at-Risk** — 분위회귀 IRLS (Adrian 2019 AER) |
| `src/dartlab/core/finance/excessBondPremium.py` | **Excess Bond Premium** — 신용 스트레스 (Gilchrist-Zakrajšek 2012 AER) |
| `src/dartlab/core/finance/creditCycle.py` | **Verdad 신용사이클 4단계** — 팽창/정점/수축/저점 (Greenwood-Hanson-Jin 2019) |
| `src/dartlab/core/finance/bondRiskPremia.py` | **Cochrane-Piazzesi Factor** — 채권 초과수익 R²=0.44 (CP 2005 AER) |
| `src/dartlab/core/finance/inventoryCycle.py` | 재고순환 + ISM |
| `src/dartlab/core/finance/termsOfTrade.py` | 교역조건 |
| `src/dartlab/core/finance/corporateAggregate.py` | 기업집계 |
| `src/dartlab/core/finance/strategyRules.py` | 40개 전략 룰엔진 |
| `src/dartlab/core/finance/portfolioMapping.py` | regime → 자산배분 |
| `src/dartlab/core/finance/macroBacktest.py` | walk-forward 백테스트 |
| `src/dartlab/gather/fred/catalog.py` | FRED ~84개 시리즈 |
| `src/dartlab/gather/ecos/catalog.py` | ECOS ~53개 지표 |
| `src/dartlab/review/macro/report.py` | 경제분석 보고서 조립 (6막 서사) — review(L3)로 이동 |
| `src/dartlab/review/macro/builders.py` | macro dict → review Block 변환 — review(L3)로 이동 |
| `src/dartlab/review/macro/catalog.py` | 보고서 섹션 메타데이터 — review(L3)로 이동 |
| `src/dartlab/review/macro/charts.py` | macro ChartSpec 생성기 — review(L3)로 이동 |
| `src/dartlab/review/macro/narrative.py` | 서사 자동 생성 — review(L3)로 이동 |
| `scripts/publish_macro_report.py` | 보고서 자동 발간 스크립트 |
| `.github/workflows/macroReport.yml` | 매월 자동 발간 GitHub Actions |
| `tests/test_macro_l0.py` | L0 단위 테스트 38개 |

---

## 경제분석 보고서

### 3막 서사 구조

analysis 6막이 기업 내부 인과(매출→마진→현금→부채→배분→가치)를 추적하듯,
macro 3막은 경제 외부 인과(성장→인플레→금리→신용→자산가격)를 추적한다.

```
신호등 대시보드 → 제1막(국면 진단) → 제2막(인과 역추적) → 제3막(전망+리스크) → 자산배분
```

| 막 | 핵심 질문 | 소비 축 |
|---|---|---|
| 신호등 | 한눈에 상태는? | summary 종합 점수 + FCI |
| 제1막 | 지금 어디인가? | cycle + rates + assets + sentiment |
| 제2막 | 왜 이 국면인가? | crisis + liquidity + corporate |
| 제3막 | 다음에 뭐가 오나? | forecast + crisis + trade |
| 배분 | 그래서 뭘 해야 하나? | allocation + strategies |

설계 원칙 (Goldman/BIS/IMF/Bridgewater/Bloomberg 참고):
- 결론 먼저 (Goldman 역피라미드)
- 전파 경로 명시 (BIS 전달 메커니즘)
- 비교 기준 명시 (Bloomberg: 전기 대비, 과거 유사 국면 대비)
- 매 섹션 "So What" (Bloomberg Intelligence)

### API

```python
dartlab.macro.report()                    # Rich 터미널
dartlab.macro.report(fmt="html")          # HTML
dartlab.macro.report(fmt="markdown")      # 마크다운
dartlab.macro.report(market="KR")         # 한국 경제
dartlab.macro.report(as_of="2022-01-01")  # 백테스트 시점 보고서
```

review의 Block/Section/Review 시스템을 그대로 재사용.
ChartBlock으로 viz 엔진 차트 포함.

### 자동 발간 파이프라인

```
매월 1일 → GitHub Actions (macroReport.yml)
  → secrets: FRED_API_KEY + ECOS_API_KEY
  → uv run python scripts/publish_macro_report.py
    → US 보고서 + KR 보고서 + 스냅샷 JSON
    → 전월 대비 diff (국면 전환/점수 급변 감지)
  → 성공: docs/macro-reports/ + blog/06-macro-reports/ 커밋 → GitHub Pages 배포
  → 실패: GitHub Issue 자동 생성 (labels: macro, automated, bug)
```

발간 경로:
- `docs/macro-reports/{YYYY-MM}-US.md` — docs (내부)
- `docs/macro-reports/{YYYY-MM}-KR.md` — docs (내부)
- `docs/macro-reports/snapshots/{YYYY-MM}.json` — 스냅샷 (diff용)
- `blog/06-macro-reports/{YYYY-MM}-us/index.md` — 블로그 (공개)
- `blog/06-macro-reports/{YYYY-MM}-kr/index.md` — 블로그 (공개)

### dartlab 3종 보고서 체계

| 보고서 | 엔진 | 구조 | 발간 | 블로그 카테고리 |
|--------|------|------|------|---------------|
| 기업분석 | review | 6막 인과 | audit 후 수동 | `05-company-reports` |
| 신용분석 | credit | 7축 등급 | publisher.py 수동 | `04-credit-reports` |
| **경제분석** | **macro** | **3막 서사** | **매월 자동 (Actions)** | **`06-macro-reports`** |
