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
