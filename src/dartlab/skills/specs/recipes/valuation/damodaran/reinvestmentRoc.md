---
id: recipes.valuation.damodaran.reinvestmentRoc
title: Damodaran 재투자율과 ROC
category: recipes
kind: recipe
scope: builtin
status: unverified
purpose: 정규화 재무 패널에서 sales-to-capital, reinvestment rate, ROIC/ROC, incremental ROC를 계산하고 성장률이 재투자와 수익성으로 설명되는지 반증하는 절차. 트리거 — 'ROIC 재투자율', 'growth = ROC x reinvestment', 'Damodaran value driver'.
whenToUse:
  - ROIC 재투자율
  - growth equals ROC times reinvestment
  - Damodaran value driver
  - sales to capital
  - incremental ROC
linkedSkills:
  - recipes.valuation.damodaran.normalizedFinancials
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
  - 성장률을 과거 CAGR만으로 확정하지 않는다.
  - invested capital 결손 시 ROC를 계산하지 않는다.
  - L2 엔진 호출 금지.
failureModes:
  - 음수 invested capital에서 ROC 폭주
  - 성장률과 재투자율 불일치를 무시
  - 산업 sales-to-capital fallback 사유 누락
examples:
  - 삼성전자 reinvestment ROC
  - AAPL sales-to-capital sanity check
  - INTC incremental ROC 반증
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
  description: "매출 성장률이 implied reinvestment capacity를 초과하는데도 optimistic growth로 통과시키면 실패로 본다."
lastUpdated: "2026-05-13"
---

## 공개 호출 방식

```python
import dartlab
import importlib.resources as resources
import json

target = "005930"
industry_key = "semiconductor"
c = dartlab.Company(target)

industry_defaults = json.loads(
    resources.files("dartlab.reference.data").joinpath("damodaranIndustryDefaults.json").read_text(encoding="utf-8")
)
industry = industry_defaults["industries"].get(
    industry_key, industry_defaults["industries"]["totalMarketWithoutFinancials"]
)

ratios = c.show("ratios", freq="Y")
rows = [
    {"metric": "industrySalesToCapital", "value": industry.get("salesToInvestedCapital")},
    {"metric": "industryOperatingMarginPct", "value": industry.get("preTaxOperatingMarginPct")},
    {"metric": "ratioRows", "value": getattr(ratios, "height", None)},
]

emit_result(
    table=rows,
    values={"target": target, "industryKey": industry_key, "fallback": industry_key not in industry_defaults["industries"]},
    date=industry_defaults["_meta"].get("asOfDate"),
)
```

## 호출 동작

### 1. 결론 도출

가치 driver를 `growth = reinvestmentRate x ROC` 관점에서 한 문장으로 판정한다. 성장 가정이 가능한지, 과한지, 보수적인지 구분한다.

### 2. 핵심 근거 수집

정규화 재무 패널의 NOPAT, invested capital, capex, 감가상각, 운전자본 증감과 산업 sales-to-capital fallback을 묶는다.

### 3. 메커니즘 분석

재투자는 `capex - depreciation + deltaNonCashWorkingCapital`로 계산한다. ROC는 `NOPAT / investedCapital`, incremental ROC는 `deltaNOPAT / deltaInvestedCapital`로 계산한다.

### 4. 반례·한계

negative invested capital, 구조조정 적자, 대규모 M&A 연도는 평균에서 제외하거나 별도 flag를 둔다. 산업 fallback은 결론 강도를 낮춘다.

### 5. 후속 모니터링

성장률, 재투자율, ROC, sales-to-capital의 불일치 항목을 `fcffDcf`의 assumption guard로 넘긴다.

## 대표 반환 형태

`valueDrivers : dict` — `reinvestmentRate`, `roc`, `incrementalRoc`, `salesToCapital`, `impliedGrowth`, `flags`를 담는다.

## 연계 절차

1. recipes.valuation.damodaran.normalizedFinancials - 입력 패널 생성.
2. recipes.valuation.damodaran.fcffDcf - 성장률과 reinvestment consistency 반영.
3. recipes.valuation.damodaran.scenarioFalsifier - 가격 내재 성장률과 비교.

## 기본 검증

- 성장률이 ROC x 재투자율보다 크면 반드시 반례로 표시한다.
- industry default를 썼으면 `fallback: true`와 source as-of를 결과에 남긴다.

