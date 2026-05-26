---
id: recipes.technical.momentumFlowDivergence
title: 모멘텀 × 수급 다이버전스 (20 거래일)
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: 20 거래일 가격 일일 수익률과 외인+기관 순매수의 상관계수를 종목별로 산출해 모멘텀↔수급 동조/다이버전스 신호를 추출. 트리거 — '수급 다이버전스', '가격 수급 상관', 'momentum flow divergence'.
whenToUse:
  - 가격 모멘텀이 수급과 일치하는지 확인하고 싶을 때
  - breakout 직후 수급 confirmation 점검
  - 단기 entry 보조 신호로 수급 부합 여부 검증
  - 모멘텀 신호의 false positive 거르기
inputs:
  - stockCode (KR)
outputs:
  - tableRef (code · correlation · ret20 · flowSum · divergence · sampleN)
  - dateRef (마지막 거래일)
linkedSkills:
  - engines.gather
  - engines.quant
  - engines.company
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - tableRef
  - dateRef
  - executionRef
  - sourceRef
expectedNovelty:
  - priceFlowCorrelation
  - flowSign
  - divergence
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
    5 종목 모두 동일 부호 divergence (전부 +1 또는 전부 -1) 면 신호 변별력 없음. 또한
    sampleN < 10 (수급 데이터 충분치 못함) 인 종목이 절반 이상이면 본 윈도우는 무의미.
  pythonCheck: |
    signs = {r["divergence"] for r in result["table"]}
    insufficient = sum(1 for r in result["table"] if r.get("sampleN", 0) < 10)
    assert len(signs) >= 2, "divergence 가 모든 target 동일 — 변별력 0"
    assert insufficient < len(result["table"]) / 2, "sampleN < 10 종목이 과반"
failureModes:
  - flow 데이터 결측 종목 → sampleN < 10 → 상관계수 신뢰도 저하
  - 거래일 휴장 다수 포함 윈도우 → 20 거래일 미만으로 단축
  - 외인 1 회성 대규모 매매 → 상관계수 outlier
forbidden:
  - 단일 종목 correlation 만으로 매수/매도 단정 — 본 신호는 다른 펀더멘털·기술 신호와 결합
  - sampleN 미공개로 결과만 인용 (sampleN < 10 표시 강제)
  - 미국/일본 종목 입력 — gather flow KR 한정
examples:
  - "삼성전자 20일 가격 vs 수급 상관"
  - "SK 하이닉스 다이버전스 점검"
  - "모멘텀 신호 수급 confirmation"
lastUpdated: '2026-05-21'
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

code = "005930"
px = dartlab.gather("price", code)
flow = dartlab.gather("flow", code)

# 20 거래일 윈도우 — 21 일 받아 pct_change 1 row drop
px20 = (
    px.select(["date", "close"])
    .sort("date")
    .tail(21)
    .with_columns(pl.col("close").pct_change().alias("ret"))
    .drop_nulls()
    .with_columns(pl.col("date").cast(pl.Utf8))
)
flow20 = (
    flow.select(["date", "foreignNet", "institutionNet"])
    .sort("date")
    .tail(20)
    .with_columns((pl.col("foreignNet") + pl.col("institutionNet")).alias("netBuy"))
    .with_columns(pl.col("date").cast(pl.Utf8))
)
joined = px20.join(flow20, on="date", how="inner").sort("date")

n = joined.height
if n < 5:
    correlation = 0.0
    ret20 = 0.0
    flowSum = 0
else:
    rets = joined["ret"].to_list()
    flows = [float(x) for x in joined["netBuy"].to_list()]
    mean_r = sum(rets) / n
    mean_f = sum(flows) / n
    num = sum((r - mean_r) * (f - mean_f) for r, f in zip(rets, flows))
    den_r = (sum((r - mean_r) ** 2 for r in rets)) ** 0.5
    den_f = (sum((f - mean_f) ** 2 for f in flows)) ** 0.5
    correlation = num / (den_r * den_f) if den_r * den_f > 0 else 0.0
    ret20 = float(sum(rets))
    flowSum = int(sum(flows))

momentumSign = 1 if ret20 > 0 else -1
flowSign = 1 if flowSum > 0 else -1
divergence = momentumSign * flowSign  # +1 = 동조, -1 = 다이버전스

last_date = joined["date"].max() if n > 0 else None

emit_result(
    table=[{
        "code": code,
        "correlation": round(correlation, 4),
        "ret20": round(ret20, 4),
        "flowSum": flowSum,
        "momentumSign": momentumSign,
        "flowSign": flowSign,
        "divergence": divergence,
        "sampleN": n,
    }],
    date=last_date,
    headline={"metric": "correlation", "value": round(correlation, 4)},
)
```

## 호출 동작

1. `gather("price", code)` — OHLCV DataFrame (1년 기본).
2. `gather("flow", code)` — 외인/기관/개인 순매수 DataFrame (KR Naver).
3. 마지막 21 거래일 close → 20 일 일일 수익률 시계열.
4. 마지막 20 거래일 외인+기관 순매수 시계열.
5. date inner join → Pearson 상관계수.
6. 누적 수익률 부호 × 누적 순매수 부호 → divergence ∈ {+1, -1}.
7. `emit_result` headline=correlation (수치) → cross-target stability scoreboard 가능.

## 대표 반환 형태

- `tableRef` 1 개 — 종목별 1 row (correlation·ret20·flowSum·divergence·sampleN).
- `dateRef` 1 개 — 마지막 join 거래일.
- headline metric = `correlation` (Pearson).

## 연계 절차

1. `engines.gather` — price / flow 두 axis.
2. `engines.quant` — 같은 종목의 기술적 verdict 와 본 correlation 결합 시 false positive 거르기 효과.
3. `recipes.fundamental.disclosure.event` — 이벤트 근처 다이버전스 발현 여부 비교.

## 기본 검증

- sampleN ≥ 10 종목만 신호 채택. sampleN < 10 은 "데이터 부족" 표시.
- correlation 값은 [-1, +1]. |corr| < 0.10 = 무신호.
- divergence = -1 + |corr| > 0.30 동시일 때만 "강한 다이버전스" 표현.
- 펀더멘털 신호 (analysis) 와 함께 봐야 false positive 제거.

## 한계

- KR 만 지원 (`gather("flow")` 가 Naver KR 전용).
- 20 거래일 = 1 달 정도 — 더 긴 윈도우는 별 recipe.
- 외인+기관 합산 — 외인만 / 기관만 분리는 후속 변형.
