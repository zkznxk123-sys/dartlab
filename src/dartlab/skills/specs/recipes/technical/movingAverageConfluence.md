---
id: recipes.technical.movingAverageConfluence
title: 이동평균선 정합 (5/20/60/120 동시 정렬)
category: recipes
kind: recipe
scope: builtin
status: curated
purpose: 5/20/60/120 일 단순 이동평균선의 *정렬* 상태 분류 — 완전 정렬 (오름차순 또는 내림차순) row 만 *추세 합의* 후보. 단일 골든크로스 함정 회피.
whenToUse:
  - 이동평균선 정렬
  - 추세 합의
  - 골든크로스 confirmation
  - MA confluence
examples:
  - 005930 5/20/60/120 이동평균선 완전 정렬 상태
  - 추세 합의 종목 — 4 MA 동시 정렬
  - 골든크로스 confirmation 신호
expectedOutputs:
  - 4 MA (5/20/60/120) 단일값 + 정렬 순서
  - 라벨 (상승 정렬 / 하강 정렬 / 혼재)
  - 정렬 유지 일수 (현재 추세 합의 지속 기간)
linkedSkills:
  - engines.gather
  - engines.quant
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
    - quant
testUniverse:
  market: KR
  stockCodes:
    - "005930"
falsifier:
  description: "거래일 < 130 이면 120 일 MA 결론 X. 완전 정렬 row 비율이 < 5% 이면 변별력 작음."
lastUpdated: "2026-05-22"
validatedAt: '2026-05-27'
---

## 공개 호출 방식

```python
import dartlab
import polars as pl
import statistics

target = "005930"

try:
    px = dartlab.gather("price", target).head(160).to_dicts()
except Exception:
    px = []
px.sort(key=lambda r: str(r.get("date") or r.get("tradeDate")))
closes = [(r.get("date") or r.get("tradeDate"), float(r.get("close") or 0)) for r in px if r.get("close")]

def sma(series, window):
    if len(series) < window: return None
    return statistics.mean(series[-window:])

rows = []
for i in range(120, len(closes)):
    sub = [c[1] for c in closes[:i+1]]
    ma5, ma20, ma60, ma120 = sma(sub, 5), sma(sub, 20), sma(sub, 60), sma(sub, 120)
    if None in (ma5, ma20, ma60, ma120): continue
    if ma5 > ma20 > ma60 > ma120:
        align = "bullish"
    elif ma5 < ma20 < ma60 < ma120:
        align = "bearish"
    else:
        align = "mixed"
    rows.append({"date": closes[i][0], "close": closes[i][1], "ma5": ma5, "ma20": ma20, "ma60": ma60, "ma120": ma120, "alignment": align})

table = pl.DataFrame(rows) if rows else pl.DataFrame(
    schema={"date": pl.Utf8, "close": pl.Float64, "ma5": pl.Float64, "ma20": pl.Float64,
            "ma60": pl.Float64, "ma120": pl.Float64, "alignment": pl.Utf8}
)

bull_n = int((table["alignment"] == "bullish").sum()) if table.height else 0
bear_n = int((table["alignment"] == "bearish").sum()) if table.height else 0
mixed_n = table.height - bull_n - bear_n
latest = table["alignment"][-1] if table.height else None

emit_result(
    table=table.tail(10) if table.height > 10 else table,
    values={"bullishDays": bull_n, "bearishDays": bear_n, "mixedDays": mixed_n, "latest": latest},
    date=str(closes[-1][0]) if closes else None,
    sources=["dartlab://gather/price"],
)
```

## 호출 동작

### 1. 결론 도출

latest alignment + 정렬 일수 단정. 예: "최신: ma5=78,500 / ma20=77,200 / ma60=74,800 / ma120=71,500 → bullish 완전 정렬 (오름차순). 40일 history 중 bullish 25일 (62%) + bearish 5일 + mixed 10일 → 현재 추세 합의 phase, latest 5일 연속 bullish 유지."

### 2. 핵심 근거 수집

- dartlab.gather('price', target) latest 160 row close 시계열
- 각 거래일 × 5/20/60/120 SMA 4 종
- alignment 분류: bullish (ma5>20>60>120) / bearish (ma5<20<60<120) / mixed
- 40+ 일 history bullish / bearish / mixed 카운트

### 3. 메커니즘 분석

```
close 시계열 160 row → 각 시점 4 MA 계산
   SMA(5)   → 단기 (1주)
   SMA(20)  → 1개월
   SMA(60)  → 3개월
   SMA(120) → 6개월
   ↓
alignment 분류 (각 거래일):
   ma5 > ma20 > ma60 > ma120 → bullish (완전 오름차순)
   ma5 < ma20 < ma60 < ma120 → bearish (완전 내림차순)
   그 외                      → mixed (혼재)
   ↓
40+ 일 history 누적:
   bullishDays / bearishDays / mixedDays 카운트
   latest = 가장 최신 alignment
   ↓
*추세 합의* 신호:
   bullish 비율 > 50% + latest=bullish → 강세 추세 합의 (multi timeframe)
   bearish 비율 > 50% + latest=bearish → 약세 추세 합의
   mixed 다수                            → 추세 불분명 (consolidation)
```

단일 골든크로스 (ma5 ma20 교차) 함정 회피 — 4 MA 동시 정렬 강제. *추세 합의* = multi timeframe (1주 + 1월 + 3월 + 6월) 같은 방향 confirm.

### 4. 반례·한계

- 거래일 < 130 → 120일 MA 결론 X.
- 완전 정렬 비율 < 5% → 변별력 작음 (KOSPI 일반적 mixed 다수).
- 단독 매수 결론 X — 거래량/펀더멘털 결합 필수.
- range bound 종목 (consolidation 장기) → 항상 mixed → 신호 없음.

### 5. 후속 모니터링

- bullish 지속 → `recipes.technical.atrRegimeShift` 로 변동성 체제 결합.
- bullish + momentum → `recipes.quant.momentumFactor` 로 12-1m return 정합.
- bearish 진입 → `recipes.technical.priceVolumeZScore` 로 거래량 burst 점검.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `date` | 거래일 |
| `close` | 종가 |
| `ma5`/`ma20`/`ma60`/`ma120` | 이동평균선 |
| `alignment` | bullish / bearish / mixed |

## 연계 절차

1. recipes.technical.atrRegimeShift - 정렬과 변동성 체제 결합.
2. recipes.quant.momentumFactor - 12-1m return 정합.

## 기본 검증

- 거래일 < 130 이면 결론 X.
- 완전 정렬 비율 < 5% 이면 변별력 작음 — 한계.
- 단독 매수 결론 X — 거래량·펀더멘털 결합.
