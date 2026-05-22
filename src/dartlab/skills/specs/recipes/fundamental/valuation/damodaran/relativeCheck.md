---
id: recipes.fundamental.valuation.damodaran.relativeCheck
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
  - recipes.fundamental.valuation.damodaran.fcffDcf
  - engines.scan
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
  - EV/Sales ? EV/EBIT ? P/B ? ???? sanity check
  - DCF ??? multiple implied story ??
  - US/KR peer availability? partial fallback

expectedNovelty:
  - damodaranL15Memo
  - reverseDcfFalsifier
  - l15GapLedger
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
    - "000660"
    - "138930"
    - "AAPL"
    - "INTC"
  asOfPolicy: latest
falsifier:
  description: "US valuation scan 부재를 partial gap으로 표시하지 않으면 실패로 본다."
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
    table=memo["tables"]["relativeCheck"],
    values=memo["headline"],
    date=memo.get("asOf"),
    units=memo["units"],
    sources=memo["sources"],
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

1. recipes.fundamental.valuation.damodaran.fcffDcf - DCF 결과 입력.
2. recipes.fundamental.valuation.damodaran.scenarioFalsifier - multiple이 깨는 가정 반증.
3. recipes.fundamental.valuation.damodaran.deepDive - 최종 memo에 gap 반영.

## 기본 검증

- US 기업은 `partial` 또는 `blocked` 표시 없이 relative valuation 완료 선언 금지.
- multiple 결과는 DCF 가정 검산으로만 사용한다.

