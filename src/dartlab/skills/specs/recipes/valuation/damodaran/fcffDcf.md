---
id: recipes.valuation.damodaran.fcffDcf
title: Damodaran FCFF DCF 밴드
category: recipes
kind: recipe
scope: builtin
status: unverified
purpose: 정규화 FCFF, 재투자율, ROC, WACC를 조합해 고성장기, 전환기, 정상상태의 FCFF DCF 가치 밴드를 만드는 절차. 트리거 — 'FCFF DCF', 'Damodaran DCF band', 'terminal ROC consistency'.
whenToUse:
  - FCFF DCF
  - Damodaran DCF band
  - terminal ROC consistency
  - intrinsic value DCF
  - 다모다란 가치 밴드
linkedSkills:
  - recipes.valuation.damodaran.normalizedFinancials
  - recipes.valuation.damodaran.reinvestmentRoc
  - recipes.valuation.damodaran.costOfCapital
  - engines.company
  - engines.gather
toolRefs:
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - valueRef
  - dateRef
  - executionRef
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
forbidden:
  - terminal growth가 risk-free rate를 초과하는 가정을 통과시키지 않는다.
  - reinvestment 없이 고성장률만 넣지 않는다.
  - L2 엔진 호출 금지.
failureModes:
  - terminal value가 전체 가치의 대부분인데 민감도 누락
  - negative FCFF를 기계적으로 평균
  - 금융업에 generic FCFF 적용
examples:
  - 삼성전자 FCFF DCF band
  - AAPL terminal growth consistency
  - INTC turnaround DCF blocker
gap:
  primary:
    - gather
    - reference
testUniverse:
  market: KR+US
  stockCodes:
    - "005930"
    - "000660"
    - "AAPL"
    - "INTC"
  asOfPolicy: latest
falsifier:
  description: "terminal growth, ROC, reinvestment가 서로 불일치해도 fair value band를 확정하면 실패로 본다."
lastUpdated: "2026-05-13"
---

## 공개 호출 방식

```python
import dartlab
import importlib.resources as resources
import json

target = "005930"
c = dartlab.Company(target)
market = getattr(c, "market", "KR")

country_defaults = json.loads(
    resources.files("dartlab.reference.data").joinpath("damodaranDefaults.json").read_text(encoding="utf-8")
)
currency = getattr(c, "currency", "KRW")
country_code = country_defaults.get("currencyToCountry", {}).get(currency, "KR")
country = country_defaults["countries"].get(country_code, country_defaults["countries"]["KR"])

try:
    price = dartlab.gather("price", target, market="US") if market == "US" else dartlab.gather("price", target)
    price_status = "usable"
except Exception as exc:
    price = None
    price_status = type(exc).__name__

rows = [
    {"assumption": "riskFreeRatePct", "value": country.get("riskFreeRate")},
    {"assumption": "terminalGrowthCeilingPct", "value": country.get("riskFreeRate")},
    {"assumption": "pricePath", "value": price_status},
]

emit_result(
    table=rows,
    values={"target": target, "market": market, "dcfStatus": "assumptionReady" if price is not None else "blocked"},
    date=country_defaults["_meta"].get("asOfDate"),
)
```

## 호출 동작

### 1. 결론 도출

가치 밴드는 `bear`, `base`, `bull` 3개로 낸다. 결론은 “현재가 대비 할인율”보다 “어떤 성장·마진·ROC 스토리가 가격에 필요한가”를 함께 말한다.

### 2. 핵심 근거 수집

정규화 FCFF, 성장률, 재투자율, ROC, WACC, terminal growth ceiling, 가격 path를 사용한다.

### 3. 메커니즘 분석

명시기간 FCFF는 매출 성장, 마진, 세율, 재투자로 만든다. terminal value는 정상상태 ROC와 재투자율이 terminal growth를 설명할 때만 통과한다.

### 4. 반례·한계

terminal value 비중이 과도하면 결론을 낮춘다. turnaround 기업은 normalized FCFF가 양수로 전환되는 근거가 없으면 blocked로 둔다.

### 5. 후속 모니터링

마진, sales-to-capital, WACC, terminal growth 민감도를 `scenarioFalsifier`로 넘긴다.

## 대표 반환 형태

`dcfBand : dict` — `bear`, `base`, `bull`, `terminalValueShare`, `assumptionTable`, `consistencyFlags`, `fallbacks`를 담는다.

## 연계 절차

1. recipes.valuation.damodaran.costOfCapital - 할인율 범위.
2. recipes.valuation.damodaran.relativeCheck - DCF 결과의 peer sanity check.
3. recipes.valuation.damodaran.scenarioFalsifier - reverse DCF와 민감도 반증.

## 기본 검증

- terminal growth는 country risk-free rate 이하.
- growth는 reinvestmentRate x ROC로 설명 가능해야 한다.
- price path가 없으면 reverse DCF와 현재가 비교는 blocked 처리한다.

