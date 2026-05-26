---
id: recipes.sentiment.foreignBuyMomentum
title: 외국인 누적 순매수 모멘텀 (5/20/60 일 가속도)
category: recipes
kind: recipe
scope: builtin
status: tested
purpose: 외국인 누적 순매수의 5/20/60 거래일 변화율 비교. 가속도 (5d 대비 60d 상대 기울기) 가 양수면 *가속*, 음수면 *감속*. 절대 보유 비율이 아닌 *flow 가속도* 측정.
whenToUse:
  - 외국인 매매 모멘텀
  - foreign buy acceleration
  - 외인 누적 순매수
  - flow 가속도
examples:
  - 005930 외인 매수 가속하고 있나
  - 외국인 누적 순매수 5/20/60일 가속도 신호
  - 외인 flow 가속 종목 (감속 종목)
expectedOutputs:
  - 5d / 20d / 60d 외인 누적 순매수 변화율 단일값 + 가속도 (5d/60d 기울기 비)
  - 가속 / 감속 / 중립 라벨 (가속도 부호)
  - 외인 누적 순매수 시계열 표 (60d window)
linkedSkills:
  - engines.company
  - engines.gather
  - recipes.sentiment.flowImbalance
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
    - synth
testUniverse:
  market: KR
  stockCodes:
    - "005930"
    - "000660"
falsifier:
  description: "거래일 < 60 이면 60d 변화 측정 불가. 대형 indexing 이벤트 (MSCI 리밸런싱) 가 가속도 noise."
lastUpdated: "2026-05-22"
---

## 공개 호출 방식

```python
import dartlab
import polars as pl

target = "005930"
c = dartlab.Company(target)

try:
    flow = c.gather("flow").head(70).to_dicts()
except Exception:
    flow = []
flow.sort(key=lambda r: str(r.get("date") or r.get("tradeDate")))

foreign = [float(r.get("foreignNet") or 0) for r in flow]

def cumsum(arr):
    s = 0
    out = []
    for v in arr:
        s += v
        out.append(s)
    return out

cum = cumsum(foreign)
n = len(cum)

def window_chg(days):
    if n < days + 1: return None
    return cum[-1] - cum[-days-1]

c5, c20, c60 = window_chg(5), window_chg(20), window_chg(60)
# 가속도: 5일 평균 / 60일 평균 = (c5/5) / (c60/60) - 1
accel = None
if c5 is not None and c60 is not None and c60 != 0:
    rate5 = c5 / 5
    rate60 = c60 / 60
    if rate60 != 0:
        accel = (rate5 / rate60) - 1

table = pl.DataFrame([{
    "cumForeign5d": c5,
    "cumForeign20d": c20,
    "cumForeign60d": c60,
    "rate5dPerDay": (c5 / 5) if c5 is not None else None,
    "rate60dPerDay": (c60 / 60) if c60 is not None else None,
    "acceleration": accel,
    "phase": "accelerating" if (accel is not None and accel > 0.2) else "decelerating" if (accel is not None and accel < -0.2) else "steady",
}])

emit_result(
    table=table,
    values={"acceleration": accel, "phase": table["phase"][0] if table.height else None},
    date=str(flow[-1].get("date") or flow[-1].get("tradeDate")) if flow else None,
    sources=["dartlab://gather/flow"],
)
```

## 호출 동작

외국인 일별 순매수 누적 → 5/20/60 일 변화. 가속도 = (5일 일평균 / 60일 일평균) - 1. > 0.2 = 가속, < -0.2 = 감속, 그 외 = steady.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `cumForeign5d` | 직전 5 일 외인 순매수 |
| `cumForeign60d` | 직전 60 일 외인 순매수 |
| `acceleration` | 일평균 비율 변화 |
| `phase` | accelerating / decelerating / steady |

## 연계 절차

1. recipes.sentiment.flowImbalance - 가속도 + imbalance 결합.
2. recipes.sentiment.retailFlowReversal - 외인 가속 vs 개인 반전 동시 확인.

## 기본 검증

- 거래일 < 60 이면 결론 X.
- MSCI 리밸런싱 / 대형 indexing 이벤트 시점은 한계 명시.
- 가속도 단독 매수 결론 X — 가격·수급과 결합.
