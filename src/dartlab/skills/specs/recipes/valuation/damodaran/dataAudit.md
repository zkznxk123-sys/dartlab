---
id: recipes.valuation.damodaran.dataAudit
title: Damodaran L1.5 데이터 감사
category: recipes
kind: recipe
scope: builtin
status: unverified
purpose: Damodaran식 가치평가를 시작하기 전에 L1/L1.5 데이터만으로 재무, 가격, 시총, 세그먼트, 국가·산업 기본값, 문서 근거가 충분한지 판정하는 절차. 트리거 — 'Damodaran 데이터 감사', 'L1.5 가치평가 가능성', 'DCF 전 데이터 점검'.
whenToUse:
  - Damodaran 데이터 감사
  - L1.5 가치평가 가능성
  - DCF 전 데이터 점검
  - KR US valuation data audit
  - 다모다란 스킬 기초 점검
linkedSkills:
  - engines.company
  - engines.gather
  - engines.scan
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
    limitations:
      - 패키지 내장 reference JSON과 로컬 데이터 snapshot만 점검한다.
forbidden:
  - c.analysis, c.quant, c.credit, c.industry, c.story, dartlab.macro 호출 금지.
  - Company.show("PRICE")를 가격 SSOT로 쓰지 않는다.
  - 누락 데이터를 0으로 채우지 않는다.
failureModes:
  - DART와 EDGAR의 topic alias 차이를 coverage 부족이 아니라 사업 변화로 오판
  - Damodaran reference가 stale인데 정상 가정으로 사용
  - 금융업을 일반 FCFF DCF 가능 대상으로 통과
examples:
  - 삼성전자 Damodaran 데이터 감사
  - AAPL L1.5 가치평가 가능성 점검
  - DCF 전에 missing evidence 정리
gap:
  primary:
    - gather
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
  description: "country/industry reference 또는 price path가 결손인데 usable 판정을 내리면 실패로 본다."
lastUpdated: "2026-05-13"
---

## 공개 호출 방식

```python
import dartlab
import importlib.resources as resources
import json

target = "005930"
c = dartlab.Company(target)
market = getattr(c, "market", "KR")

def load_reference(name):
    return json.loads(
        resources.files("dartlab.reference.data").joinpath(name).read_text(encoding="utf-8")
    )

checks = []
for topic in ("IS", "BS", "CF", "ratios", "segments"):
    try:
        obj = c.show(topic, freq="Y") if topic in {"IS", "BS", "CF", "ratios"} else c.show(topic)
        checks.append({"area": topic, "status": "usable", "rows": getattr(obj, "height", None)})
    except Exception as exc:
        checks.append({"area": topic, "status": "missing", "reason": type(exc).__name__})

try:
    price = dartlab.gather("price", target, market="US") if market == "US" else dartlab.gather("price", target)
    checks.append({"area": "price", "status": "usable", "rows": getattr(price, "height", None)})
except Exception as exc:
    checks.append({"area": "price", "status": "missing", "reason": type(exc).__name__})

country_defaults = load_reference("damodaranDefaults.json")
industry_defaults = load_reference("damodaranIndustryDefaults.json")
checks.append({"area": "countryReference", "status": country_defaults["_meta"].get("freshnessStatus", "unknown")})
checks.append({"area": "industryReference", "status": industry_defaults["_meta"].get("coverageStatus", "unknown")})

blocked = [row for row in checks if row["status"] == "missing"]
emit_result(
    table=checks,
    values={"target": target, "market": market, "decision": "blocked" if blocked else "usableWithFallback"},
    date=country_defaults["_meta"].get("asOfDate"),
)
```

## 호출 동작

### 1. 결론 도출

대상 기업을 `usable`, `usableWithFallback`, `blocked` 중 하나로 판정한다. `usable`은 재무 3표, 가격, 국가 reference, 산업 reference가 모두 확인된 경우에만 쓴다.

### 2. 핵심 근거 수집

`Company.show("IS"|"BS"|"CF"|"ratios"|"segments")`, `dartlab.gather("price")`, `reference/data/damodaranDefaults.json`, `reference/data/damodaranIndustryDefaults.json`를 확인한다.

### 3. 메커니즘 분석

데이터 감사는 계산 전 게이트다. 재무 패널이 없으면 정규화가 불가능하고, 가격·시총이 없으면 reverse DCF가 불가능하며, reference가 stale이면 비용자본 가정이 fallback으로 내려간다.

### 4. 반례·한계

EDGAR는 KR topic alias보다 거칠 수 있다. `segments`가 없거나 사업 설명 topic이 provider별 이름으로만 있으면 결론을 낮은 confidence로 내려야 한다.

### 5. 후속 모니터링

country reference as-of, industry reference coverage, price latest date, missing topic list를 다음 단계로 넘긴다.

## 대표 반환 형태

`coverage : list[dict]` — `area`, `status`, `rows`, `reason`을 담는다. 최종 `decision`은 `usable`, `usableWithFallback`, `blocked` 중 하나다.

## 연계 절차

1. recipes.valuation.damodaran.businessModelFit - 모델 적합성 판정.
2. recipes.valuation.damodaran.normalizedFinancials - 재무 패널 정규화.
3. recipes.valuation.damodaran.costOfCapital - reference stale/fallback 반영.

## 기본 검증

- 5개 고정 타깃 중 KR 1개, US 1개 이상은 `usableWithFallback` 이상이어야 한다.
- 금융업 타깃은 데이터가 있어도 일반 FCFF `usable`로 승격하지 않는다.
- L2 호출 금지 정적 검사를 통과해야 한다.

