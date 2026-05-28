---
id: recipes.news.industryNewsSpillover
title: 산업 뉴스 spillover (peer 이벤트 → target 영향 추적)
category: recipes
kind: recipe
scope: builtin
status: curated
purpose: 같은 산업 peer 의 주요 공시·뉴스 발생 직후 target 의 가격 변동 lag (T+1 / T+3 / T+5). peer 이벤트 spillover 가 *유의미* 한 회사는 동조성 강함 — 산업 분석 신호.
whenToUse:
  - 산업 spillover
  - peer 이벤트 영향
  - 산업 동조성
  - spillover lag
examples:
  - peer 공시 발생 직후 005930 가격 영향
  - 산업 뉴스 spillover lag — T+1 T+3 T+5
  - 동종 종목 이벤트 따라 움직이는 회사
expectedOutputs:
  - T+1 / T+3 / T+5 target 가격 변동 평균 (peer 이벤트 직후)
  - peer 이벤트 row 카운트 + spillover 유의 lag (가장 강한 시점)
  - 동조성 강도 라벨 (강 / 중 / 약 / 무 기준 T+3 변동 절대값)
linkedSkills:
  - engines.industry
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
    - industry
testUniverse:
  market: KR
  stockCodes:
    - "005930"
    - "000660"
falsifier:
  description: "peer 이벤트 < 5 이면 spillover 결론 X. 시장 전체 충격 (지수 ±3%+) 동시 발생 시 산업 spillover 분리 불가."
lastUpdated: "2026-05-22"
validatedAt: '2026-05-27'
---

## 공개 호출 방식

```python
import dartlab
import polars as pl
from datetime import datetime, timedelta

target = "005930"
c = dartlab.Company(target)

def parseDate(v):
    if isinstance(v, datetime): return v.date()
    s = str(v)[:10].replace(".","-")
    try: return datetime.strptime(s, "%Y-%m-%d").date()
    except: return None

# target 가격
try:
    target_px = c.gather("price").head(180).to_dicts()
except Exception:
    target_px = []
px_by_date = {parseDate(p.get("date") or p.get("tradeDate")): float(p.get("close") or 0) for p in target_px}

# peer events
try:
    peers = c.industry("peers").to_dicts()[:6]
except Exception:
    peers = []

events = []
for p in peers:
    code = p.get("code") or p.get("stockCode")
    if not code or code == target: continue
    try:
        peer_news = dartlab.Company(code).gather("news").head(30).to_dicts()
    except Exception:
        peer_news = []
    for n in peer_news:
        d = parseDate(n.get("date") or n.get("publishedAt"))
        if d:
            events.append({"date": d, "peer": code, "title": (n.get("title") or "")[:60]})

# spillover: T+1 / T+3 / T+5 target return
def ret_after(d, days):
    sorted_dates = sorted(px_by_date.keys())
    after = [(x, px_by_date[x]) for x in sorted_dates if x > d]
    if len(after) < days or px_by_date.get(d) is None:
        return None
    return after[days-1][1] / px_by_date[d] - 1 if px_by_date.get(d) else None

rows = []
for e in events[:50]:
    if e["date"] not in px_by_date: continue
    rows.append({
        "eventDate": str(e["date"]),
        "peer": e["peer"],
        "title": e["title"],
        "targetRetT1": ret_after(e["date"], 1),
        "targetRetT3": ret_after(e["date"], 3),
        "targetRetT5": ret_after(e["date"], 5),
    })

table = pl.DataFrame(rows) if rows else pl.DataFrame(
    schema={"eventDate": pl.Utf8, "peer": pl.Utf8, "title": pl.Utf8,
            "targetRetT1": pl.Float64, "targetRetT3": pl.Float64, "targetRetT5": pl.Float64}
)

emit_result(
    table=table,
    values={"eventCount": table.height},
    date=None,
    sources=["dartlab://gather/news", "dartlab://gather/price", "dartlab://industry/peers"],
)
```

## 호출 동작

### 1. 결론 도출

peer 이벤트 spillover lag 단정 (T+1 평균 return). 예: "peer 이벤트 12 건 평균 target T+1 +0.8%, T+3 +1.4%, T+5 +2.1% — 동조성 강함 (산업 spillover effect 신호)."

### 2. 핵심 근거 수집

- peer 회사 list (Company.industry('peers'))
- peer 별 뉴스/공시 이벤트 시점 (Company.gather('news') 또는 disclosure)
- target 가격 시계열 (Company.gather('price'))
- T+1 / T+3 / T+5 가격 변동률 (이벤트 직후 1/3/5 거래일)

### 3. 메커니즘 분석

```
peer 이벤트 시점 t_i (N 건)
   ↓
각 t_i 별 target 가격
   T+1: close[t_i+1] / close[t_i] - 1
   T+3: close[t_i+3] / close[t_i] - 1
   T+5: close[t_i+5] / close[t_i] - 1
   ↓
N 건 평균 T+1 / T+3 / T+5 산출
   |avg T+1| > 1%  → 유의미 spillover 후보
   < 0.5%          → 비유의미 (시장 noise)
   부호 일관성     → 양수 / 음수 spillover 방향
```

peer 이벤트 빈도 ↑ + 평균 lag return 큼 = 산업 동조성 강함. 부호 음수 = 시장 risk-off spillover (peer 악재 → target 동반 하락).

### 4. 반례·한계

- peer 정의 (GICS sub-industry vs broad) 차이로 spillover 강도 변화.
- 같은 시점 다수 peer 이벤트 (산업 전반) → spillover 측정 오염 (어떤 peer event 가 driver 인지 식별 X).
- 시장 전체 충격 (KOSPI ±3%) 시점은 spillover 와 시장 효과 혼합.
- T+5 너무 길면 다른 이벤트 (자기 종목 공시 등) overlap.

### 5. 후속 모니터링

- 유의미 spillover 발생 (|T+1| > 1%): `recipes.industry.sectorMomentumLeadership` 로 leader/laggard 위치 확인.
- 음수 spillover 일관 시: `recipes.industry.marginCompressionScan` 으로 산업 mature/decline 신호 확인.
- spillover 방향 mixed: peer 이벤트 종류별 분리 (실적 vs 인수 vs 임원 변동) 필요 — `recipes.news.eventTimelineFusion` cluster 활용.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `eventDate` | peer 이벤트 시점 |
| `peer` | peer 종목코드 |
| `title` | 뉴스 제목 |
| `targetRetT1/T3/T5` | target T+1/T+3/T+5 변동 |

## 연계 절차

1. recipes.industry.industryStagePhase - spillover 강도와 phase 정합.
2. recipes.news.disclosureNewsCrosscheck - peer 뉴스의 1 차 출처 검증.

## 기본 검증

- peer 이벤트 < 5 이면 결론 X.
- 지수 동시 변동 (±3%+) 시 spillover 분리 불가 — 한계 명시.
- 인과 단정 X — *lag 상관* 자체가 정량 사실.
