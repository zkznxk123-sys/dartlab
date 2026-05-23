---
id: recipes.fundamental.valuation.damodaran.reinvestmentRoc
title: Damodaran 재투자율과 ROC
category: recipes
kind: recipe
scope: builtin
status: tested
purpose: 정규화 재무 패널에서 sales-to-capital, reinvestment rate, ROIC/ROC, incremental ROC를 계산하고 성장률이 재투자와 수익성으로 설명되는지 반증하는 절차. 트리거 — 'ROIC 재투자율', 'growth = ROC x reinvestment', 'Damodaran value driver'.
whenToUse:
  - ROIC 재투자율
  - growth equals ROC times reinvestment
  - Damodaran value driver
  - sales to capital
  - incremental ROC
linkedSkills:
  - recipes.fundamental.valuation.damodaran.normalizedFinancials
  - engines.company
  - engines.analysis
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
  - sales-to-capital ? reinvestment rate ? ROIC/ROC ?
  - ???? ????? ????? ????? ??
  - incremental ROC ?? ?? ?? ??

expectedNovelty:
  - damodaranL15Memo
  - reverseDcfFalsifier
  - l15GapLedger
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
    - "138930"
    - "AAPL"
    - "INTC"
  asOfPolicy: latest
falsifier:
  description: "매출 성장률이 implied reinvestment capacity를 초과하는데도 optimistic growth로 통과시키면 실패로 본다."
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
        table = c.show(topic, freq="Y")
    except TypeError:
        table = c.show(topic)
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
    table=memo["tables"]["reinvestmentRoc"],
    values=memo["headline"],
    date=memo.get("asOf"),
    units=memo["units"],
    sources=memo["sources"],
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

1. recipes.fundamental.valuation.damodaran.normalizedFinancials - 입력 패널 생성.
2. recipes.fundamental.valuation.damodaran.fcffDcf - 성장률과 reinvestment consistency 반영.
3. recipes.fundamental.valuation.damodaran.scenarioFalsifier - 가격 내재 성장률과 비교.

## 기본 검증

- 성장률이 ROC x 재투자율보다 크면 반드시 반례로 표시한다.
- industry default를 썼으면 `fallback: true`와 source as-of를 결과에 남긴다.

