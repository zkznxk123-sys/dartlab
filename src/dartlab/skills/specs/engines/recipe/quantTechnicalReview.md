---
id: engines.recipe.quantTechnicalReview
title: quant 기술적 review (지표 + 모멘텀 + 변동성 + 패턴)
category: engines
kind: recipe
scope: builtin
status: unverified
purpose: 단일 종목의 기술적 신호를 지표 종합 + 모멘텀 + 변동성 + 차트 패턴 4 축으로 묶어 entry/exit 판단을 보강하는 절차. 트리거 — '기술적 신호', '모멘텀 변동성', '차트 패턴 4 축'.
whenToUse:
  - 기술적 분석
  - quant 분석
  - 차트 신호
  - 모멘텀 분석
  - RSI MACD 볼린저
  - 변동성 점검
  - 차트 패턴 인식
linkedSkills:
  - engines.company.researchStarter
  - engines.quant.indicators
  - engines.quant.momentum
  - engines.quant.volatility
  - engines.quant.chartPatterns
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - valueRef
  - dateRef
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
    limitations:
      - browser 안에서는 price 시계열 일부 한정
lastUpdated: '2026-05-07'
---

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")

verdict = c.quant("판단")
indicators = c.quant("지표")
momentum = c.quant("모멘텀")
volatility = c.quant("변동성")
patterns = c.quant("패턴")
```

## 호출 동작

기술적 종합 판정 (verdict) + 45 개 지표 시계열 + 모멘텀 + 변동성 + 차트 패턴 결합.

1. 회사 진입
2. quant("판단") — 종합 verdict (RSI/ADX/MACD/볼린저/상대강도)
3. quant("지표") — 45 개 지표 DataFrame
4. quant("모멘텀") — 단기/중기/장기 모멘텀
5. quant("변동성") — ATR / Bollinger Band / 역사적 변동성
6. quant("패턴") — 차트 패턴 (head&shoulders, double top/bottom 등)

## 대표 반환 형태

- `tableRef` 3+ 개 (지표 / 모멘텀 / 변동성)
- `valueRef` 5+ (verdict / RSI / ADX / MACD signal / ATR)
- `dateRef` 1 개

## 연계 절차

1. engines.company.researchStarter — 회사 진입
2. engines.quant.indicators — 45 지표
3. engines.quant.momentum — 모멘텀
4. engines.quant.volatility — 변동성
5. engines.quant.chartPatterns — 차트 패턴

## 기본 검증

- verdict 단독 노출 X — 핵심 지표 (RSI / ADX / MACD) 함께.
- 시간 단위 명시 (일봉 / 주봉 / 월봉).
- "강한 매수" 단정 X — 지표 값 + 신뢰 구간 함께.
- 펀더멘털 (analysis) 과 함께 보면 더 강한 신호.
