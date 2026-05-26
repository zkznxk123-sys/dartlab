---
id: recipes.quant.sizeFactor
title: Size 팩터 (Fama-French SMB) — log market cap percentile
category: recipes
kind: recipe
scope: builtin
status: tested
purpose: Fama-French 1992 의 Size 팩터 — log(market cap) 의 peer 단면 percentile rank. small-cap premium 측면. 단순 시총이 아닌 log 변환 후 cross-section.
whenToUse:
  - size 팩터
  - SMB Fama-French
  - market cap rank
  - small-cap premium
examples:
  - 005930 시총 rank — small / mid / large 어디
  - Fama-French size 팩터 — small-cap premium 상위 종목
  - log market cap cross-section 분위
expectedOutputs:
  - log(market cap) 단일값 + peer percentile
  - quartile 라벨 (small / mid / mid-large / large)
  - universe quartile 경계값 + 자기 종목 위치
linkedSkills:
  - engines.company
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
    - company
testUniverse:
  market: KR
  stockCodes:
    - "005930"
    - "000660"
falsifier:
  description: "시총 데이터 누락 회사가 절반 이상이면 percentile 결론 X. KOSPI 전체가 아닌 산업 peer 단면이므로 산업 평균 size 따라 결론 변동 — 한계 명시."
lastUpdated: "2026-05-22"
---

## 공개 호출 방식

```python
import dartlab
import polars as pl
import math

target = "005930"
c = dartlab.Company(target)

def market_cap(code):
    try:
        snap = dartlab.Company(code).show("snapshot").to_dicts()
        if not snap:
            return None
        return float(snap[0].get("marketCap") or 0)
    except Exception:
        return None

own_cap = market_cap(target)
own_log_cap = math.log(own_cap) if own_cap and own_cap > 0 else None

try:
    peers = c.industry("peers").to_dicts()[:20]
except Exception:
    peers = []

peer_rows = []
for p in peers:
    code = p.get("code") or p.get("stockCode")
    if not code or code == target:
        continue
    cap = market_cap(code)
    if cap and cap > 0:
        peer_rows.append({"code": code, "marketCap": cap, "logCap": math.log(cap)})

def rank(my_log_cap):
    vals = sorted([r["logCap"] for r in peer_rows])
    if not vals or my_log_cap is None:
        return None
    below = sum(1 for v in vals if v < my_log_cap)
    return below / len(vals)

# small size premium: 작을수록 rank 1
own_rank = rank(own_log_cap)
own_size_rank = (1 - own_rank) if own_rank is not None else None

table = pl.DataFrame([{
    "ownMarketCap": own_cap,
    "ownLogCap": own_log_cap,
    "peerCount": len(peer_rows),
    "ownPercentileLargeToSmall": own_rank,
    "smbRankSmallIs1": own_size_rank,
}])

emit_result(
    table=table,
    values={"marketCap": own_cap, "smbRank": own_size_rank, "peerCount": len(peer_rows)},
    date=None,
    sources=["dartlab://show/snapshot", "dartlab://industry/peers"],
)
```

## 호출 동작

target 의 log(market cap) + peer 단면 percentile rank. small premium 측면이므로 *작을수록 rank 1* 로 invert 표기.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `ownMarketCap` | 본 회사 시총 |
| `ownLogCap` | log(시총) |
| `ownPercentileLargeToSmall` | peer 단면 (1 = 가장 큰) |
| `smbRankSmallIs1` | invert (1 = 가장 작은) |

## 연계 절차

1. recipes.quant.valueFactor - small + value 결합 (Fama-French double sort).
2. recipes.quant.qualityFactor - small × quality (junk 제거 후).
3. recipes.meta.screen.smallCapDiscovery - small cap 발굴 트랙.

## 기본 검증

- peer < 10 이면 percentile 불안정.
- 산업 peer 단면이라 산업 평균 size 따라 결론 변동 — KOSPI 전체 단면 별 트랙으로 추가 가능.
- small cap = high return 단정 금지 — anomaly 약화 시기 (2010s) 다수.
