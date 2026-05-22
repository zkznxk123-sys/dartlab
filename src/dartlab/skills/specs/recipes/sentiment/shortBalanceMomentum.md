---
id: recipes.sentiment.shortBalanceMomentum
title: 공매도 잔고 변화율 모멘텀
category: recipes
kind: recipe
scope: builtin
status: drafted
graphTier: L1.5
cluster: sentiment
purpose: 일별 공매도 잔고 (short balance, 또는 그 변화율) 의 20 거래일 z-score. 잔고 급증은 약세 베팅 cluster, 급감은 short covering 단서. 추론 라벨 없이 정량 모멘텀만. gather L1 단일. 트리거 — '공매도 잔고', 'short balance', 'short covering'.
whenToUse:
  - 공매도 잔고 모멘텀
  - short interest momentum
  - 약세 베팅 cluster
  - short squeeze 후보
inputs:
  - short balance rows
outputs:
  - shortBalanceMomentum table
capabilityRefs:
  - Company.gather
linkedSkills:
  - engines.gather
  - recipes.sentiment.flowImbalance
  - engines.company
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - target
  - tableRef
  - dateRef
  - sourceRef
  - executionRef
visualRefs:
  - "engines.viz.tableBackedChart"
visualGuidance:
  - "표 기반 순위·추세는 engines.viz.tableBackedChart만 사용하고 tableRef/evidenceBinding이 없으면 차트 대신 검산 표로 낮춘다."
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
    - synth
testUniverse:
  market: KR
  stockCodes:
    - "005930"
    - "000660"
expectedOutputs:
  - 일별 공매도 잔고 + 변화율 표
  - 20일 rolling z-score
  - z ≥ 2 (잔고 급증) / ≤ -2 (covering) row 카운트
failureModes:
  - 잔고 (shares outstanding 분모 변동) 와 잔고비율 (잔고/총주식수) 혼동
  - 공매도 일변동량 (daily short volume) 과 잔고 (stock) 혼동
  - 거래일 < 30 으로 z-score 노이즈
forbidden:
  - 공매도 잔고만으로 약세 결론
  - short covering 신호를 "상승 시그널" 로 라벨링
falsifier:
  description: "잔고 stock 과 일변동 flow 를 혼동하거나, 단일 row z 값으로 결론 내면 실패."
audiences:
  llm: c.gather("shortBalance") 또는 동등 axis 결과를 받아 변화율 + z-score 산출. 추론 라벨 X.
  agent: 잔고 급증 row 는 직전 가격 변동도 같이 표기.
  human: 약세 베팅이 *얼마나* 가 아닌 *얼마나 빠르게 증가/감소* 하는지 z-score 로 본다.
humanIntro: "shortBalanceMomentum 는 *공매도 잔고 자체* 가 아닌 *변화율 모멘텀* 을 본다. 잔고가 늘 높은 종목과 *최근 급증* 한 종목은 다른 신호다."
lastUpdated: "2026-05-22"
---

## 공개 호출 방식

```python
import dartlab
import polars as pl
import statistics

target = "005930"
c = dartlab.Company(target)

def rows(value, limit=120):
    if hasattr(value, "head") and hasattr(value, "to_dicts"):
        return value.head(limit).to_dicts()
    if isinstance(value, list):
        return value[:limit]
    return []

short_rows = rows(c.gather("shortBalance"), limit=120)

series = []
for r in short_rows:
    bal = r.get("shortBalance") or r.get("short_balance") or r.get("balanceShares")
    try:
        bal = float(bal) if bal is not None else None
    except (TypeError, ValueError):
        bal = None
    series.append({
        "date": r.get("date") or r.get("tradeDate"),
        "balance": bal,
    })

series.sort(key=lambda x: str(x["date"] or ""))
prev = None
for s in series:
    if prev is not None and s["balance"] is not None and prev > 0:
        s["changePct"] = (s["balance"] - prev) / prev
    else:
        s["changePct"] = None
    if s["balance"] is not None:
        prev = s["balance"]

WINDOW = 20
changes = [s["changePct"] for s in series if s["changePct"] is not None]
for idx, s in enumerate(series):
    if s["changePct"] is None:
        s["z"] = None
        continue
    earlier = [c for c in changes[:idx] if c is not None][-WINDOW:]
    if len(earlier) < 5:
        s["z"] = None
        continue
    mu = statistics.mean(earlier)
    sd = statistics.stdev(earlier) if len(earlier) > 1 else 0
    s["z"] = (s["changePct"] - mu) / sd if sd > 0 else None

table = pl.DataFrame(series) if series else pl.DataFrame(
    schema={"date": pl.Utf8, "balance": pl.Float64, "changePct": pl.Float64, "z": pl.Float64}
)

surge = int((table["z"].fill_null(0) >= 2).sum()) if table.height else 0
covering = int((table["z"].fill_null(0) <= -2).sum()) if table.height else 0

emit_result(
    table=table,
    values={"rows": table.height, "surgeCount": surge, "coveringCount": covering},
    date=str(table["date"].max()) if table.height else None,
    sources=["dartlab://gather/shortBalance"],
)
```

## 호출 동작

일별 공매도 잔고 시계열에서 직전일 대비 변화율 산출 후 20 거래일 rolling z-score. z ≥ 2 = 잔고 급증, z ≤ -2 = covering 단서. *잔고 absolute 크기 자체* 는 결론 근거 아님.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `date` | 거래일 |
| `balance` | 공매도 잔고 (주) |
| `changePct` | 직전일 대비 변화율 |
| `z` | 20 거래일 변화율 z-score |

## 연계 절차

1. recipes.sentiment.flowImbalance - 외국인/기관 수급과 같이 보면 *방향* 단서.
2. recipes.fundamental.quality.forensics.controllingPowerJudgment - 잔고 급증 시 의결권 분쟁 의심.

## 기본 검증

- 거래일 < 30 이면 z-score 결론 X.
- 공매도 일변동량 (volume) 과 잔고 (stock) 혼동 금지.
- short covering 신호를 "상승 시그널" 로 라벨링 금지 — covering 은 *기존 약세 베팅 해제* 의 정량 사실일 뿐.
