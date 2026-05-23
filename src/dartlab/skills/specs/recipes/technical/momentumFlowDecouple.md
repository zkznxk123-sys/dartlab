---
id: recipes.technical.momentumFlowDecouple
title: 모멘텀-수급 동조 와해 (momentumFlowSplit v2 변형)
category: recipes
kind: recipe
scope: builtin
status: tested
purpose: momentumFlowSplit 의 spread bimodal 실패 (std 임계 0.50 미세 초과) 보강. v2 는 *spread 자체* 가 아닌 *상관계수의 시점간 변화* — 직전 60 거래일 가격×수급 상관 vs 최근 20 거래일 상관 = 동조성 와해 정도 (correlation drop). spread bimodal 회피. 트리거 — '동조 와해', 'momentum flow decouple', 'correlation drop'.
whenToUse:
  - 모멘텀 수급 와해
  - correlation drop
  - 가격 수급 decouple
  - 단기 추세 신뢰도 점검
linkedSkills:
  - engines.gather
  - engines.quant
  - recipes.technical.momentumFlowDivergence
  - recipes.technical.momentumFlowSplit
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - tableRef
  - dateRef
  - sourceRef
  - executionRef
expectedOutputs:
  - 종목별 corr60 (이전 60일) + corr20 (최근 20일) + decouple = corr60 - corr20
  - 5 종목 단면 std (변별력 신호)
gap:
  primary:
    - gather
    - quant
testUniverse:
  market: KR
  stockCodes:
    - "005930"
    - "000660"
    - "035420"
    - "051910"
    - "207940"
falsifier:
  description: |
    5 종목 decouple 단면 std ≤ 0.20 이면 변별력 0. v1 (spread bimodal) 실패 모드 그대로
    재현된 신호. 또한 corr60 / corr20 둘 다 |값| < 0.1 인 종목이 절반 이상이면 본 신호는
    sample 안에서 *상관 자체가 없는* 상황.
  pythonCheck: |
    decouples = [r["decouple"] for r in result["table"] if r["decouple"] is not None]
    import statistics
    assert len(decouples) >= 3 and statistics.stdev(decouples) > 0.20, "decouple 단면 std ≤ 0.20 — v1 실패 모드 그대로"
failureModes:
  - 60 거래일 / 20 거래일 표본이 휴장 다수로 단축
  - flow 결측 종목 → corr 산출 불가
  - 외인 1 회성 대규모 매매 outlier 가 corr60 왜곡
forbidden:
  - decouple 단일값으로 매수/매도 단정
  - corr 부호 미공개로 결과만 인용
examples:
  - 005930 60일 vs 20일 상관 와해
  - 5 종목 correlation drop 단면
lastUpdated: "2026-05-22"
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
visualRefs:
  - "engines.viz.tableBackedChart"
---

## 공개 호출 방식

```python
import dartlab
import polars as pl
import statistics

codes = ["005930", "000660", "035420", "051910", "207940"]

def pearson(a, b):
    if len(a) < 5 or len(a) != len(b):
        return None
    ma, mb = statistics.mean(a), statistics.mean(b)
    num = sum((x-ma)*(y-mb) for x, y in zip(a, b))
    da = sum((x-ma)**2 for x in a) ** 0.5
    db = sum((y-mb)**2 for y in b) ** 0.5
    return num / (da*db) if da*db else None

rows = []
for code in codes:
    try:
        px = dartlab.gather("price", code).head(80).to_dicts()
        fl = dartlab.gather("flow", code).head(80).to_dicts()
    except Exception:
        px, fl = [], []
    if not px or not fl:
        rows.append({"code": code, "corr60": None, "corr20": None, "decouple": None, "sampleN": 0})
        continue
    px.sort(key=lambda r: str(r.get("date") or r.get("tradeDate")))
    fl.sort(key=lambda r: str(r.get("date") or r.get("tradeDate")))
    flow_by_date = {str(r.get("date") or r.get("tradeDate"))[:10]: (
        float(r.get("foreignNet") or 0) + float(r.get("institutionNet") or 0)
    ) for r in fl}
    closes = []
    flows = []
    prev_close = None
    for p in px:
        d = str(p.get("date") or p.get("tradeDate"))[:10]
        close = float(p.get("close") or p.get("closePrice") or 0)
        if prev_close and prev_close > 0 and d in flow_by_date:
            closes.append((close / prev_close) - 1)
            flows.append(flow_by_date[d])
        prev_close = close
    if len(closes) < 60:
        rows.append({"code": code, "corr60": None, "corr20": None, "decouple": None, "sampleN": len(closes)})
        continue
    corr60 = pearson(closes[-60:-20], flows[-60:-20])
    corr20 = pearson(closes[-20:], flows[-20:])
    decouple = (corr60 - corr20) if (corr60 is not None and corr20 is not None) else None
    rows.append({
        "code": code,
        "corr60": corr60,
        "corr20": corr20,
        "decouple": decouple,
        "sampleN": len(closes),
    })

table = pl.DataFrame(rows)
decouples = [v for v in table["decouple"].to_list() if v is not None]
crossSectionStd = statistics.stdev(decouples) if len(decouples) >= 3 else None

emit_result(
    table=table,
    values={"universe": len(codes), "crossSectionStd": crossSectionStd},
    date=None,
    sources=["dartlab://gather/price", "dartlab://gather/flow"],
)
```

## 호출 동작

종목별 직전 60 거래일 (단, 최근 20 일 제외) 가격 일변동률 vs 수급 (외인+기관 순매수) Pearson 상관 `corr60` + 최근 20 거래일 상관 `corr20` 산출. `decouple = corr60 - corr20` 가 양수 (상관 와해) / 음수 (상관 강화). 5 종목 단면 std 가 0.20 이상이면 변별력 통과.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `code` | 종목코드 |
| `corr60` | 이전 60 거래일 (최근 20일 제외) 가격-수급 Pearson |
| `corr20` | 최근 20 거래일 가격-수급 Pearson |
| `decouple` | corr60 - corr20 |
| `sampleN` | join 성공 표본 수 |

## 연계 절차

1. recipes.technical.momentumFlowDivergence - 직접 corr 만 (v1 차분 없이).
2. recipes.technical.momentumFlowSplit - v1 spread 와 비교.
3. recipes.sentiment.flowImbalance - 와해 시점 수급 imbalance 확인.

## 기본 검증

- sampleN < 60 인 종목은 corr60 결론 X.
- corr60 / corr20 둘 다 |값| < 0.1 이면 상관 자체가 없는 상황 — decouple 신호도 의미 없음.
- decouple 단일값 → 매수/매도 라벨 변환 금지.
