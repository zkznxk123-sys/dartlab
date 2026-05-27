---
id: recipes.quant.qualityFactor
title: Quality 팩터 — QMJ (Frazzini-Pedersen-Asness 2014)
category: recipes
kind: recipe
scope: builtin
status: curated
purpose: Frazzini-Pedersen-Asness 2014 "Quality Minus Junk" 의 4 축 — Profitability (ROE/ROA) + Growth (5y CAGR) + Safety (low leverage·low earnings vol) + Payout (FCF / NI) — composite z-score. junk 회사 회피용 quality screen.
whenToUse:
  - quality 팩터
  - QMJ Asness
  - quality minus junk
  - 4 축 composite quality
examples:
  - 005930 quality 팩터 4 축 점수 (ROE / 성장 / 안정성 / 배당)
  - QMJ 상위 종목 — junk 회피 screen
  - 005930 이 quality vs junk 어디
expectedOutputs:
  - 4 축 (Profitability·Growth·Safety·Payout) 개별 z-score
  - composite QMJ z-score 단일값
  - peer percentile rank + 상위 / 하위 quartile 종목 list
linkedSkills:
  - engines.company
  - engines.quant
  - engines.analysis
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
  - "engines.viz.peerMatrix"
  - "engines.viz.tableBackedChart"
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
gap:
  primary:
    - quant
    - analysis
testUniverse:
  market: KR
  stockCodes:
    - "005930"
    - "000660"
falsifier:
  description: "4 축 중 측정 가능한 게 ≤ 2 개면 composite 결론 X. peer < 8 이면 z-score 불안정."
lastUpdated: "2026-05-22"
validatedAt: '2026-05-27'
---

## 공개 호출 방식

```python
import dartlab
import polars as pl
import statistics

target = "005930"
c = dartlab.Company(target)

def quality_metrics(code):
    try:
        comp = dartlab.Company(code)
        rows = comp.analysis("profitabilityRatios").to_dicts()
        if not rows:
            return None
        recent = rows[-1]
        roe = float(recent.get("roe") or 0)
        roa = float(recent.get("roa") or 0)
        # growth (5y revenue CAGR)
        try:
            r5 = comp.show("revenue").to_dicts()
            if len(r5) >= 5 and float(r5[-5].get("revenue") or 0) > 0:
                growth = (float(r5[-1].get("revenue") or 1) / float(r5[-5].get("revenue") or 1)) ** (1/5) - 1
            else:
                growth = None
        except Exception:
            growth = None
        # safety: debt/equity + earnings vol
        try:
            bs = comp.show("bs").to_dicts()[-1]
            de = float(bs.get("totalLiabilities") or 0) / max(float(bs.get("totalEquity") or 1), 1)
        except Exception:
            de = None
        # payout: FCF / NI
        try:
            cf = comp.analysis("capitalAllocation").to_dicts()[-1]
            fcf = float(cf.get("freeCashFlow") or 0)
            ni = float(cf.get("netIncome") or 1)
            payout = fcf / ni if ni else None
        except Exception:
            payout = None
        return {"roeRoa": (roe + roa) / 2, "growth": growth, "safety": -de if de is not None else None, "payout": payout}
    except Exception:
        return None

own = quality_metrics(target)
try:
    peers = c.industry("peers").to_dicts()[:15]
except Exception:
    peers = []

peer_rows = []
for p in peers:
    code = p.get("code") or p.get("stockCode")
    if not code or code == target:
        continue
    m = quality_metrics(code)
    if m:
        peer_rows.append({"code": code, **m})

def z_score(metric, my_val):
    vals = [r[metric] for r in peer_rows if r[metric] is not None]
    if len(vals) < 4 or my_val is None:
        return None
    mu, sd = statistics.mean(vals), statistics.stdev(vals) if len(vals) > 1 else 0
    return (my_val - mu) / sd if sd > 0 else None

if own:
    zs = {k: z_score(k, own[k]) for k in ("roeRoa", "growth", "safety", "payout")}
    valid = [v for v in zs.values() if v is not None]
    composite = sum(valid) / len(valid) if valid else None
else:
    zs = {}
    composite = None

table = pl.DataFrame([{
    "axis": k, "ownValue": own[k] if own else None, "zScore": zs.get(k)
} for k in ("roeRoa", "growth", "safety", "payout")])

emit_result(
    table=table,
    values={"qmjComposite": composite, "peerCount": len(peer_rows)},
    date=None,
    sources=["dartlab://analysis/profitabilityRatios", "dartlab://show/revenue", "dartlab://show/bs", "dartlab://analysis/capitalAllocation"],
)
```

## 호출 동작

### 1. 결론 도출

QMJ composite z-score 단일값 + 4 축 개별 z-score 단정 + peer 분위. 예: "QMJ composite z=+1.2 (top 15%) — Profit z=+0.9 / Growth z=+1.5 / Safety z=+0.3 / Payout z=+2.0 → quality 후보 confirmed."

### 2. 핵심 근거 수집

- Profitability — ROE / ROA (analysis.profitabilityRatios)
- Growth — 매출 5y CAGR (show revenue 시계열)
- Safety — debt/equity + earnings volatility (show BS + earnings std)
- Payout — FCF / NI (analysis.capitalAllocation)
- peer set (산업 cross-section)

### 3. 메커니즘 분석

```
4 축 raw 산출
   ↓
각 축 peer 단면 z-score = (own - peer_mean) / peer_std
   ↓
composite z = avg(measurable axis z-scores)
   ↓
composite z ≥ +1.0  → quality 후보 (QMJ Q1)
composite z 0 ~ +1  → mid quality
composite z < 0     → junk 후보 (QMJ Q5)
측정 가능 축 ≤ 2    → composite X (한계 표기)
```

4 축 모두 양수면 가장 강한 quality 신호. Payout z 만 높고 다른 축 낮으면 거짓 quality (배당만 높은 junk 위장).

### 4. 반례·한계

- 회계 정책 차이 (revenue recognition · depreciation) peer 비교 시 raw 비교 노이즈.
- 신규 상장 (history < 5y) Growth 측정 불가.
- 금융사 (은행·증권·보험) 의 debt/equity 정의 다름 — Safety 축 비교 의미 X.
- 일회성 이익 (자산매각 · 충당금환입) peer mean inflated.

### 5. 후속 모니터링

- composite z ≥ +1 시: `recipes.fundamental.valuation.damodaran.relativeCheck` 로 가격 검증.
- Safety z < -1 시: `recipes.fundamental.credit.usHighYieldSpread` regime 확인.
- Payout z 높음 + Growth z 낮음: `recipes.fundamental.dividend.foreignOwnershipCorr` 외인 매수 정합 확인.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `axis` | roeRoa / growth / safety / payout |
| `ownValue` | 본 회사 값 |
| `zScore` | peer 단면 z-score |

## 연계 절차

1. recipes.quant.valueFactor - QMJ junk 제거 후 value rank.
2. recipes.industry.industryStagePhase - phase 와 quality 정합.
3. recipes.fundamental.valuation.damodaran.reinvestmentRoc - quality 깊이 분석.

## 기본 검증

- peer < 8 이면 z-score 불안정 — 한계 명시.
- 4 축 중 측정 가능 ≤ 2 이면 composite X.
- 단일 ROE 로 quality 결론 금지 — 4 축 분리 표기.
