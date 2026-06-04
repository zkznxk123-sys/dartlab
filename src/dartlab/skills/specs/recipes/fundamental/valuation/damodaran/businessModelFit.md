---
id: recipes.fundamental.valuation.damodaran.businessModelFit
title: Damodaran 모델 적합성 게이트
category: recipes
kind: recipe
scope: builtin
status: curated
purpose: 일반 FCFF DCF를 적용해도 되는 회사인지 금융업, 보험, 지주, 적자, 고성장, 경기순환, 구조전환 유형으로 먼저 분류하는 절차. 트리거 — 'DCF 모델 적합성', '금융업 DCF 차단', 'Damodaran business model fit'.
whenToUse:
  - DCF 모델 적합성
  - 금융업 DCF 차단
  - Damodaran business model fit
  - business model valuation gate
  - 다모다란 모델 선택
linkedSkills:
  - recipes.fundamental.valuation.damodaran.dataAudit
  - engines.company
  - engines.gather
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - valueRef
  - dateRef
  - executionRef
  - sourceRef
expectedOutputs:
  - generic FCFF ?? ??? ?? ??
  - ???????distress???? fallback route
  - ?? ?? confidence? ?? valuation path

expectedNovelty:
  - damodaranL15Memo
  - reverseDcfFalsifier
  - l15GapLedger
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
from pathlib import Path

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
        table = c.panel(topic, freq="Y")
    except TypeError:
        table = c.panel(topic)
    except Exception:
        return pl.DataFrame()
    return table if isinstance(table, pl.DataFrame) else pl.DataFrame()


def _latestPrice(frame):
    if not isinstance(frame, pl.DataFrame) or frame.height == 0:
        return {}
    date_col = "date" if "date" in frame.columns else "Date" if "Date" in frame.columns else None
    close_col = "close" if "close" in frame.columns else "Close" if "Close" in frame.columns else None
    latest = frame.sort(date_col).tail(1).to_dicts()[0] if date_col else frame.tail(1).to_dicts()[0]
    out = {}
    if close_col and latest.get(close_col) is not None:
        out["price"] = latest.get(close_col)
    if date_col and latest.get(date_col) is not None:
        out["priceDate"] = str(latest.get(date_col))
    return out


def _marketData():
    out = {}
    try:
        price_frame = dartlab.gather("price", target, market="US") if market == "US" else dartlab.gather("price", target)
        out.update(_latestPrice(price_frame))
    except Exception as exc:
        out["priceError"] = type(exc).__name__

    if market == "KR":
        krx_path = Path("data/krx/prices/raw-2026.parquet")
        if krx_path.exists():
            try:
                krx = (
                    pl.scan_parquet(str(krx_path))
                    .filter(pl.col("ISU_CD") == target)
                    .select(["BAS_DD", "TDD_CLSPRC", "MKTCAP", "LIST_SHRS"])
                    .sort("BAS_DD")
                    .tail(1)
                    .collect()
                )
                if krx.height:
                    row = krx.to_dicts()[0]
                    out.update(
                        {
                            "price": row.get("TDD_CLSPRC") or out.get("price"),
                            "priceDate": str(row.get("BAS_DD") or out.get("priceDate")),
                            "marketCap": row.get("MKTCAP"),
                            "shares": row.get("LIST_SHRS"),
                        }
                    )
            except Exception as exc:
                out["marketCapError"] = type(exc).__name__

    if market == "US" and out.get("price") is not None:
        cik = str(getattr(c, "cik", "") or "")
        for path in (Path(f"data/edgar/finance/{cik}.parquet"), Path(f"data/edgar/finance/{target}.parquet")):
            if not path.exists():
                continue
            try:
                shares = (
                    pl.scan_parquet(str(path))
                    .filter((pl.col("unit") == "shares") & pl.col("tag").str.contains("SharesOutstanding"))
                    .select(["val", "filed"])
                    .sort("filed")
                    .tail(1)
                    .collect()
                )
                if shares.height:
                    out["shares"] = shares["val"][0]
                    out["marketCap"] = float(out["price"]) * float(out["shares"])
                    break
            except Exception as exc:
                out["marketCapError"] = type(exc).__name__
    return out


country_defaults = _loadReference("damodaranDefaults.json")
industry_defaults = _loadReference("damodaranIndustryDefaults.json")
statements = {topic: _safeShow(topic) for topic in ("IS", "BS", "CF")}
memo = buildDamodaranMemo(
    target=target,
    market=market,
    currency=currency,
    companyName=company_name,
    statements=statements,
    countryDefaults=country_defaults,
    industryDefaults=industry_defaults,
    marketData=_marketData(),
)

emit_result(
    table=memo["tables"]["modelFit"],
    values=memo["headline"],
    date=memo.get("asOf"),
    units=memo["units"],
    sources=memo["sources"],
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

1. recipes.fundamental.valuation.damodaran.dataAudit - 데이터 가능성 확인.
2. recipes.fundamental.valuation.damodaran.normalizedFinancials - generic FCFF 후보만 정규화.
3. recipes.fundamental.valuation.damodaran.relativeCheck - generic FCFF 부적합 기업의 대체 sanity check.

## 기본 검증

- `138930`은 일반 FCFF DCF 차단 또는 financial-firm 전용 모델 필요로 분류되어야 한다.
- 제조·소프트웨어 기업은 결손이 없을 때 generic FCFF 후보로 통과 가능해야 한다.

