---
id: recipes.fundamental.valuation.damodaran.rdCapitalization
title: Damodaran R&D 자본화 감사
category: recipes
kind: recipe
scope: builtin
status: unverified
purpose: L1 재무제표의 연구개발비 라인을 찾아 R&D 자본화 필요 여부와 결손을 표시하는 Damodaran식 정규화 절차. 트리거 — 'R&D capitalization', '연구개발비 자본화', 'Damodaran R&D adjustment'.
whenToUse:
  - R&D capitalization
  - 연구개발비 자본화
  - Damodaran R&D adjustment
linkedSkills:
  - recipes.fundamental.valuation.damodaran.normalizedFinancials
  - recipes.fundamental.valuation.damodaran.accountTraceAudit
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
  - R&D ?? ?? ?? ??? ??? ???
  - ?? L1/L1.5 ?? ?? ? fallbackAccepted ?? blocker
  - normalized EBIT/FCFF ?? ? ?? ?

expectedNovelty:
  - rdAdjustmentAudit
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
forbidden:
  - L2 엔진 호출 금지.
  - R&D 라인이 없는데 0으로 확정하지 않는다.
failureModes:
  - 연구개발비 결손을 정상 비용 구조로 오판
examples:
  - AAPL R&D 자본화 감사
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
  description: "R&D 라인이 없는데 capitalization adjustment를 usable로 표시하면 실패로 본다."
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
    price_date = str(price_frame.tail(1).to_dicts()[0].get("date", "")) if isinstance(price_frame, pl.DataFrame) and price_frame.height else None
except Exception:
    price_date = None

memo = buildDamodaranMemo(
    target=target,
    market=market,
    currency=currency,
    companyName=company_name,
    statements={topic: _safeShow(topic) for topic in ("IS", "BS", "CF")},
    countryDefaults=_loadReference("damodaranDefaults.json"),
    industryDefaults=_loadReference("damodaranIndustryDefaults.json"),
    marketData={"priceDate": price_date} if price_date else {},
)

emit_result(
    table=memo["tables"]["rdCapitalization"],
    values=memo["headline"],
    date=memo.get("asOf"),
    units=memo["units"],
    sources=memo["sources"],
)
```

## 호출 동작

### 1. 결론 도출

R&D 라인이 있으면 자본화 검토 대상으로, 없으면 `fallbackAccepted` 결손으로 표시한다.

### 2. 핵심 근거 수집

`Company.show("IS"|"CF")`의 snakeId와 항목명을 검색한다.

### 3. 메커니즘 분석

R&D는 성장 투자 성격이 강하므로 비용 처리된 금액이 크면 NOPAT와 invested capital 정규화 후보가 된다.

### 4. 반례·한계

상각기간 추정은 아직 reference가 없으므로 엔진 계산이 아니라 감사 절차로 둔다.

### 5. 후속 모니터링

후속 스킬은 `normalizedFinancials`와 `fcffDcf`다.

## 대표 반환 형태

`rdCapitalization : list[dict]` — `adjustment`, `status`, `lineItem`, `latestYear`, `latestValue`, `action`.

## 연계 절차

1. recipes.fundamental.valuation.damodaran.accountTraceAudit - 계정 trace 확인.
2. recipes.fundamental.valuation.damodaran.normalizedFinancials - 정규화 패널 반영 후보 점검.
