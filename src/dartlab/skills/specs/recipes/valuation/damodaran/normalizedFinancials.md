---
id: recipes.valuation.damodaran.normalizedFinancials
title: Damodaran 정규화 재무 패널
category: recipes
kind: recipe
scope: builtin
status: unverified
purpose: L1 재무제표만으로 매출, 영업이익, 세율, NOPAT, 운전자본, 감가상각, capex, FCF를 5-10년 패널로 정규화하는 절차. 트리거 — 'normalized financials', 'Damodaran 재무 정규화', 'FCFF 계산 전 패널'.
whenToUse:
  - normalized financials
  - Damodaran 재무 정규화
  - FCFF 계산 전 패널
  - NOPAT invested capital panel
  - 다모다란 정규화 재무
linkedSkills:
  - recipes.valuation.damodaran.dataAudit
  - recipes.valuation.damodaran.businessModelFit
  - engines.company
toolRefs:
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - valueRef
  - dateRef
  - executionRef
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
forbidden:
  - 결손 계정을 0으로 채우지 않는다.
  - 일회성 적자를 정상 마진으로 단정하지 않는다.
  - L2 엔진 호출 금지.
failureModes:
  - DART/EDGAR 계정명 차이를 같은 snakeId로 정규화하지 못함
  - capex 부호를 반대로 해석
  - flow 항목과 stock 항목을 같은 방식으로 합산
examples:
  - 삼성전자 10년 normalized financials
  - AAPL NOPAT invested capital 패널
  - 반도체 사이클 정상 마진 계산
gap:
  primary:
    - company
    - reference
testUniverse:
  market: KR+US
  stockCodes:
    - "005930"
    - "000660"
    - "AAPL"
    - "INTC"
  asOfPolicy: latest
falsifier:
  description: "revenue, operating income, CFO 중 하나라도 trace 없이 계산되면 정규화 패널 실패로 본다."
lastUpdated: "2026-05-13"
---

## 공개 호출 방식

```python
import dartlab

target = "005930"
c = dartlab.Company(target)

def show(topic):
    try:
        return c.show(topic, freq="Y")
    except Exception as exc:
        return {"error": type(exc).__name__}

tables = {topic: show(topic) for topic in ("IS", "BS", "CF")}
coverage = []
for topic, table in tables.items():
    columns = list(getattr(table, "columns", []))
    years = [col for col in columns if str(col)[:4].isdigit()]
    coverage.append({"topic": topic, "rows": getattr(table, "height", None), "years": len(years)})

trace_rows = []
for account in ("sales", "operating_profit", "cash_flow_from_operations"):
    try:
        trace_rows.append({"account": account, "trace": str(c.trace(account))[:160]})
    except Exception as exc:
        trace_rows.append({"account": account, "trace": type(exc).__name__})

emit_result(
    table=coverage + trace_rows,
    values={"target": target, "minYears": min([row.get("years", 0) for row in coverage] or [0])},
    date="latest",
)
```

## 호출 동작

### 1. 결론 도출

정규화 패널의 사용 가능 기간과 결손 계정을 먼저 말한다. 최소 5년 미만이면 DCF 가정보다 데이터 한계를 앞에 둔다.

### 2. 핵심 근거 수집

IS/BS/CF 연간 표와 주요 계정 trace를 묶는다. 매출, 영업이익, 법인세, CFO, capex, 감가상각, 현금, 총부채, 자본, 운전자본 계정의 출처를 남긴다.

### 3. 메커니즘 분석

NOPAT은 영업이익과 실효세율에서 만들고, invested capital은 영업자본 중심으로 계산한다. capex와 운전자본 증감은 FCFF 연결을 위해 따로 보관한다.

### 4. 반례·한계

세율이 음수이거나 60%를 넘으면 normalized tax fallback을 쓴다. 적자 기업은 단순 평균 대신 사이클 정상화 또는 turnaround flag를 남긴다.

### 5. 후속 모니터링

다음 단계는 재투자율, ROC, FCFF를 같은 패널에서 계산한다. 결손 계정은 `dataAudit` gap ledger로 되돌린다.

## 대표 반환 형태

`normalizedPanel : list[dict]` — `year`, `revenue`, `ebit`, `taxRate`, `nopat`, `investedCapital`, `cfo`, `capex`, `fcff`, `sourceTrace`를 담는다.

## 연계 절차

1. recipes.valuation.damodaran.reinvestmentRoc - 정규화 패널에서 재투자율과 ROC 계산.
2. recipes.valuation.damodaran.fcffDcf - FCFF 현금흐름으로 가치 밴드 계산.
3. recipes.valuation.damodaran.scenarioFalsifier - 정규화 값으로 reverse DCF 반증.

## 기본 검증

- 각 핵심 계정은 trace 또는 명시적 fallback reason을 가져야 한다.
- flow 항목은 연간 flow, BS 항목은 연말 stock으로 취급한다.

