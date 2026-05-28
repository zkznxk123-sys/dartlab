---
id: recipes.technical.atrRegimeShift
title: ATR 변동성 체제 전환 (단기 vs 장기 ATR ratio)
category: recipes
kind: recipe
scope: builtin
status: curated
purpose: ATR(5) vs ATR(60) ratio 의 z-score. > +1.5σ = 변동성 확대 체제, < -1.5σ = 수축 체제. 단일 변동성 절대값이 아닌 *체제 전환* 추적. 트리거 — 'ATR 변동성 체제 전환 (단기 vs 장기 ATR ratio)', 'atr regime shift', 'atrRegimeShift'.
whenToUse:
  - 변동성 체제 전환
  - ATR ratio z
  - vol regime shift
  - 단기 vs 장기 변동성
examples:
  - 005930 변동성 체제 확대 / 수축 신호
  - ATR(5) / ATR(60) ratio z-score
  - 단기 vol 폭증 종목
expectedOutputs:
  - ATR(5) + ATR(60) + ratio + z-score 단일값
  - 체제 라벨 (확대 / 수축 / 평상 — z 임계 ±1.5σ)
  - 시계열 chart (ratio z-score 6mo window)
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
  description: "거래일 < 80 이면 ATR(60) 결론 X. 시장 전체 변동성 (KOSPI VKOSPI) 동시 확대 시 회사별 신호 분리 어려움."
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
    px = dartlab.gather("price", target).head(100).to_dicts()
except Exception:
    px = []
px.sort(key=lambda r: str(r.get("date") or r.get("tradeDate")))
ohlc = [(float(r.get("high") or 0), float(r.get("low") or 0), float(r.get("close") or 0))
        for r in px if r.get("close")]

def true_ranges(start, end):
    trs = []
    prev_close = ohlc[start-1][2] if start > 0 else None
    for i in range(start, end):
        h, l, c = ohlc[i]
        if prev_close is None:
            tr = h - l
        else:
            tr = max(h - l, abs(h - prev_close), abs(l - prev_close))
        trs.append(tr)
        prev_close = c
    return trs

if len(ohlc) < 80:
    table = pl.DataFrame(schema={"atr5": pl.Float64, "atr60": pl.Float64, "ratio": pl.Float64, "regime": pl.Utf8})
else:
    end = len(ohlc)
    atr5 = statistics.mean(true_ranges(end-5, end))
    atr60 = statistics.mean(true_ranges(end-60, end))
    ratio = atr5 / atr60 if atr60 > 0 else None
    # baseline of ratio z-score from rolling history
    ratios = []
    for i in range(60, end):
        sub5 = true_ranges(i-5, i)
        sub60 = true_ranges(i-60, i)
        if statistics.mean(sub60) > 0:
            ratios.append(statistics.mean(sub5) / statistics.mean(sub60))
    if len(ratios) > 5:
        mu, sd = statistics.mean(ratios[:-1]), statistics.stdev(ratios[:-1])
        z = (ratio - mu) / sd if sd > 0 else None
    else:
        z = None
    regime = "expand" if (z is not None and z >= 1.5) else "contract" if (z is not None and z <= -1.5) else "steady"
    table = pl.DataFrame([{"atr5": atr5, "atr60": atr60, "ratio": ratio, "ratioZ": z, "regime": regime}])

emit_result(
    table=table,
    values={"regime": table["regime"][0] if table.height else None,
            "ratioZ": float(table["ratioZ"][0]) if table.height and table["ratioZ"][0] is not None else None},
    date=str(px[-1].get("date") or px[-1].get("tradeDate")) if px else None,
    sources=["dartlab://gather/price"],
)
```

## 호출 동작

### 1. 결론 도출

ATR ratio + z + regime 단정. 예: "ATR(5)=1,820 / ATR(60)=950 → ratio=1.92 (단기 변동성 평년 대비 1.9배). 60일 baseline mean=1.05 / std=0.45 → z=+1.93 → regime=expand (단기 변동성 확대 phase, 평년 대비 +1.93σ)."

### 2. 핵심 근거 수집

- gather('price', target) latest 100 row OHLC
- True Range = max(high-low, |high-prevClose|, |low-prevClose|)
- ATR(5) = mean(TR latest 5), ATR(60) = mean(TR latest 60)
- ratio = ATR(5) / ATR(60), baseline 60일 rolling z-score

### 3. 메커니즘 분석

```
OHLC 100 row → True Range 계산
   TR[i] = max(high-low, |high-prevClose|, |low-prevClose|)
   ↓
ATR(N) = mean(TR latest N)
   ATR(5)  → 단기 변동성 (최근 1주)
   ATR(60) → 장기 변동성 (3개월)
   ratio = ATR(5) / ATR(60)
   ↓
rolling z-score (60일 baseline):
   각 시점 i → ratio[i] 계산
   mean(ratio 60일 history) + std → ratio[t] z
   ↓
regime 판정:
   z ≥ +1.5 → expand (단기 변동성 평년 대비 가속)
   |z| < 1.5 → steady (정상)
   z ≤ -1.5 → contract (단기 변동성 수축, 정체 phase)
   ↓
체제 전환 신호:
   expand 진입 → 이벤트 driven 변동성 가속 (catalysts watch)
   contract 진입 → 정체 / consolidation phase
   체제 전환 빈번 → 변동성 cycle 짧음 (KOSPI 일반 패턴)
```

ATR ratio 는 *상대 변동성* — 절대값 아님. 단순 ATR 절대값 비교 시 시기별 levels 다름 (cross-time 비교 무의미). ratio + z 는 시기 정규화.

### 4. 반례·한계

- 거래일 < 80 → ATR(60) 결론 X.
- 시장 전체 변동성 (VKOSPI) 동시 확대 시 회사별 신호 분리 어려움.
- regime 변경 단독 매수 결론 X — *체제 변화* 사실만.
- 60일 baseline 짧음 — 큰 regime shift 시 후행.

### 5. 후속 모니터링

- expand 진입 → `recipes.news.eventVolatilityCheck` 로 이벤트 induced 변동성 비교.
- contract 지속 → `recipes.quant.lowVolFactor` 로 변동성 팩터 정합.
- regime 빈번 전환 → `recipes.technical.priceVolumeZScore` 로 거래량 burst event 점검.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `atr5` / `atr60` | 단기/장기 ATR |
| `ratio` | atr5 / atr60 |
| `ratioZ` | rolling z-score |
| `regime` | expand / contract / steady |

## 연계 절차

1. recipes.news.eventVolatilityCheck - 이벤트 induced 변동성과 비교.
2. recipes.quant.lowVolFactor - 변동성 팩터 신호 정합.

## 기본 검증

- 거래일 < 80 이면 결론 X.
- 시장 변동성 동시 확대 시 회사별 신호 분리 어려움.
- regime 변경 단독 매수 결론 X — *변동성 체제 변화* 자체가 사실.
