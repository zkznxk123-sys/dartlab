---
id: recipes.fundamental.governance.boardIndependenceTrend
title: 이사회 독립성 추세 (사외이사 비중 + 다선 history)
category: recipes
kind: recipe
scope: builtin
status: tested
purpose: 사외이사 비중 + 평균 임기 + 동시 다선 (다른 회사 이사회 동시 재직) 횟수의 연도별 추세. 단순 사외이사 비율이 아닌 *실질적 독립성* 측정. governance ↔ analysis 격리.
whenToUse:
  - 이사회 독립성 추세
  - 사외이사 비중
  - 다선 history
  - 거버넌스 점검
linkedSkills:
  - engines.company
  - engines.analysis
  - recipes.fundamental.governance.audit
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
  - "engines.viz.mermaidDiagram"
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
    - analysis
    - synth
testUniverse:
  market: KR
  stockCodes:
    - "005930"
    - "000660"
falsifier:
  description: "이사회 명부 raw 누락 회사는 결론 X. 다선 회수가 0 인데 사외이사 비중만 본 결론은 *실질적 독립성* 미증명."
lastUpdated: "2026-05-22"
---

## 공개 호출 방식

```python
import dartlab
import polars as pl

target = "005930"
c = dartlab.Company(target)

try:
    board_rows = c.gather("boardComposition").to_dicts()
except Exception:
    board_rows = []

audit = []
for r in sorted(board_rows, key=lambda x: str(x.get("year") or "")):
    total = int(r.get("totalDirectors") or 0)
    indep = int(r.get("independentDirectors") or 0)
    avg_tenure = float(r.get("avgTenureYears") or 0)
    multi_seat = int(r.get("multiSeatCount") or 0)
    audit.append({
        "year": r.get("year"),
        "independentPct": indep / total if total else None,
        "avgTenureYears": avg_tenure,
        "multiSeatCount": multi_seat,
    })

table = pl.DataFrame(audit) if audit else pl.DataFrame(
    schema={"year": pl.Utf8, "independentPct": pl.Float64,
            "avgTenureYears": pl.Float64, "multiSeatCount": pl.Int64}
)

emit_result(
    table=table,
    values={"years": table.height},
    date=str(table["year"].max()) if table.height else None,
    sources=["dartlab://gather/boardComposition"],
)
```

## 호출 동작

연도별 (1) 사외이사 비중 (2) 평균 임기 (3) 다선 회수 3 축 시계열. 사외이사 비중 ≥ 0.5 + 평균 임기 ≤ 6 + multi-seat 0 이 권장 임계 (한국 상장사 기준).

## 대표 반환 형태

| column | 의미 |
|---|---|
| `year` | 결산 연도 |
| `independentPct` | 사외이사 비중 |
| `avgTenureYears` | 평균 임기 |
| `multiSeatCount` | 다선 횟수 |

## 연계 절차

1. recipes.fundamental.governance.audit - 거버넌스 종합 audit.
2. recipes.fundamental.quality.forensics.executiveCompensationAudit - 보상-이사회 정합.

## 기본 검증

- 이사회 명부 raw 누락 시 결론 X.
- 다선 회수 0 이라도 *실질적 독립성* 측정엔 임원-주주 관계 추가 검증 필요.
- 비중 단독 결론 금지 — 3 축 분리 표기.
