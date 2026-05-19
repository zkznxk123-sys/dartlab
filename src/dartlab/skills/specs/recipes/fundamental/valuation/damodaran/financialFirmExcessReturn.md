---
id: recipes.fundamental.valuation.damodaran.financialFirmExcessReturn
title: Damodaran 금융업 Excess Return 경로
category: recipes
kind: recipe
scope: builtin
status: unverified
purpose: 은행·보험·증권 등 금융업이 일반 FCFF에서 차단될 때 book equity, ROE proxy, cost of equity를 이용해 excess-return 모델 필요성을 표시하는 절차. 트리거 — 'financial firm excess return', '금융업 가치평가', '은행 Damodaran'.
whenToUse:
  - financial firm excess return
  - 금융업 가치평가
  - 은행 Damodaran
linkedSkills:
  - recipes.fundamental.valuation.damodaran.businessModelFit
  - recipes.fundamental.valuation.damodaran.costOfCapital
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - sourceRef
  - tableRef
  - valueRef
  - dateRef
  - executionRef
expectedOutputs:
  - ??? generic FCFF ?? ??
  - ROE ? cost of equity ? excess return proxy table
  - ??/?? ?? ?? ?? ? fallback route

expectedNovelty:
  - financialFirmRoute
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
forbidden:
  - 금융업을 generic FCFF로 강제하지 않는다.
  - L2 credit/valuation 엔진 호출 금지.
failureModes:
  - 은행을 FCFF DCF로 평가
examples:
  - 138930 금융업 excess return 경로
gap:
  primary:
    - Company
    - reference
testUniverse:
  market: KR+US
  stockCodes:
    - "005930"
    - "000660"
    - "138930"
    - "AAPL"
    - "INTC"
  asOfPolicy: latest
falsifier:
  description: "금융업 blocker가 있는데 FCFF usable로 표시하면 실패로 본다."
lastUpdated: "2026-05-14"
---

## 공개 호출 방식

```python
import dartlab
import importlib.resources as resources
import json

import polars as pl
from dartlab.synth.damodaranL15 import buildDamodaranMemo

target = "005930"
c = dartlab.Company(target)
market = getattr(c, "market", "US" if not target.isdigit() else "KR")
currency = getattr(c, "currency", "USD" if market == "US" else "KRW")
company_name = getattr(c, "corpName", getattr(c, "companyName", target))


def _loadReference(name):
    return json.loads(resources.files("dartlab.reference.data").joinpath(name).read_text(encoding="utf-8"))


def _safeShow(topic):
    try:
        table = c.show(topic, freq="Y")
    except TypeError:
        table = c.show(topic)
    except Exception:
        return pl.DataFrame()
    return table if isinstance(table, pl.DataFrame) else pl.DataFrame()


try:
    dartlab.gather("price", target, market="US") if market == "US" else dartlab.gather("price", target)
except Exception:
    pass

memo = buildDamodaranMemo(
    target=target,
    market=market,
    currency=currency,
    companyName=company_name,
    statements={topic: _safeShow(topic) for topic in ("IS", "BS", "CF")},
    countryDefaults=_loadReference("damodaranDefaults.json"),
    industryDefaults=_loadReference("damodaranIndustryDefaults.json"),
    marketData={},
)

emit_result(
    table=memo["tables"]["financialFirmExcessReturn"],
    values=memo["headline"],
    date=memo.get("asOf"),
    units=memo["units"],
    sources=memo["sources"],
)
```

## 호출 동작

### 1. 결론 도출

금융업이면 excess-return 모델 경로를 열고, 비금융이면 notApplicable로 표시한다.

### 2. 핵심 근거 수집

`Company.show("BS"|"IS")`의 book equity와 NOPAT proxy, Damodaran cost of equity reference를 사용한다.

### 3. 메커니즘 분석

금융업은 reinvestment와 debt 개념이 비금융 FCFF와 다르므로 book capital 대비 excess return으로 별도 처리해야 한다.

### 4. 반례·한계

규제자본, 대손충당금, 보험 float 데이터가 없으면 완전한 금융업 모델은 engine backlog로 남긴다.

### 5. 후속 모니터링

후속 스킬은 `sumOfParts`, `distressAdjustedDcf`다.

## 대표 반환 형태

`financialFirmExcessReturn : list[dict]` — `metric`, `value`, `status`.

## 연계 절차

1. recipes.fundamental.valuation.damodaran.businessModelFit - 금융업 blocker 확인.
2. recipes.fundamental.valuation.damodaran.costOfCapital - cost of equity reference 확인.
