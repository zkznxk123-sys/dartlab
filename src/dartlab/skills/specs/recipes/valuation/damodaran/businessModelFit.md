---
id: recipes.valuation.damodaran.businessModelFit
title: Damodaran 모델 적합성 게이트
category: recipes
kind: recipe
scope: builtin
status: unverified
purpose: 일반 FCFF DCF를 적용해도 되는 회사인지 금융업, 보험, 지주, 적자, 고성장, 경기순환, 구조전환 유형으로 먼저 분류하는 절차. 트리거 — 'DCF 모델 적합성', '금융업 DCF 차단', 'Damodaran business model fit'.
whenToUse:
  - DCF 모델 적합성
  - 금융업 DCF 차단
  - Damodaran business model fit
  - business model valuation gate
  - 다모다란 모델 선택
linkedSkills:
  - recipes.valuation.damodaran.dataAudit
  - engines.company
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
  - 금융업을 일반 제조업 FCFF DCF로 통과시키지 않는다.
  - 단일 적자 연도만 보고 구조적 부실로 단정하지 않는다.
  - L2 엔진 호출 금지.
failureModes:
  - 은행의 예금부채를 영업부채처럼 취급
  - 사이클 저점 적자를 영구 적자 기업으로 오판
  - 지주회사 NAV 할인과 영업회사 DCF를 혼합
examples:
  - 138930 일반 FCFF DCF 차단
  - 반도체 경기순환 모델 적합성
  - AAPL mature quality 분류
gap:
  primary:
    - company
    - gather
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
  description: "금융업 또는 보험업을 genericFcffEligible=true로 통과시키면 실패로 본다."
lastUpdated: "2026-05-13"
---

## 공개 호출 방식

```python
import dartlab

target = "138930"
c = dartlab.Company(target)
market = getattr(c, "market", "KR")

def safe_show(topic):
    try:
        return c.show(topic, freq="Y")
    except TypeError:
        return c.show(topic)
    except Exception as exc:
        return {"error": type(exc).__name__}

profile = {"target": target, "market": market, "name": getattr(c, "corpName", target)}
is_table = safe_show("IS")
bs_table = safe_show("BS")
segments = safe_show("segments")

text = " ".join(str(value).lower() for value in profile.values())
financial_terms = ("bank", "banks", "insurance", "brokerage", "financial", "금융", "은행", "보험", "증권")
is_financial = any(term in text for term in financial_terms)
decision = "financialFirmOnly" if is_financial else "genericFcffCandidate"

emit_result(
    table=[
        {"test": "financialFirm", "result": is_financial},
        {"test": "hasIncomeStatement", "result": hasattr(is_table, "height")},
        {"test": "hasBalanceSheet", "result": hasattr(bs_table, "height")},
        {"test": "hasSegments", "result": hasattr(segments, "height")},
    ],
    values={"target": target, "market": market, "modelFit": decision},
    date="latest",
)
```

## 호출 동작

### 1. 결론 도출

`genericFcffCandidate`, `cyclicalFcff`, `turnaroundNeedsNormalization`, `financialFirmOnly`, `holdingCompanyNeedsNav` 중 하나로 모델 적합성을 낸다.

### 2. 핵심 근거 수집

회사명, 시장, 세그먼트, 손익계산서, 재무상태표, 최근 적자 여부, 부채 구조를 L1/L1.5 표면에서만 읽는다.

### 3. 메커니즘 분석

Damodaran식 valuation은 회사 유형이 먼저다. 같은 매출 성장률이라도 은행, 반도체, 소프트웨어, 지주회사는 현금흐름과 자본 정의가 다르므로 DCF 엔진보다 모델 적합성 게이트가 앞선다.

### 4. 반례·한계

텍스트 alias만으로 업종을 확정하지 않는다. 세그먼트와 재무제표 구조가 충돌하면 `usableWithFallback` 이하로 낮춘다.

### 5. 후속 모니터링

모델 적합성 결과는 `fcffDcf`의 실행 가능 여부와 `relativeCheck`의 비교군 선택에 전달한다.

## 대표 반환 형태

`modelFit : dict` — `modelType`, `genericFcffEligible`, `blockers`, `fallbackModel`, `evidence`를 포함한다.

## 연계 절차

1. recipes.valuation.damodaran.dataAudit - 데이터 가능성 확인.
2. recipes.valuation.damodaran.normalizedFinancials - generic FCFF 후보만 정규화.
3. recipes.valuation.damodaran.relativeCheck - generic FCFF 부적합 기업의 대체 sanity check.

## 기본 검증

- `138930`은 일반 FCFF DCF 차단 또는 financial-firm 전용 모델 필요로 분류되어야 한다.
- 제조·소프트웨어 기업은 결손이 없을 때 generic FCFF 후보로 통과 가능해야 한다.

