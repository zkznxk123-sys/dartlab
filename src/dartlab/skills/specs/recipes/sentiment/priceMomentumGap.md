---
id: recipes.sentiment.priceMomentumGap
title: 가격 모멘텀 갭 (5/20/60 일 변화율 격차)
category: recipes
kind: recipe
scope: builtin
status: curated
graphTier: L1.5
cluster: sentiment
purpose: 종가 시계열의 5·20·60 거래일 수익률 변화율 갭을 산출. 단기 (5d) - 중기 (60d) 갭이 양수면 *모멘텀 가속*, 음수면 *모멘텀 감속*. 추론 라벨 (강세/약세) 없이 정량 갭만. price gather 단일. 트리거 — '가격 모멘텀 갭 (5/20/60 일 변화율 격차)', 'price momentum gap', 'priceMomentumGap'.
whenToUse:
  - 가격 모멘텀
  - momentum gap
  - 단기 중기 격차
  - price acceleration
examples:
  - 005930 단기 중기 모멘텀 격차 정량
  - 5일 20일 60일 수익률 갭 — 가속인가 감속인가
  - 가격 모멘텀 가속하는 종목
expectedOutputs:
  - 5d / 20d / 60d 수익률 단일값
  - 갭 (5d - 60d) 단일값 + 부호
  - 가속 / 감속 / 중립 라벨 (갭 부호 기반)
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
expectedNovelty:
  - priceMomentumGapTable
  - shortMidGapDiff
falsifier:
  description: "거래일 < 60 이면 60d 변화율 측정 불가 — 결론 X. 권리락·액면분할 같은 corporate action 후에는 raw price 갭이 의미 없으므로 한계 명시."
forbidden:
  - 가속/감속 갭 자체를 매수/매도 결정으로 단정 금지.
  - corporate action 보정 없이 raw 가격 갭으로 모멘텀 단정 금지.
failureModes:
  - 거래일 < 60 인 신규상장주는 60d 갭 계산 불가
  - 권리락/액면분할 직후는 가격 점프로 갭 오염
  - 한 종목 갭을 sector / 시장 갭과 비교 안 하면 의미 약함
lastUpdated: '2026-05-23'
validatedAt: '2026-05-27'
---

## 공개 호출 방식

```python
import dartlab
import polars as pl

target = "005930"
c = dartlab.Company(target)

try:
    price_df = c.gather("price").head(70)
    price_rows = price_df.to_dicts() if hasattr(price_df, "to_dicts") else []
except Exception:
    price_rows = []

# 오름차순 정렬 (날짜)
price_rows.sort(key=lambda r: str(r.get("date") or r.get("tradeDate") or ""))


def closeOf(r):
    for k in ("close", "closePrice", "adjClose"):
        v = r.get(k)
        if v is not None:
            try:
                return float(v)
            except Exception:
                continue
    return None


closes = [closeOf(r) for r in price_rows]
closes = [c for c in closes if c is not None and c > 0]


def window_chg(days):
    if len(closes) < days + 1:
        return None
    return (closes[-1] / closes[-days - 1]) - 1.0


c5, c20, c60 = window_chg(5), window_chg(20), window_chg(60)
short_mid_gap = (c5 - c60) if (c5 is not None and c60 is not None) else None

phase = "insufficient"
if short_mid_gap is not None:
    if short_mid_gap > 0.05:
        phase = "accelerating"
    elif short_mid_gap < -0.05:
        phase = "decelerating"
    else:
        phase = "steady"

latest_date = (
    str(price_rows[-1].get("date") or price_rows[-1].get("tradeDate"))
    if price_rows
    else None
)

table = pl.DataFrame(
    [
        {
            "ret5d": c5,
            "ret20d": c20,
            "ret60d": c60,
            "shortMidGap": short_mid_gap,
            "phase": phase,
            "tradingDaysAvailable": len(closes),
        }
    ]
)

emit_result(
    table=table,
    values={
        "shortMidGap": short_mid_gap,
        "phase": phase,
        "tradingDaysAvailable": len(closes),
    },
    date=latest_date,
    sources=["dartlab://gather/price"],
)
```

## 호출 동작

### 1. 결론 도출

5/20/60d 수익률 갭 phase 단정 (가속 / 감속 / 중립). 예: "5d +2.4% / 20d +5.1% / 60d +12.8% → 갭 (5d - 60d) = -10.4%p → 감속 phase (60d 강세 후 단기 둔화)."

### 2. 핵심 근거 수집

- 종가 70 거래일 (Company.gather('price'))
- ret5d = close[-1]/close[-6] - 1
- ret20d = close[-1]/close[-21] - 1
- ret60d = close[-1]/close[-61] - 1
- 갭 = ret5d - ret60d (또는 5d 일평균 - 60d 일평균)

### 3. 메커니즘 분석

```
종가 70 거래일 → 5/20/60d 누적 수익률 산출
   ↓
갭 = (5d/5 일평균) - (60d/60 일평균)
   > +0.5%p   → 가속 (단기 모멘텀 급격)
   ±0.5%p     → 중립
   < -0.5%p   → 감속 (장기 강세 후 단기 둔화 또는 reversal)
```

가속 = 단기 추세 강화. 감속 = 추세 둔화. 갭 큰 양수 + ret60d 양수 = momentum 가속. 갭 음수 + ret60d 양수 = reversal 신호.

### 4. 반례·한계

- 70 거래일 부족 종목 (신규 상장) 60d 측정 불가.
- 갭 단독 매수/매도 단정 금지 — 가격 시계열 + 거래량 동행 필요.
- 시장 전체 강세장에서는 모든 종목 가속 양수 — relative 비교 필요.
- 누적 수익률만 — 변동성 (Sharpe) 무시.

### 5. 후속 모니터링

- 가속 phase + 거래량 ↑: `recipes.technical.priceVolumeZScore` 로 거래량 동행 확인.
- 감속 phase + 60d 강세: reversal 후보 — `recipes.technical.rsiBollingerCluster` 로 overbought 확인.
- 갭 부호 빈번 전환: `recipes.technical.atrRegimeShift` 로 변동성 체제 확인.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `ret5d` | 5 거래일 누적 수익률 |
| `ret20d` | 20 거래일 누적 수익률 |
| `ret60d` | 60 거래일 누적 수익률 |
| `shortMidGap` | ret5d − ret60d |
| `phase` | accelerating / steady / decelerating / insufficient |

## 연계 절차

1. recipes.sentiment.foreignBuyMomentum — 가격 갭과 외인 가속도 두 축 동시 확인.
2. recipes.sentiment.flowImbalance — 갭 위쪽 phase 에서 수급 imbalance 점검.

## 기본 검증

- 거래일 < 60 이면 갭 결론 X — phase=insufficient.
- 권리락·액면분할 직후 row 는 한계 명시.
- 단일 종목 갭을 단독 sentiment 결론으로 사용 금지 — sector / 시장 비교 권장.
