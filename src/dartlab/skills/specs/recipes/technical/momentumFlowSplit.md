---
id: recipes.technical.momentumFlowSplit
title: 모멘텀 × 수급 주체별 분리 + multi-window
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: momentumFlowDivergence (1 호) 의 정보 손실 한계 보강 — 외인+기관 합산 대신 외인·기관·개인 3 주체 분리 + 10/20/60 거래일 multi-window 동시 산출. 주체별 행동 분기 + window별 정합성 차이 모두 가시화. 트리거 — '주체별 수급 corr', 'multi-window flow divergence', '외인 vs 기관 의견 분기'.
whenToUse:
  - 외인과 기관 행동이 다른지 확인
  - 단기 (10 일) vs 중기 (60 일) 수급 정합 차이 점검
  - 개인 매수 주도 vs 기관 매수 주도 종목 분리
inputs:
  - stockCode (KR)
outputs:
  - tableRef (window × {code · corrForeign · corrInst · corrIndiv · sampleN})
  - dateRef (마지막 거래일)
linkedSkills:
  - engines.gather
  - recipes.technical.momentumFlowDivergence
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - tableRef
  - dateRef
expectedNovelty:
  - corrForeign
  - corrInst
  - corrIndiv
  - spreadForeignInst
testUniverse:
  stockCodes:
    - "005930"
    - "000660"
    - "035420"
    - "051910"
    - "207940"
  market: KR
falsifier:
  description: |
    20 일 윈도우에서 corrForeign 과 corrInst 의 차이 (spread) 가 5 종목 모두
    0.05 미만이면 외인/기관 분리 의미 없음 — 합산 (1 호 recipe) 으로 충분.
    또한 3 window (10/20/60) 모두 corrForeign 부호 동일 종목이 5 개 모두면
    multi-window 의미 없음 — 단일 window 로 충분.
  pythonCheck: |
    # 20 일 윈도우만 추출
    rows20 = [r for r in result["table"] if r.get("window") == 20]
    spreads = [abs(r.get("corrForeign", 0) - r.get("corrInst", 0)) for r in rows20]
    flat_spread = all(s < 0.05 for s in spreads)
    assert not flat_spread, "외인-기관 spread 모두 0.05 미만 — 주체 분리 무의미"
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
    limitations:
      - Naver flow API CORS
failureModes:
  - 저유동 종목 sampleN < 10 → corr 노이즈
  - 외인 1 회성 대규모 거래로 corr outlier
  - 60 일 윈도우는 fiscal 사건 (배당락·분할) 포함 가능 — 보정 안 함
forbidden:
  - 3 주체 corr 중 하나만 인용 (필히 3 종 동시 표시)
  - sampleN < 10 결과 silent 인용
  - 미국/일본 종목 입력
examples:
  - "삼성전자 외인 vs 기관 의견 분기"
  - "10일/20일/60일 수급 정합 차이"
  - "주체별 corr"
lastUpdated: '2026-05-21'
---

## 공개 호출 방식

```python
import dartlab
import polars as pl

code = "005930"
px = dartlab.gather("price", code)
flow = dartlab.gather("flow", code)

px_sorted = (
    px.sort("date")
    .select(["date", "close"])
    .with_columns(pl.col("date").cast(pl.Utf8))
)
flow_sorted = (
    flow.sort("date")
    .select(["date", "foreignNet", "institutionNet", "individualNet"])
    .with_columns(pl.col("date").cast(pl.Utf8))
)

def pearson(xs, ys):
    n = len(xs)
    if n < 5:
        return 0.0
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den_x = (sum((x - mean_x) ** 2 for x in xs)) ** 0.5
    den_y = (sum((y - mean_y) ** 2 for y in ys)) ** 0.5
    if den_x * den_y == 0:
        return 0.0
    return num / (den_x * den_y)

def compute_window(window: int) -> dict:
    px_win = (
        px_sorted.tail(window + 1)
        .with_columns(pl.col("close").pct_change().alias("ret"))
        .drop_nulls()
    )
    flow_win = flow_sorted.tail(window)
    joined = px_win.join(flow_win, on="date", how="inner").sort("date")
    n = joined.height
    if n < 5:
        return {
            "window": window,
            "corrForeign": 0.0,
            "corrInst": 0.0,
            "corrIndiv": 0.0,
            "sampleN": n,
        }
    rets = [float(x) for x in joined["ret"].to_list()]
    foreign = [float(x) for x in joined["foreignNet"].to_list()]
    inst = [float(x) for x in joined["institutionNet"].to_list()]
    indiv = [float(x) for x in joined["individualNet"].to_list()]
    return {
        "window": window,
        "corrForeign": round(pearson(rets, foreign), 4),
        "corrInst": round(pearson(rets, inst), 4),
        "corrIndiv": round(pearson(rets, indiv), 4),
        "sampleN": n,
    }

rows = []
for w in (10, 20, 60):
    r = compute_window(w)
    rows.append({"code": code, **r})

# 20 일 윈도우 spread 를 headline 으로 — 외인/기관 의견 분기 크기
r20 = next((r for r in rows if r["window"] == 20), rows[0])
spread = abs(r20["corrForeign"] - r20["corrInst"])

emit_result(
    table=rows,
    date=str(px_sorted["date"].max()),
    headline={"metric": "spreadForeignInst20d", "value": round(spread, 4)},
)
```

## 호출 동작

1. `gather("price", code)` — OHLCV (1 년).
2. `gather("flow", code)` — 외인/기관/개인 일별 순매수 (KR).
3. date inner join 후 10/20/60 거래일 각 윈도우에서 외인·기관·개인 3 주체 corr 산출.
4. headline = 20 일 윈도우의 |corrForeign - corrInst| = spread.

## 대표 반환 형태

- `tableRef` — 3 row (window 10/20/60), 컬럼 code · corrForeign · corrInst · corrIndiv · sampleN.
- `dateRef` — 마지막 join 거래일.

## 연계 절차

1. `engines.gather` — `gather("price", code)` OHLCV.
2. `engines.gather` — `gather("flow", code)` 외인/기관/개인 일별 순매수.
3. `runPython` — 윈도우 (10/20/60) × 주체 (외인/기관/개인) 9 corr + spread 인라인 산출.
4. `recipes.technical.momentumFlowDivergence` — 1 호 합산 신호와 본 분리 신호 동시 비교.
5. `recipes.technical.quantTechnicalReview` — 같은 종목 기술적 verdict 결합.

## 기본 검증

- spread20d ≥ 0.5 + 부호 반대 (corrForeign × corrInst < 0) 동시일 때만 "외인 ↔ 기관 명확한 의견 분기" 표현.
- 3 윈도우 corr 가 모두 같은 부호 + 값 차이 < 0.1 이면 "안정적 정합" — 단일 윈도우 동일 결론.
- 1 호 (`momentumFlowDivergence`) 와 함께 보면 합산 정보 (corrTotal) 와 분리 정보 (corrForeign/Inst/Indiv) 가 동시 가시화.

## 한계

- KR 만 (`gather("flow")` Naver 한정).
- 외인/기관/개인 분류는 Naver 기준 — institutional sub-class (사모/연기금/은행) 미세분.
- 윈도우 3 종 default — 사용자 정의 윈도우는 별 recipe.
