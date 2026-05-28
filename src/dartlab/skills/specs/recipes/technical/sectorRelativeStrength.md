---
id: recipes.technical.sectorRelativeStrength
title: 섹터 대비 상대 강도 (20d / 60d 수익률 차)
category: recipes
kind: recipe
scope: builtin
status: curated
graphTier: L1.5
cluster: technical
purpose: 종목 20/60d 수익률 vs 동일 sector 평균 수익률 차 (relative strength). 상대 강도 양수면 *섹터 outperform*, 음수면 *underperform*. 추론 라벨 없이 정량 차분만. price + sector gather 결합. 트리거 — '섹터 대비 상대 강도 (20d / 60d 수익률 차)', 'sector relative strength', 'sectorRelativeStrength'.
whenToUse:
  - 섹터 상대 강도
  - relative strength
  - sector RS
  - 섹터 outperform
examples:
  - 005930 섹터 평균 대비 상대 강도
  - 섹터 outperform 종목 — 20d / 60d 기준
  - sector RS 정량 — 종목 - 섹터 차
expectedOutputs:
  - 20d / 60d 종목 수익률 + 섹터 평균 수익률 + 차 단일값
  - 라벨 (outperform / underperform / 동행 — 임계 ±3%p)
  - 시계열 chart (relative strength 6mo)
linkedSkills:
  - engines.gather
  - recipes.sentiment.priceMomentumGap
  - recipes.technical.movingAverageConfluence
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
  - relativeStrengthGap
  - sectorBenchmarkDiff
falsifier:
  description: "sector gather row 가 없거나 60 거래일 미달이면 결론 X. 섹터 분류 변경 (재분류 직후) 직후 row 는 의미 약함."
forbidden:
  - relative strength 단일 시점 값으로 종목 강세/약세 단정 금지
  - 섹터 분류 변경 시점 미보정 결론 금지
failureModes:
  - sector gather row 부족
  - 60 거래일 윈도우 미충족
  - 섹터 분류 (GICS / KRX) 변경 직후 row 오염
lastUpdated: '2026-05-23'
validatedAt: '2026-05-27'
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


def closeOf(r):
    for k in ("close", "closePrice", "adjClose"):
        v = floatOr(r.get(k))
        if v is not None and v > 0:
            return v
    return None


def ret(rows, days):
    closes = [closeOf(r) for r in rows]
    closes = [v for v in closes if v is not None]
    if len(closes) < days + 1:
        return None
    return (closes[-1] / closes[-days - 1]) - 1.0


try:
    pdf = c.gather("price").head(70)
    p_rows = pdf.to_dicts() if hasattr(pdf, "to_dicts") else []
except Exception:
    p_rows = []
p_rows.sort(key=lambda r: str(r.get("date") or r.get("tradeDate") or ""))

try:
    sdf = c.gather("sector").head(70)
    s_rows = sdf.to_dicts() if hasattr(sdf, "to_dicts") else []
except Exception:
    s_rows = []
s_rows.sort(key=lambda r: str(r.get("date") or r.get("tradeDate") or ""))

stock_ret_20 = ret(p_rows, 20)
stock_ret_60 = ret(p_rows, 60)

# sector row 의 수익률 컬럼 fallback — sectorReturn / avgReturn / indexClose
def sectorRet(rows, days):
    # sector index close 가 있으면 그걸로 계산.
    closes = []
    for r in rows:
        for k in ("indexClose", "sectorIndex", "close"):
            v = floatOr(r.get(k))
            if v is not None and v > 0:
                closes.append(v)
                break
    if len(closes) >= days + 1:
        return (closes[-1] / closes[-days - 1]) - 1.0
    # fallback: row 별 ret 직접 컬럼
    rets = [floatOr(r.get("ret") or r.get("return") or r.get("sectorReturn")) for r in rows]
    rets = [x for x in rets if x is not None]
    if len(rets) >= days:
        # 누적 (1+r) product
        prod = 1.0
        for x in rets[-days:]:
            prod *= 1.0 + x
        return prod - 1.0
    return None


sector_ret_20 = sectorRet(s_rows, 20)
sector_ret_60 = sectorRet(s_rows, 60)

rs_20 = (
    (stock_ret_20 - sector_ret_20)
    if (stock_ret_20 is not None and sector_ret_20 is not None)
    else None
)
rs_60 = (
    (stock_ret_60 - sector_ret_60)
    if (stock_ret_60 is not None and sector_ret_60 is not None)
    else None
)

phase = "insufficient"
if rs_60 is not None:
    if rs_60 > 0.05:
        phase = "outperform"
    elif rs_60 < -0.05:
        phase = "underperform"
    else:
        phase = "inline"

latest_date = (
    str(p_rows[-1].get("date") or p_rows[-1].get("tradeDate"))
    if p_rows
    else None
)

table = pl.DataFrame(
    [
        {
            "stockRet20d": stock_ret_20,
            "stockRet60d": stock_ret_60,
            "sectorRet20d": sector_ret_20,
            "sectorRet60d": sector_ret_60,
            "rs20d": rs_20,
            "rs60d": rs_60,
            "phase": phase,
            "priceRowsAvailable": len(p_rows),
            "sectorRowsAvailable": len(s_rows),
        }
    ]
)

emit_result(
    table=table,
    values={
        "rs20d": rs_20,
        "rs60d": rs_60,
        "phase": phase,
    },
    date=latest_date,
    sources=["dartlab://gather/price", "dartlab://gather/sector"],
)
```

## 호출 동작

### 1. 결론 도출

종목 vs 섹터 60d 상대 강도 phase 단정 (outperform / inline / underperform / insufficient). 예: "종목 60d +12.4% vs 섹터 60d +5.1% → rs60d=+7.3%p → outperform phase."

### 2. 핵심 근거 수집

- 종목 가격 row 70 거래일 (Company.gather('price'))
- 섹터 인덱스 또는 row-level ret 70 거래일 (Company.gather('sector'))
- 20d / 60d 수익률 계산 (closes[-1]/closes[-N-1] - 1)

### 3. 메커니즘 분석

```
종목 close 시계열 → 20d / 60d 수익률 산출
섹터 indexClose 시계열 → 20d / 60d 수익률 산출
                       ↓
rs20d = 종목ret20d - 섹터ret20d
rs60d = 종목ret60d - 섹터ret60d
                       ↓
rs60d > +5%   → outperform (섹터 평균 대비 강세)
rs60d < -5%   → underperform (섹터 평균 대비 약세)
±5% 안       → inline (섹터 동행)
data < 60d   → insufficient
```

rs60d 부호 + 절대값 같이 봐야 일관성 판정. rs20d 와 rs60d 부호 다르면 단기 reversal 신호.

### 4. 반례·한계

- 섹터 분류 변경 직후 row (M&A · spin-off) 는 비교 base 깨짐 — 한계 표기.
- rs 부호로 매수/매도 단정 금지 — 정량 차분 표면만.
- 섹터 인덱스가 큰 종목 weight 에 영향받으면 (top-heavy) 자기 종목 영향 자동 제거 안 됨.
- 60d 미만 데이터 → phase=insufficient.

### 5. 후속 모니터링

- rs20d vs rs60d 부호 다르면: `recipes.sentiment.priceMomentumGap` 로 단/중기 모멘텀 갭 확인.
- outperform 진입 직후: `recipes.technical.movingAverageConfluence` 로 추세 합의 검증.
- underperform 진입 + 60d 갭 -10%p 초과: `recipes.industry.sectorMomentumLeadership` 로 laggard 위치 확인.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `stockRet60d` | 종목 60d 수익률 |
| `sectorRet60d` | 섹터 60d 수익률 |
| `rs60d` | 둘 차이 (relative strength) |
| `phase` | outperform / inline / underperform / insufficient |

## 연계 절차

1. recipes.sentiment.priceMomentumGap — 종목 단독 모멘텀 갭과 결합.
2. recipes.technical.movingAverageConfluence — 이동평균 confluence 와 RS 두 축 동시.

## 기본 검증

- price / sector row 60 거래일 미만 → phase=insufficient.
- 섹터 분류 변경 직후 row 는 한계 표기.
- rs 부호로 매수/매도 단정 금지 — 정량 차분만 표면.
