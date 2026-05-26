---
id: recipes.industry.supplyChainConcentration
title: 매출 상위 고객 / 매입 상위 거래처 비중 (HHI 기반)
category: recipes
kind: recipe
scope: builtin
status: tested
purpose: 회사의 매출 상위 5 고객 비중 + 매입 상위 5 거래처 비중을 HHI (Herfindahl) 로 정량화. 단일 큰 고객 의존 = 가격 협상력 약화·credit 리스크 누적. 사업보고서 본문 (특수관계자 거래·주요고객) raw 가 들어와야. analysis 단일축.
whenToUse:
  - 매출 고객 집중도
  - 매입 거래처 집중도
  - 공급망 HHI
  - 단일 고객 의존
examples:
  - 005930 매출 상위 고객 의존도가 얼마
  - 단일 고객 매출 비중 50% 넘는 종목
  - 매출 / 매입 HHI 정량 — 가격 협상력 약화 신호
expectedOutputs:
  - 매출 top 5 고객 비중 + HHI 단일값 (0-1)
  - 매입 top 5 거래처 비중 + HHI 단일값
  - 사업보고서 출처 (특수관계자 거래·주요고객 본문 ref)
linkedSkills:
  - engines.company
  - engines.industry
  - engines.gather
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
    - gather
    - analysis
testUniverse:
  market: KR
  stockCodes:
    - "005930"
    - "000660"
falsifier:
  description: "사업보고서에 상위 고객/거래처 명시 안 된 회사 (B2C 소매 등) 는 본 recipe 비적용. peer 데이터 < 4 면 cross-section 한계."
lastUpdated: "2026-05-22"
---

## 공개 호출 방식

```python
import dartlab
import polars as pl

target = "005930"
c = dartlab.Company(target)

def hhi(shares):
    """shares = list of share % (sum ≤ 100). HHI = sum(s_i^2). 0 ~ 10000."""
    return sum(s * s for s in shares)

# 사업보고서 본문에서 추출된 raw 가정 — 실제 API: c.gather('majorCustomers') 또는 disclosure parse
try:
    cust_rows = c.gather("majorCustomers").to_dicts()
except Exception:
    cust_rows = []
try:
    supp_rows = c.gather("majorSuppliers").to_dicts()
except Exception:
    supp_rows = []

def top_shares(rows, n=5):
    rows_sorted = sorted(rows, key=lambda r: -float(r.get("sharePct") or 0))[:n]
    return [float(r.get("sharePct") or 0) for r in rows_sorted]

cust_top = top_shares(cust_rows)
supp_top = top_shares(supp_rows)

table = pl.DataFrame([{
    "metric": "customers",
    "topShares": str(cust_top),
    "hhi": hhi(cust_top),
    "topCount": len(cust_rows),
}, {
    "metric": "suppliers",
    "topShares": str(supp_top),
    "hhi": hhi(supp_top),
    "topCount": len(supp_rows),
}])

emit_result(
    table=table,
    values={"custHhi": hhi(cust_top), "suppHhi": hhi(supp_top)},
    date=None,
    sources=["dartlab://gather/majorCustomers", "dartlab://gather/majorSuppliers"],
)
```

## 호출 동작

매출 상위 5 고객의 각 share% 를 추출해 HHI = sum(s_i^2) 산출. 매입 상위 5 거래처도 동일. HHI 임계 (일반 산업조직 기준):
- HHI < 1500: 분산
- 1500 ~ 2500: 보통 집중
- > 2500: 고도 집중 (단일 의존 리스크)

## 대표 반환 형태

| column | 의미 |
|---|---|
| `metric` | customers / suppliers |
| `topShares` | 상위 5 의 share% list |
| `hhi` | Herfindahl 지수 |
| `topCount` | 사업보고서 명시 거래처 수 |

## 연계 절차

1. recipes.industry.industryStagePhase - mature phase 의 집중도 비교.
2. recipes.fundamental.credit.distressCandidateScreen - HHI > 2500 → credit 신호 가중.
3. recipes.fundamental.quality.forensics.noteSignalExtractor - 특수관계자 매출 분리.

## 기본 검증

- 사업보고서 raw 없는 회사 (B2C 소매·다수 소비자) 는 본 recipe 비적용.
- 5 미만 거래처만 명시된 경우 HHI 상향 편향 — top 3 / top 5 분리 표기.
- 특수관계자 거래는 별도 분리 — 일반 고객 HHI 와 섞지 않는다.
