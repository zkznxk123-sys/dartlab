---
id: recipes.fundamental.governance.relatedPartyTransactionShare
title: 특수관계자 매출·매입 비중 추세
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: 특수관계자 (대주주·계열사) 와의 매출 + 매입 + 자금대여 비중의 연도별 추세. 비중 > 30% 또는 *전체 매출보다 빠르게 성장* 시 일감몰아주기·이전가격 의심 후보. governance + forensics 결합.
whenToUse:
  - 특수관계자 거래 비중
  - 일감몰아주기 의심
  - related party transaction
  - 계열사 의존
linkedSkills:
  - engines.company
  - engines.gather
  - recipes.fundamental.quality.forensics.noteSignalExtractor
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
  - "engines.viz.evidenceCoverage"
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
    - analysis
testUniverse:
  market: KR
  stockCodes:
    - "005930"
    - "000660"
falsifier:
  description: "특수관계자 거래 raw 누락 (소규모 회사·미공시) 시 결론 X. 비중 단일값만 보고 의심 단정 금지 — 추세 + 매출 성장률 비교 필수."
lastUpdated: "2026-05-22"
---

## 공개 호출 방식

```python
import dartlab
import polars as pl

target = "005930"
c = dartlab.Company(target)

try:
    rpt_rows = c.gather("relatedPartyTransactions").to_dicts()
except Exception:
    rpt_rows = []

try:
    rev_rows = c.show("revenue").to_dicts()
    rev_by_year = {str(r.get("year"))[:4]: float(r.get("revenue") or 0) for r in rev_rows}
except Exception:
    rev_by_year = {}

audit = []
for r in sorted(rpt_rows, key=lambda x: str(x.get("year") or "")):
    yr = str(r.get("year"))[:4]
    sales_to_rp = float(r.get("salesToRelated") or 0)
    purch_from_rp = float(r.get("purchasesFromRelated") or 0)
    total_rev = rev_by_year.get(yr, 0)
    audit.append({
        "year": yr,
        "salesToRpPct": sales_to_rp / total_rev if total_rev else None,
        "purchPct": purch_from_rp / total_rev if total_rev else None,
        "absoluteSales": sales_to_rp,
    })

table = pl.DataFrame(audit) if audit else pl.DataFrame(
    schema={"year": pl.Utf8, "salesToRpPct": pl.Float64, "purchPct": pl.Float64, "absoluteSales": pl.Float64}
)

emit_result(
    table=table,
    values={"years": table.height,
            "latestSalesPct": float(table["salesToRpPct"].drop_nulls().tail(1)[0]) if table["salesToRpPct"].drop_nulls().len() else None},
    date=str(table["year"].max()) if table.height else None,
    sources=["dartlab://gather/relatedPartyTransactions", "dartlab://show/revenue"],
)
```

## 호출 동작

연도별 특수관계자 매출 / 매입 / 총매출 비율 산출. 비중 > 30% 또는 연도 간 ≥ +5%p 증가 시 *일감몰아주기 의심* 표시. 동시에 같은 매출이 절대값으로 늘었는지도 분리 표기.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `year` | 결산 연도 |
| `salesToRpPct` | 특수관계자 매출 / 총매출 |
| `purchPct` | 특수관계자 매입 / 총매출 |
| `absoluteSales` | 특수관계자 매출 절대값 |

## 연계 절차

1. recipes.fundamental.quality.forensics.noteSignalExtractor - 주석 본문에서 특수관계자 분리.
2. recipes.fundamental.quality.forensics.controllingPowerJudgment - 실질지배력 시점 변경 추적.
3. recipes.fundamental.governance.audit - 거버넌스 종합 audit.

## 기본 검증

- 특수관계자 거래 raw 누락 회사는 본 recipe 비적용.
- 비중 단일 시점만으로 의심 결론 X — 추세 + 매출 성장률 비교 필수.
- *합법적* 그룹 내부거래도 있으므로 *의심 후보* 로만 표기.
