---
id: recipes.technical.priceVolumeZScore
title: 거래량 z-score + 가격 변화율 동조 신호
category: recipes
kind: recipe
scope: builtin
status: curated
graphTier: L1.5
cluster: technical
purpose: 일별 종가 변화율과 거래량 20 거래일 z-score 의 동조 점검. 거래량 z ≥ 2 인 row 가 양수/음수 수익률 어느 쪽으로 쏠리는지 정량 카운트. 추론 라벨 없이 *event row 비율* 만. price gather 단일.
whenToUse:
  - 거래량 폭증
  - volume z-score
  - 가격 거래량 동조
  - high-volume day
examples:
  - 005930 거래량 폭증 + 가격 동조 신호
  - 거래량 z ≥ 2 row 가 양수 / 음수 수익률 쏠림
  - high-volume day 가격 방향 정량
expectedOutputs:
  - 거래량 z ≥ 2 row 수 + 양수 / 음수 카운트 분리
  - 양수 비율 단일값 (rising 측 쏠림 정도)
  - 가장 큰 z + 그날 수익률 (event highlight)
linkedSkills:
  - engines.gather
  - recipes.sentiment.priceMomentumGap
  - recipes.technical.atrRegimeShift
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
  - highVolumeBalance
  - volReturnSkew
falsifier:
  description: "거래일 < 30 이면 20d 윈도우 z 신뢰도 낮음 — 결론 X. 액면분할·권리락 직후 거래량 점프를 z 폭증으로 처리하면 실패."
forbidden:
  - 거래량 z ≥ 2 row 단독으로 추세전환 단정 금지
  - 액면분할·corporate action 보정 없이 z 폭증 단정 금지
failureModes:
  - 거래일 < 30 (윈도우 부족)
  - 액면분할·권리락 같은 corporate action 후 점프
  - 시간외 거래 거래량 포함 여부 불명
lastUpdated: '2026-05-23'
validatedAt: '2026-05-27'
---

## 공개 호출 방식

```python
import dartlab
import polars as pl
import statistics

target = "005930"
c = dartlab.Company(target)

try:
    df = c.gather("price").head(80)
    rows = df.to_dicts() if hasattr(df, "to_dicts") else []
except Exception:
    rows = []

rows.sort(key=lambda r: str(r.get("date") or r.get("tradeDate") or ""))


def floatOr(v):
    try:
        return float(v) if v is not None else None
    except Exception:
        return None


parsed = []
prev_close = None
for r in rows:
    close = floatOr(r.get("close") or r.get("closePrice") or r.get("adjClose"))
    vol = floatOr(r.get("volume") or r.get("tradeVolume") or r.get("vol"))
    if close is None or vol is None:
        continue
    ret = None
    if prev_close and prev_close > 0:
        ret = (close / prev_close) - 1.0
    parsed.append(
        {
            "date": str(r.get("date") or r.get("tradeDate")),
            "close": close,
            "volume": vol,
            "ret": ret,
        }
    )
    prev_close = close

WINDOW = 20
event_pos = 0
event_neg = 0
events = []
for i, r in enumerate(parsed):
    if i < WINDOW:
        continue
    win = [parsed[j]["volume"] for j in range(i - WINDOW, i)]
    mu = statistics.mean(win)
    sd = statistics.stdev(win) if len(win) > 1 else 0
    z = (r["volume"] - mu) / sd if sd > 0 else None
    if z is None:
        continue
    if z >= 2:
        events.append({"date": r["date"], "z": round(z, 2), "ret": r["ret"]})
        if r["ret"] is not None:
            if r["ret"] > 0:
                event_pos += 1
            elif r["ret"] < 0:
                event_neg += 1

table = pl.DataFrame(events) if events else pl.DataFrame(
    schema={"date": pl.Utf8, "z": pl.Float64, "ret": pl.Float64}
)

n_events = len(events)
skew = None
if n_events > 0:
    skew = round((event_pos - event_neg) / n_events, 3)

latest_date = parsed[-1]["date"] if parsed else None

emit_result(
    table=table,
    values={
        "tradingDays": len(parsed),
        "events": n_events,
        "eventPos": event_pos,
        "eventNeg": event_neg,
        "posNegSkew": skew,
    },
    date=latest_date,
    sources=["dartlab://gather/price"],
)
```

## 호출 동작

### 1. 결론 도출

거래량 폭증 event row + 가격 방향 skew 단정. 예: "최근 80거래일 z≥2 event row 12 건 (양수 8 / 음수 4) → skew +0.33 (rising 측 쏠림) — 매수 거래량 우세."

### 2. 핵심 근거 수집

- 가격·거래량 80거래일 row (Company.gather('price'))
- 일별 수익률 (close/prev_close - 1)
- 20거래일 rolling 거래량 z-score = (volume - rolling_mean) / rolling_std

### 3. 메커니즘 분석

```
80거래일 close + volume 시계열
   ↓
일별 수익률 = close[t] / close[t-1] - 1
20일 rolling volume z = (volume[t] - mean_20d) / std_20d
   ↓
z ≥ 2 인 row 만 event row 추출 (거래량 폭증)
   ↓
event row 의 수익률 부호 카운트
   posCount = (return > 0) 카운트
   negCount = (return < 0) 카운트
   skew = (posCount - negCount) / total
   skew > +0.3   → rising-side dominant (상승 거래량 우세)
   ±0.3          → 양방향 (혼재)
   skew < -0.3   → falling-side dominant (하락 거래량 우세)
```

거래량 z ≥ 2 + 수익률 큼 = capitulation 또는 breakout 후보. event row 수 ↑ + skew 절대값 ↑ = 신호 강도 ↑.

### 4. 반례·한계

- 지수 동시 변동일 (장 전체 폭증) 의 event row 종목 고유 신호 X.
- 신규 상장 종목 (volume 변동성 큼) z-score 정의 불안정.
- 호가 단위 변경·액면분할 직후 거래량 시계열 break.
- 80일 단기 표본 — 변동성 regime shift 안 잡힘.

### 5. 후속 모니터링

- skew > +0.5 + event row 다수: `recipes.sentiment.foreignBuyMomentum` 으로 외인 매수 동행 확인.
- skew < -0.5: `recipes.sentiment.retailFlowReversal` 로 capitulation 가능성 확인.
- event row 시점 ±공시: `recipes.fundamental.disclosure.eventRadar.priceFlowReaction` 으로 이벤트 동행 검증.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `date` | event row 일자 |
| `z` | 거래량 z-score (≥ 2) |
| `ret` | 당일 수익률 |

values:
- `events` — z ≥ 2 row 총 수
- `eventPos` / `eventNeg` — 양/음 수익률 row 수
- `posNegSkew` — (pos − neg) / events

## 연계 절차

1. recipes.sentiment.priceMomentumGap — event row 시점이 가속 phase 와 겹치는지.
2. recipes.technical.atrRegimeShift — 거래량 z 와 ATR 변동성 regime 동시 확인.

## 기본 검증

- 거래일 < 30 → 결론 X.
- 액면분할 직후는 거래량 점프로 z 오염 — 한계 표기.
- skew 부호로 sentiment 라벨 단정 금지.
