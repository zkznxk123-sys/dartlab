---
id: engines.quant
title: Quant
kind: curated
scope: builtin
status: observed
category: engines
purpose: Quant 엔진은 가격, 기술적 신호, 팩터, 리스크, 텍스트/공시, 횡단면 랭킹, 포트폴리오, 백테스트를 46개 축으로 실행하는 정량 분석 스킬이다. 트리거 — '퀀트', '팩터', '백테스트', '모멘텀', '기술적 신호'.
whenToUse:
  - Quant
  - quant
  - 모멘텀
  - 변동성
  - 팩터
  - 백테스트
  - 포트폴리오
  - 기술적 지표
  - 멀티팩터 순위
inputs:
  - axis
  - stockCode 또는 ticker
  - 종목 리스트
  - market
  - benchmarkMode
  - style/rule
outputs:
  - guide DataFrame
  - axis별 DataFrame 또는 dict
  - backtest/portfolio result
  - assumptions/flags
capabilityRefs:
  - quant
  - Company.quant
knowledgeRefs:
  - start.dartlabSkillOs
  - engines.gather
  - engines.analysis
sourceRefs:
  - dartlab://skills/engines.quant
requiredEvidence:
  - target
  - period
  - metric
  - benchmark
  - valueRef
  - dateRef
  - executionRef
expectedOutputs:
  - 선택한 quant axis
  - 공개 호출
  - 기간/벤치마크/가정
  - 대표 반환 형태
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: supported
  pyodide:
    status: limited
failureModes:
  - 기간/벤치마크 없는 성과 수치를 말함
  - 단일 종목 축과 횡단면/포트폴리오 축을 혼동함
  - 백테스트 결과를 미래 성과 보장처럼 표현함
forbidden:
  - 투자 성과를 보장하지 않는다.
  - 기간, 수수료/슬리피지 가정, 벤치마크 없이 백테스트 결론을 내지 않는다.
  - 공개 API 호출법, guide 축, 반환 형태가 바뀌었는데 이 skill을 갱신하지 않은 상태로 완료 처리하지 않는다.
examples:
  - 삼성전자 기술적 판단
  - 모멘텀 가치 퀄리티 멀티팩터 점검
  - 종목 리스트 리스크패리티 포트폴리오
  - dartlab.quant 46 축 가이드
  - DCF 가치평가 (Damodaran)
  - 베타와 시장 민감도 측정
  - 백테스트 trendFollow 전략
procedure:
  - dartlab.quant() 로 46 축 가이드 DataFrame 확인.
  - axis 선택 (지표 · 판단 · 베타 · 순위 · 리스크패리티 · backtest 등).
  - 단일 종목은 dartlab.quant(axis, code), 종목 리스트는 dartlab.quant(axis, [code1, code2]).
  - 결과의 period · benchmark · valueRef · dateRef · executionRef 묶음.
  - 백테스트 결론은 미래 성과 보장 아님 — 가정 (수수료 · 슬리피지 · 벤치마크) 명시.
linkedSkills:
  - engines.quant.damodaranValuation
  - engines.quant.indicators
  - engines.quant.factor
  - engines.gather
  - engines.analysis
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

`quant`는 가격/거래량/수급/팩터/공시 텍스트/포트폴리오/전략을 정량적으로 계산하는 L2 엔진이다. 재무제표의 회계적 인과 해석은 `analysis`, 시장 레벨 매크로 해석은 `macro`, 후보 유니버스 발굴은 `scan`이 담당한다.

## 공개 호출 방식

```python
import dartlab

guide = dartlab.quant()

tech = dartlab.quant("지표", "005930")
verdict = dartlab.quant("판단", "005930")
beta = dartlab.quant("베타", "005930", benchmarkMode="sector")
ranking = dartlab.quant("순위")
portfolio = dartlab.quant("리스크패리티", ["005930", "000660"])
bt = dartlab.quant("backtest", "005930", style="trendFollow")

c = dartlab.Company("005930")
company_quant = c.quant("모멘텀")
```

## 호출 동작

무인자 `dartlab.quant()`는 46개 축 가이드 DataFrame을 반환한다. axis와 종목을 주면 가격/거래량/재무/공시 snapshot을 읽어 축별 결과를 계산한다.

축은 단일 종목 축, 종목 불필요 횡단면 축, 종목 리스트 포트폴리오 축, rule/style 기반 전략 축으로 나뉜다. 필요한 입력이 없으면 가이드 또는 오류/제한을 반환하고 값을 만들지 않는다.

## 전체 축/메서드 목록

| axis | label | group | 대표 호출 |
| --- | --- | --- | --- |
| indicators | 지표 | 기술적 | `dartlab.quant("지표", "005930")` |
| signals | 신호 | 기술적 | `dartlab.quant("신호", "005930")` |
| verdict | 판단 | 기술적 | `dartlab.quant("판단", "005930")` |
| momentum | 모멘텀 | 기술적 | `dartlab.quant("모멘텀", "005930")` |
| volatility | 변동성 | 기술적 | `dartlab.quant("변동성", "005930")` |
| forecast | 예측 | 기술적 | `dartlab.quant("예측", "005930", horizon=5)` |
| marketContext | 시장맥락 | 리스크 | `dartlab.quant("시장맥락", "005930")` |
| regime | 레짐 | 기술적 | `dartlab.quant("레짐", "005930")` |
| pattern | 패턴 | 기술적 | `dartlab.quant("패턴", "005930")` |
| chartPatterns | 차트패턴 | 기술적 | `dartlab.quant("차트패턴", "005930")` |
| beta | 베타 | 리스크 | `dartlab.quant("베타", "005930")` |
| benchmark | 벤치마크 | 리스크 | `dartlab.quant("벤치마크", "005930")` |
| factor | 팩터 | 리스크 | `dartlab.quant("팩터", "005930")` |
| tailrisk | 꼬리위험 | 리스크 | `dartlab.quant("꼬리위험", "005930")` |
| residual | 잔여수익 | 리스크 | `dartlab.quant("잔여수익", "005930")` |
| liquidity | 유동성 | 미시구조 | `dartlab.quant("유동성", "005930")` |
| flow | 수급 | 미시구조 | `dartlab.quant("수급", "005930")` |
| volume | 거래량 | 미시구조 | `dartlab.quant("거래량", "005930")` |
| divergence | 괴리 | 펀더멘털 | `dartlab.quant("괴리", "005930")` |
| quality | 퀄리티 | 펀더멘털 | `dartlab.quant("퀄리티", "005930")` |
| value | 가치 | 펀더멘털 | `dartlab.quant("가치", "005930")` |
| earnings | 이익모멘텀 | 펀더멘털 | `dartlab.quant("이익모멘텀", "005930")` |
| sentiment | 공시심리 | 텍스트/공시 | `dartlab.quant("공시심리", "005930")` |
| toneChange | 톤변화 | 텍스트/공시 | `dartlab.quant("톤변화", "005930")` |
| eventSignal | 이벤트신호 | 텍스트/공시 | `dartlab.quant("이벤트신호", "005930")` |
| riskText | 리스크텍스트 | 텍스트/공시 | `dartlab.quant("리스크텍스트", "005930")` |
| governanceQuant | 거버넌스퀀트 | 텍스트/공시 | `dartlab.quant("거버넌스퀀트", "005930")` |
| ranking | 순위 | 횡단면 | `dartlab.quant("순위")` |
| pairs | 페어 | 횡단면 | `dartlab.quant("페어")` |
| screen | 스크린 | 횡단면 | `dartlab.quant("스크린")` |
| altman | Altman Z | 펀더멘털 | `dartlab.quant("altman")` |
| piotroski | Piotroski F | 펀더멘털 | `dartlab.quant("piotroski")` |
| beneish | Beneish M | 펀더멘털 | `dartlab.quant("beneish")` |
| accruals | Sloan Accrual | 펀더멘털 | `dartlab.quant("accruals")` |
| qfactor | q-factor | 펀더멘털 | `dartlab.quant("qfactor")` |
| qmj | QMJ | 펀더멘털 | `dartlab.quant("qmj")` |
| bab | BAB 저베타 | 리스크 | `dartlab.quant("bab")` |
| surprise | 이익서프라이즈 | 펀더멘털 | `dartlab.quant("surprise")` |
| fundmom | 펀더-가격 모멘텀 | 펀더멘털 | `dartlab.quant("fundmom")` |
| meanvar | 평균분산 | 포트폴리오 | `dartlab.quant("평균분산", ["005930", "000660"])` |
| riskparity | 리스크패리티 | 포트폴리오 | `dartlab.quant("리스크패리티", ["005930", "000660"])` |
| allocation | 자산배분 | 포트폴리오 | `dartlab.quant("자산배분", ["005930", "000660"])` |
| strategy | 전략 | 전략 DSL | `dartlab.quant("strategy", "005930", rule=myRule)` |
| backtest | 백테스트 | 전략 DSL | `dartlab.quant("backtest", "005930", style="trendFollow")` |
| style | 스타일 | 전략 DSL | `dartlab.quant("style", "005930", name="all")` |
| entry | 진입진단 | 전략 DSL | `dartlab.quant("entry", "005930", style="all")` |
| walkforward | 워크포워드 | 전략 DSL | `dartlab.quant("walkforward", "005930", style="meanReversion")` |
| multi | 멀티자산 | 전략 DSL | `dartlab.quant("multi", ["005930", "000660"], style="trendFollow")` |

## axis-specific 회피 (회귀 가드)

각 axis 의 sub-spec 본문은 base SKILL.md 의 axis 표에 흡수됨 (2026-05-18 Phase C 정리). standalone 유지: `engines.quant.forecast` · `walkforward` · `scanBacktest` · `marketContext` (algorithm 구체).

| axis | axis-specific 회피 |
| --- | --- |
| accruals | Sloan accruals 한 지표로 분식 단정 X (Beneish + 정합성 동반); (NI−CFO)/TA 분기 vs 연결 vs 별도 scope 혼용 X |
| allocation | ERC 가중치 윈도우 (60D vs 252D) 명시; covariance shrinkage (ledoit-wolf) 방법 명시 |
| altman | Altman Z 임계 (제조 1.81/2.99) 비제조 적용 X (Z'/Z'' 별도); 단일 분기 Z 만으로 부도 단정 X (4 분기 시계열) |
| bab | BAB 레버리지 가정 미명시 수익률 인용 X; 252D beta 가 미래 beta 일치 가정 X |
| backtest | in-sample 결과를 OOS 약속으로 X (walk-forward/cpcv 동반); look-ahead bias 점검 없이 verdict X |
| benchmark | 벤치마크 (KOSPI/KRX300/섹터) 명시 없이 outperformance X; 시총가중 vs 동일가중 차이 무시 X |
| beneish | M > -1.78 한 신호로 분식 단정 X (accruals + 정합성 + 감사 동반); 1990 미국 threshold 를 KR 직접 적용 X |
| beta | benchmarkMode (market/sector/style/auto) 명시; 회귀 기간 (3y/5y/10y) 명시 |
| chartPatterns | 차트 패턴 → 자동 매매 신호 단정 X (거래량/시장환경 동반); 목표가 패턴만으로 단언 X (fundamental anchor) |
| damodaranValuation | 적자 회사에 PER 기반 보정 없이 DCF 단정 X |
| divergence | 재무 vs 가격 괴리 한 신호로 매매 X (산업/매크로 동반); mean reversion + 시장효율성 가정 명시 |
| earnings | SUE 한 분기로 PEAD 단정 X (다분기 누적); 컨센서스 추정기관 수/편차 명시 |
| entry | 진입진단 = 실시간 진단만 (백테스트 검증 X); 스톱/청산 단일 룰 X (변동성/리스크 한도 동반) |
| eventSignal | 이벤트 (M&A/경영진) 단일 신호로 가격 영향 단정 X; 공시 발표 vs 가격 반영 시점 차이 명시 |
| factor | 팩터 (size/value/momentum/quality/vol) 분류 명시; 단일 팩터로 *전략* 단정 X (멀티팩터) |
| flow | 기관/외국인 매매 단방향 신호 단정 X; 보고 시점 (당일 vs T+1) 명시 |
| fundmom | earnings + 12-1 모멘텀 합성 가중치 명시; Chordia-Shivakumar 미국 표본 KR 동일 가정 X |
| governanceQuant | 사외이사 비율/감사의견 단일 지표 단정 X (다지표 결합); 정량 점수만으로 인과 단정 X (정성 보고서 동반) |
| indicators | 30+ 지표 임의 선택 X (분석 의도 그룹 선택); 같은 지표 다른 lookback 혼용 X |
| liquidity | Amihud 비유동성 한 지표로 시장 충격 단정 X; Roll 스프레드 가정 위배 시점 명시 |
| meanvar | Markowitz MV 입력 추정 윈도우 명시; sample mean 노이즈를 진짜 결과로 단정 X |
| momentum | 단일 lookback 만으로 *추세* 단정 X (다중 cross-check); ADTV 낮은 종목 신뢰도 명시 |
| multi | 가중 (equal/inv_vol/risk_parity) 명시; 리밸런싱 주기 (monthly/quarterly) 명시 |
| pairs | 공적분 → 영구 관계 단정 X (구조 변화 시 재검증); spread mean reversion 가정 명시 |
| pattern | 캔들스틱 한 봉으로 추세 단정 X (거래량/다음 봉 confirmation); 지지/저항 자동 탐지 단언 X (zigzag 파라미터 의존) |
| piotroski | F-score 8+ 만으로 *우량* 단정 X (시총/산업 분기); 단일 분기 만으로 X (4+ 분기 시계열) |
| qfactor | Hou-Xue-Zhang q-factor 미국 표본 KR 동일 가정 X; ROE + (-assetGrowth) 합성 가중치 명시 |
| qmj | QMJ (Quality Minus Junk) 미국 기준 KR 동일 가정 X; Profitability + Safety 합성 가중치 명시 |
| quality | quality 산식 (ROE/GP-A/accrual/debt) 분류 명시; 단일 metric 으로 *quality* 단정 X |
| ranking | universe (전종목 vs 산업) 명시; 결손 종목 처리 (skip vs flag) 명시 |
| regime | Hamilton 2-state HMM 학습 윈도우 의존성 명시; Viterbi 추정을 미래 예측으로 단정 X |
| residual | 팩터 모델 (FF3/FF5/Carhart) 명시; 잔여 모멘텀 회귀 윈도우 명시 |
| riskparity | HRP 클러스터링 거리 (correlation) 명시; 모든 시장 환경 우월 단정 X |
| riskText | 리스크 팩터 텍스트 단일 신호로 가격 인과 단정 X; 한국어 NLP 모델/사전 명시 |
| screen | 상위 종목을 곧바로 매수 추천 X (정성 + 분석 파이프라인); 스타일 (가치/모멘텀/퀄리티/저변동) 명시 |
| sentiment | EXTERNAL CONTENT 마커 무시 X; 단일 keyword 빈도로 *심리* 단정 X (다중 keyword) |
| signalReview | 백테스트 가정 (수수료/슬리피지/리밸런싱) 없이 성과 X |
| signals | 골든크로스/RSI/MACD/볼린저 단일 신호 X (다지표 confirm); 표준 파라미터 (RSI 14/MACD 12-26-9) 명시 |
| strategy | 사용자 룰 in-sample 결과 OOS 단정 X; sizing/stop 파라미터 (벤치 fix vs ATR) 명시 |
| style | 8 스타일 프리셋 결과 절대 점수 단정 X (KR reproducibility); 스타일 명시 |
| surprise | Bernard-Thomas PEAD 미국 결과 KR 동일 가정 X; YoY NI z-score 분모 (sigma) 정의 명시 |
| tailrisk | CVaR/MDD 한 지표 단정 X (다지표 결합); VaR/CVaR 신뢰수준 (95%/99%) 명시 |
| toneChange | 공시 톤 변화 한 신호로 가격 인과 단정 X; NLP 모델/사전 (한국어 LM) 명시 |
| value | 단일 멀티플 (PER 만) *value* 단정 X (PER/PBR/PSR/EV-EBITDA 종합); cycle peak PER 낮음 = *value trap* 가능성 |
| verdict | 단일 신호 기반 verdict X (5+ 신호 종합); 가격 기준일 (latestAsOf) 명시 |
| volatility | GARCH(1,1)/HAR-RV 모델 가정/윈도우 명시; 역사적 변동성 (252D) 으로 미래 단정 X (조건부 모델 동반) |
| volume | OBV 추세 한 지표로 매매 X (가격 추세 동반); 거래량/가격 괴리 한 신호로 미래 단정 X |
| worldClass | 가정 (윈도우/가중치/리밸런싱) 명시 없이 Sharpe/IR X; quant 본체 axis_registry 외 임의 디렉터리 추가 X |

**공통 forbidden** (모든 axis): 성과 보장 표현 X · 기간/benchmark/가정 명시 없이 수익률 인용 X · 정량 신호를 인과 분석 결론으로 제시 X.

## 대표 반환 형태

```text
dartlab.quant()
-> DataFrame
   axis, label, description, example, group
```

축 실행은 DataFrame 또는 dict를 반환한다.

```text
target, period, priceDate/latestAsOf, benchmark,
metric, value, score/signal/rank, assumptions, flags
```

백테스트/전략 축은 기간, 룰, 스타일, 포지션, 수익률, drawdown, Sharpe/DSR/PBO 성격의 검증 값을 포함할 수 있다. 포트폴리오 축은 종목별 weight, risk contribution, covariance/correlation 기반 가정을 포함할 수 있다.

## Top-level helper (axis 미등록)

`scanBacktest` 는 axis 가 아닌 attribute 로만 호출한다 (registry dispatcher 의 `fn(stockCode, **kw)` 계약과 시그니처가 어긋나기 때문 — 첫 인자가 DataFrame).

```python
top = dl.scan("valuation").filter(pl.col("등급") == "A").sort("PER").head(20)
result = dl.quant.scanBacktest(top, style="trendFollow", topN=20)
result.scanContext  # {'universeSize': 20, 'scanResultHash': '...', ...}
```

세부 sub-spec: `engines.quant.scanBacktest`.

## evidence 기준

정량 결과는 target, period, benchmark, metric, value, dateRef, executionRef가 필요하다. 백테스트는 수수료, 슬리피지, 리밸런싱, in-sample/out-of-sample 구분을 확인한다.

## 기본 실행 순서

1. 단일 종목, 횡단면, 포트폴리오, 전략 중 작업 유형을 구분한다.
2. 축을 모르면 `dartlab.quant()`로 guide를 확인한다.
3. 필요한 target 또는 종목 리스트를 넣어 axis를 실행한다.
4. 기간, benchmark, assumptions, flags를 확인한다.
5. 재무적 의미 해석은 `analysis`, 후보 발굴은 `scan`, 보고서 조합은 `story`로 넘긴다.

## 기본 검증

스킬은 공개 실행 문서다. `dartlab.quant()` guide 축, 공개 호출, 대표 반환 키가 바뀌면 이 파일과 관련 응용 스킬을 같은 변경에서 갱신한다.
