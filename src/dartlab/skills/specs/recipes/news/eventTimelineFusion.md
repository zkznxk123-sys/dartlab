---
id: recipes.news.eventTimelineFusion
title: Event Timeline Fusion
category: recipes
kind: recipe
scope: builtin
status: tested
graphTier: L1.5
cluster: news
purpose: 공시·뉴스·가격 3 source 를 시간순으로 fuse 해 같은 사건이 어디서 먼저 나타났는지 row 단위로 본다. 뉴스 선행 또는 가격 선행 row 만 의심 후보로 emit.
whenToUse:
  - 공시 뉴스 가격 시간순
  - 정보 비대칭 의심 row
  - 뉴스 선행 사건 추출
inputs:
  - filing rows
  - news rows
  - price rows
outputs:
  - eventTimelineFusion table
capabilityRefs:
  - Company.disclosure
  - Company.liveFilings
  - Company.gather
toolRefs:
  - EngineCall
  - RunPython
knowledgeRefs:
  - runtime.untrustedContent
  - engines.company
  - engines.gather
sourceRefs:
  - dartlab://skills/recipes.news.eventTimelineFusion
requiredEvidence:
  - skillRef
  - tableRef
  - dateRef
  - sourceRef
  - executionRef
expectedOutputs:
  - 사건별 (공시·뉴스·가격) 시간 순서
  - 뉴스 선행 row 수와 평균 leadDays
  - 가격 선행 row 수 (정보 누설 의심)
visualRefs:
  - engines.viz.evidenceCoverage
visualGuidance:
  - "eventTimelineFusion 결과는 표·timeline 이 우선이며, source 별 row 분포만 engines.viz.evidenceCoverage 로 보조한다."
linkedSkills:
  - recipes.news.disclosureNewsCrosscheck
  - recipes.news.untrustedToneAudit
  - recipes.fundamental.disclosure.eventRadar.eventInbox
gap:
  primary:
    - synth
    - gather
falsifier:
  description: "정기·중복·시장 전반 이벤트를 정보 비대칭 의심으로 분류하면 실패로 본다."
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
forbidden:
  - 뉴스 선행 row 를 그 자체로 내부정보 결론
  - 가격 변동만으로 사건 결론
  - 동일 사건의 정정·재공시를 별개 timeline 행으로 분리
failureModes:
  - 시장 전반 충격 (지수 급락) 을 회사 사건으로 오인
  - 정기보고서 제출을 뉴스 선행으로 오인
  - 가격 변동 임계 (예: ±3%) 를 외부 변수 (지수 동시 변동) 보정 없이 사용
examples:
  - 최근 30 일 사건별 source 선후
  - 가격이 공시보다 먼저 움직인 사건 식별
audiences:
  llm: 3 source row 를 EngineCall 로 받은 뒤 시간순 정렬과 priceAbs 임계만 수행하고 의미 추론은 하지 않는다.
  agent: 의심 row 는 답변 본문에 source/date/leadDays/priceMove 를 같이 표기.
  human: 같은 사건이 공시·뉴스·가격에서 어떤 순서로 보였는지 시계열로 본다.
humanIntro: "eventTimelineFusion 은 disclosureNewsCrosscheck 의 매칭 결과를 가격 시계열과 합친다. 정보가 공시 → 뉴스 → 가격 순으로 정상 흘렀는지, 또는 그 반대 순서가 있는지 row 단위로 본다."
lastUpdated: "2026-05-21"
testUniverse:
  market: KR
  stockCodes:
    - "005930"
---

## 공개 호출 방식

AI 도구 실행 순서는 `EngineCall` 우선이다. 아래 Python 블록은 공시·뉴스·가격 row 를 받아 사건 단위 시간순 fusion 을 만드는 **RunPython fallback** 절차다.

```python
import dartlab
import polars as pl
from datetime import datetime, timedelta

target = "005930"
c = dartlab.Company(target)

def rows(value, limit=120):
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

try:
    filings = rows(c.liveFilings(days=30), limit=80)
except Exception:
    filings = []
news_rows = rows(c.gather("news"), limit=120)
price_rows = rows(c.gather("price"), limit=120)

PRICE_ABS_THRESHOLD = 0.03

events = []
for f in filings:
    d = parseDate(f.get("date") or f.get("rcept_dt") or f.get("filedAt"))
    if not d:
        continue
    events.append({"date": d, "source": "filing", "title": str(f.get("title") or "")[:80]})

for n in news_rows:
    d = parseDate(n.get("date") or n.get("publishedAt") or n.get("pubDate"))
    if not d:
        continue
    events.append({"date": d, "source": "news", "title": str(n.get("title") or "")[:80]})

for p in price_rows:
    d = parseDate(p.get("date") or p.get("tradeDate"))
    change = p.get("change") or p.get("changePct") or p.get("pctChange")
    try:
        ch = float(change) if change is not None else None
    except (TypeError, ValueError):
        ch = None
    if not d or ch is None:
        continue
    if abs(ch) < PRICE_ABS_THRESHOLD:
        continue
    events.append({"date": d, "source": "price", "title": f"{ch:+.2%}"})

events.sort(key=lambda e: (e["date"], 0 if e["source"] == "filing" else 1 if e["source"] == "news" else 2))

WINDOW = timedelta(days=3)
clusters = []
for e in events:
    if clusters and (e["date"] - clusters[-1]["dateMin"]) <= WINDOW:
        clusters[-1]["items"].append(e)
        clusters[-1]["dateMax"] = e["date"]
    else:
        clusters.append({"dateMin": e["date"], "dateMax": e["date"], "items": [e]})

audit_rows = []
for cl in clusters:
    sources_order = [it["source"] for it in cl["items"]]
    leader = sources_order[0]
    suspect = "newsLead" if leader == "news" and "filing" in sources_order else \
              "priceLead" if leader == "price" and "filing" in sources_order else \
              "normal"
    audit_rows.append({
        "dateMin": str(cl["dateMin"]),
        "dateMax": str(cl["dateMax"]),
        "leader": leader,
        "sources": ",".join(sources_order),
        "suspect": suspect,
        "items": len(cl["items"]),
        "headline": cl["items"][0]["title"],
    })

table = pl.DataFrame(audit_rows) if audit_rows else pl.DataFrame(
    schema={
        "dateMin": pl.Utf8, "dateMax": pl.Utf8, "leader": pl.Utf8,
        "sources": pl.Utf8, "suspect": pl.Utf8, "items": pl.Int64, "headline": pl.Utf8,
    }
)

headline = {
    "clusters": table.height,
    "newsLead": int((table["suspect"] == "newsLead").sum()) if table.height else 0,
    "priceLead": int((table["suspect"] == "priceLead").sum()) if table.height else 0,
}

emit_result(
    table=table,
    values=headline,
    date=str(table["dateMax"].max()) if table.height else None,
    sources=[
        "dartlab://providers/dart/disclosure",
        "dartlab://gather/news",
        "dartlab://gather/price",
        "dartlab://runtime/untrustedContent",
    ],
)
```

## 호출 동작

3 source 의 row 를 시간순 정렬하고 ±3 day window 로 cluster 한다. cluster 안 첫 row 가 `news` 인데 뒤에 `filing` 이 있으면 `newsLead`, 첫 row 가 `price` 인데 뒤에 `filing` 이 있으면 `priceLead`. 그 외는 `normal`. 가격은 일변동 ±3% 이상만 cluster 에 포함시켜 noise 를 줄인다.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `dateMin` / `dateMax` | cluster 시간 범위 |
| `leader` | filing / news / price |
| `sources` | cluster 안 source 순서 (`news,filing,price` 등) |
| `suspect` | normal / newsLead / priceLead |
| `items` | cluster 안 row 수 |
| `headline` | cluster 첫 row 제목 |

## 연계 절차

1. recipes.news.untrustedToneAudit - cluster 안 뉴스 본문 마커 검증.
2. recipes.news.disclosureNewsCrosscheck - cluster 매칭 정밀화.
3. recipes.fundamental.disclosure.eventRadar.eventInbox - newsLead/priceLead cluster 만 inbox 로 승격.

## 기본 검증

- `newsLead` 또는 `priceLead` row 는 *의심 후보* 로만 표시, 결론 X.
- 가격 임계 (±3%) 는 외부 변수 (지수 동시 변동) 보정 없이 사용 — 답변 한계로 명시.
- cluster window (±3 day) 가 짧으면 정정·재공시를 별개 cluster 로 분리할 위험이 있다 — 답변에 window 값을 명시.
