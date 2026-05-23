---
id: recipes.technical.movingAverageConfluence
title: 이동평균선 정합 (5/20/60/120 동시 정렬)
category: recipes
kind: recipe
scope: builtin
status: tested
purpose: 5/20/60/120 일 단순 이동평균선의 *정렬* 상태 분류 — 완전 정렬 (오름차순 또는 내림차순) row 만 *추세 합의* 후보. 단일 골든크로스 함정 회피.
whenToUse:
  - 이동평균선 정렬
  - 추세 합의
  - 골든크로스 confirmation
  - MA confluence
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
falsifier:
  description: "거래일 < 130 이면 120 일 MA 결론 X. 완전 정렬 row 비율이 < 5% 이면 변별력 작음."
lastUpdated: "2026-05-22"
---

## 공개 호출 방식

```python
import dartlab
import polars as pl
import statistics

target = "005930"

try:
    px = dartlab.gather("price", target).head(160).to_dicts()
except Exception:
    px = []
px.sort(key=lambda r: str(r.get("date") or r.get("tradeDate")))
closes = [(r.get("date") or r.get("tradeDate"), float(r.get("close") or 0)) for r in px if r.get("close")]

def sma(series, window):
    if len(series) < window: return None
    return statistics.mean(series[-window:])

rows = []
for i in range(120, len(closes)):
    sub = [c[1] for c in closes[:i+1]]
    ma5, ma20, ma60, ma120 = sma(sub, 5), sma(sub, 20), sma(sub, 60), sma(sub, 120)
    if None in (ma5, ma20, ma60, ma120): continue
    if ma5 > ma20 > ma60 > ma120:
        align = "bullish"
    elif ma5 < ma20 < ma60 < ma120:
        align = "bearish"
    else:
        align = "mixed"
    rows.append({"date": closes[i][0], "close": closes[i][1], "ma5": ma5, "ma20": ma20, "ma60": ma60, "ma120": ma120, "alignment": align})

table = pl.DataFrame(rows) if rows else pl.DataFrame(
    schema={"date": pl.Utf8, "close": pl.Float64, "ma5": pl.Float64, "ma20": pl.Float64,
            "ma60": pl.Float64, "ma120": pl.Float64, "alignment": pl.Utf8}
)

bull_n = int((table["alignment"] == "bullish").sum()) if table.height else 0
bear_n = int((table["alignment"] == "bearish").sum()) if table.height else 0
mixed_n = table.height - bull_n - bear_n
latest = table["alignment"][-1] if table.height else None

emit_result(
    table=table.tail(10) if table.height > 10 else table,
    values={"bullishDays": bull_n, "bearishDays": bear_n, "mixedDays": mixed_n, "latest": latest},
    date=str(closes[-1][0]) if closes else None,
    sources=["dartlab://gather/price"],
)
```

## 호출 동작

각 거래일 5/20/60/120 일 SMA 정렬 분류. 완전 오름차순 (ma5>20>60>120) = bullish, 완전 내림차순 = bearish, 그 외 = mixed. latest row 의 alignment 가 핵심.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `date` | 거래일 |
| `close` | 종가 |
| `ma5`/`ma20`/`ma60`/`ma120` | 이동평균선 |
| `alignment` | bullish / bearish / mixed |

## 연계 절차

1. recipes.technical.atrRegimeShift - 정렬과 변동성 체제 결합.
2. recipes.quant.momentumFactor - 12-1m return 정합.

## 기본 검증

- 거래일 < 130 이면 결론 X.
- 완전 정렬 비율 < 5% 이면 변별력 작음 — 한계.
- 단독 매수 결론 X — 거래량·펀더멘털 결합.
