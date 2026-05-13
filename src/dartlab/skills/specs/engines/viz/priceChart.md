---
id: engines.viz.priceChart
title: Viz - 주가차트
kind: curated
scope: builtin
status: observed
category: engines
purpose: OHLCV 가격 시계열을 `price-chart` ChartSpec 으로 변환해 Svelte ChartRenderer 에서 캔들·종가선·거래량·이동평균·벤치마크를 함께 그리는 시각화 실행 스킬이다.
whenToUse:
  - 주가차트
  - price chart
  - candlestick
  - 캔들차트
  - OHLCV
  - 거래량 차트
  - 이동평균선
  - 시장 대비 주가
inputs:
  - 종목코드 또는 ticker
  - market (KR / US)
  - start / end 기간
  - 선택 벤치마크 KOSPI / KOSDAQ / KOSPI200 / S&P500
outputs:
  - chartType price-chart ChartSpec
  - data rows (date/open/high/low/close/volume)
  - overlays (ma20/ma60 등)
  - evidenceBinding
toolRefs:
  - RunPython
  - CompileVisual
knowledgeRefs:
  - engines.viz
  - engines.gather.price
  - engines.gather.flow
  - engines.quant.momentum
  - engines.quant.chartPatterns
sourceRefs:
  - dartlab://skills/engines.viz.priceChart
requiredEvidence:
  - target
  - period
  - latestAsOf
  - provider
  - evidenceBinding
  - executionRef
expectedOutputs:
  - price-chart spec
  - 주가 추세와 거래량 설명
  - 벤치마크 대비 상대 성과
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: supported
  pyodide:
    status: limited
    limitations:
      - 브라우저에서는 사전 제공된 HF 가격 parquet 또는 landing priceRuntime 이 노출한 row 범위만 사용한다.
failureModes:
  - 수정주가와 raw 가격을 섞어 수익률을 계산함
  - 휴장일을 최신 거래일로 착각함
  - 가격 차트를 투자 권고 신호로 단정함
  - 벤치마크를 같은 기간으로 정렬하지 않고 상대 성과를 그림
  - 거래량 없는 close-only 데이터에 캔들 차트를 강제함
forbidden:
  - 가격 row 없이 임의 캔들 생성 금지
  - evidenceBinding 또는 evidenceIds 없는 차트 emit 금지
  - 최신 종가를 말할 때 기준 거래일 누락 금지
  - 캔들 패턴만으로 매수/매도 판단 금지
examples:
  - 삼성전자 1년 주가와 거래량
  - AAPL 주가와 MA20/MA60
  - 종목 주가와 KOSPI200 상대 성과
  - 공시 이벤트와 주가 반응
linkedSkills:
  - engines.viz
  - engines.gather.price
  - engines.gather.flow
  - engines.quant.momentum
  - engines.quant.chartPatterns
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-13'
---

## 엔진 역할

`engines.viz.priceChart` 는 가격 원자료를 일반 line chart 로 뭉개지 않고 주가 분석에 맞는 시각화 계약으로 바꾼다. `price-chart` 는 같은 spec 안에 OHLCV row, 종가 series, 이동평균, 거래량, 벤치마크 상대지수, 이벤트 마커를 담는다.

이 skill 은 가격 데이터를 해석하지 않는다. 추세 판단은 `engines.quant.momentum`, 패턴 판단은 `engines.quant.chartPatterns`, 수급 결합은 `engines.gather.flow`, 최종 투자 문맥은 상위 recipe 또는 story 가 담당한다.

## 공개 호출 방식

```python
import dartlab
from dartlab.gather import getDefaultGather
from dartlab.viz import emit_chart
from dartlab.viz.generators import specPriceChart

g = getDefaultGather()

# 1. 개별 종목 OHLCV
price = g.history("005930", start="2025-01-01", end="2025-12-31", market="KR")

# 2. 선택 벤치마크. 데이터가 없으면 benchmarkRows 없이 진행한다.
kospi = dartlab.gather("krxIndex", "raw", market="KOSPI", start="2025-01-01", end="2025-12-31")

spec = specPriceChart(
    price,
    stockCode="005930",
    corpName="삼성전자",
    market="KR",
    benchmarkRows=kospi,
    benchmarkName="KOSPI",
)

if spec is not None:
    emit_chart(spec)
```

`CompileVisual` 경로에서는 이미 확보한 row list 를 그대로 넘긴다.

```python
CompileVisual(
    chartType="price-chart",
    title="삼성전자 주가",
    data=[
        {"date": "2025-01-02", "open": 53000, "high": 54500, "low": 52800, "close": 54200, "volume": 12345678},
        {"date": "2025-01-03", "open": 54200, "high": 55100, "low": 53800, "close": 54800, "volume": 10101010},
    ],
    source="gather:price:KR:005930",
)
```

## 호출 동작

`specPriceChart(rows, ...)` 는 Polars/Pandas/list[dict] 입력을 흡수한다. `date/open/high/low/close/volume` 컬럼을 우선 사용하고, KRX 원천 컬럼인 `BAS_DD`, `TDD_CLSPRC`, `TDD_HGPRC`, `TDD_LWPRC`, `ACC_TRDVOL`, 지수 컬럼 `CLSPRC_IDX` 도 읽는다.

입력 row 는 날짜 기준으로 정렬된다. `close` 가 없거나 날짜가 없는 row 는 버린다. 이동평균은 기본 `MA20`, `MA60` 을 계산한다. 벤치마크 row 가 있으면 같은 날짜 기준으로 100 기준 상대지수를 만들어 `options.benchmarkSeries` 에 넣는다.

`ChartRenderer` 는 `price-chart` 를 `PriceChart.svelte` 로 dispatch 한다. 렌더러는 3M/6M/1Y/All 범위 선택, 캔들/라인 토글, 거래량 하단 패널, MA overlay, hover crosshair 를 제공한다.

## 대표 반환 형태

```python
{
    "chartType": "price-chart",
    "title": "삼성전자 주가 · 거래량",
    "data": [
        {"date": "2025-01-02", "open": 53000.0, "high": 54500.0, "low": 52800.0, "close": 54200.0, "volume": 12345678.0}
    ],
    "series": [
        {"name": "종가", "data": [54200.0], "type": "line"},
        {"name": "MA20", "data": [None], "type": "line", "overlay": True}
    ],
    "categories": ["2025-01-02"],
    "options": {
        "mode": "candlestick",
        "unit": "원",
        "volumeUnit": "주",
        "overlays": ["ma20", "ma60"],
        "benchmarkName": "KOSPI",
        "benchmarkSeries": [{"date": "2025-01-02", "value": 100.0}],
        "events": []
    },
    "evidenceBinding": {
        "tableRef": "gather:price:D",
        "source": "gather",
        "stockCode": "005930",
        "topic": "price",
        "periodKind": "D",
        "periods": ["2025-01-02"]
    }
}
```

## 연계 절차

1. `engines.gather.price` — 대상 종목의 OHLCV 를 확보한다. 한국 6 자리 코드는 `market="KR"`, 미국 ticker 는 `market="US"` 를 명시한다.
2. `engines.gather.flow` — 한국 종목에서 수급 해석이 필요하면 외국인/기관 flow 를 별도 근거로 붙인다.
3. `engines.quant.momentum` — 주가의 상대 강도, 수익률, 변동성 판단을 계산한다.
4. `engines.quant.chartPatterns` — W/M/H&S 등 패턴 주장이 필요할 때만 보조로 호출한다.
5. `engines.viz` — 최종 `price-chart` spec 을 `emit_chart` 로 출력한다.

## 기본 검증

- `rows` 가 2개 미만이면 차트를 만들지 않는다.
- 최신 종가를 답변에 쓰면 `latestAsOf` 를 직전 거래일로 명시한다.
- 벤치마크는 종목 가격과 같은 기간으로 정렬하고, 원 단위와 상대지수 축을 혼동하지 않는다.
- 캔들 차트가 필요한 경우 `open/high/low/close` 가 모두 있는지 확인한다. close-only 데이터는 line mode 로 fallback 한다.
- `evidenceBinding` 또는 `evidenceIds` 가 없으면 `emit_chart` 하지 않는다.

## AI 직접 사용 방식

사용자가 “주가 흐름”, “차트로 보여줘”, “시장 대비 어땠나”라고 물으면 이 skill 을 고른다. 먼저 `engines.gather.price` 로 OHLCV 를 확보하고, 가격만으로 결론을 내리지 말고 `engines.quant.momentum` 또는 `engines.gather.flow` 를 같이 확인한다. 답변은 차트 → 기간 수익률 → 거래량 변화 → 벤치마크 대비 → 한계 순서로 조립한다.
