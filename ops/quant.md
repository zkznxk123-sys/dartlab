# Quant

**주체**: quant 엔진 (`c.quant(axis)` · `dartlab.quant(axis)`).
**현재**: 8 그룹 30 축 · NumPy 순수 계산 · 기술적 지표 / 팩터 / 밸류에이션 / 시뮬레이션 · 텍스트 감성.
**방향**: 팩터 백테스트 리포트 블록화 · 포트폴리오 최적화 개선 · quant/review 통합 심화.

종목 레벨 정량분석 엔진. 기술적 지표부터 팩터 모델, 텍스트 감성, 포트폴리오 최적화까지.

## 호출 계약

```python
import dartlab
c = dartlab.Company("005930")
c.quant()                # 가이드 — 30축
c.quant("모멘텀")         # 단일 축 분석
```

## 노트북

[![marimo](https://marimo.io/shield.svg)](https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo/04_quant.py)
[![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/04_quant.ipynb)

---

| 항목 | 내용 |
|------|------|
| 레이어 | L2 |
| 진입점 | `c.quant()`, `c.quant("종합")`, `dartlab.quant("축", "종목")` |
| 소비 | gather(price, flow), scan 프리빌드 parquet, docs/changes parquet |
| 생산 | ai(L3)가 정량 판단에 소비, review가 기술적 섹션에 소비 |
| 축 | 8그룹 — 기존 7그룹 + Strategy DSL (사용자 컨트롤 백테스트) |

## Company-bound 인터페이스

```python
c = dartlab.Company("005930")
c.quant()               # 가이드
c.quant("모멘텀")        # 단일 축 분석
c.quant("종합")          # 종합 기술 판단

# EDGAR (미국)
c = dartlab.Company("AAPL")
c.quant("베타")          # 시장 베타 + CAPM (market="US" 자동)
```

`c.quant` 는 Quant 인스턴스를 반환하는 property. `c.quant("축")` 호출 시 stockCode 자동 전달.

## 호출 계약 (4엔진 통일 패턴)

```python
c = dartlab.Company("005930")

# 1. 무인자 → 가이드 DataFrame (axis | label | description | example | group)
print(c.quant())

# 2. 종합 기술 판단
c.quant("종합")          # → dict (verdict, score, rsi, adx, sma20/60, ...)
c.quant("verdict")       # 영문 alias

# 3. 축별 분석
c.quant("지표")          # 45개 기술 지표 DataFrame
c.quant("모멘텀")        # 모멘텀 분석
c.quant("베타")          # 시장 베타 + CAPM
c.quant("팩터")          # Fama-French 5
```

다른 분석 엔진(analysis/macro/credit/scan)도 동일 패턴: 무인자 → 가이드, "축이름" → 분석.

## 설계 원칙

- **축 기반 디스패치** — macro/scan과 동일 패턴 (`_AXIS_REGISTRY` + `_ALIASES` + lazy import)
- **numpy 전용** — GARCH, HMM, HRP 전부 numpy 직접 구현. 외부 통계 라이브러리 0
- **DART/EDGAR 동시 지원** — market="auto" (6자리=KR, 알파벳=US)
- **메모리 안전** — scan parquet은 lazy scan, 포트폴리오는 순차 OHLCV 로드
- **analysis(L2) import 금지** — 펀더멘털 데이터는 scan 프리빌드 경유

## API

```python
import dartlab

# 가이드
dartlab.quant()                                # 29축 카탈로그

# 단일 종목 (축 + 종목코드)
dartlab.quant("모멘텀", "005930")              # 모멘텀 분석
dartlab.quant("momentum", "005930")            # 영문 키
dartlab.quant("변동성", "AAPL")               # EDGAR 종목
dartlab.quant("꼬리위험", "005930")            # CVaR, 최대낙폭, Sortino

# 횡단면 (종목 불필요)
dartlab.quant("순위")                          # 멀티팩터 복합 순위
dartlab.quant("스크린")                        # 팩터 스크리닝

# 포트폴리오 (종목 리스트)
dartlab.quant("평균분산", ["005930","000660"])  # Markowitz

# accessor 패턴
dartlab.quant.momentum("005930")
dartlab.quant.verdict("005930")
```

## 축 체계 (8그룹)

기존 7그룹 신호/지표/팩터 + Strategy DSL 그룹 (사용자 boolean 룰 백테스트). 시총 횡단면
의존 0 — 단일 종목만 지원. KR 전용 스타일은 EdgarCompany 호출 시 NotApplicable sentinel.

## 7그룹 신호/지표

### A. 기술적 (technical) — 가격 전용

| 축 | key | 설명 | 상태 |
|---|---|---|---|
| 지표 | indicators | 45개 기술적 지표 DataFrame | 구현 |
| 신호 | signals | 9개 매매 신호 | 구현 |
| 판단 | verdict | 강세/중립/약세 + **3 카테고리 분해** (추세/모멘텀/변동성) | ✅ Phase 5 audit 검증 (12년 데이터) |
| 모멘텀 | momentum | 12-1개월 횡단면, 시계열, 52주 신고가 | 구현 |
| 변동성 | volatility | GARCH(1,1), HAR-RV, 기간구조 | 구현 |
| 레짐 | regime | Hamilton 2-state HMM, 추세추종 | 구현 |
| 패턴 | pattern | 캔들스틱 10종, 지지/저항 | 구현 |

### B. 리스크 (risk) — 가격 + 벤치마크

| 축 | key | 설명 | 상태 |
|---|---|---|---|
| 베타 | beta | CAPM β + α + R² + t-stat | ✅ OK (Phase 2C 보완 완료) |
| 팩터 | factor | FF5(MKT+SMB+HML+RMW+CMA) — book-based 진짜 횡단면 회귀 | ✅ 재구현 완료 (Phase 2B). size proxy = bookEquity (시총 미수집), Phase 2A1 후 진짜 시총 교체 |
| 꼬리위험 | tailrisk | CVaR/MDD/Sortino + riskFree 파라미터 | ✅ OK (Phase 2C 보완 완료) |
| 잔여수익 | residual | 팩터 제거 후 잔여 모멘텀 | ✅ factor 재구현으로 자동 정상화 |

### C. 미시구조 (microstructure) — 가격 + 거래량/수급

| 축 | key | 설명 | 상태 |
|---|---|---|---|
| 유동성 | liquidity | Amihud, Roll 스프레드, 회전율 | 구현 |
| 수급 | flow | 기관/외국인 매매 (KR전용) | 구현 |
| 거래량 | volume | OBV 추세, 거래량-가격 괴리 | 구현 |

### D. 펀더멘털 퀀트 (fundamental) — scan 프리빌드

| 축 | key | 설명 | 상태 |
|---|---|---|---|
| 괴리 | divergence | 재무-기술적 괴리 진단 | 구현 |
| 퀄리티 | quality | Asness 퀄리티 — 횡단면 z, 금융주 sector skip, CIS+IS 강건 추출 | ✅ Phase 2C 보완 완료 (성공률 6/15 → 10/15) |
| 가치 | value | book-based 수익성/효율성 횡단면 z (시총 미수집으로 PBR/PER/PSR 미산출) | ✅ 재구현 완료 (Phase 2B). 한계 명시 — Phase 2A1 후 진짜 가치 팩터로 교체 |
| 이익모멘텀 | earnings | SUE, PEAD, 수정 모멘텀 | 구현 (외부 호출 ≤1곳) |

### E. 텍스트/공시 (text) — dartlab 고유

| 축 | key | 설명 | 상태 |
|---|---|---|---|
| 공시심리 | sentiment | Loughran-McDonald 감성 스코어링 (docs 텍스트 → pos/neg/uncert 집계 + 시계열) | 구현 (외부 호출 ≤1곳) |
| 톤변화 | toneChange | 기간별 공시 톤 변화 감지 (연속 기간 감성 차 + 신규 부정 단어) | 구현 (외부 호출 ≤1곳) |
| 이벤트신호 | eventSignal | allFilings 이벤트 기반 신호 (strategy/styles/eventDriven 사용 중) | 구현 |
| 리스크텍스트 | riskText | 리스크 키워드 밀도·시계열·신규 키워드 탐지 | 구현 (외부 호출 ≤1곳) |
| 거버넌스퀀트 | governanceQuant | 소유집중·감사의견·이사회·보수 4축 복합 점수 | 구현 (외부 호출 ≤1곳) |

### F. 횡단면 (crossSection) — 시장 레벨

| 축 | key | 설명 | 상태 |
|---|---|---|---|
| 순위 | ranking | 멀티팩터 복합 순위 | stub |
| 페어 | pairs | 공적분 페어 탐색 | stub |
| 스크린 | screen | 팩터 스크리닝 프리셋 | stub |

### G. 포트폴리오 (portfolio) — 멀티종목

| 축 | key | 설명 | 상태 |
|---|---|---|---|
| 평균분산 | meanvar | Markowitz long-only (active-set QP) + Ledoit-Wolf 옵션 + riskFree | ✅ Phase 2C 완료 (clip+renorm → active-set 교체) |
| 리스크패리티 | riskparity | HRP (Lopez de Prado) — 진짜 single-linkage clustering | ✅ Phase 2C 완료 |
| 자산배분 | allocation | Equal Risk Contribution (Maillard 2010) | ✅ description 정정 + alias 정리 완료 |

### H. Strategy DSL — 사용자 boolean 룰 + 백테스트 + Lopez 검증

사용자가 가설을 boolean expression 으로 직접 컴포즈 (가중치 박지 마라). 8 검증
스타일 프리셋 + walk_forward + CPCV + DSR + PBO. **시총 의존 0** (단일 종목만).
외부 의존 0 (numpy + polars + math 만, 정규분포 CDF/PPF 자체 구현).

| 축 | key | 설명 | 상태 |
|---|---|---|---|
| 전략 | strategy | 사용자 정의 boolean Rule 백테스트 | ✅ Phase D 완료 |
| 백테스트 | backtest | 스타일명 또는 Rule 백테스트 (cpcv 옵션) | ✅ Phase D 완료 |
| 스타일 | style | 8 검증 프리셋 일괄/단일 백테스트 | ✅ Phase E 완료 |
| 진입진단 | entry | 현재 시점 entry/exit/stop 한 줄 진단 | ✅ Phase F 완료 |
| 워크포워드 | walkforward | Lopez 슬라이딩 OOS Sharpe + DSR + PBO | ✅ Phase D 완료 |

#### 8 검증 스타일 (시총 의존 0)

| key | 한글 | 시장 | 핵심 신호 | 학술 근거 |
|---|---|---|---|---|
| trendFollow | 추세추종 | KR/US | TSMOM (12-1M momentum) + EMA20>EMA60 | Moskowitz-Ooi-Pedersen 2012 |
| meanReversion | 평균회귀 | KR/US | residual z-score < -1.25 + RSI<35 + vol normal | Avellaneda-Lee 2008 OU |
| breakout | 돌파 | KR/US | Donchian 20 entry + 10 exit + OBV | Faith Turtle System 1 |
| dipBuy | 눌림목매수 | KR/US | bull regime + EMA50 위 + RSI<50 | BTFD (Phase 4 R1: RSI 40→50) |
| eventDriven | 이벤트드리븐 | KR(DART)/US | DART 공시 + SMA5 + T+20 | Bernard-Thomas 1989 / Park-Chai 2020 |
| flowFollow | 수급추종 | **KR only, ≥30일** | foreign/inst 5일 누적 양수 | Choe-Kho-Stulz 2005 (단기 효과) |
| lowVolDefensive | 저변동방어 | KR/US | vol q40 + MDD self z-score > 0 | Frazzini-Pedersen 2014 BAB (self-z 변형) |
| seasonalKR | 한국캘린더 | **KR only** | TOM (월말 3 + 월초 3) | Lakonishok-Smidt 1988 / 한국재무학회 2018 |

**Phase 4 R1-R4 정정 (2026-04-09)**:
- R1 dipBuy: RSI 40 → 50 (bull&above_ema 와 RSI<40 은 물리적 양립 불가)
- R2 lowVolDefensive: 절대 MDD 임계 폐기 → self-history z-score (KR 시장 현실화)
- R3 eventDriven: `load_allfilings_for_stock` 60일 제한 폐기 + DART 8자리 → OHLCV 10자리 date format fix
- R4 flowFollow: naver 5일 한계 → status="data_limited" sentinel + 학술 출처 명시

**5년 KOSPI 5종목 백테스트 검증 결과 (2026-04-09)**:

| 종목 | trendFollow | meanReversion | dipBuy | eventDriven | lowVolDefensive | seasonalKR |
|---|---:|---:|---:|---:|---:|---:|
| 삼성전자 | +0.84 | +0.17 | +0.30 | **+1.14** | +0.06 | +0.60 |
| SK하이닉스 | +0.82 | +0.19 | **+1.04** | +0.84 | +0.14 | +0.38 |
| 현대차 | +0.43 | +0.05 | +0.41 | +0.69 | +0.12 | +0.10 |
| 카카오 | +0.56 | +0.19 | -0.58 | +0.28 | +0.23 | +0.43 |
| 셀트리온 | -0.74 | -0.39 | -0.28 | +0.01 | +0.23 | +0.29 |

**6 학술 효과 한국 시장 재현 성공**: TSMOM (대형 기술주), Avellaneda-Lee (winrate 97~100%),
BTFD (강세장), Bernard-Thomas PEAD (sharpe 1.14, DSR 1.00), BAB (보수적), TOM (76 trades 안정).

KR 전용 스타일 (`flowFollow`, `seasonalKR`)은 EdgarCompany 호출 시
`BacktestResult.not_applicable()` sentinel 반환 (예외 X, None X). `_DART_ONLY_EXEMPT` 등록 불필요.

#### Strategy DSL 사용 패턴

```python
from dartlab.quant.strategy import Signal, Rule

# 1. 사용자 boolean rule (가중치 없음)
s = Signal()
s.add("rsi_oversold", c.quant("신호", series=True)["rsiSignal"] == 1)
s.add("regime_bull", c.quant("레짐", series=True)["_series"]["state"] == 2)
rule = Rule(s.rsi_oversold & s.regime_bull, exit_expr=...).with_stop("atr", k=3.0)

# 2. 백테스트
bt = c.quant("strategy", rule=rule)
print(f"Sharpe={bt.sharpe:.2f} DSR={bt.dsr:.2f}")

# 3. 8 스타일 일괄
all_styles = c.quant("스타일")  # dict[str, BacktestResult]

# 4. 오늘 진입 진단
e = c.quant("진입진단")          # dict[str, EntryVerdict]

# 5. Walk-forward + DSR/PBO
wf = c.quant("워크포워드", style="seasonalKR", train=120, test=30)
```

review 6막 시장분석 섹션에 `strategySnapshot` 카드 자동 등장 — 8 스타일 백테스트
매트릭스 (Sharpe/MDD/DSR/오늘진입/오늘청산/Trades/판정).

#### 검증 메트릭 (자체 구현, scipy 0)

- **Sharpe / Sortino / MDD / Winrate / Profit Factor / Expectancy / Turnover / Exposure** — 표준
- **DSR (Bailey-López de Prado 2014)** — Deflated Sharpe Ratio, 다중 시도 + skew/kurt 정정
- **PBO (Bailey-Borwein-López de Prado-Zhu 2015)** — Probability of Backtest Overfitting
- **CPCV (López de Prado AFML)** — Combinatorial Purged Cross-Validation, embargo 지원
- **walk_forward** — Lopez 슬라이딩 train/test
- 정규분포 CDF/PPF: `math.erf` + Acklam Beasley-Springer-Moro 근사 (외부 라이브러리 0)

## 학술 근거

| 방법론 | 출처 | 축 |
|---|---|---|
| Fama-French 5-Factor | Fama & French (2015) | factor |
| q-Factor | Hou, Xue, Zhang (2015) | factor |
| Cross-Sectional Momentum | Jegadeesh & Titman (1993) | momentum |
| Time-Series Momentum | Moskowitz, Ooi, Pedersen (2012) | momentum |
| 52-Week High | George & Hwang (2004) | momentum |
| Momentum Crash Hedging | Barroso & Santa-Clara (2015) | momentum |
| GARCH(1,1) | Bollerslev (1986) | volatility |
| HAR-RV | Corsi (2009) | volatility |
| Hamilton Regime Switching | Hamilton (1989) | regime |
| Amihud Illiquidity | Amihud (2002) | liquidity |
| Roll Spread | Roll (1984) | liquidity |
| CVaR/Expected Shortfall | Artzner et al. (1999) | tailrisk |
| Asness Quality | Asness, Frazzini, Pedersen (2019) | quality |
| SUE/PEAD | Ball & Brown (1968), Bernard & Thomas (1989) | earnings |
| Loughran-McDonald | Loughran & McDonald (2011) | sentiment |
| HRP | Lopez de Prado (2016) | riskparity |
| Black-Litterman | Black & Litterman (1992) | allocation |
| Engle-Granger | Engle & Granger (1987) | pairs |
| Information Coefficient / IR | Grinold & Kahn (2000) *Active Portfolio Management* Ch.6 | `strategy/metrics.py::calcIR` + `factor.py` |
| Fundamental Law of Active Management | Grinold & Kahn Ch.6 | `strategy/metrics.py::fundamentalLawIR` |
| Cross-sectional IC / ICIR | Grinold & Kahn Ch.5 | `ranking.py::calcCrossSectionIC` |
| Residual Risk Decomposition | Grinold & Kahn Ch.7 | `factor.py::decomposeRisk` |
| Information Analysis (IC significance, decay, breadth) | Grinold & Kahn Ch.8 | `strategy/metrics.py` (icSignificance/factorDecayRate/breadthFromFrequency) |
| Holdings Factor Decomposition | Grinold & Kahn Ch.3-4 | `portfolio.py::holdingsToFactorExposure` |
| Constrained Min-Variance (sector/factor cap) | Grinold & Kahn Ch.13 | `portfolio.py::constrainedMinVariance` |

모든 Grinold 수식은 **quant 엔진 (L2) 내부** 에 위치 — 다른 L2 엔진이 공유하지 않는 전용 수식.
`core/` (L0) 로 올리지 않음. (대비: Damodaran 수식은 credit↔valuation 공유 필요 → core/finance).

## 지표 45개 (indicators.py)

### 추세 (11개)
SMA, EMA, WMA, DEMA, TEMA, HMA, VWMA, MACD, ADX, PSAR, SuperTrend

### 모멘텀 (10개)
RSI, Stochastic, Stochastic RSI, KDJ, ROC, Momentum, Williams %R, CCI, CMO, Awesome Oscillator, Ultimate Oscillator

### 변동성 (7개)
Bollinger Bands, Bollinger %B, Bollinger Width, ATR, Keltner Channel, Donchian Channel, Ulcer Index

### 거래량 (9개)
OBV, MFI, Force Index, A/D Line, Chaikin Money Flow, Ease of Movement, NVI, PVI, PVT, VWAP

### 특수 (8개)
Elder Ray, TRIX, DPO, Pivot Points, Linear Regression, Zigzag

## 신호 9개 (signals.py)

크로스오버, 크로스언더, 양방향 크로스, 골든크로스, RSI 신호, MACD 신호, 볼린저 신호, 채널 돌파, ADX 필터

## 데이터 흐름

| 타입 | 소스 | 축 |
|---|---|---|
| 가격 전용 | gather("price") | indicators, momentum, volatility, regime, pattern, tailrisk |
| 가격+벤치마크 | gather("price") + 지수 | beta, factor, residual |
| 가격+수급 | gather("flow") | flow |
| scan 프리빌드 | scan/*.parquet | quality, value, earnings, ranking |
| 텍스트 | docs/*.parquet, changes.parquet | sentiment, toneChange, riskText |
| 이벤트 | allFilings/*.parquet | eventSignal |
| 멀티종목 | 순차 OHLCV | meanvar, riskparity, allocation |

## 하위호환

기존 `dartlab.quant("005930", "indicators")` 호출은 DeprecationWarning + 자동 swap.

## Audit 결과 (Phase 1 — 2026-04-06)

quant risk/portfolio/fundamental 9축에 대한 실측 audit 완료. 개별 보고서: `data/dart/auditQuant/{factor,meanvar,riskparity,allocation,value,p2_bundle}.md`.

| 등급 | 축 | 핵심 |
|---|---|---|
| ❌ 치명 | factor | FF5 SMB/HML이 진짜와 음의 상관(−0.51), alpha 부호 반대(real +81% vs proxy −22%). 가짜 프록시 폐기 대상 |
| ❌ 치명 | value | 60% 종목 deep_value, KB금융 growth, 시가총액 미사용. 실은 ROE+자본비율의 평균, 가치 팩터 아님 |
| ❌ 치명 | residual | factor 의존 — factor 재구현으로 자동 해결 |
| ⚠️ 보완 | meanvar | clip+renorm Min-Var 5종목 무해(0.02% 손실), Tangency 6%p 차이, rf=0 가정 미명시 |
| ⚠️ 보완 | riskparity | "Single-linkage" docstring 거짓(평균거리 정렬), 결과는 max 1.78%p 차이로 가까움 |
| ⚠️ 보완 | allocation | description "Black-Litterman" 거짓 — 실제 ERC. ERC 알고리즘 자체는 Newton 표준과 0 차이 |
| ⚠️ 보완 | quality | 분포 정상, prof 추출 9/15 실패, 금융주 자동 D, Asness 4축 중 2축만 |
| ✅ OK | beta | 1.5% 이내 정확. r²/alpha/t-stat 결측만 |
| ✅ OK | tailrisk | CVaR/MDD/Sortino/skew/kurt 모두 학술 정의 일치 |

**Phase 2 작업 (2026-04-06 완료)**:
- **A2 강건 추출 헬퍼** (`quant/_helpers.py:extract_account`) — IS/CIS 양쪽, alias 패턴
- **B1 factor 재구현** (`quant/factorBuild.py` 신설 + `factor.py` 회귀부 교체) — book-based 진짜 횡단면 SMB/HML/RMW/CMA 5분위, 가짜 변동성 합성 폐기
- **B2 value 재구현** — 시총 부재 한계 명시, book-based 횡단면 z (이전 60% deep_value → 분포 정상화)
- **B3 residual** — factor 수정으로 자동 정상화 (005930 alpha 부호 반전 해소)
- **C1 meanvar** — clip+renorm → active-set QP (n≤12 enumeration, n>12 iterative), Ledoit-Wolf 공분산 수축 옵션, riskFree 파라미터
- **C2 riskparity** — 평균거리 정렬 → 진짜 single-linkage agglomerative clustering
- **C3 allocation** — description Black-Litterman→ERC 정정, alias 정리
- **C4 quality** — 추출 성공률 6/15 → 10/15, 횡단면 z, 금융주 sector skip
- **C5 beta** — t-stat 추가 (r²/alpha는 이미 있었음)
- **C6 tailrisk** — riskFree 파라미터, tailRiskGrade에 medium-fat 등급 추가
- **D1 손절매** (`signals.py`) — `vAtrTrailingStop` (Chandelier), `vVolatilityScaledStop` 신설
- **D2 사이징** (`sizing.py` 신설) — kelly_fraction, kelly_continuous, inverse_volatility_weights, volatility_target_leverage, sharpe_based_size, risk_budget_leverage
- **D3 성과귀속** (`attribution.py` 신설) — Brinson-Hood-Beebower 분해, timing_effect
- **D4 팩터 한도/헤지** (`factor.py`) — `factor_exposure_limits`, `hedge_ratio`

**Phase 2 미완 (별도 작업)**:
- **A1 시가총액 인프라** — KRX/pykrx 모두 직접 호출 차단됨. dartlab.collect에 stockTotal apiType 추가가 정공법. 이게 들어와야 진짜 시총 기반 SMB/HML/PBR/PER/PSR 가능. 메모리 `quant_audit.md` 참조.

진행 상태는 메모리 `quant_audit.md` 참조.

## review 연동

review는 `extended.py`의 함수를 직접 import (변경 없음):
```python
from dartlab.quant.extended import (
    calcTechnicalSignals, calcMarketBeta,
    calcFundamentalDivergence, calcMarketAnalysisFlags,
    calcTechnicalVerdict,
)
```

## quant → review 모듈 매핑 (analysis calc 패턴)

quant 는 review 6막 시장분석 섹션에 독립 calc 모듈로 서사를 제공한다.

| calc 함수 (extended.py) | review 블록 | 서사 내용 |
|---|---|---|
| `calcTechnicalVerdict` | technicalVerdict | 종합 판단 (verdict/score) + trend 카테고리 |
| `calcTechnicalSignals` | technicalSignals | 최근 20일 매매 신호 집계 |
| `calcMarketBeta` | marketBeta | 베타/CAPM/상대강도 |
| `calcFundamentalDivergence` | fundamentalDivergence | 재무-시장 괴리 진단 |
| `calcMarketRisk` | marketRisk | ATR 변동성 등급 |
| `calcMarketAnalysisFlags` | marketAnalysisFlags | 경고/기회 플래그 |
| `calcStrategySnapshot` | strategySnapshot | 8 스타일 백테스트 + 진입 진단 |
| **`calcTrendNarrative`** | trendNarrative | **추세 서사** (12년 audit 근거) |
| **`calcRiskNarrative`** | riskNarrative | **리스크 서사** (ATR+베타+RSI) |
| **`calcSignalNarrative`** | signalNarrative | **수급 신호 서사** |
| **`calcStrategyNarrative`** | strategyNarrative | **전략 검증 서사** (Sharpe+DSR+진입) |
| **`calcCrosscheckNarrative`** | crosscheckNarrative | **재무-시장 교차 서사** |
| **`calcQuantConclusion`** | quantConclusion | **결론** (방향 카운트, 가중치 X) |

각 calc 함수는 독립 모듈 — `@_memoized_calc` 로 Company 세션 내 캐시.
review builders 가 블록으로 변환, narrate 가 한국어 서사 생성.

## 관련 코드

| 파일 | 역할 |
|------|------|
| `src/dartlab/quant/__init__.py` | 축 기반 Quant 클래스 + 레지스트리 + 디스패치 |
| `src/dartlab/quant/spec.py` | SPEC dict (AI/generateSpec용) |
| `src/dartlab/quant/_helpers.py` | 공용 OHLCV fetch, market 감지, scan parquet 로드 |
| `src/dartlab/quant/_ax_technical.py` | 기존 코드 축 래핑 |
| `src/dartlab/quant/indicators.py` | 45개 지표 (변경 없음) |
| `src/dartlab/quant/signals.py` | 9개 신호 (변경 없음) |
| `src/dartlab/quant/analyzer.py` | verdict + enrichWithIndicators |
| `src/dartlab/quant/extended.py` | beta, divergence, flags (review 연동) |
| `src/dartlab/quant/momentum.py` | 모멘텀 분석 |
| `src/dartlab/quant/tailrisk.py` | 꼬리위험 분석 |
| `src/dartlab/quant/volatility.py` | GARCH + HAR-RV |
| `src/dartlab/quant/regime.py` | HMM 레짐 감지 |
| `src/dartlab/quant/pattern.py` | 캔들스틱 + 지지/저항 |
| `src/dartlab/quant/microstructure.py` | Amihud + Roll + 회전율 |
| `src/dartlab/quant/flowAnalysis.py` | 수급 분석 |
| `src/dartlab/quant/volumeAnalysis.py` | 거래량 분석 |
