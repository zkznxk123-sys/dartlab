---
id: recipes.sentiment.insiderClusterTiming
title: 내부자 매수/매도 cluster + 가격 lag
category: recipes
kind: recipe
scope: builtin
status: tested
graphTier: L1.5
cluster: sentiment
purpose: 내부자 (임원·주요주주) 매수 또는 매도가 180 day window 안에 ≥3 명 동시 발현 시 cluster row 로 표기 + 직전 30 거래일 가격 변동 lag 와 같이 본다. *집단 시점* 자체가 sentiment 정량 신호. `recipes.fundamental.disclosure.insiderEarningsLeading` 의 *분기 surprise 선행* 측면과 분리 — 본 recipe 는 *단기 timing* 측면. 트리거 — '내부자 cluster', 'insider cluster', '집단 매수 시점'.
whenToUse:
  - 내부자 cluster timing
  - insider cluster sentiment
  - 집단 매수/매도
  - cluster 가격 lag
examples:
  - 005930 임원 주요주주 동시 매수 시점이 언제
  - 내부자 cluster 매수 — 직전 30일 가격 어디서
  - 집단 매도 cluster 형성된 종목
inputs:
  - insider rows
  - price rows
outputs:
  - insiderClusterTiming table
capabilityRefs:
  - Company.gather
linkedSkills:
  - engines.gather
  - recipes.sentiment.flowImbalance
  - recipes.fundamental.disclosure.insiderEarningsLeading
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - valueRef
  - dateRef
  - sourceRef
  - executionRef
visualRefs:
  - "engines.viz.tableBackedChart"
  - "engines.viz.mermaidDiagram"
visualGuidance:
  - "표 기반 순위·추세는 engines.viz.tableBackedChart만 사용하고 tableRef/evidenceBinding이 없으면 차트 대신 검산 표로 낮춘다."
  - "메커니즘 diagram은 engines.viz.mermaidDiagram으로 8노드 이하만 만들고 모든 edge에 문장·수치·sourceRef 근거를 둔다."
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
  - 일별 내부자 매수/매도 cluster row
  - cluster 시점 직전 30 거래일 가격 변동
  - cluster 방향 (buy / sell) 분포
failureModes:
  - 단일 거래 (1 명) 를 cluster 로 처리
  - 180 day window 가 너무 길어 무관 사건 묶임
  - 매수 cluster 와 매도 cluster 부호 혼동
forbidden:
  - cluster 자체로 "긍정/부정" 라벨링
  - 단일 cluster 로 미공개정보 유출 단정
falsifier:
  description: "≥3 명 cluster 기준 미달 row 를 cluster 로 처리하거나, 사전 가격 변동을 cluster 인과로 단정하면 실패."
audiences:
  llm: c.gather("insiderTrading") + c.gather("price") 두 source 를 받아 180 day window 안 매수/매도 ≥3 명 cluster row + 직전 30 거래일 누적 가격 변동 산출.
  agent: cluster row 마다 buy/sell 방향 + 가격 변동 같이 표기. 인과 X.
  human: 집단 시점 자체가 정량 정보. 의미 해석은 별 절차.
humanIntro: "insiderClusterTiming 은 *집단 시점* 자체를 sentiment 정량 신호로 본다. 한 명의 매수는 노이즈, 3 명 이상 180 일 안 동시는 신호로 간주. 의미 해석 (정보 유출·시그널링) 은 본 recipe 밖."
lastUpdated: "2026-05-22"
---

## 공개 호출 방식

```python
import dartlab
import polars as pl
from datetime import datetime, timedelta

target = "005930"
c = dartlab.Company(target)

def rows(value, limit=200):
    if hasattr(value, "head") and hasattr(value, "to_dicts"):
        return value.head(limit).to_dicts()
    if isinstance(value, list):
        return value[:limit]
    return []

def parseDate(v):
    if isinstance(v, datetime):
        return v.date()
    if v is None:
        return None
    s = str(v)[:10].replace(".", "-").replace("/", "-")
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None

insider_rows = rows(c.gather("insider"), limit=200)
price_rows = rows(c.gather("price"), limit=200)

# date → price 시계열
price_by_date = {}
for p in price_rows:
    d = parseDate(p.get("date") or p.get("tradeDate"))
    if d:
        price_by_date[d] = float(p.get("close") or p.get("closePrice") or 0)

# insider events sorted
events = []
for r in insider_rows:
    d = parseDate(r.get("date") or r.get("tradeDate") or r.get("filedAt"))
    if not d:
        continue
    # insider gather 스키마: tradeType(buy/sell 또는 코드), changeShares(부호로 buy/sell 추론 fallback)
    tt = str(r.get("tradeType") or r.get("direction") or "").lower()
    if tt.startswith("b") or tt == "1" or tt == "buy":
        direction = "buy"
    elif tt.startswith("s") or tt == "0" or tt == "sell":
        direction = "sell"
    else:
        try:
            direction = "buy" if float(r.get("changeShares") or 0) > 0 else "sell"
        except Exception:
            direction = "sell"
    person = r.get("name") or r.get("person") or r.get("filer") or "?"
    events.append({"date": d, "direction": direction, "person": person})

events.sort(key=lambda x: x["date"])

WINDOW = timedelta(days=180)
clusters = []
for i, e in enumerate(events):
    window_start = e["date"] - WINDOW
    same_dir = [x for x in events[:i+1] if x["direction"] == e["direction"] and x["date"] >= window_start]
    persons = {x["person"] for x in same_dir}
    if len(persons) >= 3:
        # 직전 30 거래일 가격 변동
        before = [p for d, p in price_by_date.items() if (e["date"] - timedelta(days=45)) <= d < e["date"]]
        price_chg = (before[-1] / before[0] - 1) if len(before) >= 2 and before[0] > 0 else None
        clusters.append({
            "date": str(e["date"]),
            "direction": e["direction"],
            "personsInWindow": len(persons),
            "pricePctBefore30d": price_chg,
            "latestPerson": e["person"],
        })

_cluster_schema = {
    "date": pl.Utf8,
    "direction": pl.Utf8,
    "personsInWindow": pl.Int64,
    "pricePctBefore30d": pl.Float64,
    "latestPerson": pl.Utf8,
}
table = pl.DataFrame(clusters, schema=_cluster_schema, infer_schema_length=None) if clusters else pl.DataFrame(schema=_cluster_schema)

buy_n = int((table["direction"] == "buy").sum()) if table.height else 0
sell_n = int((table["direction"] == "sell").sum()) if table.height else 0

if table.height == 0:
    # cluster 미감지 — 가장 최근 insider event 날짜를 placeholder 로 emit (date 보장).
    if events:
        latest_event_date = str(events[-1]["date"])
        table = [{"direction": "no_cluster", "date": latest_event_date, "insiderEventsScanned": len(events)}]
    else:
        latest_event_date = None
        table = [{"direction": "no_insider_data", "date": None}]
else:
    latest_event_date = str(table["date"].max())

emit_result(
    table=table,
    values={
        "clusters": (table.height if hasattr(table, "height") else len(table)),
        "buyClusters": buy_n,
        "sellClusters": sell_n,
    },
    date=latest_event_date,
    sources=["dartlab://gather/insider", "dartlab://gather/price"],
)
```

## 호출 동작

내부자 거래 row 를 시간순 정렬한 뒤, 각 row 시점 기준 직전 180 일 안 *같은 방향* 거래자 수 ≥3 명이면 cluster row 로 표시. cluster row 마다 직전 30 거래일 누적 가격 변동 (lag) 을 같이 표기. 단일 거래 (1 명) 는 cluster 아님.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `date` | cluster 형성 시점 (최신 거래일) |
| `direction` | buy / sell |
| `personsInWindow` | 180 일 안 같은 방향 거래자 수 |
| `pricePctBefore30d` | 직전 30 거래일 누적 가격 변동 |
| `latestPerson` | 마지막 거래자 이름 |

## 연계 절차

1. recipes.sentiment.flowImbalance - cluster 시점에 외인/기관 수급도 같이 본다.
2. recipes.fundamental.disclosure.insiderEarningsLeading - cluster 가 분기 EPS surprise 와 양의 IC 인지 (별 절차).

## 기본 검증

- ≥3 명 기준은 본 recipe 의 정의 — 단일 거래는 cluster 아님.
- `pricePctBefore30d` 가 cluster 형성 *원인* 이라는 인과 단정 금지.
- 180 day window 가 너무 길면 무관 사건 묶일 수 있음 — 답변에 window 값 명시.
