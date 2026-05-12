---
id: engines.recipe.economicSixActs
title: 경제분석 6막 진입 절차
category: engines
kind: recipe
scope: builtin
status: drafted
purpose: 종목 없이 경제분석을 시작할 때 macro 12축을 6막 인과 순서로 호출해 현재 경기 위치, 정책, 금융시스템, 시장 반응, 향후 시나리오를 한 번에 정리하는 절차. 트리거 — '경제분석 시작', '거시 전체', '매크로 6막', '경제 상황 요약'.
whenToUse:
  - 경제분석 시작
  - 매크로 전체
  - 거시 6막
  - 경기 정책 유동성 시장 종합
  - economic six acts
linkedSkills:
  - engines.macro
  - engines.macro.cycle
  - engines.macro.rates
  - engines.macro.liquidity
  - engines.macro.crisis
  - engines.macro.assets
  - engines.macro.sentiment
  - engines.macro.forecast
  - engines.macro.scenario
  - engines.macro.summary
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - dateRef
  - valueRef
  - executionRef
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
gap:
  primary:
    - macro
    - story
testUniverse:
  market: KR
  asOfPolicy: latest
falsifier:
  description: "summary 결과가 cycle/rates/liquidity/crisis 중 2축 이상을 포함하지 못하면 6막 진입 recipe로 부적합하다."
expectedNovelty:
  - actOrder
  - macroDashboard
  - causalSummary
forbidden:
  - 모든 경제 질문에 6막을 강제하지 않는다. 사용자가 단일 축을 원하면 해당 macro 축만 호출한다.
  - 기준일 없는 수치 판단 금지.
  - summary 점수만 보고 결론 금지 — cycle/rates/liquidity/crisis의 근거를 함께 확인한다.
failureModes:
  - KR/US 시장을 섞어 기준일과 지표 단위가 어긋남.
  - 6막 순서가 아닌 단편 축 나열로 끝남.
  - scenario를 현재 상태처럼 오해함.
examples:
  - 한국 경제 지금 어디에 있나
  - 미국 매크로 전체 상황 6막으로 정리
  - 경기와 금리와 위기 신호를 한 번에 봐줘
lastUpdated: '2026-05-12'
---

## 공개 호출 방식

```python
import dartlab

market = "KR"
guide = dartlab.macro()
try:
    summary = dartlab.macro("summary", market=market)
except Exception as exc:
    summary = {"error": str(exc)}
cycle = dartlab.macro("cycle", market=market)
rates = dartlab.macro("rates", market=market)
liquidity = dartlab.macro("liquidity", market=market)
crisis = dartlab.macro("crisis", market=market)
assets = dartlab.macro("assets", market=market)
sentiment = dartlab.macro("sentiment", market=market)
forecast = dartlab.macro("forecast", market=market)

emit_result(
    table=[
        {"act": 1, "axis": "cycle", "result": cycle},
        {"act": 3, "axis": "rates", "result": rates},
        {"act": 4, "axis": "liquidity", "result": liquidity},
        {"act": 4, "axis": "crisis", "result": crisis},
        {"act": 5, "axis": "assets", "result": assets},
        {"act": 5, "axis": "sentiment", "result": sentiment},
        {"act": 6, "axis": "forecast", "result": forecast},
    ],
    values={
        "market": market,
        "overall": summary.get("overall") if isinstance(summary, dict) else None,
        "score": summary.get("score") if isinstance(summary, dict) else None,
    },
    date=summary.get("latestAsOf") if isinstance(summary, dict) else None,
)
```

## 호출 동작

1. `dartlab.macro()` 로 사용 가능한 12축을 확인한다.
2. `summary` 를 먼저 호출해 전체 판정과 사용 가능한 하위 축 결과를 확인한다.
3. 6막 순서로 `cycle → rates → liquidity/crisis → assets/sentiment → forecast` 를 점검한다.
4. 결론은 `overall/score` 가 아니라 각 막의 근거 지표와 기준일을 묶어 작성한다.

## 대표 반환 형태

- `tableRef`: 6막별 axis 결과 목록.
- `valueRef`: `overall`, `score`, 핵심 지표 값.
- `dateRef`: 각 macro 축의 최신 관측일 또는 실행 기준일.
- 답변 본문: 현재 국면, 정책 방향, 금융 취약성, 시장 반응, 다음 확인 시나리오.

## 연계 절차

1. 현재 위치가 불명확하면 `engines.recipe.historicalPositioning` 으로 과거 위기 대비 위치를 비교한다.
2. 신용 취약성이 핵심이면 `engines.recipe.creditCycleStressMap` 으로 이동한다.
3. 꼬리위험 질문이면 `engines.recipe.tailRiskScenarioScan` 으로 이동한다.

## 기본 검증

- `summary` 와 개별 axis의 방향이 충돌하면 충돌을 숨기지 않고 병기한다.
- KR 분석은 `market="KR"`, US 분석은 `market="US"` 를 명시한다.
- 기준일이 없는 값은 판단 근거가 아니라 보조 힌트로만 쓴다.
