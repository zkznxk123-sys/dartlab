---
id: recipes.valuation.damodaran.storyToDrivers
title: Damodaran 스토리-드라이버 변환
category: recipes
kind: recipe
scope: builtin
status: unverified
purpose: narrativeMap의 사업 스토리를 성장률, 정상 마진, sales-to-capital, WACC, terminal growth, reverse DCF 요구 성장률로 변환하는 절차. 트리거 — 'story to drivers', '스토리를 숫자로', 'Damodaran driver map'.
whenToUse:
  - story to drivers
  - 스토리를 숫자로
  - Damodaran driver map
linkedSkills:
  - recipes.valuation.damodaran.narrativeMap
  - recipes.valuation.damodaran.reinvestmentRoc
  - recipes.valuation.damodaran.scenarioFalsifier
toolRefs:
  - RunPython
requiredEvidence:
  - skillRef
  - sourceRef
  - tableRef
  - valueRef
  - dateRef
  - executionRef
expectedOutputs:
  - narrative hypothesis? ?? driver mapping
  - driver source ? fallback ? confidence ?
  - DCF ???? ?? growth/margin/ROC/risk ??

expectedNovelty:
  - storyDriverTranslation
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
forbidden:
  - L2/L3 story 또는 valuation 엔진 호출 금지.
  - 임의 성장률을 근거 없이 채택하지 않는다.
failureModes:
  - 성장률과 재투자율/ROC의 연결 누락
  - 현재 가격이 요구하는 스토리와 base story를 구분하지 않음
examples:
  - AAPL story to drivers
  - 삼성전자 성장 스토리 숫자 변환
gap:
  primary:
    - Company
    - gather
    - synth
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
  description: "story claim이 driver value로 변환되지 않으면 실패로 본다."
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


def _marketData():
    try:
        frame = dartlab.gather("price", target, market="US") if market == "US" else dartlab.gather("price", target)
        if isinstance(frame, pl.DataFrame) and frame.height:
            return {"priceDate": str(frame.tail(1).to_dicts()[0].get("date", ""))}
    except Exception as exc:
        return {"priceError": type(exc).__name__}
    return {}


country_defaults = _loadReference("damodaranDefaults.json")
industry_defaults = _loadReference("damodaranIndustryDefaults.json")
memo = buildDamodaranMemo(
    target=target,
    market=market,
    currency=currency,
    companyName=company_name,
    statements={topic: _safeShow(topic) for topic in ("IS", "BS", "CF")},
    countryDefaults=country_defaults,
    industryDefaults=industry_defaults,
    marketData=_marketData(),
)

emit_result(
    table=memo["tables"]["storyToDrivers"],
    values=memo["headline"],
    date=memo.get("asOf"),
    units=memo["units"],
    sources=memo["sources"],
)
```

## 호출 동작

### 1. 결론 도출

story claim을 성장, 마진, 재투자, 리스크, terminal, reverse price story driver로 분해한다.

### 2. 핵심 근거 수집

정규화 재무 패널과 Damodaran reference, gather price metadata를 사용한다.

### 3. 메커니즘 분석

Damodaran식 스토리는 수치 가정으로 검증 가능해야 한다. reverse DCF가 blocked이면 현재 가격 내재 스토리는 partial로 둔다.

### 4. 반례·한계

금융업은 일반 FCFF driver로 변환하지 않고 별도 모델 경로를 남긴다.

### 5. 후속 모니터링

후속 스킬은 `growthFeasibility`, `fcffDcf`, `scenarioFalsifier`다.

## 대표 반환 형태

`storyToDrivers : list[dict]` — `storyClaim`, `driver`, `value`, `status`.

## 연계 절차

1. recipes.valuation.damodaran.narrativeMap - narrative 요소를 구조화.
2. recipes.valuation.damodaran.growthFeasibility - driver의 성장 정합성 반증.
3. recipes.valuation.damodaran.scenarioFalsifier - 현재 가격 내재 스토리 반증.

## 기본 검증

- 모든 row는 `storyClaim`, `driver`, `status`를 가져야 한다.
