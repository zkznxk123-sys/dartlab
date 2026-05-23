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

12-1m return (직전 12 개월 누적 수익률, 단 직전 1 개월 제외) + Sharpe (위험조정) + peer 단면 percentile rank. 1 개월 제외는 단기 reversal 효과 차단.

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
