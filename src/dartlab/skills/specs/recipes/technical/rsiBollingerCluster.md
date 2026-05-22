---
id: recipes.technical.rsiBollingerCluster
title: RSI + 볼린저 밴드 동시 cluster (이중 oversold/overbought)
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: RSI(14) < 30 또는 > 70 + 동시 가격이 볼린저 밴드 (20, 2σ) 하단/상단 close 인 row 만 cluster 로 표기. 단일 oscillator 함정 회피 (두 정의 동시 충족만 신호).
whenToUse:
  - RSI 과매도 과매수
  - 볼린저 밴드 cluster
  - 이중 oversold
  - 기술 신호 confirmation
linkedSkills:
  - engines.gather
  - engines.quant
  - engines.company
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
    - gather
    - quant
testUniverse:
  market: KR
  stockCodes:
    - "005930"
    - "000660"
falsifier:
  description: "거래일 < 30 이면 RSI/Bollinger 계산 불안정. 갭상승·하한가 등 단일 day 노이즈를 cluster 로 처리하면 fail."
lastUpdated: "2026-05-22"
---

## 공개 호출 방식

```python
import dartlab
import polars as pl
import statistics

target = "005930"

try:
    px = dartlab.gather("price", target).head(80).to_dicts()
except Exception:
    px = []
px.sort(key=lambda r: str(r.get("date") or r.get("tradeDate")))
closes = [(r.get("date") or r.get("tradeDate"), float(r.get("close") or 0)) for r in px if r.get("close")]

if len(closes) < 30:
    table = pl.DataFrame(schema={"date": pl.Utf8, "close": pl.Float64, "rsi": pl.Float64,
                                  "bbUpper": pl.Float64, "bbLower": pl.Float64, "signal": pl.Utf8})
else:
    # RSI(14)
    rsi_series = [None]*14
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i][1] - closes[i-1][1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
        if i >= 14:
            avg_gain = statistics.mean(gains[-14:])
            avg_loss = statistics.mean(losses[-14:])
            rs = avg_gain / avg_loss if avg_loss else 0
            rsi = 100 - (100 / (1 + rs)) if avg_loss else 100
            rsi_series.append(rsi)
    # Bollinger(20, 2)
    bb_upper = [None]*20
    bb_lower = [None]*20
    for i in range(20, len(closes)):
        window = [c[1] for c in closes[i-20:i]]
        mu = statistics.mean(window)
        sd = statistics.stdev(window)
        bb_upper.append(mu + 2*sd)
        bb_lower.append(mu - 2*sd)
    rows = []
    for i, (d, c_val) in enumerate(closes):
        if i < 20 or rsi_series[i] is None: continue
        rsi = rsi_series[i]
        bu = bb_upper[i]
        bl = bb_lower[i]
        signal = "oversoldCluster" if (rsi < 30 and c_val < bl) else \
                 "overboughtCluster" if (rsi > 70 and c_val > bu) else "normal"
        if signal != "normal":
            rows.append({"date": d, "close": c_val, "rsi": rsi, "bbUpper": bu, "bbLower": bl, "signal": signal})
    table = pl.DataFrame(rows) if rows else pl.DataFrame(
        schema={"date": pl.Utf8, "close": pl.Float64, "rsi": pl.Float64,
                "bbUpper": pl.Float64, "bbLower": pl.Float64, "signal": pl.Utf8})

emit_result(
    table=table,
    values={"clusterCount": table.height},
    date=str(closes[-1][0]) if closes else None,
    sources=["dartlab://gather/price"],
)
```

## 호출 동작

RSI(14) + 볼린저 밴드(20, 2σ) 동시 조건 충족 row 만 cluster. oversoldCluster = RSI<30 + close<lower, overboughtCluster = RSI>70 + close>upper.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `date` | 거래일 |
| `close` | 종가 |
| `rsi` | RSI(14) |
| `bbUpper` / `bbLower` | 볼린저 밴드 |
| `signal` | oversoldCluster / overboughtCluster |

## 연계 절차

1. recipes.technical.momentumFlowDivergence - cluster 시점 수급 정합.
2. recipes.sentiment.flowImbalance - cluster 시점 imbalance.

## 기본 검증

- 거래일 < 30 이면 결론 X.
- 갭상승·하한가 등 단일 day noise 는 cluster 처리 X.
- 신호 단독 매매 결정 X — 펀더멘털 결합 후.
