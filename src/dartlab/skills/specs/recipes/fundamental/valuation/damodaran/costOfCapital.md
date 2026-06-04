---
id: recipes.fundamental.valuation.damodaran.costOfCapital
title: Damodaran 비용자본 가정
category: recipes
kind: recipe
scope: builtin
status: curated
purpose: 국가 ERP, 무위험금리, 세율, 산업 beta와 debt/capital 기본값을 L1.5 reference에서 읽어 WACC 가정과 fallback reason을 만드는 절차. 트리거 — 'WACC 가정', 'Damodaran ERP beta', '비용자본 reference'.
whenToUse:
  - WACC 가정
  - Damodaran ERP beta
  - 비용자본 reference
  - cost of capital
  - 다모다란 자본비용
linkedSkills:
  - recipes.fundamental.valuation.damodaran.dataAudit
  - recipes.fundamental.valuation.damodaran.businessModelFit
  - engines.company
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - sourceRef
  - valueRef
  - dateRef
  - executionRef
expectedOutputs:
  - risk-free ? ERP ? beta ? debt cost ? tax ? WACC assumption table
  - country/industry reference freshness? fallback reason
  - WACC ???? confidence

expectedNovelty:
  - damodaranL15Memo
  - reverseDcfFalsifier
  - l15GapLedger
forbidden:
  - stale country ERP를 정상 reference처럼 사용하지 않는다.
  - beta나 부채비용 fallback을 숨기지 않는다.
  - L2 엔진 호출 금지.
failureModes:
  - 국가 ERP와 기업 통화를 혼동
  - effective tax rate와 marginal tax rate를 혼합
  - 금융업 WACC를 제조업 FCFF DCF에 그대로 적용
examples:
  - 삼성전자 WACC 가정
  - AAPL Damodaran beta ERP
  - semiconductor industry WACC fallback
gap:
  primary:
    - reference
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
  description: "country reference stale 또는 industry fallback이 있는데 confidence를 high로 표시하면 실패로 본다."
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
    table=memo["tables"]["costOfCapital"],
    values=memo["headline"],
    date=memo.get("asOf"),
    units=memo["units"],
    sources=memo["sources"],
)
```

## 호출 동작

### 1. 결론 도출

WACC를 점추정이 아니라 `base`, `low`, `high` 범위로 제시한다. stale 또는 industry fallback이 있으면 confidence를 낮춘다.

### 2. 핵심 근거 수집

country reference에서 risk-free rate, total ERP, tax rate를 읽고 industry reference에서 beta, debt/capital, cost of debt, cost of capital을 읽는다.

### 3. 메커니즘 분석

개별 beta가 없는 v1에서는 industry beta를 기본값으로 쓴다. 개별 가격 beta primitive가 L1.5에 추가되기 전까지는 industry fallback을 명시한다.

### 4. 반례·한계

KR 기업이 USD 매출 중심이어도 통화와 국가 ERP가 다를 수 있다. 통화·상장시장·매출지역이 충돌하면 단일 WACC로 단정하지 않는다.

### 5. 후속 모니터링

ERP as-of, risk-free shift, industry beta table, 개별 부채비용 대체 데이터를 모니터링한다.

## 대표 반환 형태

`costOfCapital : dict` — `riskFreeRatePct`, `erpPct`, `beta`, `costOfEquityPct`, `preTaxCostOfDebtPct`, `taxRatePct`, `waccPct`, `confidence`, `fallbacks`를 담는다.

## 연계 절차

1. recipes.fundamental.valuation.damodaran.reinvestmentRoc - ROC와 WACC spread 비교.
2. recipes.fundamental.valuation.damodaran.fcffDcf - 할인율 범위 적용.
3. recipes.fundamental.valuation.damodaran.scenarioFalsifier - WACC 민감도 반증.

## 기본 검증

- country reference stale이면 `confidence: low` 또는 갱신 필요 flag가 있어야 한다.
- industry key가 없으면 totalMarketWithoutFinancials fallback과 사유를 남긴다.

