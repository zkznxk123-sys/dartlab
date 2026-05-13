---
id: recipes.valuation.damodaran.scenarioFalsifier
title: Damodaran 시나리오 반증
category: recipes
kind: recipe
scope: builtin
status: unverified
purpose: bull/base/bear 민감도, reverse DCF, 현재 가격이 요구하는 성장·마진·ROC를 계산해 Damodaran식 내재 스토리를 반증하는 절차. 트리거 — 'reverse DCF', '내재 성장률', 'Damodaran scenario falsifier'.
whenToUse:
  - reverse DCF
  - 내재 성장률
  - Damodaran scenario falsifier
  - valuation sensitivity
  - 시나리오 반증
linkedSkills:
  - recipes.valuation.damodaran.fcffDcf
  - recipes.valuation.damodaran.reinvestmentRoc
  - recipes.valuation.damodaran.costOfCapital
  - engines.gather
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
  - 단일 base case만으로 결론을 내지 않는다.
  - 가격 내재 가정을 계산하지 않고 저평가/고평가를 단정하지 않는다.
  - L2 엔진 호출 금지.
failureModes:
  - WACC 민감도만 보고 마진·재투자 민감도 누락
  - terminal value share 과다를 무시
  - reverse DCF가 가격 path 없이 실행됨
examples:
  - 삼성전자 reverse DCF
  - AAPL 현재가 내재 성장률
  - INTC turnaround bull bear scenario
gap:
  primary:
    - gather
    - reference
testUniverse:
  market: KR+US
  stockCodes:
    - "005930"
    - "AAPL"
    - "INTC"
  asOfPolicy: latest
falsifier:
  description: "현재 가격이 요구하는 성장·마진·ROC를 계산하지 않으면 scenario falsifier 실패로 본다."
lastUpdated: "2026-05-13"
---

## 공개 호출 방식

```python
import dartlab

target = "AAPL"
c = dartlab.Company(target)
market = getattr(c, "market", "US")

try:
    price = dartlab.gather("price", target, market="US") if market == "US" else dartlab.gather("price", target)
    price_status = "usable"
except Exception as exc:
    price = None
    price_status = type(exc).__name__

scenario_grid = [
    {"case": "bear", "growthDeltaPct": -2.0, "marginDeltaPct": -3.0, "waccDeltaPct": 1.0},
    {"case": "base", "growthDeltaPct": 0.0, "marginDeltaPct": 0.0, "waccDeltaPct": 0.0},
    {"case": "bull", "growthDeltaPct": 2.0, "marginDeltaPct": 3.0, "waccDeltaPct": -1.0},
]

emit_result(
    table=scenario_grid + [{"case": "reverseDcfInput", "growthDeltaPct": None, "marginDeltaPct": None, "waccDeltaPct": None, "priceStatus": price_status}],
    values={"target": target, "market": market, "priceUsable": price is not None},
    date="latest",
)
```

## 호출 동작

### 1. 결론 도출

현재 가격이 요구하는 성장, 마진, ROC가 과거·산업·재투자 능력과 맞는지 판정한다.

### 2. 핵심 근거 수집

DCF 밴드, WACC 범위, 가격 path, 정규화 마진, sales-to-capital, ROC를 사용한다.

### 3. 메커니즘 분석

reverse DCF는 가격을 입력으로 두고 필요한 매출 성장률 또는 terminal margin을 역산한다. 역산값이 산업 상위권을 넘어가면 bull case라도 반증 flag를 남긴다.

### 4. 반례·한계

가격 path가 없으면 reverse DCF는 blocked다. terminal value share가 높으면 모든 scenario에 confidence penalty를 부여한다.

### 5. 후속 모니터링

다음 실적 발표에서 매출 성장, 마진, capex, 운전자본, WACC 변화가 내재 스토리를 확인하는지 추적한다.

## 대표 반환 형태

`scenarioFalsifier : dict` — `scenarioGrid`, `reverseDcf`, `requiredGrowth`, `requiredMargin`, `requiredRoc`, `breakConditions`, `monitoringTriggers`를 담는다.

## 연계 절차

1. recipes.valuation.damodaran.fcffDcf - DCF 밴드 입력.
2. recipes.valuation.damodaran.relativeCheck - peer multiple 반증 결합.
3. recipes.valuation.damodaran.deepDive - 최종 memo의 반례·한계 섹션.

## 기본 검증

- bull/base/bear 3개 scenario가 모두 있어야 한다.
- reverse DCF는 가격 입력이 없으면 blocked로 남긴다.

