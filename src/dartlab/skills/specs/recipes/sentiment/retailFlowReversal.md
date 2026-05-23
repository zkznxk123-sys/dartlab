---
id: recipes.sentiment.retailFlowReversal
title: 개인 매매 반전 신호 (외인/기관 vs 개인 z-divergence)
category: recipes
kind: recipe
scope: builtin
status: tested
purpose: 개인 순매수 z-score 와 (외인+기관) 순매수 z-score 의 부호 반대 발산. 두 z 갭 ≥ 3 인 row 는 *스마트머니 vs 개인 반전 점* 후보. sentiment 페르소나 보조.
whenToUse:
  - 개인 매매 반전
  - retail flow reversal
  - 스마트머니 vs 개인
  - 수급 다이버전스
linkedSkills:
  - engines.company
  - engines.gather
  - recipes.sentiment.flowImbalance
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
    - synth
testUniverse:
  market: KR
  stockCodes:
    - "005930"
    - "000660"
falsifier:
  description: "거래일 < 30 으로 z-score 노이즈. 같은 부호 (둘 다 매수 또는 둘 다 매도) 는 reversal 신호 아님."
lastUpdated: "2026-05-22"
---

## 공개 호출 방식

```python
import dartlab
import polars as pl
import statistics

target = "005930"
c = dartlab.Company(target)

try:
    flow = c.gather("flow").head(120).to_dicts()
except Exception:
    flow = []
flow.sort(key=lambda r: str(r.get("date") or r.get("tradeDate")))

retail = [float(r.get("individualNet") or 0) for r in flow]
smart = [float(r.get("foreignNet") or 0) + float(r.get("institutionNet") or 0) for r in flow]

WINDOW = 20
rows = []
for i, r in enumerate(flow):
    if i < WINDOW: continue
    r_window = retail[i-WINDOW:i]
    s_window = smart[i-WINDOW:i]
    r_mu, r_sd = statistics.mean(r_window), statistics.stdev(r_window) if len(r_window) > 1 else 0
    s_mu, s_sd = statistics.mean(s_window), statistics.stdev(s_window) if len(s_window) > 1 else 0
    z_r = (retail[i] - r_mu) / r_sd if r_sd > 0 else None
    z_s = (smart[i] - s_mu) / s_sd if s_sd > 0 else None
    rev = "smartBuy_retailSell" if (z_s and z_r and z_s >= 1.5 and z_r <= -1.5) else \
          "smartSell_retailBuy" if (z_s and z_r and z_s <= -1.5 and z_r >= 1.5) else "normal"
    rows.append({"date": r.get("date") or r.get("tradeDate"), "zRetail": z_r, "zSmart": z_s, "reversal": rev})

if rows:
    table = pl.DataFrame(rows)
    rev_n = int((table["reversal"] != "normal").sum())
    latest_date = str(table["date"].max())
else:
    # 윈도우 만족 X — 데이터 부족 표시 + 최신 flow 날짜 표면
    latest_date = str(flow[-1].get("date") or flow[-1].get("tradeDate")) if flow else None
    table = [{"reversal": "insufficient", "date": latest_date, "flowRowsAvailable": len(flow), "windowRequired": WINDOW}]
    rev_n = 0

emit_result(
    table=table,
    values={"reversalCount": rev_n, "rows": (table.height if hasattr(table, "height") else len(table))},
    date=latest_date,
    sources=["dartlab://gather/flow"],
)
```

## 호출 동작

20 거래일 rolling z-score 두 시계열: 개인 / (외인+기관). z 부호 반대이고 둘 다 |값| ≥ 1.5 면 *반전 cluster* row.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `date` | 거래일 |
| `zRetail` | 개인 순매수 z |
| `zSmart` | (외인+기관) z |
| `reversal` | smartBuy_retailSell / smartSell_retailBuy / normal |

## 연계 절차

1. recipes.sentiment.flowImbalance - 단일 imbalance 와 갭 비교.
2. recipes.sentiment.consensusRevisionPace - reversal 시점 컨센서스 변화.

## 기본 검증

- 거래일 < 30 이면 결론 X.
- 동일 부호 (둘 다 매수 또는 매도) 는 reversal 아님.
- *스마트머니 = 항상 옳다* 단정 금지 — 정량 관찰일 뿐.
