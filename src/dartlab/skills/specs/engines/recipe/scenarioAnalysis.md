---
id: engines.recipe.scenarioAnalysis
title: 시나리오 분석 (forecast + macro 시나리오 + quant regime)
category: engines
kind: recipe
scope: builtin
status: unverified
purpose: 회사 forecast 를 base/bull/bear 3 시나리오 + 매크로 시나리오 가정 + 시장 regime 판정 3 축으로 묶어 불확실성을 정량화하는 절차. 트리거 — 'base/bull/bear', '3 시나리오', '시장 regime', '불확실성 정량화'.
whenToUse:
  - 시나리오 분석
  - base bull bear
  - 불확실성 평가
  - 매크로 시나리오 영향
  - 시장 regime 판단
  - 매출 전망 시나리오
  - 적정주가 범위
linkedSkills:
  - engines.company.researchStarter
  - engines.analysis.revenueForecast
  - engines.macro.scenario
  - engines.quant.regime
  - engines.analysis.macroSensitivity
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
      - browser 안에서는 forecast scenario 가정 grid 일부 한정
forbidden:
  - 시나리오 가정 (성장률 / 마진 / 매크로) 명시 없이 base / bull / bear 단정 금지.
  - 단일 시나리오 (예 — base) 결과를 점추정 fair value 로 단정 금지.
  - 시장 regime (HMM 2-state) 결과를 미래 regime 예측으로 단정 금지.
  - 매크로 시나리오 (1997 / 2008) 직접 비교를 반복 가능성으로 단정 금지.
failureModes:
  - 시나리오 확률 (base 50% / bull 30% / bear 20%) 임의 부여
  - 매크로 시나리오 (146 프리셋) 임의 선택
  - regime 추정의 학습 윈도우 의존성"
  - 회사 forecast 와 매크로 시나리오 일관성 누락
  - 시나리오 결과 분포의 신뢰구간 미명시
examples:
  - 삼성전자 base / bull / bear 시나리오
  - 매크로 (금리 인상) + 회사 forecast
  - regime + 시나리오 결합
  - 시나리오 + valuation band
lastUpdated: '2026-05-07'
---

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")

forecast = c.analysis("forecast", "매출전망")
sensitivity = c.analysis("financial", "macro민감도")
macro_scenario = dartlab.macro("scenario")
regime = c.quant("국면")
```

## 호출 동작

회사 매출 전망 (3 시나리오) → 매크로 변수별 sensitivity → 매크로 시나리오 가정 → 현재 시장 regime 판정 결합. 가정 변수를 정해진 grid 로 흔들어 결과 분포 생성.

1. 회사 진입
2. analysis("forecast", "매출전망") — base/bull/bear 매출
3. analysis("financial", "macro민감도") — 환율·금리·유가 elasticity
4. macro("scenario") — 매크로 시나리오 가정 grid
5. quant("국면") — 시장 regime 판정 (bull/bear/range)

## 대표 반환 형태

- `tableRef` 3+ 개 (forecast 시나리오 + sensitivity + macro scenario)
- `valueRef` 6+ (base/bull/bear 매출 / 환율 elasticity / regime 판정 / 확률 가중 적정가)
- `dateRef` 1 개

## 연계 절차

1. engines.company.researchStarter — 회사 진입
2. engines.analysis.revenueForecast — 매출 base/bull/bear
3. engines.analysis.macroSensitivity — 매크로 elasticity
4. engines.macro.scenario — 매크로 시나리오 가정
5. engines.quant.regime — 시장 regime

## 기본 검증

- 시나리오는 항상 가정 명시 (환율 / 금리 / 매출 성장률 / 마진 등).
- 각 시나리오에 확률 또는 가능성 등급 함께.
- 단일 forecast X — 분포 (range, 확률 가중 평균).
- regime 판정 근거 (변동성 / 추세 / 거래량) 명시.
