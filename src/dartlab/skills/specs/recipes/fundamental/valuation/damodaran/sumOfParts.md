---
id: recipes.fundamental.valuation.damodaran.sumOfParts
title: Damodaran Sum-of-Parts 경로
category: recipes
kind: recipe
scope: builtin
status: unverified
purpose: 세그먼트·지주회사·복합 사업에 대해 단일 FCFF 대신 segment별 revenue/EBIT 근거와 결손을 분리하는 절차. 트리거 — 'sum of parts', 'SOTP', '세그먼트 가치평가'.
whenToUse:
  - sum of parts
  - SOTP
  - 세그먼트 가치평가
linkedSkills:
  - recipes.fundamental.valuation.damodaran.narrativeMap
  - recipes.fundamental.valuation.damodaran.normalizedFinancials
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
  - reported company ?? ???? fallback? segment blocker
  - SOTP ??? ??? ?? segment evidence
  - ???? ?? ?? ? deferredWithBlocker

expectedNovelty:
  - sumOfPartsRoute
forbidden:
  - 세그먼트 근거 없이 임의 SOTP를 만들지 않는다.
  - L2 industry/story 엔진 호출 금지.
failureModes:
  - 복합기업을 단일 마진으로만 평가
examples:
  - 삼성전자 SOTP 경로 점검
gap:
  primary:
    - company
    - frame
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
  description: "segmentDisclosure가 없는데 segment별 가치를 확정하면 실패로 본다."
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
    table=memo["tables"]["sumOfParts"],
    values=memo["headline"],
    date=memo.get("asOf"),
    units=memo["units"],
    sources=memo["sources"],
)
```

## 호출 동작

### 1. 결론 도출

단일 회사 재무와 세그먼트 공시 결손을 분리해 SOTP 가능성을 판정한다.

### 2. 핵심 근거 수집

`Company.show` 재무 3표와 segment topic 또는 frame segment table의 필요성을 함께 남긴다.

### 3. 메커니즘 분석

세그먼트별 성장·마진·자본집약도가 다르면 단일 FCFF보다 SOTP가 적합하다.

### 4. 반례·한계

세그먼트 revenue/EBIT가 없으면 singleSegmentFallback으로만 둔다.

### 5. 후속 모니터링

후속 스킬은 `peerMultipleDecomposition`과 `fcffDcf`다.

## 대표 반환 형태

`sumOfParts : list[dict]` — `part`, `revenue`, `ebit`, `status`, `source`.

## 연계 절차

1. recipes.fundamental.valuation.damodaran.narrativeMap - 사업 단위 후보 확인.
2. recipes.fundamental.valuation.damodaran.normalizedFinancials - 전체 재무 baseline 확인.
