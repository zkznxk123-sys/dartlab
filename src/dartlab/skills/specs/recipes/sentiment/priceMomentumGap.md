---
id: recipes.sentiment.priceMomentumGap
title: 가격 모멘텀 갭 (5/20/60 일 변화율 격차)
category: recipes
kind: recipe
scope: builtin
status: tested
graphTier: L1.5
cluster: sentiment
purpose: 종가 시계열의 5·20·60 거래일 수익률 변화율 갭을 산출. 단기 (5d) - 중기 (60d) 갭이 양수면 *모멘텀 가속*, 음수면 *모멘텀 감속*. 추론 라벨 (강세/약세) 없이 정량 갭만. price gather 단일.
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

종가 70 거래일을 받아 5/20/60d 누적 수익률을 계산하고, 단기-중기 갭 (5d − 60d) 으로 가속/감속 phase 라벨링. 추론 X — 갭 자체만 정량 표기.

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
