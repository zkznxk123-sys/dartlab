# 02a · 밸류에이션 격상 스펙 — 내재가치 엔진 프로화

> 출처: 코드 직독(`analysis/valuation/**` · `analysis/financial/_proformaCore.py` · `synth/{bottomUpBeta,impliedERP,riskPremiums}.py` · `core/utils/calc.py` 전수). 본 문서는 *그것만 보고 재조사 없이 구현 가능한* 완전 설계다.
>
> **핵심 발견(01 의 4대 결함보다 정확한 진단)**: dartlab 은 이미 CAPM bottom-up WACC·implied ERP·reverse-DCF·재투자항등식·정합성 7-룰을 **전부 보유**한다. 진짜 결함은 *"엔진이 자기 능력을 안 쓴다"* — primary 경로(`calcDFV`→`_calcTwoStageDcf`)가 이 능력들을 **gate 뒤에 두고 우회**한다. 격상 = 신규 빌드 80%, *기존 능력 배선/디게이트* 20%가 아니라, **디게이트 80% + 신규(fade·reverse 결박) 20%**. SSOT 를 개선하지 병렬 신설 금지.

---

## 1. SSOT 맵 — 파일 + 현재 진입점 (file:line)

밸류에이션은 3층이다. 위로 갈수록 조합·배선, 아래로 갈수록 수식.

### 1.1 L2-조합 진입점 (단일 적정가 콜)
- **`src/dartlab/analysis/valuation/dFV.py:56` `calcDFV(company, *, basePeriod, overrides)`** — *최상위 SSOT*. 기업유형×생애주기→모델선택→삼각검증→qualityWACC→survival 가중→opinion. landing `/report` 가 소비할 단일 콜.
  - `dFV.py:196` `_getBaseWACC(company)` → CAPM 우선, 섹터 fallback (디게이트 지점 ①)
  - `dFV.py:200` `calcQualityWACC` 호출 (질적 가감)
  - `dFV.py:182` `_calcTwoStageDcf` 호출 (DCF 본체 — 결함 집중지)
  - `dFV.py:224-228` Bull/Base/Bear = `primaryValue × (1 ± 0.12)` **고정 ±12%** (결함 ④의 본진, dcf.py:586 보다 여기가 라이브)
  - `dFV.py:262` `_buildConsistency` (정합성 7-룰 — 사후 점검만, 입력엔 안 묶임)

### 1.2 L2-헬퍼 (계산 위임)
- **`src/dartlab/analysis/valuation/_dFVCalcs.py`**
  - `:44 _getBaseWACC` — ① `_estimateWacc` (CAPM, **단 bottomUp/impliedErp/country flag 안 켬**) → ② sector `discountRate` → ③ 10.0
  - `:72 _triangulate` — primary vs secondary 괴리 %, 합의/부분/불일치 (단순 거리)
  - `:263 _calcTwoStageDcf(company, lifePhase, overrides)` — `multiStageDcf` 호출. **`reinvestment_path` 는 override 없으면 None** (결함 ③)
- **`src/dartlab/analysis/valuation/_dFVTsd.py`** (Two-Stage resolver chain)
  - `:33 _tsdResolveWacc` — forced→(impliedErp|bottomUp|country flag 있을 때만)`computeCompanyWacc`→roic fallback→9.0. **flag 기본 False → CAPM 풀체인 비활성** (디게이트 지점 ②)
  - `:92 _tsdResolveHighGrowth` — `calcGrowthTrend` 매출 CAGR, clamp [-5,25]. **재투자 무관** (결함 ①·③)
  - `:116 _tsdBuildPhases` — 생애주기별 [5,3,2]년 × [g, g×0.5, g×0.2] 감쇠. 성장률만 감쇠, ROIC fade 없음 (결함 ④)
  - `:149 _tsdResolveTerminalGrowth` — phase별 Rf 감쇠 (Damodaran ERP 기준, 이미 양호)

### 1.3 L2-수식 본체 (순수 함수)
- **`src/dartlab/analysis/valuation/dcf.py`**
  - `:46 multiStageDcf(...)` — N-phase Gordon. **`:194-197` marginPath 받고 `pass`** (결함 ③의 코드 증거), `:212-213` terminal = `projections[-1]×(1+g)/(r-g)` — terminal 재투자 미반영 (결함 ④)
  - `:330 dcfValuation(...)` — 단순 2-stage. `:429 wacc = discountRate or sectorParams.discountRate` (결함 ②), `:455-457 revCagr clamp [-5,15]` (결함 ①), `:465 tv` (terminal fade 없음, 결함 ④), `:586-615 fullValuation` verdict = 0.8/1.2 밴드 + 단순평균 (결함 ④)
- **`src/dartlab/analysis/valuation/priceImplied.py`**
  - `:27 reverseImpliedGrowth(series, marketCap, *, wacc=10, terminalGrowth=2, horizon=3)` — **이진탐색 reverse-DCF 이미 존재**. `:117 _bisectImpliedGrowth`. ⚠ wacc·tg **하드코딩 디폴트**, calcDFV 와 미연결 (디게이트 지점 ③·결함 핵심)
  - `:167 computeGap(implied, forecastGrowthRate)` — gap→신호
- **`src/dartlab/analysis/valuation/_dcfHelpers.py`** — `_resolveBaseFcf`(:110, mid-cycle 정규화 체인), `_projectFcf`(:122, blend), `_getNetDebt`(:31)
- **`src/dartlab/analysis/valuation/residualIncome.py:183`** — RIM, fade factor(omega) 동적 추정 (RIM 은 이미 fade 있음 — DCF 에 이식 모델)

### 1.4 WACC 입력 엔진 (이미 프로급, 디게이트만 필요)
- **`src/dartlab/analysis/financial/_proformaCore.py:145` `computeCompanyWacc(series, *, country, impliedErp, bottomUpBeta, betaOverride, marketCap, ...)`** — *완성된 CAPM*. `Ke=Rf+β×(ERP+CRP)`, `Kd=이자비용/총차입금` clamp[2,15], 시총가중. `:289 kd=rf+1.0` fallback. `:312 wacc clamp[4,20]`. **모든 프로 레버 보유 — 단 calcDFV 가 flag 안 켜고 호출**
- **`src/dartlab/analysis/financial/_investmentAnalysisRoic.py:28` `_estimateWacc(company)`** — `computeCompanyWacc` 래퍼. **betaOverride=regression β 만, country/impliedErp/bottomUp flag 미전달** (디게이트 지점 ①의 코드 증거)
- **`:107 calcRoicTimeline(company)`** — ROIC=NOPAT/투하자본 시계열 + `waccEstimate` + `decomposeRoic` 분해 + spread. **fade 의 입력(ROIC 시계열) 이미 산출됨**
- **`src/dartlab/synth/bottomUpBeta.py:18` `calcBottomUpBeta(*, sector, debtToEquity, taxRate, country)`** — Hamada unlever/relever, peer scan. ⚠ `:265 betaLevered=sector_beta` (peer별 회귀 β 미구현 — peer D/E 만 진짜, β 는 섹터 상수). **개선 여지 but 작동**
- **`src/dartlab/synth/impliedERP.py:23` `calcImpliedERP(country)`** — Gordon 역산 ERP + 분기 cache
- **`src/dartlab/synth/riskPremiums.py:53` `loadDamodaranERP(countryCode)`** — Rf·matureERP·CRP·세율·등급 SSOT (`reference/data/damodaranDefaults.json`)
- **`src/dartlab/credit/scoring/creditScorecard.py`** + `company.credit("등급")` → `{score, grade}` (qualityWACC `_creditSpread` 가 score band→%p, dCR 20등급→스프레드 매핑은 band 화 됨)

### 1.5 핵심 항등식·정합성 (이미 존재, 미배선)
- **`src/dartlab/core/utils/calc.py:126` `reinvestmentIdentity(growthRatePct, roicPct)`** → `{impliedReinvestRate=g/ROIC}` — **결함 ③의 해법 함수 이미 존재**
- **`:52 decomposeRoic(...)`** → `excessReturnPct=(ROIC-WACC)` — **결함 ④ fade 의 입력 이미 존재**
- **`src/dartlab/analysis/valuation/consistency.py:31 calcCashFlowConsistency(...)`** — 7-룰(TG≤Rf, g=reinvest×ROIC, TV비중, 단일모델, 세율, 성장낙관). **사후 점검 only — 가정 생성엔 안 묶임**

### 1.6 SectorParams 데이터형
- `src/dartlab/frame/sector/__init__.py` → re-export `dartlab.core.sector`. `SectorParams(discountRate, growthRate, perMultiple, pbrMultiple, evEbitdaMultiple, beta, exitMultiple, ...)`. `getMarketParams(currency)→MarketParams(riskFreeRate, totalErp, defaultTaxRate)`. `getSectorParamsByName(name)`. → 섹터 β·exitMultiple 은 여기서 공급(상수). **이게 결함 ②가 의존하는 단일숫자 출처.**

---

## 2. 아마추어 격차 — 코드 증거

| # | 결함 | 코드 증거 | 진짜 원인 |
|---|---|---|---|
| ① | 성장 = 매출 3Y CAGR clamp | `dcf.py:455-457` `revCagr; min(max(revCagr,-5),15)` · `_dFVTsd.py:92` highG clamp[-5,25] | 과거 외삽. 재투자/ROIC 와 무관 |
| ② | WACC = 섹터 단일숫자 | `dcf.py:429` `discountRate or sectorParams.discountRate` · `_dFVCalcs.py:60-68` sector fallback | dcfValuation 직접경로는 CAPM 우회. calcDFV 는 `_estimateWacc` 쓰나 **bottomUp/impliedErp/country flag 안 켬**(`_investmentAnalysisRoic.py:87-93`) |
| ③ | 성장에 재투자 미연결 | `dcf.py:194-197` `if marginPath...: pass` · `_dFVCalcs.py:286-287` `reinvestment_path=applyOverride(None,...)` (override 없으면 None) | FCF 를 재투자 0 으로 키움 = 무에서 가치창조. `reinvestmentIdentity` 보유하나 가정생성에 미사용 |
| ④ | terminal excess-return fade 없음 | `dcf.py:212-213` terminal=`fcf×(1+g)/(r-g)` (ROIC 영구 가정) · `dFV.py:224-228` bull/bear=`±0.12` 고정 · `dcf.py:610-615` verdict 0.8/1.2 + 단순평균 | ROIC>WACC 영구 가정 → TV 과대. 시나리오가 드라이버 아닌 산술밴드 |
| ⑤(신규발견) | reverse-DCF 미배선·하드코딩 | `priceImplied.py:33-34` `wacc=10, terminalGrowth=2` 디폴트 · `_valuationOther.py:261` `reverseImpliedGrowth(series, marketCap=...)` (회사 WACC 미전달) | "결정타 exhibit" 이 calcDFV 의 WACC/펀더멘탈 성장과 단절. 별도 함수로 표류 |
| ⑥(신규발견) | bottom-up β 가 섹터상수 | `bottomUpBeta.py:265` `"betaLevered": sector_beta` | peer D/E 는 진짜 unlever 하나 peer별 β 는 섹터상수 — relever 효과만 살고 peer 분산 죽음 |

→ 01·§4 의 "모델이 틀렸다" 가 정확. 단 ②·⑤ 는 *틀린 게 아니라 끈 것*. 디게이트가 최단 ROI.

---

## 3. 프로 방법론 — 수식 + dartlab 데이터 소스 (입력별)

### 3.1 Bottom-up 회사 WACC
```
Ke = Rf + β_L(firm) × (matureERP + CRP)
β_L(firm) = β_U(peer mean) × (1 + (1-t) × D/E_market)      # Hamada relever
Kd = max(2, min(15, 이자비용TTM / 총차입금)) × (1 - t)      # 세후
WACC = E/(D+E)·Ke + D/(D+E)·Kd_aftertax                     # 시장가 가중
```
| 입력 | 소스 (dartlab) |
|---|---|
| Rf, matureERP, CRP, 등급 | `loadDamodaranERP(countryCode)` (KR Rf~3.4, ERP~6.8) — `riskPremiums.py:53` |
| ERP(시장내재 옵션) | `calcImpliedERP("KR")` — `impliedERP.py:23` (impliedErp=True) |
| β_U peer mean, D/E relever | `calcBottomUpBeta(sector, debtToEquity, country)` — `bottomUpBeta.py:18` |
| D/E (시장가 우선) | marketCap(=E) + BS 차입금(=D). `_proformaCore.py:272-281` 이미 추출 |
| Kd | IS `finance_costs`/`interest_expense` ÷ BS 차입금. `_proformaCore.py:284-289` |
| 세율 t | `profit_before_tax`·`income_tax_expense` 유효세율 clamp[0,0.5]. `_proformaCore.py:295-300` |
| **Kd 정밀화(신규)** | `company.credit("등급")` score→dCR 20등급→스프레드: `Kd = Rf + creditSpread(grade)`. qualityWACC `_creditSpread`(`qualityWACC.py:83`) 의 band 를 **bp 스프레드 테이블**로 승격해 Kd 에 직결 (현재는 WACC 가감으로만 씀 — 이중계산 회피 위해 *Kd 입력*으로 단일화) |

**조치**: `computeCompanyWacc` 는 그대로. 호출부가 `bottomUpBeta=True, impliedErp=True(옵션), country=resolveCountry, creditGrade` 를 넘기게 디게이트.

### 3.2 재투자 묶인 성장 (Damodaran 항등식)
```
expectedGrowth_g = reinvestmentRate × ROIC
reinvestmentRate = (netCapex + ΔNWC) / NOPAT
NOPAT = 영업이익 × (1 - 유효세율)
ROIC = NOPAT / investedCapital   (investedCapital = 자본 + 총차입금 - 현금)
FCFF_t = NOPAT_t × (1 - reinvestmentRate_t)        # 재투자 차감 후 현금
```
| 입력 | 소스 |
|---|---|
| NOPAT, ROIC, investedCapital 시계열 | `calcRoicTimeline(company)["history"]` — `_investmentAnalysisRoic.py:107` (이미 NOPAT·IC·roic·effectiveTaxRate 행 산출) |
| netCapex | CF `purchase_of_property_plant_and_equipment`(+무형). `calcInvestmentIntensity`(:321) capex 시계열 |
| ΔNWC | BS 매출채권+재고-매입채무 차분. `_proformaCore.py:_extractBaseYear` 운전자본 라인 |
| 항등식 변환 | `reinvestmentIdentity(g, roic)` — `calc.py:126` (역방향: g→재투자율도 가능) |

**핵심 전환**: 성장률을 *입력*으로 받지 말고, **`g = reinvestRate × ROIC` 로 도출**. 매출 CAGR(`_tsdResolveHighGrowth`)은 reinvestRate 추정 실패 시 *fallback* 으로 강등. 세그먼트 분해 가능 시(volume×price, `_revenueSegment.py` axisPath) 매출 동인을 reinvestRate 추정에 우선 — 불가하면 reinvest×ROIC.

### 3.3 Excess-return fade (경쟁 수렴)
```
명시구간 t=1..N: ROIC_t = ROIC_0 + (WACC - ROIC_0) × (t/N)^k    # ROIC→WACC 선형/볼록 수렴
g_t = reinvestRate_t × ROIC_t                                    # fade 된 ROIC 로 성장
terminal: g_∞ 고정(=_tsdResolveTerminalGrowth), ROIC_∞ → WACC + spreadFloor
terminal reinvestRate = g_∞ / ROIC_∞                            # 무료성장 차단(핵심)
TV = FCFF_N × (1 + g_∞) / (WACC - g_∞)                          # 단, FCFF_N 은 재투자 반영분
```
- `ROIC_0` = `calcRoicTimeline` 최신, `WACC` = §3.1, fade exponent `k`: 해자(moat) 강하면 k>1(느린 수렴), 약하면 k≤1.
- moat 입력: ROIC-WACC spread 지속성 = `calcRoicTimeline` history 의 spread 시계열 표준편차/평균(이미 보유). RIM 의 omega(`residualIncome.py:183`) 재사용 가능.
- terminal reinvestRate = g_∞/ROIC_∞ → **terminal 에서도 무료성장 0** (Damodaran 핵심).

### 3.4 Reverse-DCF (헤드라인 exhibit)
```
solve g* s.t.  marketCap + netDebt = Σ PV(FCFF(g*)) + PV(TV(g*))   # 이진탐색
판정: g* (시장내재) vs g_fund (=reinvestRate×ROIC, §3.2)
"시장은 g*% 가격에 반영, 펀더멘털 지지 g_fund% → (g*-g_fund) 만큼 고평가/저평가"
```
- 솔버: **이미 존재** `_bisectImpliedGrowth`(`priceImplied.py:254`). 그대로 사용.
- **수정점**: `reverseImpliedGrowth` 가 §3.1 회사 WACC·§3.2 펀더멘털 g 를 인자로 받게 배선(현재 `wacc=10` 하드코딩). `computeGap(implied, g_fund)` 로 신호.

### 3.5 다중모델 신뢰도 가중 삼각검증
```
weight_DCF   = baseW × (1 - max(0, TVshare - 0.70)/0.30)   # TV>70%면 감점
weight_DDM   = 0 if 무배당 else baseW × min(1, payout/0.6) # 배당커버리지
weight_RIM   = baseW × omega                                # 우위지속
weight_REL   = baseW × min(1, peerCount/20)                 # peer 충분성
centralIV = Σ(weight_i × IV_i) / Σweight_i
bear/base/bull = 세 드라이버(g, margin, WACC) 를 ±1σ 흔든 DCF 재계산  # ±12% 산술 폐기
```
- 적용도 신호: `calcMethodFitness`(`fitness.py:162`) 가 이미 fitness 점수 산출 — 이를 weight 로 승격.
- TVshare = `multiStageDcf` 반환 `tvShare`(이미 있음). payout/omega/peerCount = `_ddmFitness`/`_rimFitness`/`_relativeFitness` 입력 재사용.

---

## 4. 구체적 격상 — 변경/추가 함수 (시그니처)

> 원칙: **SSOT 개선**. 신규 모듈 1개(`_dFVDrivers.py`)만 추가하고 나머지는 기존 함수 수정. 병렬 dFV 신설 금지.

### 4.1 디게이트 (변경 — 최우선, 최단 ROI)
1. **`_investmentAnalysisRoic.py:_estimateWacc`** — `computeCompanyWacc` 호출에 `bottomUpBeta=True, impliedErp=False(기본)/True(옵션), country=resolveCountryFromCurrency` 전달. creditGrade 주입(아래 4.4).
   - sig 불변, 내부 호출 인자만 추가. 회귀 가드: WACC clamp[4,20] 유지.
2. **`_dFVCalcs.py:_calcTwoStageDcf`** — `reinvestment_path` 를 override 의존이 아니라 **`buildReinvestmentPath(company, waccPct)` (신규 §4.3)** 로 채움. `multiStageDcf(..., reinvestmentPath=path)`.
3. **`dFV.py:224-228`** — bull/bear `±0.12` 삭제 → `buildDriverScenarios(...)`(신규 §4.3) 결과로 교체.

### 4.2 수식 본체 수정 (변경)
4. **`dcf.py:multiStageDcf`** — `:194-197` `pass` 제거. `reinvestmentPath` 주어지면:
   ```python
   fcff_t = nopat_t * (1 - reinvestmentPath[t])   # 재투자 차감
   ```
   `marginPath` 도 revenue×margin→NOPAT 경로로 실반영. terminal: `terminalReinvest = g_inf / roic_inf` 받아 `FCFF_N` 보정.
   - sig 추가: `roicPath: list[float] | None = None`, `terminalRoic: float | None = None`.
5. **`priceImplied.py:reverseImpliedGrowth`** — sig 에 `wacc`·`terminalGrowth` 는 유지하되 **calcDFV 가 회사 WACC 를 전달**하도록 호출부 수정. `fundamentalGrowth: float | None = None` 추가 → 반환 dict 에 `gapVsFundamental`, `signal` 직접 산출(computeGap 내장).

### 4.3 신규 모듈 `src/dartlab/analysis/valuation/_dFVDrivers.py`
```python
def buildReinvestmentPath(company, *, waccPct: float, years: int, lifePhase: str | None,
                          fadeExponent: float = 1.0) -> tuple[list[float], list[float]]:
    """재투자율·ROIC fade 경로 산출 (g = reinvest × ROIC).
    Returns: (reinvestmentPath, roicPath) — 연도별. calcRoicTimeline·reinvestmentIdentity 사용."""

def buildDriverScenarios(*, baseIV: float, baseGrowth: float, baseMargin: float, baseWacc: float,
                         roicPath, reinvestPath, fcfBase, netDebt, shares, terminalGrowth
                         ) -> dict:
    """bear/base/bull = 3 드라이버(g·margin·WACC) ±1σ 흔든 DCF 재계산.
    Returns: {bear, base, bull, drivers: {growth:{lo,hi}, margin:{...}, wacc:{...}}}"""

def triangulateWeighted(allMethods: dict, *, tvShare, payout, omega, peerCount, fitness: dict) -> dict:
    """신뢰도 가중 삼각검증. Returns: {centralIV, weights, checks, confidence}"""

def reverseDcfExhibit(company, *, waccPct: float, fundamentalGrowth: float, marketCap, netDebt) -> dict:
    """헤드라인 reverse-DCF. priceImplied.reverseImpliedGrowth 회사 WACC 로 호출 +
    g_fund 비교. Returns: {impliedGrowth, fundamentalGrowth, gap, signal, assumptions}"""
```

### 4.4 신용 → Kd 스프레드 (변경)
6. **`qualityWACC.py:_creditSpread`** — score band 를 **bp 스프레드 테이블**(`reference/data/` JSON)로 승격: dCR 20등급→`{AAA:+30bp, AA:+50, A:+90, BBB:+170, BB:+350, B:+600, CCC:+1000}`. `computeCompanyWacc` 가 `Kd = Rf + spread(grade)` 로 사용(이자비용 역산보다 우선, 무차입사 대응). **이중계산 회피**: 신용을 Kd 입력으로 단일화하면 qualityWACC 의 creditSpread 가감은 제거(Fernandez 원칙 — 입력 한 곳).

### 4.5 calcDFV 출력 확장 (변경)
7. **`dFV.py:calcDFV` 반환 dict** 추가 키: `reverseDcf`(§4.3 exhibit), `reinvestmentCheck`(g vs reinvest×ROIC), `driverScenarios`(§4.3), `waccBuildup`(Rf/β/ERP/Kd/weights — `computeCompanyWacc` details 노출). `consistency` 는 이미 있음.

---

## 5. 검증 / 졸업 게이트 (모델은 *증명*되어야 탑재)

> `tests/_attempts/valuationUplift/` 에서 개념확립→데모→클린→docstring 확정 후 본진. 게이트 통과 전 `/report` 배선 금지. 실행: `bash tests/test-lock.sh tests/quant/test_valuationUplift.py -m "..." -v` (전수 pytest 금지).

### G1 — 단위 정합 (marker `unit`, 데이터 불요)
- `reinvestmentIdentity` round-trip: g=8,ROIC=16 → reinvest=0.5, 역산 g 복원.
- fade: ROIC_0=20%·WACC=8%·N=5 → ROIC_5 == WACC(±0.1), 단조 수렴.
- terminal 무료성장 차단: terminalReinvest>0 이고 `g_∞>0`이면 `g_∞ == terminalReinvest×ROIC_∞`.
- reverse-DCF 항등: `reverseImpliedGrowth` 가 뱉은 g* 를 정방향 DCF 에 넣으면 EV==marketCap+netDebt(±1%).

### G2 — 백테스트 (marker `requires_data, slow`) — **핵심 게이트**
`test_valuation_sanity.py:SANITY_CASES` 10사 + 확장(20사) 대상:
- **구현 적정가 vs 실현주가 회귀**: t 시점 데이터(basePeriod 과거 4분기)만으로 IV 산출 → t+12M 실현주가와 비교. 측정: ① 방향 적중률(저평가 콜 후 상승) > 코인플립(>55%), ② |IV/실현가 - 1| 중앙값이 **격상 전 < 격상 후** (개선 입증), ③ reverse-DCF gap 부호가 12M 수익률 부호와 상관 ρ>0.2.
- 게이트: 격상 후가 격상 전(baseline 원장 `tests/quant/_baselines/valuationBacktest.json`) 대비 **회귀 없음**(중앙 오차 ≤ baseline, 방향적중 ≥ baseline). 신규 위반 0.

### G3 — 민감도 그리드 (marker `requires_data`)
- WACC(±2%p)×g(±2%p) 5×5 그리드 IV 분산 산출(`sensitivityAnalysis` 재사용). 게이트: ① TVshare < 0.80 (아니면 confidence=low 강제), ② 그리드 단조성(WACC↑→IV↓), ③ p90/p10 비율 < 3.0(폭주 방지).

### G4 — sanity 무회귀 (기존 `test_valuation_sanity.py`)
- 10사 IV/현재가 비율 기존 범위 유지(삼성 10~500% 등). 모델수 ≥ 2. **격상이 sanity 깨면 reject.**

### G5 — 정합성 (marker `unit`)
- `calcCashFlowConsistency` 가 격상 출력에 대해 score ≥ 70, critical flag 0(g=reinvest×ROIC 위반 없음 — 격상으로 구조적 해소 확인).

---

## 6. 리포트 통합 — 어느 섹션/블록이 소비하나

PRD(00) 아크 `[7] 밸류에이션` + `[9] 리스크` + `[2] 수익체력`. 블록 어휘(03 `report.ts`)와 결박:

| 리포트 블록 | calcDFV 출력 키 | 아크 위치 |
|---|---|---|
| `valuationBridge` | `dFV`, `waccBuildup`(Rf→β→Ke→Kd→WACC), `allMethods`, `triangulation.weights` | [7] 본체 — 콜 |
| `scenario` | `driverScenarios{bear,base,bull, drivers}` (±10% 장난 폐기, 드라이버 표기) | [7] |
| `exhibit`(reverse-DCF) | `reverseDcf{impliedGrowth, fundamentalGrowth, gap, signal}` | [7] **헤드라인** |
| `callout`/`verdict` | `opinion`, `confidence`, `reinvestmentCheck`, `consistency.flags` (noComposite) | [7]→[9] 전환 |
| `driverTree` | `reinvestmentCheck`(g=reinvest×ROIC), ROIC vs WACC fade | [2] 수익체력 결박 |
| 리스크 bear | `driverScenarios.bear` + credit(별도 02-E) | [9] |

- landing `/report` (`landing/src/lib/report/`) 는 현재 calcDFV 미소비(01·§1) — **신규 배선**: `dataCore.requestParquetRows` SSOT 경유로 calcDFV 결과 fetch(베이크 0 원칙 — 런타임 직독). 차트는 MiniFinChart 위임.
- Python story `story/builders/valuation.py:263 narrateDFV` 는 이미 calcDFV 소비 — 신규 키(reverseDcf·driverScenarios) narrate 추가.

---

## 7. 리스크 + 의존성

**리스크**
- **R1 외부 fetch 의존**: bottom-up β·reverse-DCF 모두 marketCap·β(`_fetchBeta` naver) 필요. 콜드/403 시 None — fallback 체인(섹터 β→1.0) 유지하되 `confidence=low` 표기. *모델 끄지 말고 가정 명시*(operator 원칙: honest-skip 금지).
- **R2 bottom-up β 가 섹터상수(⑥)**: peer별 회귀 β 미구현. 격상 1차는 D/E relever 만으로도 섹터단일 대비 개선 — peer β 회귀는 2차(scan macroBeta 재사용 가능, `scan/macroBeta.py`).
- **R3 재투자율 음수/폭주**: 적자·자본잠식사 NOPAT≤0 → reinvestRate 정의불가. `_tsdMaybeNormalizeFcf`(정규화) 경로로 분기 + clamp. recipe `reinvestmentRoc.md` forbidden("음수 IC 에서 ROC 금지") 준수.
- **R4 이중계산(Fernandez)**: 신용을 Kd(§4.4)·qualityWACC 양쪽에 넣으면 이중 페널티. **Kd 단일화** 필수 — qualityWACC creditSpread 제거.
- **R5 백테스트 생존편향**: SANITY 10사는 대형주 편중. G2 는 상폐·턴어라운드 포함 20사로 확장.
- **R6 메모리**: 백테스트 N사×과거분기 = Company 다수 로드(200~500MB/사). 게이트는 `scope=module` fixture + `gc.collect()` + 직렬(병렬 agent ≤2).

**의존성**
- 선행: 없음(모든 입력 엔진 존재). credit→Kd 스프레드 테이블 JSON 신설(`reference/data/creditSpreadTable.json`).
- 후행: 03(report.ts 블록 어휘) — `valuationBridge`·`scenario`·`exhibit` 계약 확정돼야 6장 배선.
- 데이터: `scan/finance.parquet`(peer), `damodaranDefaults.json`(ERP), price gather(naver) — 전부 SSOT 경유, 신규 베이크 0.
- 계층: 전부 L2(`analysis`) 내부 + L1.5(`synth`) 호출 — 단방향 유지. `_dFVDrivers.py` 는 L2, synth/calc 만 import(L2↔L2 cross 금지 준수).
