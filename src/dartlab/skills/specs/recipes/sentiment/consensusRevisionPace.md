---
id: recipes.sentiment.consensusRevisionPace
title: 컨센서스 revision 속도 (애널리스트 EPS 추정 변화율 z-score)
category: recipes
kind: recipe
scope: builtin
status: deprecated
purpose: 30/60/90 일 윈도우 별 EPS 추정 변화율 + revision count 의 z-score. 본 신호는 *애널리스트 합의의 변화 속도* 정량화 — 단순 컨센서스 절대값이 아닌 *변화율*. sentiment 페르소나 보조.
whenToUse:
  - 컨센서스 revision 속도
  - EPS 추정 변화율
  - revision pace
  - 애널리스트 합의 변화
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
  description: "애널리스트 < 3 명 종목은 컨센 노이즈 큼. EPS 자체가 음수 → 양수 전환 시 변화율 정의 불안정."
lastUpdated: "2026-05-22"
deprecatedAt: '2026-05-23'
deprecatedReason: "c.gather('consensus') axis 미구현 — 데이터 소스 추가 후 재작성"
---

## 공개 호출 방식

```python
import dartlab
import polars as pl
import statistics
from datetime import datetime, timedelta

target = "005930"
c = dartlab.Company(target)

try:
    con_rows = c.gather("consensus").to_dicts()
except Exception:
    con_rows = []

def parseDate(v):
    if isinstance(v, datetime): return v.date()
    s = str(v)[:10].replace(".","-")
    try: return datetime.strptime(s, "%Y-%m-%d").date()
    except: return None

con_rows = sorted([r for r in con_rows if parseDate(r.get("asOf"))], key=lambda r: parseDate(r.get("asOf")))

eps_series = []
for r in con_rows:
    eps = r.get("epsConsensus") or r.get("avgEps")
    try: eps = float(eps) if eps is not None else None
    except: eps = None
    if eps is not None:
        eps_series.append({"asOf": parseDate(r.get("asOf")), "eps": eps, "analystCount": int(r.get("analystCount") or 0)})

if len(eps_series) < 4:
    table = pl.DataFrame(schema={"window": pl.Utf8, "epsChangePct": pl.Float64, "analystCountDelta": pl.Int64})
    emit_result(table=table, values={"insufficient": True}, date=None, sources=["dartlab://gather/consensus"])
else:
    last = eps_series[-1]
    rows = []
    for window_days in (30, 60, 90):
        past = [x for x in eps_series if x["asOf"] >= last["asOf"] - timedelta(days=window_days)]
        if len(past) >= 2:
            chg = (last["eps"] / past[0]["eps"] - 1) if past[0]["eps"] else None
            analyst_delta = last["analystCount"] - past[0]["analystCount"]
            rows.append({"window": f"{window_days}d", "epsChangePct": chg, "analystCountDelta": analyst_delta})
    table = pl.DataFrame(rows) if rows else pl.DataFrame(schema={"window": pl.Utf8, "epsChangePct": pl.Float64, "analystCountDelta": pl.Int64})
    emit_result(
        table=table,
        values={"epsLatest": last["eps"], "analystLatest": last["analystCount"]},
        date=str(last["asOf"]),
        sources=["dartlab://gather/consensus"],
    )
```

## 호출 동작

EPS 컨센서스 시계열 (asOf 별) 정렬 후 30/60/90 일 윈도우 변화율 + 애널리스트 수 변화. 변화율 > +5% = 상향 revision, < -5% = 하향 revision.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `window` | 30d / 60d / 90d |
| `epsChangePct` | EPS 추정 변화율 |
| `analystCountDelta` | 애널리스트 수 변화 |

## 연계 절차

1. recipes.sentiment.flowImbalance - revision 시점 외인/기관 수급 정합.
2. recipes.fundamental.disclosure.event - 실적 공시 직전 revision 패턴.

## 기본 검증

- 애널리스트 < 3 명 종목은 컨센 noise — 한계 명시.
- EPS 부호 전환 (음 → 양) 시 변화율 정의 불안정 — 절대값 표기 병행.
- revision 단독 결론 X — 가격·수급과 결합.
