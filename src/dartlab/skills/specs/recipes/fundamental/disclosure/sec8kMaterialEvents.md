---
id: recipes.fundamental.disclosure.sec8kMaterialEvents
title: SEC 8-K material event burst (30 day 윈도우 카운트)
category: recipes
kind: recipe
scope: builtin
status: tested
purpose: 미국 8-K material event filing 의 30 일 윈도우 카운트 + Item 분류 분포. ≥ 5 건 또는 Item 5.02 (임원 변동) ≥ 2 건 = *전환점 burst* 후보. EDGAR raw.
whenToUse:
  - 8-K burst
  - SEC material event
  - 임원 변동 cluster
  - 미국 이벤트 burst
examples:
  - AAPL 8-K 30일 안 burst 카운트
  - SEC material event 폭증 종목
  - Item 5.02 임원 변동 cluster
expectedOutputs:
  - 30d 안 8-K 총 건수 + Item 분류 분포
  - Item 5.02 (임원 변동) 카운트
  - burst 라벨 (≥ 5 건 OR Item 5.02 ≥ 2 = 전환점 후보)
linkedSkills:
  - engines.edgar
  - engines.gather
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
    - synth
testUniverse:
  market: US
  tickers:
    - "AAPL"
    - "MSFT"
falsifier:
  description: "8-K filing < 3 이면 burst 결론 X. 정기 (Item 8.01 disclosure) 만 burst 처리하면 false positive."
lastUpdated: "2026-05-22"
---

## 공개 호출 방식

```python
import dartlab
import polars as pl
from collections import Counter
from datetime import datetime, timedelta

ticker = "AAPL"

try:
    filings = dartlab.providers.edgar.fetch8kFilings(ticker, days=60)
except Exception:
    filings = []

def parseDate(v):
    if isinstance(v, datetime): return v.date()
    s = str(v)[:10].replace(".","-")
    try: return datetime.strptime(s, "%Y-%m-%d").date()
    except: return None

events = []
for f in filings:
    d = parseDate(f.get("filingDate"))
    item = (f.get("item") or "").strip()
    if d:
        events.append({"date": d, "item": item, "title": (f.get("title") or "")[:60]})
events.sort(key=lambda e: e["date"])

# 30 day window count
WINDOW = timedelta(days=30)
clusters = []
for e in events:
    start = e["date"] - WINDOW
    same_window = [x for x in events if start <= x["date"] <= e["date"]]
    if len(same_window) >= 5:
        item_counts = Counter(x["item"] for x in same_window)
        clusters.append({
            "windowEnd": str(e["date"]),
            "filingCount": len(same_window),
            "items": dict(item_counts),
            "execEvents": item_counts.get("5.02", 0),
        })
        break  # first cluster

if not clusters:
    item_counts = Counter(e["item"] for e in events)
    clusters = [{
        "windowEnd": str(events[-1]["date"]) if events else None,
        "filingCount": len(events),
        "items": dict(item_counts),
        "execEvents": item_counts.get("5.02", 0),
    }] if events else []

table = pl.DataFrame(clusters) if clusters else pl.DataFrame(
    schema={"windowEnd": pl.Utf8, "filingCount": pl.Int64, "items": pl.Object, "execEvents": pl.Int64}
)

emit_result(
    table=table,
    values={"latestCount": clusters[-1]["filingCount"] if clusters else 0,
            "execEvents": clusters[-1]["execEvents"] if clusters else 0},
    date=clusters[-1]["windowEnd"] if clusters else None,
    sources=["dartlab://edgar/8k"],
)
```

## 호출 동작

직전 60 일 8-K filing 시간순 정렬 후, 30 일 윈도우 안 ≥ 5 건 cluster 검출. Item 분포 (5.02 임원변동, 1.01 신규계약, 2.02 실적, 5.07 의결 결과 등) 도 같이.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `windowEnd` | window 끝 일자 |
| `filingCount` | 30 일 안 8-K 수 |
| `items` | Item 분류 dict |
| `execEvents` | Item 5.02 (임원변동) 카운트 |

## 연계 절차

1. recipes.fundamental.disclosure.event - 사건 inbox 와 결합.
2. recipes.fundamental.quality.forensics.executiveCompensationAudit - 임원 변동 + 보상 변화.

## 기본 검증

- 8-K < 3 이면 burst 결론 X.
- Item 8.01 정기성만 burst 처리하지 않도록 Item 별 가중치.
- *burst* = recession 단정 X — 정량 사실 표기.
