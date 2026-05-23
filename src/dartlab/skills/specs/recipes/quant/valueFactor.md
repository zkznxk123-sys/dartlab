---
id: recipes.quant.valueFactor
title: Value 팩터 composite (Fama-French B/M + E/P + CF/P)
category: recipes
kind: recipe
scope: builtin
status: tested
purpose: Fama-French 1992 의 Value 팩터를 B/M (Book/Market) + E/P (Earnings yield) + CF/P (Cash flow yield) 3 정의 평균으로 composite 산출. 단일 회사 + peer set percentile rank. 단일 지표 (PER 단독) 함정 회피.
whenToUse:
  - value 팩터
  - B/M E/P CF/P composite
  - Fama-French value
  - 가치주 rank
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
  description: "3 정의 부호가 갈리면 (B/M 높은데 E/P 음수) composite 결론 X. peer < 10 이면 percentile rank 불안정."
lastUpdated: "2026-05-22"
---

## 공개 호출 방식

```python
import dartlab
import polars as pl

target = "005930"
c = dartlab.Company(target)

def value_metrics(code):
    try:
        comp = dartlab.Company(code)
        snap = comp.show("snapshot").to_dicts()
        if not snap:
            return None
        s = snap[0]
        bm = float(s.get("bookToMarket") or s.get("bvps_over_price") or 0)
        ep = float(s.get("earningsYield") or s.get("eps_over_price") or 0)
        cfp = float(s.get("cashflowYield") or s.get("ocf_per_share_over_price") or 0)
        return {"bm": bm, "ep": ep, "cfp": cfp}
    except Exception:
        return None

own = value_metrics(target)
try:
    peers = c.industry("peers").to_dicts()[:20]
except Exception:
    peers = []

peer_rows = []
for p in peers:
    code = p.get("code") or p.get("stockCode")
    if not code or code == target:
        continue
    m = value_metrics(code)
    if m:
        peer_rows.append({"code": code, **m})

# percentile rank — 각 정의별로
def rank(metric, my_val):
    vals = sorted([r[metric] for r in peer_rows if r[metric] is not None])
    if not vals or my_val is None:
        return None
    below = sum(1 for v in vals if v < my_val)
    return below / len(vals)

if own:
    rank_bm = rank("bm", own["bm"])
    rank_ep = rank("ep", own["ep"])
    rank_cfp = rank("cfp", own["cfp"])
    ranks = [r for r in (rank_bm, rank_ep, rank_cfp) if r is not None]
    composite = sum(ranks) / len(ranks) if ranks else None
else:
    rank_bm = rank_ep = rank_cfp = composite = None

table = pl.DataFrame([{
    "metric": "valueComposite",
    "ownBm": own["bm"] if own else None,
    "ownEp": own["ep"] if own else None,
    "ownCfp": own["cfp"] if own else None,
    "rankBm": rank_bm,
    "rankEp": rank_ep,
    "rankCfp": rank_cfp,
    "composite": composite,
    "peerCount": len(peer_rows),
}])

emit_result(
    table=table,
    values={"composite": composite, "peerCount": len(peer_rows)},
    date=None,
    sources=["dartlab://show/snapshot", "dartlab://industry/peers"],
)
```

## 호출 동작

target 의 B/M, E/P, CF/P 3 정의 + peer set 단면 percentile rank 산출. composite = 3 rank 평균 (0~1, 1 = 가장 cheap). 단일 지표 우월 단정 금지.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `ownBm/Ep/Cfp` | 본 회사 3 정의 값 |
| `rankBm/Ep/Cfp` | peer 단면 percentile (0~1) |
| `composite` | 3 rank 평균 |
| `peerCount` | peer 표본 |

## 연계 절차

1. recipes.quant.qualityFactor - value × quality 결합 (Asness QMJ junk 제거).
2. recipes.fundamental.valuation.damodaran.peerMultipleDecomposition - 단순 multiple 함정 검증.
3. recipes.industry.industryStagePhase - phase 와 value rank 정합.

## 기본 검증

- peer < 10 이면 percentile rank 불안정 — 한계 명시.
- E/P < 0 (적자) 회사는 EP 정의 제외, 나머지 2 로만 composite.
- 단일 정의 (PER 단독) 결론 금지 — 3 정의 분리 표기.
