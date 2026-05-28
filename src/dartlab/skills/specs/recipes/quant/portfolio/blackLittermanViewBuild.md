---
id: recipes.quant.portfolio.blackLittermanViewBuild
title: Black-Litterman View Build
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: Black-Litterman 1992 — equilibrium prior + investor views → posterior expected returns + covariance. quant `blackLitterman` 모듈 사용자 표면 recipe. **status=drafted**. 트리거 — 'Black-Litterman', 'BL views', 'equilibrium prior', 'posterior returns', 'investor views'.
whenToUse:
  - Black-Litterman
  - BL views
  - equilibrium prior
  - investor views
  - posterior returns
linkedSkills:
  - engines.quant
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - valueRef
  - dateRef
  - executionRef
  - sourceRef
visualRefs:
  - engines.viz.tableBackedChart
gap:
  primary:
    - quant
    - scan
testUniverse:
  market: KR
  stockCodes:
    - "005930"
    - "000660"
    - "035720"
    - "207940"
    - "035420"
  asOfPolicy: latest
falsifier:
  description: posterior expected returns == prior = views 영향 0 = view 설정 오류.
  pythonCheck: |
    assert not (posterior == prior).all()
expectedNovelty:
  - posteriorReturns
  - posteriorCov
  - viewImpact
forbidden:
  - views 단순 점추정 X — confidence (uncertainty) 동행.
  - market cap weight = equilibrium prior 가정 — KR universe 시 small-cap 왜곡 주의.
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: limited
  pyodide:
    status: limited
---

## 공개 호출 방식

```python
from dartlab.quant.blackLitterman import blackLittermanPosterior, buildSimpleViews

universe = ["005930", "000660", "035720", "207940", "035420"]
prior = ...   # equilibrium prior (market cap weight)
cov = ...     # historical covariance
views = buildSimpleViews(["005930 > 000660 by 2%"])   # relative views
posterior = blackLittermanPosterior(prior, cov, views)
```

## 호출 동작

prior (equilibrium) + covariance + views (relative / absolute) → posterior μ, Σ 반환. confidence 매개 (τ).

## 대표 반환 형태

dict — `posteriorReturns + posteriorCov + viewImpact + tau`.

## 연계 절차

1. 본 recipe → posterior estimates.
2. posterior + meanCVaR 결합 → `recipes.quant.portfolio.meanCvarConstruction`.
3. view 시계열 backtest → walk-forward.
