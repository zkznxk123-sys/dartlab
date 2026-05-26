---
id: recipes.sentiment.foreignHoldingLevel
title: 외국인 보유 비율 절대 수준 (cross-section level)
category: recipes
kind: recipe
scope: builtin
status: drafted
graphTier: L1.5
cluster: sentiment
purpose: 일별 flow gather row 의 외국인 보유 비율 (foreignHoldingRatio) 최신값을 절대 수준으로 표면. 5%~50% 범위로 종목 간 큰 변동성을 가지는 정량 신호. 추론 라벨 없이 cross-section level 만. flow gather 단일.
whenToUse:
  - 외인 보유 절대 수준
  - foreign holding ratio
  - 외인 보유율 raw
  - cross-section level
linkedSkills:
  - engines.gather
  - recipes.sentiment.foreignBuyMomentum
  - recipes.sentiment.flowImbalance
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
    - "035720"
    - "207940"
    - "035420"
expectedNovelty:
  - foreignHoldingPctRaw
  - crossSectionLevel
falsifier:
  description: "flow row 없으면 결론 X. 보유율 절대값 자체로 매수/매도 신호 단정하면 실패."
forbidden:
  - 보유율 50% 이상이라고 강세 단정 금지
  - 보유율 변화율 ↔ 보유율 절대 혼동 금지
failureModes:
  - flow row 0 또는 foreignHoldingRatio 컬럼 부재
  - 보유율 vs 보유 변화율 혼동
  - 시간외 거래 보정 안 한 비율
lastUpdated: '2026-05-23'
---

## 공개 호출 방식

```python
import dartlab
import polars as pl

target = "005930"
c = dartlab.Company(target)

try:
    flow_df = c.gather("flow").head(5)
    flow_rows = flow_df.to_dicts() if hasattr(flow_df, "to_dicts") else []
except Exception:
    flow_rows = []


def floatOr(v):
    try:
        return float(v) if v is not None else None
    except Exception:
        return None


# 최신 (head 0 — 정렬은 latest first 인 경우가 일반)
latest_pct = None
latest_date = None
for r in flow_rows:
    v = floatOr(r.get("foreignHoldingRatio") or r.get("foreignRatio"))
    if v is not None:
        latest_pct = v
        latest_date = r.get("date") or r.get("tradeDate")
        break

level = "insufficient"
if latest_pct is not None:
    if latest_pct >= 40:
        level = "veryHigh"
    elif latest_pct >= 20:
        level = "high"
    elif latest_pct >= 10:
        level = "moderate"
    elif latest_pct >= 0:
        level = "low"

table = pl.DataFrame(
    [
        {
            "stockCode": target,
            "foreignHoldingPct": latest_pct,
            "level": level,
            "flowRowsScanned": len(flow_rows),
        }
    ]
)

emit_result(
    table=table,
    values={
        "foreignHoldingPct": latest_pct,
        "level": level,
    },
    date=str(latest_date) if latest_date else None,
    sources=["dartlab://gather/flow"],
)
```

## 호출 동작

flow gather row 5 일 분 중 가장 최신 foreignHoldingRatio 컬럼 추출. 40% 이상 = veryHigh, 20~40 = high, 10~20 = moderate, 0~10 = low. 추론 X — 절대 수준 표면화만.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `stockCode` | 종목 코드 |
| `foreignHoldingPct` | 외인 보유 비율 (%) |
| `level` | veryHigh / high / moderate / low / insufficient |

## 연계 절차

1. recipes.sentiment.foreignBuyMomentum — 보유 *level* + flow *가속도* 두 축 동시.
2. recipes.industry.sectorFlowConcentration — 섹터 안 보유율 분포.

## 기본 검증

- flow row 0 → level=insufficient.
- 보유율 절대값 자체로 매수/매도 단정 금지.
- 보유율 변화 (recipes.sentiment.foreignBuyMomentum) 와 별 측면이므로 같이 보면 더 풍부.
