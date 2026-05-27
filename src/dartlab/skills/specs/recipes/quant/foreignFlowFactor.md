---
id: recipes.quant.foreignFlowFactor
title: 외인 보유율 factor cross-section (5종 quartile)
category: recipes
kind: recipe
scope: builtin
status: tested
graphTier: L1.5
cluster: quant
purpose: 다종목 cross-section 에서 외인 보유 비율의 quartile 분포 측정 + 자기 종목 percentile 위치. quant factor 5 + (value/momentum/quality/size/lowVol) 와 같은 cross-section 형식. 추론 라벨 없이 ranking 만. flow gather 결합.
whenToUse:
  - 외인 보유 factor
  - foreign holding cross-section
  - factor exposure
  - quartile ranking
examples:
  - 005930 외인 보유율 cross-section 어느 분위
  - 외인 보유율 상위 quartile 종목
  - foreign flow factor 노출도 정량
expectedOutputs:
  - universe quartile 분포 (4 bin 경계값)
  - 자기 종목 percentile rank + quartile 라벨 (Q1~Q4)
  - 상위 quartile 종목 list (top 10)
linkedSkills:
  - engines.gather
  - recipes.sentiment.foreignHoldingLevel
  - recipes.quant.macroBetaFactor
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
  - foreignHoldingFactor
  - quartileRank
falsifier:
  description: "측정 종목 < 5 면 quartile 신뢰도 낮음 — 결론 X. 정적 보유율로 모멘텀 단정하면 실패."
forbidden:
  - 외인 비중 자체로 factor return 단정 금지
  - quartile 위치를 매수/매도 결정으로 단정 금지
failureModes:
  - 종목 수 부족
  - 시간외 거래 보정 안 한 비율
  - 정적 보유 ↔ 동적 매매 혼동
lastUpdated: '2026-05-23'
---

## 공개 호출 방식

```python
import dartlab
import polars as pl

target = "005930"
# cross-section: 자기 종목 + 다른 4 종목
peers = ["000660", "035720", "207940", "035420"]
codes = [target] + peers


def floatOr(v):
    try:
        return float(v) if v is not None else None
    except Exception:
        return None


rows = []
for code in codes:
    try:
        c = dartlab.Company(code)
        flow_df = c.gather("flow").head(5)
        flow_rows = flow_df.to_dicts() if hasattr(flow_df, "to_dicts") else []
    except Exception:
        flow_rows = []
    pct = None
    for r in flow_rows:
        v = floatOr(r.get("foreignHoldingRatio") or r.get("foreignRatio"))
        if v is not None:
            pct = v
            break
    if pct is not None:
        rows.append({"stockCode": code, "foreignHoldingPct": pct})

rows.sort(key=lambda r: r["foreignHoldingPct"])
n = len(rows)
target_idx = next((i for i, r in enumerate(rows) if r["stockCode"] == target), None)
target_pct_rank = (target_idx / (n - 1)) if (target_idx is not None and n > 1) else None
target_pct = next((r["foreignHoldingPct"] for r in rows if r["stockCode"] == target), None)

quartile = None
if target_pct_rank is not None:
    if target_pct_rank <= 0.25:
        quartile = "Q1"
    elif target_pct_rank <= 0.50:
        quartile = "Q2"
    elif target_pct_rank <= 0.75:
        quartile = "Q3"
    else:
        quartile = "Q4"

table = pl.DataFrame(
    [
        {
            "stockCode": r["stockCode"],
            "foreignHoldingPct": r["foreignHoldingPct"],
            "rank": i,
            "isTarget": r["stockCode"] == target,
        }
        for i, r in enumerate(rows)
    ]
)

emit_result(
    table=table,
    values={
        "universeSize": n,
        "targetPct": target_pct,
        "targetPercentile": (round(target_pct_rank * 100, 1) if target_pct_rank is not None else None),
        "quartile": quartile,
    },
    date="latest",
    sources=["dartlab://gather/flow"],
)
```

## 호출 동작

### 1. 결론 도출

cross-section quartile + percentile 단정. 예: "5 종목 universe (005930 + 4 peer) — 외인 보유율: 005930=54% / 035420=52% / 207940=18% / 000660=49% / 035720=42%. 005930 rank=4 (정렬 1-5) / percentile=80% / quartile=Q4 → 상위 quartile (외인 보유 집중도 높음). KOSPI 외인 평균 33% 대비 +21%p — large-cap 외인 favored 표면."

### 2. 핵심 근거 수집

- 5 종목 codes (target + 4 peer)
- 각 code × Company.gather('flow') latest row → foreignHoldingRatio
- universe rank 정렬 → target percentile
- quartile bucket: Q1 (0-25%) / Q2 (25-50%) / Q3 (50-75%) / Q4 (75-100%)

### 3. 메커니즘 분석

```
universe (5+ 종목) cross-section → 외인 보유율 ranking
   각 code latest foreignHoldingRatio
   정렬 → rank index 0-N
   ↓
target percentile = target_rank / (N-1) × 100
   ↓
quartile 분류:
   percentile ≤ 25%  → Q1 (외인 비중 하위)
   25% < percentile ≤ 50% → Q2
   50% < percentile ≤ 75% → Q3
   percentile > 75% → Q4 (외인 비중 상위)
   ↓
factor cross-section (정량 사실, 추론 X):
   Q4 = 외인 favored (정적 보유)
   Q1 = 외인 underweight
   Q1 → Q4 추세 변경 시 외인 inflow phase
   Q4 → Q1 추세 변경 시 외인 outflow phase
```

cross-section factor 5 + (value/momentum/quality/size/lowVol) 와 같은 형식. *정적 보유율* — 동적 순매수와 구분 필요. quartile 위치 자체는 매수/매도 결정 아님 (forbidden).

### 4. 반례·한계

- universeSize < 5 → quartile 신뢰도 낮음 (결론 X).
- 정적 보유율 vs 동적 순매수 명확 구분 — 보유율 높음 ≠ 매수 가속.
- quartile 위치를 매수/매도 결정으로 단정 → forbidden.
- 시간외 거래 보정 안 한 비율 → noise.

### 5. 후속 모니터링

- Q4 → Q3 추세 변경 → `recipes.sentiment.foreignBuyMomentum` 으로 외인 가속도 분석.
- Q1 → Q2 추세 변경 → `recipes.sentiment.foreignHoldingLevel` 로 단독 level 시계열.
- quartile 위치 + 가격 동조 → `recipes.quant.macroBetaFactor` 로 macro beta cross-section.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `stockCode` | 종목 |
| `foreignHoldingPct` | 외인 보유율 |
| `rank` | 정렬 순위 |
| `isTarget` | 자기 종목 여부 |

values: universeSize · targetPct · targetPercentile · quartile

## 연계 절차

1. recipes.sentiment.foreignHoldingLevel — 자기 종목 단독 level + cross-section quartile.
2. recipes.quant.macroBetaFactor — 다른 factor cross-section 비교.

## 기본 검증

- universeSize < 5 → quartile 신뢰도 낮음.
- 정적 보유율 ↔ 동적 순매수 명확 구분.
- quartile 위치가 *매수/매도 신호* 가 아님.
