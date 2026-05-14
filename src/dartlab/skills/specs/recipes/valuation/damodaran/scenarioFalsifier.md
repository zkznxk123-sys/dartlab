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
expectedNovelty:
  - damodaranL15Memo
  - reverseDcfFalsifier
  - l15GapLedger
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
    - "000660"
    - "138930"
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
    table=memo["tables"]["scenarioFalsifier"],
    values=memo["headline"],
    date=memo.get("asOf"),
    units=memo["units"],
    sources=memo["sources"],
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

