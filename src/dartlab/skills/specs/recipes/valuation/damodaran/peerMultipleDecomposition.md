---
id: recipes.valuation.damodaran.peerMultipleDecomposition
title: Damodaran Peer Multiple 분해
category: recipes
kind: recipe
scope: builtin
status: unverified
purpose: EV/Sales, EV/EBIT, P/B 같은 상대가치 multiple을 성장·마진·ROC·리스크 driver로 분해해 DCF sanity check로만 쓰는 절차. 트리거 — 'peer multiple decomposition', '상대가치 분해', 'multiple sanity check'.
whenToUse:
  - peer multiple decomposition
  - 상대가치 분해
  - multiple sanity check
linkedSkills:
  - recipes.valuation.damodaran.relativeCheck
  - recipes.valuation.damodaran.storyToDrivers
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
  - peer multiple? margin ? growth ? ROC ? risk driver? ??? ?
  - peer universe ??? ? market coverage status
  - multiple ?? ?? ?? ?? ??

expectedNovelty:
  - peerMultipleDriverMap
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
forbidden:
  - L2 valuation 또는 industry 엔진 호출 금지.
  - multiple만으로 적정가 결론을 내리지 않는다.
failureModes:
  - peer 차이를 성장·마진·리스크로 분해하지 않음
examples:
  - 삼성전자 peer multiple decomposition
gap:
  primary:
    - scan
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
  description: "multiple을 DCF 가정 검산이 아니라 단독 결론으로 쓰면 실패로 본다."
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
    price_frame = dartlab.gather("price", target, market="US") if market == "US" else dartlab.gather("price", target)
except Exception:
    price_frame = pl.DataFrame()

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

table = list(memo["tables"]["peerMultipleDecomposition"])
try:
    scan_frame = dartlab.scan("valuation") if market == "KR" else pl.DataFrame()
    scan_status = "usable" if isinstance(scan_frame, pl.DataFrame) and scan_frame.height else "missing"
except Exception as exc:
    scan_status = type(exc).__name__
table.append({"multiple": "dartlab.scan('valuation')", "companyValue": None, "driverLink": "peer primitive", "driverValue": scan_status, "status": scan_status})

emit_result(
    table=table,
    values=memo["headline"],
    date=memo.get("asOf"),
    units=memo["units"],
    sources=memo["sources"],
)
```

## 호출 동작

### 1. 결론 도출

상대가치 multiple을 DCF driver별 sanity check로 분해한다.

### 2. 핵심 근거 수집

`Company.show`, `dartlab.gather("price")`, KR의 `dartlab.scan("valuation")`, Damodaran reference를 사용한다.

### 3. 메커니즘 분석

EV/Sales는 성장과 sales-to-capital, EV/EBIT는 마진, P/B는 ROC-WACC spread와 연결한다.

### 4. 반례·한계

US peer primitive가 없으면 peer universe는 partial로 남긴다.

### 5. 후속 모니터링

후속 스킬은 `multipleNarrativeCheck` 또는 `scenarioFalsifier`다.

## 대표 반환 형태

`peerMultipleDecomposition : list[dict]` — `multiple`, `companyValue`, `driverLink`, `driverValue`, `status`.

## 연계 절차

1. recipes.valuation.damodaran.relativeCheck - 회사 multiple 계산.
2. recipes.valuation.damodaran.storyToDrivers - multiple 차이를 driver로 해석.
3. recipes.valuation.damodaran.scenarioFalsifier - 가격 내재 스토리와 대조.

## 기본 검증

- multiple row는 단독 투자 결론이 아니라 driverLink를 가져야 한다.
