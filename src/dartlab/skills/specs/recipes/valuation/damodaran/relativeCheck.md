---
id: recipes.valuation.damodaran.relativeCheck
title: Damodaran 상대가치 검산
category: recipes
kind: recipe
scope: builtin
status: unverified
purpose: EV/Sales, EV/EBIT, PE, PB 등 상대가치를 DCF 결론의 sanity check로만 사용하고 US valuation scan 부재는 partial gap으로 남기는 절차. 트리거 — 'relative valuation check', 'DCF peer sanity', 'Damodaran multiple cross-check'.
whenToUse:
  - relative valuation check
  - DCF peer sanity
  - Damodaran multiple cross-check
  - EV Sales EV EBIT
  - 상대가치 검산
linkedSkills:
  - recipes.valuation.damodaran.fcffDcf
  - engines.scan
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
  - multiple만으로 본질가치를 확정하지 않는다.
  - US valuation scan 부재를 숨기지 않는다.
  - L2 엔진 호출 금지.
failureModes:
  - peer group 없이 market-wide multiple만 비교
  - 적자 기업 PE를 정상 multiple로 사용
  - KR valuation snapshot을 US 기업에 적용
examples:
  - 삼성전자 DCF peer sanity
  - AAPL US relative valuation partial
  - EV Sales multiple check
gap:
  primary:
    - scan
    - gather
testUniverse:
  market: KR+US
  stockCodes:
    - "005930"
    - "AAPL"
    - "INTC"
  asOfPolicy: latest
falsifier:
  description: "US valuation scan 부재를 partial gap으로 표시하지 않으면 실패로 본다."
lastUpdated: "2026-05-13"
---

## 공개 호출 방식

```python
import dartlab

target = "005930"
c = dartlab.Company(target)
market = getattr(c, "market", "KR")
rows = []

if market == "KR":
    try:
        valuation_scan = dartlab.scan("valuation")
        rows.append({"metric": "krValuationScan", "status": "usable", "rows": getattr(valuation_scan, "height", None)})
    except Exception as exc:
        rows.append({"metric": "krValuationScan", "status": "missing", "reason": type(exc).__name__})
else:
    rows.append({"metric": "usValuationScan", "status": "partial", "reason": "L1.5 US valuation scan not implemented"})

try:
    price = dartlab.gather("price", target, market="US") if market == "US" else dartlab.gather("price", target)
    rows.append({"metric": "price", "status": "usable", "rows": getattr(price, "height", None)})
except Exception as exc:
    rows.append({"metric": "price", "status": "missing", "reason": type(exc).__name__})

emit_result(
    table=rows,
    values={"target": target, "market": market, "relativeStatus": "partial" if market == "US" else "usableWithFallback"},
    date="latest",
)
```

## 호출 동작

### 1. 결론 도출

상대가치는 DCF를 대체하지 않고 sanity check로만 쓴다. DCF가 peer multiple 분포와 크게 어긋나면 가정 재검토를 요구한다.

### 2. 핵심 근거 수집

KR은 `scan("valuation")` snapshot과 가격 path를 쓴다. US는 v1에서 가격 path만 확인하고 peer valuation primitive 부재를 gap으로 남긴다.

### 3. 메커니즘 분석

EV/Sales는 마진과 sales-to-capital 가정의 sanity check, EV/EBIT은 정상 마진의 sanity check, PB는 금융업·자본집약 업종의 보조 체크로 쓴다.

### 4. 반례·한계

적자 기업 PE, 현금 과다 기업 EV multiple, 회계 기준이 다른 peer group은 결론 강도를 낮춘다.

### 5. 후속 모니터링

US valuation scan 구현, peer group mapping, market cap/share count normalization을 gap ledger로 넘긴다.

## 대표 반환 형태

`relativeCheck : dict` — `multiples`, `peerCoverage`, `sanityFlags`, `missingPrimitives`, `status`를 담는다.

## 연계 절차

1. recipes.valuation.damodaran.fcffDcf - DCF 결과 입력.
2. recipes.valuation.damodaran.scenarioFalsifier - multiple이 깨는 가정 반증.
3. recipes.valuation.damodaran.deepDive - 최종 memo에 gap 반영.

## 기본 검증

- US 기업은 `partial` 또는 `blocked` 표시 없이 relative valuation 완료 선언 금지.
- multiple 결과는 DCF 가정 검산으로만 사용한다.

