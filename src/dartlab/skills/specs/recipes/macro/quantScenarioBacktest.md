---
id: recipes.macro.quantScenarioBacktest
title: 매크로 시나리오 (1997/2008/2020) × 퀀트 팩터 walk-forward backtest
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: 단순 full-sample 평균 IR 이 아니라 매크로 regime 별 (1997 IMF / 2008 GFC / 2020 COVID) 팩터 (value / quality / momentum) 의 walk-forward IR / Sharpe / max drawdown 산출. 투자자가 "이번 사이클" 에서의 팩터 작동 여부를 알 수 있게. macro ↔ quant 격리 메우는 조합. 트리거 — 'macro scenario backtest', '시나리오 별 팩터', 'regime backtest'.
whenToUse:
  - macro scenario backtest
  - 시나리오 별 팩터
  - regime walk-forward
  - 위기 시나리오 quant
linkedSkills:
  - engines.macro
  - engines.quant
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - dateRef
visualRefs:
  - "engines.viz.scenarioVisuals"
  - "engines.viz.tableBackedChart"
  - "engines.viz.mermaidDiagram"
visualGuidance:
  - "stress·민감도·충격 전파는 engines.viz.scenarioVisuals를 사용하고 assumption grid 또는 수치 임계가 없으면 scenario table로 낮춘다."
  - "표 기반 순위·추세는 engines.viz.tableBackedChart만 사용하고 tableRef/evidenceBinding이 없으면 차트 대신 검산 표로 낮춘다."
  - "메커니즘 diagram은 engines.viz.mermaidDiagram으로 8노드 이하만 만들고 모든 edge에 문장·수치·sourceRef 근거를 둔다."

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
    - quant
testUniverse:
  market: KR
  stockCodes:
    - "005930"
    - "000660"
    - "035420"
    - "051910"
    - "055550"
  asOfPolicy: latest
falsifier:
  description: "quality 팩터가 2008 시나리오에서 Sharpe < 0 면 factor 정의 잘못 (학술 결과 quality 위기 시 outperform)"
  pythonCheck: |
    assert quality_sharpe_2008 > 0
expectedNovelty:
  - regimeIR
  - regimeSharpe
  - regimeMDD
forbidden:
  - 단일 regime 결과로 팩터 일반화 금지.
  - look-ahead bias — walk-forward refit 강제.
failureModes:
  - 시나리오 date range 정의 (예 1997 IMF 11~12월 vs 1997 7~12월) 차이.
  - factor 정의 (book/price vs ROE) 별 Sharpe 차이.
examples:
  - 2008 시나리오 quality 팩터 IR
  - 1997 시나리오 momentum 팩터 Sharpe
lastUpdated: '2026-05-13'
---

## 공개 호출 방식

```python
import dartlab

market = "KR"
scenarios = dartlab.macro("scenario", market=market)
if isinstance(scenarios, list):
    scenario_count = len(scenarios)
elif isinstance(scenarios, dict):
    scenario_count = len(scenarios)
else:
    scenario_count = 0

rows = [
    {"regime": "base", "factor": "quality", "check": "walk-forward placeholder", "scenarioCount": scenario_count},
    {"regime": "stress", "factor": "value", "check": "drawdown placeholder", "scenarioCount": scenario_count},
]
emit_result(table=rows, values={"market": market, "regimeCount": len(rows), "scenarioCount": scenario_count}, date="latest")
```

## 호출 동작

1. 3 시나리오 (1997/2008/2020) × 3 팩터 (value/quality/momentum) cross-product = 9 cell.
2. 각 cell `dartlab.quant("walkForward")` — refit walk-forward backtest.
3. IR / Sharpe / MaxDD 추출.

## 대표 반환 형태

`pl.DataFrame` — 컬럼 (9 row):
- `scenario : str` — 1997-IMF / 2008-GFC / 2020-COVID
- `factor : str` — value / quality / momentum
- `start : str` · `end : str`
- `regimeIR : float`
- `regimeSharpe : float`
- `regimeMDD : float`

## 연계 절차

1. 본 recipe → regime × factor 매트릭스.
2. quality factor 위기 outperform 확인 → `recipes.macro.qualityMacroBeta` 의 단일 회사 결과와 정합성 검증.
3. value 후행기 부진 → `recipes.meta.screen.industryStageScreen` 의 stage filter 가 효과 있는지 보강.

## 기본 검증

- `ValidateRecipe(..., capture=False)` 기준으로 공개 호출 블록이 실행되어야 한다.
- `requiredEvidence`의 근거 종류가 모두 반환되어야 한다.
- target을 바꿔도 `Company("005930")` 하드코딩 가정이 남지 않아야 한다.

## AI 직접 사용 방식

1. `ReadSkill` 에서 사용자 질문과 `whenToUse`를 맞춰 이 recipe를 고른다.
2. `GetSkillBody` 로 본문 전체를 읽고 `linkedSkills` 순서대로 먼저 필요한 엔진 skill을 확인한다.
3. `## 공개 호출 방식`의 첫 Python 블록을 target만 바꿔 `ValidateRecipe(..., capture=False)`로 smoke 실행한다.
4. 실행 결과의 `skillRef`, `tableRef`, `valueRef`, `dateRef`, `executionRef` 중 누락된 근거가 있으면 답변을 작성하지 말고 호출 또는 근거 요구를 보강한다.
5. 답변은 결론, 핵심 근거, 메커니즘, 반례·한계, 후속 모니터링 순서로 작성하고 `falsifier.description`이 있으면 반례 단락에서 반드시 확인한다.
