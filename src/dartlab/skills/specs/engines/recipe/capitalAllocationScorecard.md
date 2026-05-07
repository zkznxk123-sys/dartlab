---
id: engines.recipe.capitalAllocationScorecard
title: 자본배분 점수카드 (FCF 5 사용처 + ROIIC + SGR — L1 raw)
category: engines
kind: recipe
scope: builtin
status: unverified
purpose: Buffett-style 자본배분 평가 — FCF 의 5 사용처 (재투자·배당·자사주·M&A·부채상환) 비중 + 증분자본수익률 (ROIIC) + 지속가능성장률 (SGR) 을 L1 raw 시계열에서 직접 계산해 경영진의 자본배분 효율을 평가하는 절차. analysis axis 미사용. 트리거 — '자본배분 평가', 'FCF 사용처', 'ROIIC', 'Buffett 자본배분'.
whenToUse:
  - 자본배분 평가
  - FCF 사용처 분석
  - Buffett 자본배분 점수
  - ROIIC 증분자본수익률
  - 지속가능성장률 SGR
  - 경영진 효율 평가
linkedSkills:
  - engines.company
  - engines.gather
  - engines.recipe.dupontDriver
  - engines.recipe.compounderCandidates
  - engines.recipe.intrinsicValueBand
  - engines.recipe.workingCapitalQuality
toolRefs:
  - engine_call
  - run_python
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
      - 브라우저 안에서는 다년 시계열 일부 한정
lastUpdated: '2026-05-07'
---

## 학술 근거

Warren Buffett 주주서한 (Berkshire Hathaway, 1977-2024): "**Capital allocation is the most important job of a CEO.**" 핵심 원칙:

- **5 사용처** — Free Cash Flow 가 어디로 가나: (1) 재투자 (CAPEX·R&D), (2) 배당, (3) 자사주 매입, (4) M&A, (5) 부채 상환.
- **ROIIC** (Return on Incremental Invested Capital) = ΔNOPAT / ΔInvestedCapital. 새로 투입한 자본 1 원이 얻는 수익률. 본질적 capital efficiency.
- **SGR** (Sustainable Growth Rate) = ROE × (1 − payoutRatio). 외부 자본조달 없이 가능한 성장 한계.

학술 검증:
- Penman-Reggiani (2018): ROIIC &gt; WACC 인 회사가 미래 abnormal return 강함. 단순 ROE 보다 우월.
- Damodaran (2010): "Capital Allocation Quality" — 5 사용처 비중이 회사 가치의 30-50% 설명. M&A 비중 높은 회사 평균 가치 파괴.
- Higgins (1977): SGR 가 actual growth 보다 크게 떨어지면 자본 부족 또는 비효율.

## 5 사용처 정의 (CF Statement 기반)

| 사용처 | CF 항목 (snakeId) | 부호 |
|---|---|---|
| 재투자 | capital_expenditures | 음 (CAPEX 지출) |
| 배당 | cash_dividends_paid | 음 (배당 지출) |
| 자사주 | repurchase_of_treasury_stock | 음 (자사주 매입 지출) |
| M&A | acquisitions_net_of_cash_acquired (또는 investments_acquisition) | 음 (인수 지출) |
| 부채 상환 | repayment_of_long_term_debt − issuance_of_long_term_debt | 순 (상환 - 차입) |

FCF (자유현금흐름) = `cash_flow_from_operations − capital_expenditures` (CFO − CAPEX).

## 공개 호출 방식

```python
import dartlab
import polars as pl

c = dartlab.Company("005930")

cf_df = c.show("CF", freq="Y")
bs_df = c.show("BS", freq="Y")
is_df = c.show("IS", freq="Y")
years = ["2025", "2024", "2023", "2022", "2021"]

def fetchSeries(df: pl.DataFrame, snake: str, years: list[str]) -> list[float]:
    row = df.filter(pl.col("snakeId") == snake).select(years)
    return row.to_numpy()[0].tolist() if row.height > 0 else [0.0] * len(years)

cfo = fetchSeries(cf_df, "cash_flow_from_operations", years)
capex = fetchSeries(cf_df, "capital_expenditures", years)
dividends = fetchSeries(cf_df, "cash_dividends_paid", years)
buyback = fetchSeries(cf_df, "repurchase_of_treasury_stock", years)
acq = fetchSeries(cf_df, "acquisitions_net_of_cash_acquired", years)
debtRepay = fetchSeries(cf_df, "repayment_of_long_term_debt", years)
debtIssue = fetchSeries(cf_df, "issuance_of_long_term_debt", years)

ni = fetchSeries(is_df, "net_income", years)
equity = fetchSeries(bs_df, "total_stockholders_equity", years)
investedCapital = [
    fetchSeries(bs_df, "total_stockholders_equity", years)[i]
    + fetchSeries(bs_df, "long_term_debt", years)[i]
    for i in range(len(years))
]

rows = []
for i, y in enumerate(years[:-1]):
    fcf = cfo[i] - abs(capex[i])
    totalUse = abs(capex[i]) + abs(dividends[i]) + abs(buyback[i]) + abs(acq[i]) + (debtRepay[i] - debtIssue[i])
    payoutRatio = (abs(dividends[i]) + abs(buyback[i])) / ni[i] if ni[i] > 0 else None
    sgr = (ni[i] / equity[i]) * (1 - payoutRatio) if payoutRatio is not None else None

    deltaNopat = ni[i] - ni[i+1]
    deltaInvested = investedCapital[i] - investedCapital[i+1]
    roiic = deltaNopat / deltaInvested if deltaInvested != 0 else None

    rows.append({
        "year": y,
        "fcf": fcf,
        "reinvestPct": abs(capex[i]) / totalUse if totalUse > 0 else None,
        "dividendPct": abs(dividends[i]) / totalUse if totalUse > 0 else None,
        "buybackPct": abs(buyback[i]) / totalUse if totalUse > 0 else None,
        "acquisitionPct": abs(acq[i]) / totalUse if totalUse > 0 else None,
        "debtRepayPct": (debtRepay[i] - debtIssue[i]) / totalUse if totalUse > 0 else None,
        "payoutRatio": payoutRatio,
        "sgr": sgr,
        "roiic": roiic,
    })

scorecard = pl.DataFrame(rows)
```

## 호출 동작

1. `c.show("CF" | "BS" | "IS", freq="Y")` 3 회 — 5 년 wide 시계열.
2. snakeId 로 9 항목 추출 (CFO·CAPEX·배당·자사주·M&A·부채상환·차입·NI·자본).
3. FCF 계산 + 5 사용처 비중 정규화.
4. SGR = ROE × (1 − payout) 계산.
5. ROIIC = ΔNI / ΔInvestedCapital — 증분 자본 수익률.

## 대표 반환 형태

`scorecard : pl.DataFrame` — 컬럼:
- `year`, `fcf : float`
- `reinvestPct`, `dividendPct`, `buybackPct`, `acquisitionPct`, `debtRepayPct : float` — 합 ≈ 100%
- `payoutRatio : float` — (배당 + 자사주) / NI
- `sgr : float` — 지속가능성장률
- `roiic : float` — 증분 자본 수익률

## 한계

- **snakeId 가용성** — 한국 일부 회사 CF 항목 분리 안 됨 (특히 M&A 가 investing_cashflow 안에 통합). fallback 으로 항목 누락 시 0 처리.
- **자사주 소각 vs 보유 구분 X** — 한국 회사 자사주 매입 후 소각 안 하는 비중 큼. 본 recipe 는 buyback 지출만, 소각 별도 검증 필요.
- **ROIIC 노이즈** — 단년도 ΔNI 변동 크면 음수 / 무한대 가능. 5 년 평균 ROIIC 권장.
- **WACC 부재** — Buffett 원전은 ROIIC &gt; WACC 게이트. dartlab WACC 미노출 — 본 recipe 는 ROIIC 절대값만, 자본비용 비교는 외부 추정.
- **부채 상환 부호** — 회사가 적자 보존 위해 부채 차입하면 debtRepay 음수. 자본 사용처가 아니라 *조달처*.

## 한국 / 미국 시장 차이

- **한국**: 자사주 매입 후 소각 부재로 buybackPct 신뢰성 낮음 (소각 안 하면 효과 0). Value-up 프로그램 (2024-) 으로 변화 시작. 배당 비중 평균 20% 미국 대비 낮음.
- **미국**: 자사주 매입 비중 평균 50% (S&P 500). buybackPct 가 자본배분 평가 핵심. M&A 활발 — acquisitionPct 비중 평균 20%.

## 연계 절차

1. 본 recipe → 5 년 자본배분 표 + ROIIC + SGR.
2. ROIIC &lt; SGR 이면 capital 비효율 신호 → `engines.recipe.dupontDriver` 로 ROE 동인 점검.
3. M&A 비중 큰 회사 → 인수 후 통합 효율 (goodwill 추적) 별도.
4. 자사주 비중 큰 회사 → 소각 vs 보유 구분, EPS 변화로 검증.
5. SGR &lt; actual growth → 외부 자본조달 의존 (유상증자·차입) 확인.
6. `engines.recipe.compounderCandidates` 와 상호 검증 — 진짜 compounder 는 ROIIC &gt; 15% 일관.

## 기본 검증

- 5 사용처 합 ≈ 100% (오차 5% 이내) 확인 — 누락 항목 없는지 검증.
- ROIIC 5 년 평균 분포 — 우량 회사 15-25%, 평균 5-10%, 음수 = 가치 파괴.
- SGR 와 actual revenue growth 비교 — actual &gt; SGR + 5%p = 외부 자본 의존.
- payoutRatio 60% 이상 = 성장 기회 부재 또는 보수적 경영 — 사업 단계 (성숙) 점검.
- "buyback = 좋다" 단정 X — 비싼 시점 자사주 매입 = 자본 파괴.
