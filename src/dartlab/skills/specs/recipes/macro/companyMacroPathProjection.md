---
id: recipes.macro.companyMacroPathProjection
title: 회사 P&L × 매크로 시나리오 grid → 적정가치 분포 (p25/50/75)
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: 기존 base/bull/bear 3 path DCF 가 아니라 매크로 146 시나리오 (rate × FX × 사이클 × 침체) grid × 회사 elasticity → 146 P&L path → 146 fair value → 분포 (p25/p50/p75 + 현재가 대비 확률) 산출. 단일 점추정의 한계 보완. company ↔ macro ↔ analysis 격리 메우는 조합. 트리거 — '시나리오 적정가치 분포', 'fair value distribution', '146 시나리오 valuation'.
whenToUse:
  - 시나리오 적정가치 분포
  - fair value distribution
  - 146 macro path
  - DCF 분포
linkedSkills:
  - engines.company
  - engines.analysis.revenueForecast
  - engines.analysis.macroSensitivity
  - engines.macro.scenario
  - engines.analysis.valuation
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
gap:
  primary:
    - analysis
    - macro
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
  description: "fair value 분포 std-dev 가 base price 의 5% 미만이면 시나리오들이 collapse 한 것 (sensitivity 무효)"
  pythonCheck: |
    assert fv_distribution_std / current_price >= 0.05
expectedNovelty:
  - p25FairValue
  - p50FairValue
  - p75FairValue
  - probAboveCurrent
forbidden:
  - 단일 시나리오 (base) 만으로 적정가치 단정 금지 — 분포 필수.
  - elasticity 가 산업 평균만 사용 — 회사별 추정 신뢰도 차이 무시 금지.
failureModes:
  - 146 시나리오가 너무 corner case 지향이면 분포 fat-tail 으로 왜곡.
  - DCF discount rate (WACC) 가 시나리오 별 변동 — 단순 일정 가정 시 분포 좁아짐.
examples:
  - 삼성전자 146 시나리오 fair value 분포
  - 현대차 시나리오 적정가치 p25/p50/p75
lastUpdated: '2026-05-10'
---

## 공개 호출 방식

```python
import dartlab
import polars as pl
import statistics

c = dartlab.Company("005930")

# 1. revenue 기본 forecast (base/bull/bear)
forecast = c.analysis("revenueForecast", "매출예측")
base_revenue = forecast.get("baseRevenue", 0) if isinstance(forecast, dict) else 0

# 2. 매크로 sensitivity (회사별 elasticity)
sensitivity = c.analysis("macroSensitivity", "매크로민감도")
rate_elasticity = sensitivity.get("rateElasticity", -0.05) if isinstance(sensitivity, dict) else -0.05
fx_elasticity = sensitivity.get("fxElasticity", 0.1) if isinstance(sensitivity, dict) else 0.1

# 3. 매크로 시나리오 grid (1 차 wave: 5 × 5 × 6 = 150 의 일부 — 146 으로 축소)
scenarios = dartlab.macro("scenario", market="KR")
if not isinstance(scenarios, list):
    scenarios = []
scenarios = scenarios[:146]

# 4. 각 시나리오 → P&L 충격 → DCF
fair_values = []
current_price = c.gather("price").get("latestClose", 0) if hasattr(c, "gather") else 0

for sc in scenarios:
    rate_shock = sc.get("rateShockBp", 0) / 10000 if isinstance(sc, dict) else 0
    fx_shock = sc.get("fxShockPct", 0) / 100 if isinstance(sc, dict) else 0
    revenue_delta = base_revenue * (rate_elasticity * rate_shock + fx_elasticity * fx_shock)
    shocked_revenue = base_revenue + revenue_delta
    # 단순 EV/Sales multiple 기반 fair value (DCF 풀 fold 는 별도 wave)
    valuation = c.analysis("valuation", "가치평가")
    multiple = valuation.get("evSalesMultiple", 1.5) if isinstance(valuation, dict) else 1.5
    fv = shocked_revenue * multiple
    fair_values.append(fv)

if fair_values:
    sorted_fv = sorted(fair_values)
    p25 = sorted_fv[len(sorted_fv) // 4]
    p50 = sorted_fv[len(sorted_fv) // 2]
    p75 = sorted_fv[3 * len(sorted_fv) // 4]
    above_current = sum(1 for fv in fair_values if fv > current_price) / len(fair_values)
    distribution_std = statistics.pstdev(fair_values) if len(fair_values) > 1 else 0
else:
    p25 = p50 = p75 = above_current = distribution_std = 0

emit_result(
    table=[{
        "scenarioCount": len(fair_values),
        "currentPrice": current_price,
        "p25FairValue": round(p25, 0),
        "p50FairValue": round(p50, 0),
        "p75FairValue": round(p75, 0),
        "probAboveCurrent": round(above_current, 3),
        "distributionStd": round(distribution_std, 0),
    }],
    values={"p50FairValue": p50, "probAboveCurrent": above_current},
    date="2024-12-31",
)
```

## 호출 동작

1. `c.analysis("revenueForecast")` — base revenue forecast.
2. `c.analysis("macroSensitivity")` — rate / FX elasticity.
3. `dartlab.macro("scenario")` — 146 시나리오 (rate × FX × phase grid).
4. 각 시나리오 → revenue shock → fair value (multiple 기반).
5. 분포 p25/50/75 + 현재가 대비 above 확률.

## 대표 반환 형태

`pl.DataFrame` — 단일 row:
- `scenarioCount : int`
- `currentPrice : float`
- `p25FairValue : float` · `p50FairValue : float` · `p75FairValue : float`
- `probAboveCurrent : float`
- `distributionStd : float`

## 연계 절차

1. 본 recipe → 적정가치 분포.
2. probAboveCurrent > 0.7 → strong buy / < 0.3 → strong sell signal.
3. distribution std-dev 큰 종목 → sensitivity 큰 회사. `recipes.macro.macroBetaPeerScreen` 와 결합.
