---
id: recipes.valuation.damodaran.leaseDebtAdjustment
title: Damodaran 리스부채 조정 감사
category: recipes
kind: recipe
scope: builtin
status: unverified
purpose: L1 재무제표에서 리스·사용권자산·리스부채 라인을 찾아 부채와 영업자산 조정 필요성을 표시하는 절차. 트리거 — 'lease debt adjustment', '리스부채 조정', '사용권자산 가치평가'.
whenToUse:
  - lease debt adjustment
  - 리스부채 조정
  - 사용권자산 가치평가
linkedSkills:
  - recipes.valuation.damodaran.normalizedFinancials
  - recipes.valuation.damodaran.costOfCapital
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
  - lease/right-of-use ?? ?? ??
  - debt/WACC/FCFF ?? ??? ??
  - ?? ?? ?? ? blocker ?? fallback note

expectedNovelty:
  - leaseDebtAudit
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
forbidden:
  - L2 엔진 호출 금지.
  - 리스 라인이 없는데 부채 조정 완료로 표시하지 않는다.
failureModes:
  - 리스부채를 순부채에서 누락
examples:
  - 리스부채 Damodaran 조정
gap:
  primary:
    - Company
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
  description: "lease line item이 없는데 usable 조정을 선언하면 실패로 본다."
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
    table=memo["tables"]["leaseDebtAdjustment"],
    values=memo["headline"],
    date=memo.get("asOf"),
    units=memo["units"],
    sources=memo["sources"],
)
```

## 호출 동작

### 1. 결론 도출

리스 관련 line item을 찾아 부채·자본 조정 후보인지 표시한다.

### 2. 핵심 근거 수집

`Company.show("BS"|"CF")`의 snakeId와 항목명을 검색한다.

### 3. 메커니즘 분석

운영리스 또는 사용권자산은 부채비율, invested capital, FCFF 조정에 영향을 준다.

### 4. 반례·한계

만기별 리스 지급액이 없으면 현재가치 재계산은 하지 않고 결손을 남긴다.

### 5. 후속 모니터링

후속 스킬은 `costOfCapital`, `fcffDcf`다.

## 대표 반환 형태

`leaseDebtAdjustment : list[dict]` — `adjustment`, `status`, `lineItem`, `latestValue`, `action`.

## 연계 절차

1. recipes.valuation.damodaran.accountTraceAudit - 계정 trace 확인.
2. recipes.valuation.damodaran.costOfCapital - 부채비율 fallback 확인.
