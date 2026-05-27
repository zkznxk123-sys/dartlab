---
id: recipes.fundamental.valuation.damodaran.accountTraceAudit
title: Damodaran 계정 출처 감사
category: recipes
kind: recipe
scope: builtin
status: curated
purpose: Damodaran식 재무 정규화에 쓰인 매출, EBIT, 세금, CFO, capex, 감가상각, 현금, 부채, 자본, 운전자본 계정의 L1 출처를 감사하는 절차. 트리거 — '계정 trace', '출처 감사', 'valuation account provenance'.
whenToUse:
  - 계정 trace
  - 출처 감사
  - valuation account provenance
  - Damodaran account audit
  - 재무제표 출처 확인
linkedSkills:
  - recipes.fundamental.valuation.damodaran.dataAudit
  - recipes.fundamental.valuation.damodaran.normalizedFinancials
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
  - valuation input? ?? ?? trace
  - ?? ?? ?? ??? fallback reason
  - ?? ?? ?? ??? ???

expectedNovelty:
  - valuationAccountTrace
  - missingAccountGate
  - sourceKeyAudit
forbidden:
  - trace가 없는 핵심 계정을 0으로 채우지 않는다.
  - DART/EDGAR 계정명 차이를 사업 변화로 해석하지 않는다.
  - L2 엔진 호출 금지.
failureModes:
  - capex 부호를 확인하지 않고 FCFF에 반영
  - depreciation 결손을 정상 현금흐름으로 오판
  - debt line이 없는데 부채 없음과 계정 누락을 구분하지 않음
examples:
  - 삼성전자 valuation 계정 출처 감사
  - AAPL FCFF 계정 trace
  - DCF 전에 missing account 확인
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
  description: "revenue, EBIT, CFO, capex 중 하나라도 trace 없이 usable로 표시하면 실패로 본다."
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
validatedAt: '2026-05-27'
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


def _safeShow(topic):
    try:
        table = c.show(topic, freq="Y")
    except TypeError:
        table = c.show(topic)
    except Exception:
        return pl.DataFrame()
    return table if isinstance(table, pl.DataFrame) else pl.DataFrame()


country_defaults = json.loads(
    resources.files("dartlab.reference.data").joinpath("damodaranDefaults.json").read_text(encoding="utf-8")
)
industry_defaults = json.loads(
    resources.files("dartlab.reference.data").joinpath("damodaranIndustryDefaults.json").read_text(encoding="utf-8")
)
statements = {topic: _safeShow(topic) for topic in ("IS", "BS", "CF")}
memo = buildDamodaranMemo(
    target=target,
    market=market,
    currency=currency,
    companyName=company_name,
    statements=statements,
    countryDefaults=country_defaults,
    industryDefaults=industry_defaults,
    marketData={},
)

emit_result(
    table=memo["tables"]["accountTraceAudit"],
    values=memo["headline"],
    date=memo.get("asOf"),
    units=memo["units"],
    sources=memo["sources"],
)
```

## 호출 동작

### 1. 결론 도출

valuation에 투입된 핵심 계정이 어떤 `snakeId`에서 왔는지 최신 연도 기준으로 표준화해 보여준다. 누락 계정은 DCF 계산 전에 gap으로 남긴다.

### 2. 핵심 근거 수집

`Company.show("IS"|"BS"|"CF", freq="Y")`로 들어온 표의 계정 매칭 결과를 사용한다. 매출, EBIT, 세금, CFO, capex, 감가상각, 현금, 부채, 자본, 운전자본을 최소 감시 계정으로 둔다.

### 3. 메커니즘 분석

Damodaran식 valuation은 회계 계정 선택이 가정의 출발점이다. 같은 FCFF라도 capex, depreciation, working capital 출처가 다르면 value driver 해석이 달라진다.

### 4. 반례·한계

부채 line이 없을 때는 실제 무차입과 계정 누락을 분리해야 한다. 현재 스킬은 line 부재를 `fallbackAccepted`로 낮추고, 원문 주석 기반 debt spread 판단은 후속 스킬로 남긴다.

### 5. 후속 모니터링

trace 결손 계정은 `normalizedFinancials`, `reinvestmentRoc`, `fcffDcf`의 confidence를 낮춘다.

## 대표 반환 형태

`accountTraceAudit : list[dict]` — `year`, `account`, `traceKey`, `status`, `source`를 담는다.

## 연계 절차

1. recipes.fundamental.valuation.damodaran.normalizedFinancials - 계정 사용 결과.
2. recipes.fundamental.valuation.damodaran.reinvestmentRoc - capex/working capital trace 검증.
3. recipes.fundamental.valuation.damodaran.fcffDcf - trace 결손 시 DCF confidence 하향.

## 기본 검증

- 핵심 계정마다 `usable`, `fallbackAccepted`, `missing` 중 하나를 표시한다.
- 5개 고정 타깃에서 execution과 evidence가 통과해야 한다.
