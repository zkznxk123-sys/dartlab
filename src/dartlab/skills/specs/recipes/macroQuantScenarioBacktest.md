---
id: recipes.macroQuantScenarioBacktest
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
  - engines.macro.scenario
  - engines.quant.walkforward
  - engines.quant.backtest
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - dateRef
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
lastUpdated: '2026-05-10'
---

## 공개 호출 방식

```python
import dartlab
import polars as pl

# 1. 시나리오 별 date range 정의
SCENARIO_DATES = {
    "1997-IMF": ("1997-07-01", "1998-12-31"),
    "2008-GFC": ("2008-09-01", "2009-12-31"),
    "2020-COVID": ("2020-02-01", "2020-12-31"),
}

# 2. 팩터 list
FACTORS = ["value", "quality", "momentum"]

# 3. 각 시나리오 × 각 팩터 walk-forward
results = []
for scenario, (start, end) in SCENARIO_DATES.items():
    for factor in FACTORS:
        try:
            wf = dartlab.quant("walkForward", market="KR", factor=factor, start=start, end=end)
            if isinstance(wf, dict):
                ir = wf.get("ir", 0)
                sharpe = wf.get("sharpe", 0)
                mdd = wf.get("maxDrawdown", 0)
            else:
                ir, sharpe, mdd = 0, 0, 0
        except Exception:
            ir, sharpe, mdd = 0, 0, 0
        results.append({
            "scenario": scenario,
            "factor": factor,
            "start": start,
            "end": end,
            "regimeIR": round(float(ir), 3),
            "regimeSharpe": round(float(sharpe), 3),
            "regimeMDD": round(float(mdd), 3),
        })

emit_result(
    table=results,
    values={"scenarioCount": len(SCENARIO_DATES), "factorCount": len(FACTORS)},
    date="2024-12-31",
)
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
2. quality factor 위기 outperform 확인 → `recipes.qualityMacroBeta` 의 단일 회사 결과와 정합성 검증.
3. value 후행기 부진 → `recipes.industryStageScreen` 의 stage filter 가 효과 있는지 보강.
