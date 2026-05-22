---
id: recipes.fundamental.valuation.damodaran.oneOffAdjustment
title: Damodaran 일회성 항목 조정 감사
category: recipes
kind: recipe
scope: builtin
status: unverified
purpose: 손상, 구조조정, 중단영업, 소송, 비경상 손익 등 one-off line item을 찾아 normalized EBIT/FCFF 조정 필요성을 표시하는 절차. 트리거 — 'one-off adjustment', '비경상 손익 조정', '정규화 이익'.
whenToUse:
  - one-off adjustment
  - 비경상 손익 조정
  - 정규화 이익
linkedSkills:
  - recipes.fundamental.valuation.damodaran.normalizedFinancials
  - recipes.fundamental.valuation.damodaran.accountTraceAudit
  - engines.company
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
  - impairment/restructuring/discontinued ? ??? ?? ??
  - normalized EBIT ?? ??? ??
  - ?? ??? ? ??? fallback ??

expectedNovelty:
  - oneOffNormalizationAudit
forbidden:
  - L2 엔진 호출 금지.
  - 일회성 라인 결손을 정상 반복손익으로 단정하지 않는다.
failureModes:
  - 손상차손을 반복 영업마진으로 반영
examples:
  - INTC one-off adjustment
gap:
  primary:
    - company
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
  description: "one-off 후보가 있는데 normalizedFinancials 반영 후보로 표시하지 않으면 실패로 본다."
lastUpdated: "2026-05-14"
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
  - "engines.viz.financialStructureCharts"
  - "engines.viz.scenarioVisuals"
  - "engines.viz.tableBackedChart"
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
    table=memo["tables"]["oneOffAdjustment"],
    values=memo["headline"],
    date=memo.get("asOf"),
    units=memo["units"],
    sources=memo["sources"],
)
```

## 호출 동작

### 1. 결론 도출

one-off 후보 line item을 찾고 정규화 후보로 표시한다.

### 2. 핵심 근거 수집

`Company.show("IS"|"CF")` line item의 snakeId와 항목명을 검색한다.

### 3. 메커니즘 분석

반복 영업력과 일회성 항목을 분리해야 성장·마진 가정이 과대/과소 추정되지 않는다.

### 4. 반례·한계

반복 구조조정 여부는 텍스트 근거가 필요하므로 line item 감사 단계에서 confidence를 낮춘다.

### 5. 후속 모니터링

후속 스킬은 `normalizedFinancials`, `scenarioFalsifier`다.

## 대표 반환 형태

`oneOffAdjustment : list[dict]` — `adjustment`, `status`, `lineItem`, `latestValue`, `action`.

## 연계 절차

1. recipes.fundamental.valuation.damodaran.accountTraceAudit - 계정 trace 확인.
2. recipes.fundamental.valuation.damodaran.normalizedFinancials - 정규화 후보 반영.
