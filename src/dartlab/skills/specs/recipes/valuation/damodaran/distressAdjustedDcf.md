---
id: recipes.valuation.damodaran.distressAdjustedDcf
title: Damodaran Distress 조정 DCF 경로
category: recipes
kind: recipe
scope: builtin
status: unverified
purpose: 부채비율, FCFF 음수 비율, DCF 상태를 이용해 일반 DCF에 distress 조정이 필요한지 판정하는 절차. 트리거 — 'distress adjusted DCF', '부실위험 DCF', '재무위험 가치평가'.
whenToUse:
  - distress adjusted DCF
  - 부실위험 DCF
  - 재무위험 가치평가
linkedSkills:
  - recipes.valuation.damodaran.fcffDcf
  - recipes.valuation.damodaran.costOfCapital
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
expectedNovelty:
  - distressDcfRoute
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
forbidden:
  - L2 credit 엔진 호출 금지.
  - distress 신호를 무시하고 base DCF만 결론으로 쓰지 않는다.
failureModes:
  - FCFF 지속 음수 기업을 정상 terminal value로만 평가
examples:
  - INTC distress adjusted DCF 점검
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
  description: "distressReviewRequired 신호가 있는데 final memo가 usable만 표시하면 실패로 본다."
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

emit_result(
    table=memo["tables"]["distressAdjustedDcf"],
    values=memo["headline"],
    date=memo.get("asOf"),
    units=memo["units"],
    sources=memo["sources"],
)
```

## 호출 동작

### 1. 결론 도출

부채비율과 FCFF 음수 비율이 높으면 distress 조정 필요로 표시한다.

### 2. 핵심 근거 수집

`Company.show("BS"|"CF")`, Damodaran WACC reference, DCF 상태를 사용한다.

### 3. 메커니즘 분석

부실위험이 큰 기업은 going-concern DCF만으로 결론을 내리면 terminal value가 과대평가될 수 있다.

### 4. 반례·한계

시장 기반 default spread와 distress probability primitive가 없으면 확률가중 DCF는 보류한다.

### 5. 후속 모니터링

후속 스킬은 `scenarioFalsifier`와 `deepDive`다.

## 대표 반환 형태

`distressAdjustedDcf : list[dict]` — `metric`, `value`, `status`.

## 연계 절차

1. recipes.valuation.damodaran.fcffDcf - base DCF 상태 확인.
2. recipes.valuation.damodaran.scenarioFalsifier - 반증 조건 확인.
