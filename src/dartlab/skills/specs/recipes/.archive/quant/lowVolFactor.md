---
id: recipes.quant.lowVolFactor
title: Low-Volatility 팩터 (Ang-Hodrick-Xing-Zhang 2006 anomaly)
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: Ang-Hodrick-Xing-Zhang 2006 의 *low-volatility anomaly* — 60 거래일 일변동률 표준편차 + idiosyncratic vol (시장 베타 잔차 표준편차) 두 정의의 peer 단면 percentile rank. CAPM 예측 (high vol = high return) 반례.
whenToUse:
  - low-volatility 팩터
  - vol anomaly
  - idiosyncratic vol
  - 저변동성 스크리닝
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
  description: "60 거래일 < 30 이면 vol 추정 불안정. 시장 (KOSPI) 일변동 raw 없으면 idiosyncratic 계산 불가."
lastUpdated: "2026-05-22"
---

## 공개 호출 방식

```python
import dartlab
import polars as pl
import statistics

target = "005930"

def daily_returns(code, n=80):
    try:
        px = dartlab.gather("price", code).head(n+5).to_dicts()
    except Exception:
        return []
    px.sort(key=lambda r: str(r.get("date") or r.get("tradeDate")))
    closes = [float(r.get("close") or 0) for r in px if r.get("close")]
    return [closes[i]/closes[i-1] - 1 for i in range(1, len(closes))]

# 시장 (KOSPI 지수 — 가정: code "KS11" 또는 별 axis)
try:
    market_rets = daily_returns("KS11", n=80)
except Exception:
    market_rets = []

def vol_metrics(code):
    rets = daily_returns(code, n=80)
    if len(rets) < 30:
        return None, None
    total_vol = statistics.stdev(rets) if len(rets) > 1 else 0
    if not market_rets or len(market_rets) < len(rets):
        return total_vol, None
    # idiosyncratic = residual std after market regression
    n = min(len(rets), len(market_rets))
    a, b = rets[-n:], market_rets[-n:]
    ma, mb = statistics.mean(a), statistics.mean(b)
    num = sum((x-ma)*(y-mb) for x, y in zip(a, b))
    den = sum((y-mb)**2 for y in b)
    beta = num / den if den else 0
    alpha = ma - beta * mb
    residuals = [a[i] - (alpha + beta * b[i]) for i in range(n)]
    idio = statistics.stdev(residuals) if len(residuals) > 1 else 0
    return total_vol, idio

own_total, own_idio = vol_metrics(target)
c = dartlab.Company(target)
try:
    peers = c.industry("peers").to_dicts()[:15]
except Exception:
    peers = []

peer_rows = []
for p in peers:
    code = p.get("code") or p.get("stockCode")
    if not code or code == target:
        continue
    tv, iv = vol_metrics(code)
    if tv is not None:
        peer_rows.append({"code": code, "totalVol": tv, "idioVol": iv})

def rank(metric, my_val):
    vals = [r[metric] for r in peer_rows if r[metric] is not None]
    if not vals or my_val is None:
        return None
    below = sum(1 for v in vals if v < my_val)
    return below / len(vals)

# low vol = 낮을수록 좋으니 rank 를 invert
rank_total_inv = (1 - rank("totalVol", own_total)) if own_total is not None else None
rank_idio_inv = (1 - rank("idioVol", own_idio)) if own_idio is not None else None

table = pl.DataFrame([{
    "ownTotalVol": own_total,
    "ownIdioVol": own_idio,
    "rankLowTotalVol": rank_total_inv,
    "rankLowIdioVol": rank_idio_inv,
    "peerCount": len(peer_rows),
}])

emit_result(
    table=table,
    values={"totalVol": own_total, "idioVol": own_idio, "rankLowVol": rank_total_inv},
    date=None,
    sources=["dartlab://gather/price"],
)
```

## 호출 동작

60+ 거래일 일변동률의 표준편차 (total vol) + 시장 (KOSPI 지수) 베타 회귀 잔차 std (idiosyncratic vol) 산출. peer 단면 percentile rank invert (낮은 vol = 높은 rank).

## 대표 반환 형태

| column | 의미 |
|---|---|
| `ownTotalVol` | 60 거래일 일변동 std |
| `ownIdioVol` | 시장 베타 잔차 std |
| `rankLowTotalVol` | peer 단면 (낮을수록 1) |
| `rankLowIdioVol` | idio vol 동일 |

## 연계 절차

1. recipes.quant.qualityFactor - QMJ Safety 와 결합.
2. recipes.macro.scenarioAnalysis - vol regime 변화 시 신호 안정성.
3. recipes.sentiment.flowImbalance - vol 변동 시 수급 변화.

## 기본 검증

- 거래일 < 30 이면 vol 결론 X.
- 시장 지수 raw 없으면 idiosyncratic 계산 불가 — total vol 만 표기.
- low vol anomaly 는 *bear market* 에서 가장 강함 — bull market 단독 결론 X.
