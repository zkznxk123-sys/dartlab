---
id: recipes.dividendStressTest
title: 배당 지속 가능성 — 매크로 침체 시나리오 별 cut/suspend 임계
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: 배당 정책 회사가 1997 IMF / 2008 GFC / 2020 COVID 시나리오에서 FCF 커버리지가 무너지는 임계 + 배당 cut/suspend 가능성 산출. 정상 시점 dividend yield 만 보고 매수하는 전략의 매크로 위험 가시화. analysis ↔ macro 격리 메우는 조합. 트리거 — '배당 스트레스', 'dividend cut 위험', '경기침체 배당'.
whenToUse:
  - 배당 스트레스 테스트
  - dividend cut 위험
  - 경기침체 배당
  - FCF coverage 매크로
linkedSkills:
  - engines.company
  - recipes.dividendCapitalReturn
  - engines.analysis.cashflow
  - engines.macro.scenario
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
    - "012330"
    - "055550"
  asOfPolicy: latest
falsifier:
  description: 2008 시나리오 stress test 가 dividendSurvival=Cut 인데 실제 배당 유지된 회사가 다수면 sensitivity 과민
  pythonCheck: |
    assert actual_2008_cut_rate(stress_predicted_cut) > actual_2008_cut_rate(stress_predicted_safe)
expectedNovelty:
  - dividendSurvival
  - shockedCoverage
  - scenarioRevenuShock
forbidden:
  - 시나리오 1 개 (2008) 결과로 일반 침체 단정 금지 — 1997 / 2020 함께 비교.
  - 배당 cut = 회사 폭락 단정 금지 — 일시 cut 후 회복 사례도 다수.
failureModes:
  - revenue 충격 일정 비율 가정 — 실제는 산업 별 매출 노출 다름 (금융 < 자동차 < 항공).
  - 배당 정책 (target payout vs progressive) 별 cut threshold 차이.
examples:
  - 삼성전자 2008 시나리오 배당 유지 가능?
  - KT&G 1997 시나리오 dividend cut 임계
lastUpdated: '2026-05-10'
---

## 공개 호출 방식

```python
import dartlab
import polars as pl

c = dartlab.Company("005930")

# 1. 현재 배당 + FCF coverage
div = c.analysis("dividendCapitalReturn", "배당정책")
payout_ratio = div.get("payoutRatio", 0.3) if isinstance(div, dict) else 0.3
fcf_coverage = div.get("fcfCoverage", 1.5) if isinstance(div, dict) else 1.5

# 2. P&L baseline — revenue / opMargin
is_df = c.show("IS", freq="Y")

def fetch(df, snake, year="2024"):
    row = df.filter(pl.col("snakeId") == snake).select(year)
    return float(row.to_numpy()[0][0]) if row.height > 0 else 0.0

revenue = fetch(is_df, "revenue")
op_profit = fetch(is_df, "operating_profit")
op_margin = op_profit / revenue if revenue else 0.05

# 3. 매크로 시나리오 별 revenue 충격 (학술적 평균)
SCENARIO_REVENUE_SHOCK = {
    "1997-IMF": -0.30,    # 한국 -30%
    "2008-GFC": -0.20,    # 글로벌 -20%
    "2020-COVID": -0.15,  # 단기 -15%
}

results = []
for name, shock in SCENARIO_REVENUE_SHOCK.items():
    shocked_revenue = revenue * (1 + shock)
    shocked_op = shocked_revenue * op_margin  # 마진 일정 가정 (1차 wave).
    # FCF 단순 = OP × 0.7 (세후 + 운전자본 감안).
    shocked_fcf = shocked_op * 0.7
    # 배당 = 정상 배당 (=이익 × payout) 가정.
    base_dividend = op_profit * 0.7 * payout_ratio
    shocked_coverage = shocked_fcf / base_dividend if base_dividend else 0
    if shocked_coverage > 1.2:
        survival = "Safe"
    elif shocked_coverage > 0.5:
        survival = "Cut"
    else:
        survival = "Suspend"
    results.append({
        "scenario": name,
        "revenueShock": shock,
        "shockedRevenue": round(shocked_revenue, 0),
        "shockedFCF": round(shocked_fcf, 0),
        "baseDividend": round(base_dividend, 0),
        "shockedCoverage": round(shocked_coverage, 2),
        "dividendSurvival": survival,
    })

emit_result(
    table=results,
    values={
        "imfSurvival": results[0]["dividendSurvival"],
        "gfcSurvival": results[1]["dividendSurvival"],
        "covidSurvival": results[2]["dividendSurvival"],
    },
    date="2024-12-31",
)
```

## 호출 동작

1. `c.analysis("dividendCapitalReturn")` — 현재 payout + FCF coverage.
2. `c.show("IS", freq="Y")` 로 revenue / op_profit / margin.
3. 3 시나리오 (1997/2008/2020) revenue shock 적용 → shocked FCF.
4. shocked coverage 임계: > 1.2 Safe / > 0.5 Cut / 그 이하 Suspend.

## 대표 반환 형태

`pl.DataFrame` — 컬럼 (시나리오 별 row):
- `scenario : str` — 1997-IMF / 2008-GFC / 2020-COVID
- `revenueShock : float`
- `shockedRevenue : float` · `shockedFCF : float`
- `baseDividend : float`
- `shockedCoverage : float`
- `dividendSurvival : str` — Safe / Cut / Suspend

## 연계 절차

1. 본 recipe → 3 시나리오 별 dividend survival.
2. dividend cut/suspend 시나리오 ≥ 2 → `recipes.creditMacroStress` 와 결합 — 신용 axis 영향 동시 점검.
3. universe 검증은 `recipes.distressCandidateScreen` 에 dividend payer 한정.
