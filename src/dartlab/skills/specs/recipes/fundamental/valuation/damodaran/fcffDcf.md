---
id: recipes.fundamental.valuation.damodaran.fcffDcf
title: Damodaran FCFF DCF 밴드
category: recipes
kind: recipe
scope: builtin
status: curated
purpose: 정규화 FCFF, 재투자율, ROC, WACC를 조합해 고성장기, 전환기, 정상상태의 FCFF DCF 가치 밴드를 만드는 절차. 트리거 — 'FCFF DCF', 'Damodaran DCF band', 'terminal ROC consistency'.
whenToUse:
  - FCFF DCF
  - Damodaran DCF band
  - terminal ROC consistency
  - intrinsic value DCF
  - 다모다란 가치 밴드
linkedSkills:
  - recipes.fundamental.valuation.damodaran.normalizedFinancials
  - recipes.fundamental.valuation.damodaran.reinvestmentRoc
  - recipes.fundamental.valuation.damodaran.costOfCapital
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
  - bear/base/bull FCFF DCF ?? ??
  - terminal value share? terminal growth/ROC consistency check
  - per-share/upside ?? ?? ??? blocker

expectedNovelty:
  - damodaranL15Memo
  - reverseDcfFalsifier
  - l15GapLedger
forbidden:
  - terminal growth가 risk-free rate를 초과하는 가정을 통과시키지 않는다.
  - reinvestment 없이 고성장률만 넣지 않는다.
  - L2 엔진 호출 금지.
failureModes:
  - terminal value가 전체 가치의 대부분인데 민감도 누락
  - negative FCFF를 기계적으로 평균
  - 금융업에 generic FCFF 적용
examples:
  - 삼성전자 FCFF DCF band
  - AAPL terminal growth consistency
  - INTC turnaround DCF blocker
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
  description: "terminal growth, ROC, reinvestment가 서로 불일치해도 fair value band를 확정하면 실패로 본다."
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
    table=memo["tables"]["fcffDcf"],
    values=memo["headline"],
    date=memo.get("asOf"),
    units=memo["units"],
    sources=memo["sources"],
)
```

## 호출 동작

### 1. 결론 도출

가치 밴드는 `bear`, `base`, `bull` 3개로 낸다. 결론은 “현재가 대비 할인율”보다 “어떤 성장·마진·ROC 스토리가 가격에 필요한가”를 함께 말한다.

### 2. 핵심 근거 수집

정규화 FCFF, 성장률, 재투자율, ROC, WACC, terminal growth ceiling, 가격 path를 사용한다.

### 3. 메커니즘 분석

명시기간 FCFF는 매출 성장, 마진, 세율, 재투자로 만든다. terminal value는 정상상태 ROC와 재투자율이 terminal growth를 설명할 때만 통과한다.

### 4. 반례·한계

terminal value 비중이 과도하면 결론을 낮춘다. turnaround 기업은 normalized FCFF가 양수로 전환되는 근거가 없으면 blocked로 둔다.

### 5. 후속 모니터링

마진, sales-to-capital, WACC, terminal growth 민감도를 `scenarioFalsifier`로 넘긴다.

## 대표 반환 형태

`dcfBand : dict` — `bear`, `base`, `bull`, `terminalValueShare`, `assumptionTable`, `consistencyFlags`, `fallbacks`를 담는다.

## 연계 절차

1. recipes.fundamental.valuation.damodaran.costOfCapital - 할인율 범위.
2. recipes.fundamental.valuation.damodaran.relativeCheck - DCF 결과의 peer sanity check.
3. recipes.fundamental.valuation.damodaran.scenarioFalsifier - reverse DCF와 민감도 반증.

## 기본 검증

- terminal growth는 country risk-free rate 이하.
- growth는 reinvestmentRate x ROC로 설명 가능해야 한다.
- price path가 없으면 reverse DCF와 현재가 비교는 blocked 처리한다.

