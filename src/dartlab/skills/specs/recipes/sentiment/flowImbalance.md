---
id: recipes.sentiment.flowImbalance
title: 외국인·기관·개인 순매수 imbalance z-score
category: recipes
kind: recipe
scope: builtin
status: drafted
graphTier: L1.5
cluster: sentiment
purpose: 일별 외국인·기관·개인 순매수 row 에서 imbalance (외인 - 기관 - 개인 또는 외인+기관 vs 개인) 시계열을 만들고 20 거래일 z-score 산출. 추론 라벨 (긍정/부정) 없이 *수급 비대칭* 정량만. gather L1 단일. 트리거 — '수급 imbalance', '외인 기관 z-score', 'flow sentiment'.
whenToUse:
  - 외인 기관 수급 비대칭
  - flow imbalance
  - 수급 z-score
  - 외인 매수 cluster
inputs:
  - flow rows
outputs:
  - flowImbalance table
capabilityRefs:
  - Company.gather
linkedSkills:
  - engines.gather
  - recipes.sentiment.shortBalanceMomentum
  - recipes.sentiment.insiderClusterTiming
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
visualRefs:
  - "engines.viz.tableBackedChart"
visualGuidance:
  - "표 기반 순위·추세는 engines.viz.tableBackedChart만 사용하고 tableRef/evidenceBinding이 없으면 차트 대신 검산 표로 낮춘다."
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
expectedOutputs:
  - 일별 외인·기관·개인 순매수 표
  - imbalance 시계열 + 20일 z-score
  - z ≥ 2 또는 ≤ -2 row 카운트
failureModes:
  - 거래일 수 < 30 인 신규 상장주에 z-score 적용
  - 외국인 순매수 / 보유율 변화 혼동 (둘은 다른 row)
  - 20 일 window 가 짧아 정기 IPO·MSCI 리밸런싱 노이즈
forbidden:
  - z-score 단일값으로 sentiment 라벨 (긍정/부정) 단정
  - 외인 순매수 단독으로 사건 결론
falsifier:
  description: "거래일 < 30 인데 결론 내거나, z-score 만으로 sentiment 라벨 붙이면 실패."
audiences:
  llm: c.gather("flow") 결과를 받아 imbalance 시계열 + 20 거래일 z-score 산출. 추론 라벨 X.
  agent: z ≥ 2 또는 ≤ -2 row 만 부각, 그 외는 정상 범위로 표기.
  human: 외인·기관·개인 *수급 비대칭* 자체가 정량 신호. 의미 해석은 별 절차.
humanIntro: "flowImbalance 는 sentiment 페르소나의 가장 기본 정량 신호다. 외국인이 사고 개인이 파는 패턴이 *과거 20 거래일 평균 대비* 얼마나 튀는지만 본다."
lastUpdated: "2026-05-22"
---

## 공개 호출 방식

```python
import dartlab
import polars as pl
import statistics

target = "005930"
c = dartlab.Company(target)

def rows(value, limit=120):
    if hasattr(value, "head") and hasattr(value, "to_dicts"):
        return value.head(limit).to_dicts()
    if isinstance(value, list):
        return value[:limit]
    return []

flow_rows = rows(c.gather("flow"), limit=120)

series = []
for r in flow_rows:
    f = float(r.get("foreignNet") or r.get("foreign_net") or 0)
    i = float(r.get("institutionNet") or r.get("inst_net") or 0)
    p = float(r.get("individualNet") or r.get("indiv_net") or 0)
    series.append({
        "date": r.get("date") or r.get("tradeDate"),
        "foreign": f,
        "inst": i,
        "indiv": p,
        "imbalance": (f + i) - p,
    })

series.sort(key=lambda x: str(x["date"] or ""))
imbal = [s["imbalance"] for s in series]
WINDOW = 20
for idx, s in enumerate(series):
    if idx < WINDOW:
        s["z"] = None
        continue
    window = imbal[idx-WINDOW:idx]
    mu = statistics.mean(window)
    sd = statistics.stdev(window) if len(window) > 1 else 0
    s["z"] = (s["imbalance"] - mu) / sd if sd > 0 else None

table = pl.DataFrame(series) if series else pl.DataFrame(
    schema={"date": pl.Utf8, "foreign": pl.Float64, "inst": pl.Float64,
            "indiv": pl.Float64, "imbalance": pl.Float64, "z": pl.Float64}
)

extreme_pos = int((table["z"].fill_null(0) >= 2).sum()) if table.height else 0
extreme_neg = int((table["z"].fill_null(0) <= -2).sum()) if table.height else 0

emit_result(
    table=table,
    values={"rows": table.height, "extremePos": extreme_pos, "extremeNeg": extreme_neg},
    date=str(table["date"].max()) if table.height else None,
    sources=["dartlab://gather/flow"],
)
```

## 호출 동작

일별 외국인·기관·개인 순매수 row 를 받아 imbalance = (외인 + 기관) − 개인 시계열 산출. 직전 20 거래일 rolling mean / stdev 로 z-score. z ≥ 2 또는 z ≤ -2 row 만 *비대칭 cluster 후보* 로 표시.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `date` | 거래일 |
| `foreign` | 외국인 순매수 |
| `inst` | 기관 순매수 |
| `indiv` | 개인 순매수 |
| `imbalance` | (외인+기관) − 개인 |
| `z` | 20 거래일 rolling z-score |

## 연계 절차

1. recipes.sentiment.shortBalanceMomentum - 공매도 잔고와 같이 보면 *매도 측 sentiment* 확인.
2. recipes.sentiment.insiderClusterTiming - imbalance 와 내부자 cluster 시점 비교.

## 기본 검증

- 거래일 < 30 이면 z-score 결론 X, *coverage 한계* 만 명시.
- z-score 단일값 → sentiment 라벨 변환 금지.
- MSCI 리밸런싱·IPO 록업 해제 등 *정기 이벤트* 와 겹친 row 는 한계로 분리.
