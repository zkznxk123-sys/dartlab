---
id: recipes.industry.sectorFlowConcentration
title: 섹터 자금 흐름 집중도 (외인 비중 + 거래대금 share)
category: recipes
kind: recipe
scope: builtin
status: drafted
graphTier: L1.5
cluster: industry
purpose: 종목이 속한 섹터의 외인 보유 비율 + 거래대금 share 의 단순 정량 표기. 섹터 안 종목 거래대금이 한 종목으로 집중되면 *집중*, 분산되면 *분산*. 추론 라벨 없이 절대 수치만. sector + price gather 결합.
whenToUse:
  - 섹터 자금 집중
  - sector flow concentration
  - 외인 보유율
  - 거래대금 share
linkedSkills:
  - engines.gather
  - recipes.industry.peerPriceConvergence
  - recipes.sentiment.foreignBuyMomentum
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
testUniverse:
  market: KR
  stockCodes:
    - "005930"
    - "000660"
expectedNovelty:
  - sectorFlowShare
  - foreignHoldingPct
falsifier:
  description: "섹터 정보 없으면 (sector gather 0 row) 결론 X. 단일 거래일 거래대금으로 집중도 단정 금지 — 최소 5 거래일 평균."
forbidden:
  - 거래대금 집중도 자체로 매수 시그널 단정 금지
  - 외인 보유율 절대값으로 sentiment 라벨 단정 금지
failureModes:
  - sector gather row 0
  - 단일 거래일 변동을 집중도로 오인
  - 외인 보유율 (보유 vs 매매) 정의 혼동
lastUpdated: '2026-05-23'
---

## 공개 호출 방식

```python
import dartlab
import polars as pl

target = "005930"
c = dartlab.Company(target)


def floatOr(v):
    try:
        return float(v) if v is not None else None
    except Exception:
        return None


# 종목 거래대금 평균
try:
    pdf = c.gather("price").head(10)
    p_rows = pdf.to_dicts() if hasattr(pdf, "to_dicts") else []
except Exception:
    p_rows = []

vals = []
for r in p_rows:
    cl = floatOr(r.get("close") or r.get("closePrice"))
    vol = floatOr(r.get("volume") or r.get("tradeVolume"))
    if cl is not None and vol is not None:
        vals.append(cl * vol)
target_value = sum(vals) / len(vals) if vals else None

# 외인 보유율 (flow gather row 의 마지막)
try:
    fdf = c.gather("flow").head(5)
    f_rows = fdf.to_dicts() if hasattr(fdf, "to_dicts") else []
except Exception:
    f_rows = []

foreign_pct = None
for r in f_rows:
    v = floatOr(r.get("foreignHoldingRatio") or r.get("foreignRatio"))
    if v is not None:
        foreign_pct = v
        break

# sector gather — sector total value 혹은 sector index
try:
    sdf = c.gather("sector").head(5)
    s_rows = sdf.to_dicts() if hasattr(sdf, "to_dicts") else []
except Exception:
    s_rows = []

sector_total_value = None
for r in s_rows:
    v = floatOr(r.get("totalValue") or r.get("sectorValue") or r.get("totalTradeValue"))
    if v is not None:
        sector_total_value = v
        break

share = None
if target_value is not None and sector_total_value and sector_total_value > 0:
    share = target_value / sector_total_value

phase = "insufficient"
if share is not None:
    if share > 0.20:
        phase = "concentrated"
    elif share < 0.05:
        phase = "diffuse"
    else:
        phase = "normal"

table = pl.DataFrame(
    [
        {
            "targetAvgValue": target_value,
            "sectorTotalValue": sector_total_value,
            "valueShare": share,
            "foreignHoldingPct": foreign_pct,
            "phase": phase,
            "priceRowsAvailable": len(p_rows),
            "sectorRowsAvailable": len(s_rows),
        }
    ]
)

emit_result(
    table=table,
    values={
        "valueShare": share,
        "foreignHoldingPct": foreign_pct,
        "phase": phase,
    },
    date="latest",
    sources=["dartlab://gather/price", "dartlab://gather/flow", "dartlab://gather/sector"],
)
```

## 호출 동작

종목 5 거래일 평균 거래대금 + 섹터 총 거래대금 → share 계산. 외인 보유율 (flow row) 같이 표면. share > 20% = concentrated, < 5% = diffuse, 그 외 normal. 추론 X.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `targetAvgValue` | 종목 5 거래일 평균 거래대금 |
| `sectorTotalValue` | 섹터 총 거래대금 |
| `valueShare` | targetAvgValue / sectorTotalValue |
| `foreignHoldingPct` | 외인 보유율 |
| `phase` | concentrated / normal / diffuse / insufficient |

## 연계 절차

1. recipes.industry.peerPriceConvergence — peer 분산과 concentration phase 동시 확인.
2. recipes.sentiment.foreignBuyMomentum — 외인 보유 + flow 가속도 두 축 비교.

## 기본 검증

- sector / price row 0 → phase=insufficient.
- 단일 거래일 표면화 금지 — 5 거래일 평균 사용.
- 외인 보유율 = 보유 비율 ≠ 일별 순매수 (다른 row).
