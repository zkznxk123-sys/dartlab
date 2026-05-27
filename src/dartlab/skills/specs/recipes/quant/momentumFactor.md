---
id: recipes.quant.momentumFactor
title: Momentum 팩터 (Jegadeesh-Titman 12-1m return)
category: recipes
kind: recipe
scope: builtin
status: tested
purpose: Jegadeesh-Titman 1993 "Returns to Buying Winners and Selling Losers" 의 12-1m return (직전 12 개월 수익률, 단 직전 1 개월 제외) + 변동성 조정 (Sharpe) + peer rank. 단순 모멘텀이 아닌 *위험 조정* + cross-section.
whenToUse:
  - 모멘텀 팩터
  - 12-1m return
  - Jegadeesh momentum
  - 위험조정 모멘텀
examples:
  - 005930 12-1m 모멘텀 팩터 위치
  - 위험 조정 모멘텀 (Sharpe) 상위 종목
  - Jegadeesh 모멘텀 cross-section rank
expectedOutputs:
  - 12-1m return 단일값 + 변동성 조정 Sharpe
  - peer percentile rank + quartile 라벨
  - 모멘텀 상위 quartile 종목 list (Sharpe 기준)
linkedSkills:
  - engines.company
  - engines.quant
  - engines.gather
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
    - gather
testUniverse:
  market: KR
  stockCodes:
    - "005930"
    - "000660"
falsifier:
  description: "거래일 < 252 (1 년) 인 신규 상장주는 12-1m 결론 X. crash month 직후 (단기 reversal) 의 모멘텀은 falsifier."
lastUpdated: "2026-05-22"
---

## 공개 호출 방식

```python
import dartlab
import polars as pl
import statistics
import math

target = "005930"

def mom12_1(code):
    try:
        px = dartlab.gather("price", code).head(280).to_dicts()
    except Exception:
        return None, None, None
    px.sort(key=lambda r: str(r.get("date") or r.get("tradeDate")))
    closes = [float(r.get("close") or 0) for r in px if r.get("close")]
    if len(closes) < 252:
        return None, None, None
    # 12-1m: 직전 252 거래일 중 마지막 21 거래일 제외
    end_idx = len(closes) - 21
    start_idx = end_idx - 231  # 12-1=11 month * 21
    if start_idx < 0:
        return None, None, None
    ret = closes[end_idx-1] / closes[start_idx] - 1
    # variance for Sharpe (1 month excluded same)
    daily_rets = [closes[i]/closes[i-1] - 1 for i in range(start_idx+1, end_idx)]
    sd = statistics.stdev(daily_rets) * math.sqrt(252) if len(daily_rets) > 1 else 0
    sharpe = ret / sd if sd > 0 else None
    return ret, sd, sharpe

c = dartlab.Company(target)
own_ret, own_sd, own_sharpe = mom12_1(target)

try:
    peers = c.industry("peers").to_dicts()[:15]
except Exception:
    peers = []

peer_rows = []
for p in peers:
    code = p.get("code") or p.get("stockCode")
    if not code or code == target:
        continue
    r, _, sh = mom12_1(code)
    if r is not None:
        peer_rows.append({"code": code, "ret12_1m": r, "sharpe": sh})

def rank(metric, my_val):
    vals = sorted([r[metric] for r in peer_rows if r[metric] is not None])
    if not vals or my_val is None:
        return None
    below = sum(1 for v in vals if v < my_val)
    return below / len(vals)

own_rank_ret = rank("ret12_1m", own_ret)
own_rank_sh = rank("sharpe", own_sharpe)

table = pl.DataFrame([{
    "ownRet12_1m": own_ret,
    "ownSharpe": own_sharpe,
    "rankRet": own_rank_ret,
    "rankSharpe": own_rank_sh,
    "peerCount": len(peer_rows),
}])

emit_result(
    table=table,
    values={"ret12_1m": own_ret, "sharpe": own_sharpe, "rankSharpe": own_rank_sh},
    date=None,
    sources=["dartlab://gather/price"],
)
```

## 호출 동작

### 1. 결론 도출

Jegadeesh 12-1m return + Sharpe + peer percentile 단정. 예: "12-1m return +28.4%, Sharpe 1.8, peer top 12% → momentum 후보 강함 (위험조정 분위 상위)."

### 2. 핵심 근거 수집

- 종목 일별 close 시계열 13 개월 이상 (Company.gather('price'))
- peer set close 시계열 (산업 또는 universe)
- 12-1m return = close[-1m] / close[-13m] - 1 (직전 1개월 제외)
- 변동성 (12 개월 일별 수익률 std) → Sharpe

### 3. 메커니즘 분석

```
종목 close 13+ 개월 → 일별 수익률
   ↓
12-1m return = close[t-21] / close[t-252] - 1
   (252 거래일 = 12개월, 21 거래일 제외 = 단기 reversal 회피)
   ↓
σ_annual = std(daily_returns_12mo) × √252
Sharpe = 12-1m return / σ_annual
   ↓
peer 단면 12-1m return 분포 → 자기 종목 percentile rank
   ↓
percentile ≥ 70% + Sharpe ≥ 1   → momentum 후보 강함
percentile ≥ 70% + Sharpe < 1   → 변동성 큰 momentum (주의)
percentile < 30%                → momentum 부재
```

직전 1개월 제외 — Jegadeesh-Titman 1993 이 발견한 단기 reversal 효과 (1개월 mean-reversion) 차단. Sharpe 결합 = pure return 만이 아닌 risk-adjusted 신호.

### 4. 반례·한계

- 13개월 미만 history (신규 상장) 측정 불가.
- 시장 전체 강세장에서는 거의 모든 종목 momentum 양수 — relative rank 만 의미.
- 분할·인수합병 등 corporate action 12개월 안에 있으면 return 비교 불가능.
- Sharpe 분모 σ 가 0 이면 Sharpe undefined.

### 5. 후속 모니터링

- 강한 momentum (percentile ≥ 80%) 진입: `recipes.fundamental.valuation.damodaran.relativeCheck` 로 가격 검증 (momentum vs valuation 갭).
- Sharpe < 0.5 + momentum 큼: `recipes.technical.atrRegimeShift` 로 변동성 체제 확인.
- momentum 부재 (percentile < 30%): `recipes.quant.valueFactor` 로 contrarian value 후보 cross-check.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `ownRet12_1m` | 본 회사 12-1m return |
| `ownSharpe` | 위험조정 Sharpe |
| `rankRet` | peer 단면 ret percentile |
| `rankSharpe` | peer 단면 Sharpe percentile |

## 연계 절차

1. recipes.quant.valueFactor - value × momentum 결합 (반대 신호 동시 발생).
2. recipes.technical.momentumFlowDivergence - 가격 모멘텀 vs 수급 정합.
3. recipes.sentiment.flowImbalance - 모멘텀 강화/약화 신호.

## 기본 검증

- 거래일 < 252 (1 년) 이면 결론 X.
- crash month 직후 (단기 -10%+) 의 모멘텀 신호는 reversal 가능성으로 한계.
- 단일 ret 만으로 매수 결론 X — Sharpe / value 결합 후.
