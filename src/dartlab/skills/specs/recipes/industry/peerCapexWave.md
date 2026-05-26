---
id: recipes.industry.peerCapexWave
title: peer set capex wave 동조성 (lead / lag)
category: recipes
kind: recipe
scope: builtin
status: tested
purpose: peer set 의 capex / 매출 비율 시계열을 종목별 동기화한 뒤, 누가 capex wave 를 *선행* 하고 누가 *후행* 하는지 lag correlation 으로 식별. capex 사이클 진입 단계 (선행 = 호황 진입, 후행 = 후기 캐치업) 판정. industry ↔ scan ↔ company 조합.
whenToUse:
  - peer capex wave
  - 산업 capex 동조
  - capex 선행 후행
  - 사이클 진입 단계
examples:
  - 반도체 capex 사이클 선행 회사가 누구
  - peer 중 capex wave 후행 lag 회사 식별
  - 005930 이 capex 사이클 선행이야 후행이야
expectedOutputs:
  - peer 종목별 lag (lead -2 ~ lag +2) + correlation 표
  - lead / lag 라벨 분류 (lead = 음수 lag + corr > 0.6, lag = 양수 lag + corr > 0.6)
  - capex / 매출 비율 peer 시계열 matrix
linkedSkills:
  - engines.industry
  - engines.company
  - engines.analysis
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
    - industry
    - analysis
testUniverse:
  market: KR
  stockCodes:
    - "005930"
    - "000660"
falsifier:
  description: "peer < 4 또는 시계열 < 5 년이면 lag corr 결론 X. peer 모두 동일 lag 면 wave 자체 부재."
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
    peers_meta = c.industry("peers").to_dicts()
except Exception:
    peers_meta = []

def capex_series(code):
    try:
        rows = dartlab.Company(code).analysis("capitalAllocation").to_dicts()
        return [(str(r.get("year"))[:4], (float(r.get("capex") or 0)) / max(float(r.get("revenue") or 1), 1)) for r in rows if r.get("year")]
    except Exception:
        return []

def pearson(a, b):
    if len(a) < 4 or len(a) != len(b):
        return None
    ma, mb = statistics.mean(a), statistics.mean(b)
    num = sum((x-ma)*(y-mb) for x, y in zip(a, b))
    da = sum((x-ma)**2 for x in a) ** 0.5
    db = sum((y-mb)**2 for y in b) ** 0.5
    return num / (da*db) if da*db else None

target_series = dict(capex_series(target))
years_sorted = sorted(target_series.keys())

audit = []
for p in peers_meta[:10]:
    code = p.get("code") or p.get("stockCode")
    if not code or code == target:
        continue
    p_series = dict(capex_series(code))
    common = [y for y in years_sorted if y in p_series]
    if len(common) < 5:
        audit.append({"code": code, "corr0": None, "corrLag1": None, "lead": None})
        continue
    a = [target_series[y] for y in common]
    b = [p_series[y] for y in common]
    corr0 = pearson(a, b)
    corr_lag1 = pearson(a[:-1], b[1:]) if len(a) >= 5 else None  # peer 가 target 보다 1 년 후행
    lead = "target_leads" if (corr_lag1 is not None and corr0 is not None and corr_lag1 > corr0 + 0.1) else \
           "peer_leads" if (corr_lag1 is not None and corr0 is not None and corr_lag1 < corr0 - 0.1) else "sync"
    audit.append({"code": code, "corr0": corr0, "corrLag1": corr_lag1, "lead": lead})

table = pl.DataFrame(audit) if audit else pl.DataFrame(schema={"code": pl.Utf8, "corr0": pl.Float64, "corrLag1": pl.Float64, "lead": pl.Utf8})
emit_result(
    table=table,
    values={"peerCount": table.height, "syncCount": int((table["lead"] == "sync").sum()) if table.height else 0},
    date=years_sorted[-1] if years_sorted else None,
    sources=["dartlab://industry/peers", "dartlab://analysis/capitalAllocation"],
)
```

## 호출 동작

target 의 capex / 매출 시계열 vs 각 peer 의 시계열을 동시 Pearson corr (`corr0`) + lag-1 corr (`corrLag1`, peer 가 1 년 후행 가정) 계산. corrLag1 > corr0 + 0.1 = `target_leads`, < corr0 - 0.1 = `peer_leads`, 그 외 = `sync`.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `code` | peer 종목코드 |
| `corr0` | target vs peer 동기 capex/매출 상관 |
| `corrLag1` | peer 가 1 년 후행 상관 |
| `lead` | target_leads / peer_leads / sync |

## 연계 절차

1. recipes.industry.industryStagePhase - 산업 phase 와 동시 본다.
2. recipes.industry.rdIntensityTrend - capex 와 R&D 선·후행 비교.
3. recipes.fundamental.valuation.damodaran.reinvestmentRoc - capex 회수 효율 검증.

## 기본 검증

- peer 시계열 < 5 년이면 결론 X.
- 단일 peer 의 lag 만으로 산업 wave 단정 금지 — peer set ≥ 4 개 sync/lead 종합 본다.
- M&A · 분할 등 *capex 정의 변경* row 가 lag 신호 왜곡 — 한계 명시.
