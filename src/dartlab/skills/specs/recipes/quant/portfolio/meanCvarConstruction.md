---
id: recipes.quant.portfolio.meanCvarConstruction
title: Mean-CVaR Portfolio Construction
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: Mean-CVaR (Conditional Value-at-Risk) 포트폴리오 — Rockafellar-Uryasev 2000 정통. tail risk 직접 최적화. quant `meanCVaR` 모듈 사용자 표면 recipe. **status=drafted (코드는 Sprint 5 완료, 사용자 진입점 spec 부재)**. 트리거 — 'Mean-CVaR', 'CVaR portfolio', 'tail risk 최적화', 'Rockafellar-Uryasev', 'portfolio construction'.
whenToUse:
  - mean-CVaR
  - CVaR portfolio
  - tail risk optimization
  - Rockafellar-Uryasev
  - portfolio construction
linkedSkills:
  - engines.quant
  - engines.scan
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
  description: 최적 portfolio CVaR > equal-weight CVaR = optimization 가치 0.
  pythonCheck: |
    assert optimal_cvar < equal_weight_cvar
expectedNovelty:
  - weights
  - cvar
  - expectedReturn
forbidden:
  - CVaR level 단일 선택 X — 5% / 95% / 99% 동시 검토 권장.
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
from dartlab.quant.portfolio.meanCVaR import optimizeMeanCVaR
import dartlab

universe = ["005930", "000660", "035720", "207940", "035420"]
returns = ...   # universe historical returns matrix
weights = optimizeMeanCVaR(returns, alpha=0.05, target_return=0.001)
```

## 호출 동작

historical returns matrix + alpha (CVaR level) + target return → projected gradient 최적화. weights + CVaR + expected return 반환.

## 대표 반환 형태

dict — `weights (np.array) + cvar + expectedReturn + sharpe`.

## 연계 절차

1. 본 recipe → CVaR-optimal weights.
2. 결과 vs equal-weight / mean-variance 비교.
3. `recipes.quant.portfolio.blackLittermanViewBuild` 결합 (views 반영).
