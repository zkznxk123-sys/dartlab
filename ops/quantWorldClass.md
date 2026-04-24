# dartlab quant 세계 최강 플랜 (2026-04-24)

## 진행 상태 (2026-04-24 사용자 "전부 다 순서대로" 지시 후)

**완료된 신설 모듈 (22개)**:
- Sprint 2 재무 알파 9축: `quant/alphas/{altman, piotroski, beneish, accruals, qFactor, qmj, bab, earningsSurprise, fundamentalMomentum}.py` + review (catalog/builders/registry 9개 블록)
- Sprint 3 ML 인프라 4개: `quant/labels/tripleBarrier.py`, `quant/transforms/{fracDiff, matrixProfile}.py`, `quant/transactionCost.py` (Almgren-Chriss)
- Sprint 5 Portfolio 4개: `quant/{meanCVaR, blackLitterman, nco, shrinkage}.py`
- Sprint 6 Risk 3개: `quant/{bubbleTest (SADF/GSADF), structuralBreak (Bai-Perron), johansen (cointegration + VECM)}.py`
- Sprint 7 거버넌스: `quant/multipleTesting.py` (Harvey-Liu-Zhu Haircut + White Reality Check)
- Sprint 4 일부: `quant/eventStudy.py` (CAR + BHAR), `quant/textComposite.py` (4 텍스트 축 합성)

**검증 결과**:
- 신설 21 모듈 import 100% OK
- Altman: 2080 종목, distress 40.1%, safe 36.7%, 005930 Z=5.39 / 000660 Z=7.63 ✅
- Piotroski: 2122 종목, strong 25%, 005930 F=7 / 000660 F=8 / 035420 F=5 ✅
- Beneish: 1846 종목, red flag 14.8%, 005930 M=-2.69 (clean) ✅
- Cross-Sectional IC (factor.py 추가): KR 2024→2025 fundYear→retYear, look-ahead 방지 + non-overlap stepping ✅

**미구현 (데이터 인프라 부재)**:
- Sprint 4 KOSPI200 옵션 4축: `quant/options/{ivSurface, putCallSkew, vkospi, rnd}.py` — KRX 옵션 일별 데이터 수집 인프라 필요
- Sprint 4 Flow factor 5축: `quant/flow/{shortInterest, securitiesLending, investorFlow, programTrade, blockTrade}.py` — KRX/금투협 보조 데이터 수집 필요
- Sprint 3 WorldQuant Alphas 101: 향후 별도 트랙 (대규모)
- Sprint 6 EGARCH/GJR/MS-GARCH/DCC-GARCH: likelihood 최적화 별도 구현
- Sprint 7 Macro Regime × Quant 융합: regime.py + macro.py 통합 작업 필요

## Sprint 8 — 검증 + 개선 트랙 (2026-04-24 사용자 "끝까지 밀어" 지시)

신규 22 모듈 모두 import OK 이지만 실증 미검증 → 통합 검증 러너로 끝까지.

### Phase 1 — 통합 검증 러너 (✅ 완료)
`scripts/validate/quantValidate.py` — 22 모듈 자동 시험 + 결과 → `data/quantValidation/results_*.json` + 마크다운 리포트.

### Phase 2 — 검증 실행
- **Phase 2a (12 numpy-only)**: tripleBarrier / fracDiff / matrixProfile / almgrenChriss / meanCVaR / blackLitterman / nco / shrinkage / bubbleTest (SADF+GSADF) / structuralBreak (Bai-Perron) / johansen+VECM / multipleTesting (HLZ+Reality Check) — 합성 데이터로 sanity check
- **Phase 2b (11 데이터 필요)**: 9 alpha + eventStudy + textComposite — DART finance.parquet + KRX HF dataset 필요

### Phase 3 — 진단 리포트
- 통과 / 실패 매트릭스
- 발견된 버그 / 개선점

### Phase 4 — 즉시 fix
발견된 모듈 버그 즉시 수정 → 재검증.

### Phase 5 — 최종 SSOT 갱신
- `ops/quantWorldClass.md` 업데이트
- `memory/quantGap.md` 업데이트 — 진짜 alpha 통과 universe 확정

### 검증 통과 기준
- Phase 2a: 함수 호출 성공 + 출력 sanity (positive cost / weights sum=1 / cointRank ≥ 1 / break detected 등)
- Phase 2b: universe ≥ 50 + 005930 점수 합리적 + 분포 비율 (예: distress < 60%, red flag < 30%)

검증 실패 시 즉시 fix 후 재검증, 통과률 100% 목표.



## 전제 — 세계 최강의 정의

"세계 최강" = 세 축 동시 달성.

1. **학술 완성도**: Fama-French, Grinold & Kahn, Lopez de Prado (AFML), Asness (QMJ/BAB), Sloan (Accruals), Piotroski (F-Score), Beneish (M-Score), Hou-Xue-Zhang (q-factor), Almgren-Chriss, Rockafellar-Uryasev (CVaR), Black-Litterman, Bailey-Lopez (DSR/PBO), Harvey-Liu-Zhu (multiple testing) — 표준 전부 커버.
2. **데이터 고유성**: DART 전종목 × 9년 정규화 재무 + KRX OpenAPI 25년 가격 + 옵션 + 공시 본문 + 판단 서사. 세계 어떤 퀀트 펀드도 한국 시장에서 이 수준의 통합 SSOT 없음.
3. **운영 재현성**: NumPy-only (scipy/sklearn/cvxpy 0 의존), 단일 종목코드 호출, 첫 호출 5초 이내, 독스트링 9 섹션, 판단 서사 자동.

## 현재 상태 (2026-04-24 Sprint 1.5/1.6 완료 시점)

**강점 (이미 세계 수준)**:
- 8 그룹 30 축 + Strategy DSL + 8 검증 스타일 + DSR/PBO/CPCV 거버넌스
- 진짜 Fama-French (KRX MKTCAP 직접, book proxy 폐기) — Sprint 1.6 B0 완료
- Barra-style Multi-Factor Risk (B Σ_f Bᵀ + D) — B2 완료
- Cross-Sectional IC (Grinold Ch.5, look-ahead 방지 + non-overlap) — B3 완료
- Alphalens-style factor tear sheet (long-short Sharpe + MDD + WinRate)
- 진짜 PBR/PER/PSR (valueFactor, B1 완료)
- 5 팩터 ranking (margin/ROA/debt/size/value)
- Engle-Granger ADF pairs trading
- Hamilton HMM regime, HAR-RV, GARCH 1종, Ledoit-Wolf 공분산, HRP
- Lopez 거버넌스: DSR (Deflated Sharpe), PBO (Backtest Overfit Prob), CPCV
- 45 보조지표 (gather/indicators.py SSOT)
- 9 텍스트 축 (sentiment/toneChange/riskText/governanceQuant)
- 강건한 판단 서사 (calcTrendNarrative 등) — OSS 에 없음

**약점 (세계 최강으로 가려면 추가)**:
- ❌ Accruals Quality · Piotroski F-Score · Altman Z · Beneish M-Score (재무 SSOT 있는데 미활용)
- ❌ Triple Barrier Labeling + Meta-Labeling (AFML Ch.3)
- ❌ Fractional Differentiation (AFML Ch.5) — 시계열 stationary 변환
- ❌ WorldQuant Formulaic Alphas 101 (알파 마이닝)
- ❌ q-factor (Hou-Xue-Zhang) / QMJ / BAB 공식 축
- ❌ Almgren-Chriss TC (backtest 현실성)
- ❌ Mean-CVaR (Rockafellar-Uryasev) + Black-Litterman + NCO
- ❌ OAS / Constant-correlation shrinkage, RMT denoising (LW 1종만)
- ❌ EGARCH/GJR/MS-GARCH, Bai-Perron 구조변화, SADF 버블
- ❌ Johansen 다변량 공적분 + VECM (Engle-Granger 2종만)
- ❌ Matrix Profile (유사차트 검색 killer)
- ❌ Event Study CAR/BHAR 정규
- ❌ KOSPI200 옵션 4 축 (IV surface/put-call skew/VKOSPI/RND) — dartlab 고유 최대 자산 0 활용
- ❌ 공매도 잔고 / 대차잔고 / 프로그램매매 flow factor
- ❌ 텍스트 팩터 승격 (sentiment → FF5+TEXT 회귀 축)
- ❌ Macro regime HMM + quant (regime.py 와 macro.py 분리 상태)
- ❌ Industry-neutral factor (industry engine 분리 상태)
- ❌ Harvey-Liu-Zhu multiple testing haircut (DSR 까지만)
- ❌ Cointegration VECM + Hedging Ratio 최적화

## 스프린트 플랜

### Sprint 2 — dartlab 고유 재무 알파 (2026-05 ~ 2026-06, 4주)

**전제**: dartlab 이 이미 가진 DART 9년 × 전종목 × 정규화 재무 SSOT 를 **재무 알파 factory** 로 쓴다. 이것이 AQR/Two Sigma 와의 차별점 — 그들도 한국 시장에서는 못 한다.

| 축 | 신규 함수 | 학술 근거 | 데이터 SSoT |
|---|---|---|---|
| **Accruals Quality** | `quant/accrualsFactor.py::calcAccrualsQuality` | Sloan 1996, Dechow-Dichev 2002 | `analysis/financial/earningsQuality.py` 이미 유사 로직 → calc 로 승격 |
| **Piotroski F-Score** | `quant/piotroski.py::calcPiotroski` | Piotroski 2000 (9점) | `analysis/financial/scorecard.py` 재무 9 항목 있음 |
| **Altman Z-Score** | `quant/altman.py::calcAltmanZ` | Altman 1968 (5변수) | credit/engine 이미 z score 있음 → quant 축으로 연결 |
| **Beneish M-Score** | `quant/beneish.py::calcBeneishM` | Beneish 1999 (8변수) | analysis/financial — 매출증가/매출채권회전/감가상각비/...까지 ≥ 7 변수 즉시 구성 가능 |
| **q-factor** | `quant/qFactor.py::calcQFactor` | Hou-Xue-Zhang 2015 | 투자(I/A) + 수익성(ROE) 이미 있음 |
| **QMJ (Quality minus Junk)** | `quant/qmjFactor.py::calcQMJ` | Asness-Frazzini-Pedersen 2019 | profitability + growth + safety + payout 4 축 |
| **BAB (Betting against Beta)** | `quant/babFactor.py::calcBAB` | Frazzini-Pedersen 2014 | decomposeFactor 의 beta 이미 있음 |
| **Earnings Surprise Alpha** | `quant/earningsSurprise.py::calcEarningsSurprise` | Bernard-Thomas 1989 (PEAD) | analysis/financial/predictionSignals.py 예측치 + 실측치 diff |
| **Fundamental Momentum** | `quant/fundamentalMomentum.py::calcFundMomentum` | Chordia-Shivakumar 2006 | 분기 펀더멘털 개선 + 가격 모멘텀 교차 |

- 각 함수는 `{factor, market="KR", universe="ALL"}` 호출 시 횡단면 rank 리턴.
- 전부 `calcFactorIC` 로 자동 평가 (look-ahead 방지 시계열 IC). 목표: **한국 시장 검증된 alpha 축 9개 수집**.
- review 블록: `fundamentalAlphaBlock` — 9 축 Sharpe + ICIR 한 눈에.

**검증 기준**: 2020~2024 (5년) 백테스트 Sharpe > 0.8 인 축만 축으로 편입, < 0 이면 역방향 해석 기록.

### Sprint 3 — 세계 표준 ML 알파 (2026-06 ~ 2026-07, 4주)

**AFML + WorldQuant + Grinold 고도화**.

1. **Triple Barrier Labeling + Meta-Labeling** (AFML Ch.3)
   - `quant/labels/tripleBarrier.py::labelTripleBarrier` — 수직(시간)/상단(익절)/하단(손절) 3 경계
   - Meta-labeler: primary model (예: trend signal) → size model (confidence) → filter
   - review: `metaSignalBlock`

2. **Fractional Differentiation** (AFML Ch.5)
   - `quant/fracDiff.py::fracDiffFFD` — FFD (Fixed-Width Window)
   - 시계열 memory 유지하면서 stationary — log return 대체

3. **CPCV (Combinatorial Purged Cross-Validation)** 확대
   - 현재 있지만 strategy 전용 → factor IC 에도 적용
   - `quant/cpcv.py::combinatorialPurgedCV` (범용화)

4. **WorldQuant Formulaic Alphas 101**
   - `quant/alphas101/alpha001~101.py` — rank/correlation/ts_rank 조합
   - 초기: 20 개 대표 알파 (alpha003, alpha012, alpha041, alpha101 등) 선택적 구현
   - `quant/alphaMine.py::mineAlphas(corpusCode, basePeriod)` — IC 기준 필터

5. **Matrix Profile** (유사 차트 검색)
   - `quant/matrixProfile.py::computeMP` (stumpy 수식 numpy 포팅)
   - `searchSimilarPattern(stockCode, window=20)` — 과거 유사 패턴 top-5

6. **Almgren-Chriss TC** (backtest 현실성)
   - `quant/transactionCost.py::almgrenChriss` — 시장충격 + 시간차비용 분해
   - `BacktestResult.sharpeNetOfCost` (이미 API 있음, 충실 구현)

7. **Deep Hedging (선택)** — NumPy + gradient descent 로 Black-Scholes 대체 헤지

### Sprint 4 — Korea-Native 엣지 (2026-07 ~ 2026-09, 8주) — **dartlab 최대 차별화 축**

**다른 퀀트가 못 따라오는 영역**.

1. **KOSPI200 옵션 4 축**
   - `quant/options/ivSurface.py::calcIVSurface` — 만기 × 행사가 3D IV surface
   - `quant/options/putCallSkew.py::calcPCSkew` — 25-델타 skew
   - `quant/options/vkospi.py::calcVKOSPI` — 지수 변동성
   - `quant/options/rnd.py::calcRND` — Risk-Neutral Density (Breeden-Litzenberger)
   - **forward-looking alpha** — spot 에 없는 미래 불확실성 정보 source
   - 데이터: KRX OpenAPI 옵션 일별 (시장 최고 유동성)

2. **Flow Factor (한국 시장 고유 공개 데이터)**
   - `quant/flow/shortInterest.py::calcShortInterest` — 공매도 잔고 (상위 20%)
   - `quant/flow/securitiesLending.py::calcSecLending` — 대차잔고 추이
   - `quant/flow/investorFlow.py::calcInvestorFlow` — 외국인/기관/개인 순매수 (60일)
   - `quant/flow/programTrade.py::calcProgramTrade` — 프로그램매매 (차익/비차익)
   - `quant/flow/blockTrade.py::calcBlockTrade` — 대량매매 event

3. **텍스트 팩터 승격** (dartlab 9 텍스트 축 → 공식 factor)
   - `quant/textFactor.py::calcTextFactor(kind="sentiment|toneChange|riskText|governance")`
   - **FF5+TEXT 다변수 회귀** — text alpha 가 FF5 로 설명되지 않는 residual 알파인지 검증
   - 학술: Tetlock 2007, Loughran-McDonald 2011

4. **공시 이벤트 스터디** (Event Study 정규)
   - `quant/eventStudy.py::calcCAR` — Cumulative Abnormal Return
   - `quant/eventStudy.py::calcBHAR` — Buy-and-Hold Abnormal Return
   - 이벤트 유형: 공시 유형 × regime × 규모 분해
   - dartlab 고유: DART 공시 전문 파싱 (analysis/disclosureDelta)

### Sprint 5 — Portfolio & Optimization 최강 (2026-09 ~ 2026-10, 4주)

1. **Mean-CVaR** (Rockafellar-Uryasev 2000)
   - `quant/portfolio/meanCVaR.py::optimizeMeanCVaR`
   - Sample tail risk → LP 해결 (NumPy + simplex 직접 구현)

2. **Black-Litterman** (Black-Litterman 1992)
   - `quant/portfolio/blackLitterman.py::optimizeBL` — prior + view 결합
   - View source: dartlab 판단 서사 (analysis 판정) → quant 사전 분포

3. **Nested Clustered Optimization** (AFML Ch.16)
   - `quant/portfolio/nco.py::optimizeNCO` — HRP 계층 + intra-cluster MV
   - 대안: risk parity + clustering

4. **Robust optimization** (Ben-Tal-Nemirovski)
   - parameter uncertainty 고려 worst-case 최적화

5. **Shrinkage 3 종 추가**
   - OAS (Chen 2010), Constant-correlation (Ledoit-Wolf 2003), RMT denoising (Marchenko-Pastur)

### Sprint 6 — Risk Model 심화 (2026-10 ~ 2026-11, 4주)

1. **EGARCH / GJR-GARCH / MS-GARCH**
   - `quant/garchSuite.py::fitEGARCH/fitGJR/fitMSGARCH`
   - asymmetric + regime-switching volatility

2. **Bai-Perron 구조변화** 
   - `quant/structuralBreak.py::baiPerron` — 평균/분산 구조변화 다중 시점 탐지

3. **SADF 버블 테스트** (Phillips-Shi-Yu 2015)
   - `quant/bubbleTest.py::sadf` — 지수 버블 실시간 탐지

4. **Johansen 다변량 공적분 + VECM**
   - `quant/johansen.py::johansenTest` + `calcVECM`
   - 3+ 자산 공적분 (pairsTrading 확장)

5. **DCC-GARCH**
   - 동적 조건부 상관 — 위기 시 상관 상승 포착

### Sprint 7 — 거버넌스 완성 + dartlab 통합 (2026-11 ~ 2026-12, 4주)

1. **Harvey-Liu-Zhu Haircut Sharpe** (2016)
   - `quant/strategy/metrics.py::haircutSharpe` — 다중 테스트 보정
   - multiple testing burden → Sharpe 연장된 α-penalty

2. **White Reality Check / Stepwise SPA** (Hansen 2005)
   - `quant/strategy/metrics.py::realityCheck/stepwiseSPA`
   - 여러 전략 동시 testing 우위 검증

3. **Macro Regime × Quant**
   - `quant/regime.py::calcHMMState(macro_observables=True)` — 매크로 observable 편입
   - regime 별 factor 성과 분해 (`regimeFactorPerf`)
   - review: `regimeAwareAlphaBlock`

4. **Industry-Neutral Factor**
   - `quant/factor.py::calcFactorIC(..., industryNeutral=True)`
   - 섹터 평균 제거 후 IC (industry engine 연결)

5. **Credit-Quant Integration**
   - `quant/creditQuant.py::calcDefaultRisk` — credit engine Altman 결과 → quant 부실 회피 필터

6. **6 막 인과 Quant Block 자동화**
   - review `quantNarrative` 를 6 막 (macro → sector → company → financial → valuation → quant) 인과로 직조

## 단일 종목 호출 편의성 (dartlab 사상 유지)

모든 신규 함수는 **Company.show("quant.{axis}")** 한 줄 경유:
- `c.show("quant.alpha.piotroski")` — 9 점 + 시계열
- `c.show("quant.alpha.altman")` — Z score + 부실 probability
- `c.show("quant.ic.value")` — cross-sectional IC
- `c.show("quant.options.ivSkew")` — put-call skew (한국시장)
- `c.show("quant.flow.foreign")` — 외국인 순매수 60일

review 리포트는 위 전부 자동 블록 포함. 사용자 선언 `c.show("reportMarket")` 로 일괄.

## 학술 검증 기준

- 각 신규 alpha 는 **5년 백테스트 Sharpe + DSR + PBO 3 관문 통과**
- `factorIC` 로 별도 IC 시계열 기록
- Harvey-Liu-Zhu haircut 적용 후 Sharpe 여전히 > 0 인 축만 default universe 에 포함
- 역방향 축 ("해당 팩터가 한국에선 반대") 도 정리해 정식 기록 (예: 2025 SMB 역방향 = 대형주 프리미엄 이미 확인)

## 데이터 인프라 선결 조건

| 항목 | 상태 | 차단 |
|---|---|---|
| 재무 SSoT (DART 9년) | ✅ | - |
| 가격 SSoT (KRX 25년 백필) | 진행 중 (chunk 12/13) | Sprint 2 시작 전 publish |
| 옵션 데이터 | ❌ | KRX OpenAPI 옵션 endpoint 추가 수집 (Sprint 4) |
| 공매도/대차 | ❌ | 금융투자협회 + KRX 별도 수집 (Sprint 4) |
| 투자자별 수급 | ❌ | KRX 통계 수집 (Sprint 4) |
| 공시 본문 파싱 | ✅ (분석 엔진에 있음) | quant 에서 호출만 추가 |

## 우선순위 (사용자 확인용)

1. **최우선** — Sprint 2 (재무 알파 9축): dartlab 고유 강점 극대화. 외부 퀀트 따라올 수 없음.
2. **세계 표준 필수** — Sprint 3 (AFML + WorldQuant): "진짜 세계 최강" 타이틀 필수 조건.
3. **차별화 결정타** — Sprint 4 (Korea-Native: 옵션 + flow + text): dartlab 을 완전히 독보적으로 만듦.
4. **마감재** — Sprint 5/6/7 (최적화 + risk 심화 + 거버넌스): 품질 완성.

## 완료 시 달성 상태

- 퀀트 축 30 → **60+ 축**
- 학술 근거: FF5/Grinold/AFML/Asness/WQ101/Hou-Xue/Piotroski/Beneish/Altman/Sloan/Rockafellar/Black-Litterman/Almgren-Chriss/Phillips-Shi-Yu/Harvey-Liu-Zhu 전부 커버
- **한국 시장 독보**: 옵션 4축 + flow 5축 + text 4축 + 재무 9 알파 = 22 Korea-native 축
- **단일 SSOT** DART + KRX + 옵션 + 공시텍스트 통합 — 세계 어떤 퀀트에도 없음
- 판단 서사 자동 직조 (6 막 인과) — quant 숫자 → 한국어 해석

---

## 즉시 착수 가능 (Sprint 2 킥오프)

Sprint 2 중 **Piotroski/Altman/Beneish 3축** 은 이미 analysis 엔진에 로직이 있어 `quant/` calc 로 승격만 하면 됨. 1주일 내 완료 가능. review 블록도 3개 추가만.

Triple Barrier, WorldQuant Alphas, 옵션 4축은 Sprint 3/4 에서.
