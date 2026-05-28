---
id: recipes.industry.supplyChainConcentration
title: 매출 상위 고객 / 매입 상위 거래처 비중 (HHI 기반)
category: recipes
kind: recipe
scope: builtin
status: curated
purpose: 회사의 매출 상위 5 고객 비중 + 매입 상위 5 거래처 비중을 HHI (Herfindahl) 로 정량화. 단일 큰 고객 의존 = 가격 협상력 약화·credit 리스크 누적. 사업보고서 본문 (특수관계자 거래·주요고객) raw 가 들어와야. analysis 단일축. 트리거 — '매출 상위 고객 / 매입 상위 거래처 비중 (HHI 기반)', 'supply chain concentration', 'supplyChainConcentration'.
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
validatedAt: '2026-05-27'
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

### 1. 결론 도출

custHhi + suppHhi 집중도 단정. 예: "005930 매출 top5 (HHI 1840 — 보통 집중) → 상위 1 고객 25% / 상위 5 합 62%. 매입 top5 (HHI 3200 — 고도 집중) → 단일 거래처 40% (반도체 장비 의존). 매입 측 협상력 약화 + 공급망 리스크 신호."

### 2. 핵심 근거 수집

- Company.gather('majorCustomers') 사업보고서 본문 — 상위 고객 sharePct
- Company.gather('majorSuppliers') 사업보고서 본문 — 상위 거래처 sharePct
- 각 metric × 상위 5 × HHI = sum(s_i^2) (0-10000 scale)

### 3. 메커니즘 분석

```
2 시리즈 (customers + suppliers) → 각 HHI
   상위 5 (또는 명시 개수) 의 share % 추출
   HHI = sum(s_i^2)
   ↓
임계 (산업조직 기준):
   HHI < 1500       → 분산 (가격 협상력 균형)
   HHI 1500-2500    → 보통 집중
   HHI > 2500       → 고도 집중 (단일 의존 리스크)
   ↓
customer + supplier 결합:
   custHhi 높음     → 매출 단일 의존 (고객 credit risk + 가격 협상력 약)
   suppHhi 높음     → 매입 단일 의존 (cost 협상력 약 + 공급 중단 리스크)
   둘 다 높음       → 양면 협상력 약 (mature phase + 자체 brand 약)
```

매출 단일 고객 50%+ = 그 고객 사정 (재고조정 / 단가인하 / 거래중단) 이 회사 실적 직접 직격. 매입 단일 거래처 50%+ = 공급 중단 시 즉시 생산 중단.

### 4. 반례·한계

- B2C 소매 (롯데쇼핑 등) 회사는 사업보고서에 고객 명시 안 됨 — 본 recipe 비적용.
- 5 미만만 명시 시 HHI 상향 편향 — top 3 / top 5 분리.
- 특수관계자 매출과 일반 고객 매출 혼합 — 별도 분리 필요 (RPT recipe 와 cross).
- HHI 시점 단일 — 추세 (연도별) 분리 시 변동성 신호 추가.

### 5. 후속 모니터링

- custHhi > 2500 → `recipes.fundamental.credit.distressCandidateScreen` 으로 credit 신호 가중.
- suppHhi > 2500 → `recipes.industry.peerCapexWave` 로 공급망 capex 추세 점검.
- 특수관계자 매출 큼 → `recipes.fundamental.quality.forensics.noteSignalExtractor` 로 주석 본문 분리.

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
