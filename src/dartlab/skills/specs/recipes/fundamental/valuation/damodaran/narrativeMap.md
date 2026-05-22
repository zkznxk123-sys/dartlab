---
id: recipes.fundamental.valuation.damodaran.narrativeMap
title: Damodaran 내러티브 맵
category: recipes
kind: recipe
scope: builtin
status: unverified
purpose: Company metadata, topics, 재무 패널, reference mapping을 엮어 사업 스토리를 성장·마진·리스크·모델 경로로 구조화하는 L1/L1.5 절차. 트리거 — 'Damodaran narrative map', '스토리 숫자 연결', '사업 내러티브 가치평가'.
whenToUse:
  - Damodaran narrative map
  - 스토리 숫자 연결
  - 사업 내러티브 가치평가
  - narrative and numbers
linkedSkills:
  - recipes.fundamental.valuation.damodaran.dataAudit
  - recipes.fundamental.valuation.damodaran.businessModelFit
  - recipes.fundamental.valuation.damodaran.lifeCycleClassifier
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
  - ?? narrative? growth ? margin ? reinvestment ? risk driver? ??? ?
  - text evidence ?? ? fallback note
  - story-to-driver ??? ?? narrative hypothesis

expectedNovelty:
  - narrativeDriverMap
forbidden:
  - L2/L3 story 또는 analysis 엔진 호출 금지.
  - 텍스트 근거 없이 narrative를 확정하지 않는다.
failureModes:
  - 사업 설명을 숫자 driver로 연결하지 않음
  - 금융업 모델 경로를 일반 FCFF narrative로 처리
examples:
  - 삼성전자 Damodaran 내러티브 맵
  - AAPL 스토리를 성장과 마진 가정으로 연결
gap:
  primary:
    - company
    - gather
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
  description: "narrative 요소가 growth, margin, risk, model route 중 하나에도 연결되지 않으면 실패로 본다."
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


def _latestPrice(frame):
    if not isinstance(frame, pl.DataFrame) or frame.height == 0:
        return {}
    date_col = "date" if "date" in frame.columns else "Date" if "Date" in frame.columns else None
    close_col = "close" if "close" in frame.columns else "Close" if "Close" in frame.columns else None
    latest = frame.sort(date_col).tail(1).to_dicts()[0] if date_col else frame.tail(1).to_dicts()[0]
    out = {}
    if close_col and latest.get(close_col) is not None:
        out["price"] = latest.get(close_col)
    if date_col and latest.get(date_col) is not None:
        out["priceDate"] = str(latest.get(date_col))
    return out


def _marketData():
    out = {}
    try:
        frame = dartlab.gather("price", target, market="US") if market == "US" else dartlab.gather("price", target)
        out.update(_latestPrice(frame))
    except Exception as exc:
        out["priceError"] = type(exc).__name__
    return out


country_defaults = _loadReference("damodaranDefaults.json")
industry_defaults = _loadReference("damodaranIndustryDefaults.json")
statements = {topic: _safeShow(topic) for topic in ("IS", "BS", "CF")}
memo = buildDamodaranMemo(
    target=target,
    market=market,
    currency=currency,
    companyName=company_name,
    statements=statements,
    countryDefaults=country_defaults,
    industryDefaults=industry_defaults,
    marketData=_marketData(),
)

emit_result(
    table=memo["tables"]["narrativeMap"],
    values=memo["headline"],
    date=memo.get("asOf"),
    units=memo["units"],
    sources=memo["sources"],
)
```

## 호출 동작

### 1. 결론 도출

사업 정체성, 모델 경로, 성장 스토리, 수익성 스토리, 시장 리스크를 valuation driver로 연결한다.

### 2. 핵심 근거 수집

`Company` 기본 메타데이터, `Company.show("IS"|"BS"|"CF")`, `dartlab.gather("price")`, Damodaran reference를 사용한다.

### 3. 메커니즘 분석

내러티브는 문장이 아니라 driver map이다. 각 narrative 요소는 성장률, 마진, 자본효율, 리스크, 모델 경로 중 하나 이상으로 번역되어야 한다.

### 4. 반례·한계

사업 설명 topic alias가 없으면 재무 패널과 reference 기반의 낮은 confidence mapping으로 남긴다.

### 5. 후속 모니터링

후속 스킬은 `storyToDrivers`다.

## 대표 반환 형태

`narrativeMap : list[dict]` — `narrativeElement`, `driver`, `value`, `status`, `source`.

## 연계 절차

1. recipes.fundamental.valuation.damodaran.dataAudit - 사용 가능한 L1/L1.5 근거 확인.
2. recipes.fundamental.valuation.damodaran.businessModelFit - 모델 경로 확정.
3. recipes.fundamental.valuation.damodaran.storyToDrivers - narrative를 수치 driver로 변환.

## 기본 검증

- 5개 고정 타깃에서 `tableRef`, `valueRef`, `sourceRef`를 남긴다.
- L2/L3 호출 금지 정적 검사를 통과해야 한다.
