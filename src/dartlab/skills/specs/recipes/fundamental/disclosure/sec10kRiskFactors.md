---
id: recipes.fundamental.disclosure.sec10kRiskFactors
title: SEC 10-K Item 1A 위험 요인 변화 (YoY 신규/삭제 항목 수)
category: recipes
kind: recipe
scope: builtin
status: tested
purpose: 미국 10-K Item 1A "Risk Factors" 의 직전 연도 대비 *신규 추가* / *삭제* 항목 수. 신규 risk factor ≥ 3 = 경영진의 위험 인식 전환 신호. EDGAR provider raw.
whenToUse:
  - 10-K risk factor YoY
  - SEC 위험 요인 변화
  - 미국 공시 risk
  - Item 1A 신규 위험
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
  - "engines.viz.evidenceCoverage"
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
    - search
    - analysis
testUniverse:
  market: US
  tickers:
    - "AAPL"
    - "MSFT"
falsifier:
  description: "10-K 본문 raw 누락 또는 직전 연도 없음 → 결론 X. 단순 wording 변경을 신규 위험으로 카운트하면 false positive."
lastUpdated: "2026-05-22"
---

## 공개 호출 방식

```python
import dartlab
import polars as pl
import re

ticker = "AAPL"

try:
    filings = dartlab.providers.edgar.fetch10kFilings(ticker, limit=2)
except Exception:
    filings = []

def extract_risk_items(text):
    """Item 1A 안 bullet 또는 paragraph 단위 항목 추출."""
    # heuristic: 6 어 이상 새 paragraph 시작
    return [re.sub(r"\s+", " ", p)[:120] for p in re.split(r"\n\s*\n", text) if len(p.split()) >= 6][:50]

if len(filings) < 2:
    table = pl.DataFrame(schema={"current": pl.Int64, "previous": pl.Int64, "added": pl.Int64, "removed": pl.Int64})
    emit_result(table=table, values={"insufficient": True}, date=None, sources=["dartlab://edgar/10k"])
else:
    cur_items = set(extract_risk_items(filings[0].get("item1aText", "")))
    prev_items = set(extract_risk_items(filings[1].get("item1aText", "")))
    added = len(cur_items - prev_items)
    removed = len(prev_items - cur_items)
    table = pl.DataFrame([{
        "current": len(cur_items),
        "previous": len(prev_items),
        "added": added,
        "removed": removed,
        "filingDate": filings[0].get("filingDate"),
    }])
    emit_result(
        table=table,
        values={"added": added, "removed": removed, "current": len(cur_items)},
        date=filings[0].get("filingDate"),
        sources=["dartlab://edgar/10k"],
    )
```

## 호출 동작

직전 2 개 10-K Item 1A 본문에서 paragraph 단위 위험 항목 추출 후 두 set 의 diff. added ≥ 3 또는 removed ≥ 3 = 위험 인식 *transition* 후보.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `current` | 최근 10-K 항목 수 |
| `previous` | 직전 10-K 항목 수 |
| `added` | 신규 추가 |
| `removed` | 삭제 |

## 연계 절차

1. recipes.fundamental.disclosure.filingTextSignal - 위험 키워드 frequency 결합.
2. recipes.fundamental.quality.forensics.disclosureTimingAnomaly - 위험 추가 시점과 가격 변동 비교.

## 기본 검증

- 10-K raw 누락 또는 직전 연도 없음 → 결론 X.
- *wording* 변경 (의미 동일, 표현만 변경) 을 신규로 카운트하지 않도록 paragraph 매칭 임계 적절히.
- *innovation lead* 결론은 R&D 강도만으로 단정 X.
