---
id: recipes.fundamental.valuation.damodaran.normalizedFinancials
title: Damodaran 정규화 재무 패널
category: recipes
kind: recipe
scope: builtin
status: unverified
purpose: L1 재무제표만으로 매출, 영업이익, 세율, NOPAT, 운전자본, 감가상각, capex, FCF를 5-10년 패널로 정규화하는 절차. 트리거 — 'normalized financials', 'Damodaran 재무 정규화', 'FCFF 계산 전 패널'.
whenToUse:
  - normalized financials
  - Damodaran 재무 정규화
  - FCFF 계산 전 패널
  - NOPAT invested capital panel
  - 다모다란 정규화 재무
linkedSkills:
  - recipes.fundamental.valuation.damodaran.dataAudit
  - recipes.fundamental.valuation.damodaran.businessModelFit
  - engines.company
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
  - 5-10? normalized financial panel
  - revenue ? EBIT ? tax ? NOPAT ? FCFF? source trace
  - ?? ??? ??? fallback ??

expectedNovelty:
  - damodaranL15Memo
  - reverseDcfFalsifier
  - l15GapLedger
forbidden:
  - 결손 계정을 0으로 채우지 않는다.
  - 일회성 적자를 정상 마진으로 단정하지 않는다.
  - L2 엔진 호출 금지.
failureModes:
  - DART/EDGAR 계정명 차이를 같은 snakeId로 정규화하지 못함
  - capex 부호를 반대로 해석
  - flow 항목과 stock 항목을 같은 방식으로 합산
examples:
  - 삼성전자 10년 normalized financials
  - AAPL NOPAT invested capital 패널
  - 반도체 사이클 정상 마진 계산
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
  description: "revenue, operating income, CFO 중 하나라도 trace 없이 계산되면 정규화 패널 실패로 본다."
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
    table=memo["tables"]["normalizedFinancials"],
    values=memo["headline"],
    date=memo.get("asOf"),
    units=memo["units"],
    sources=memo["sources"],
)
```

## 호출 동작

### 1. 결론 도출

정규화 패널의 사용 가능 기간과 결손 계정을 먼저 말한다. 최소 5년 미만이면 DCF 가정보다 데이터 한계를 앞에 둔다.

### 2. 핵심 근거 수집

IS/BS/CF 연간 표와 주요 계정 trace를 묶는다. 매출, 영업이익, 법인세, CFO, capex, 감가상각, 현금, 총부채, 자본, 운전자본 계정의 출처를 남긴다.

### 3. 메커니즘 분석

NOPAT은 영업이익과 실효세율에서 만들고, invested capital은 영업자본 중심으로 계산한다. capex와 운전자본 증감은 FCFF 연결을 위해 따로 보관한다.

### 4. 반례·한계

세율이 음수이거나 60%를 넘으면 normalized tax fallback을 쓴다. 적자 기업은 단순 평균 대신 사이클 정상화 또는 turnaround flag를 남긴다.

### 5. 후속 모니터링

다음 단계는 재투자율, ROC, FCFF를 같은 패널에서 계산한다. 결손 계정은 `dataAudit` gap ledger로 되돌린다.

## 대표 반환 형태

`normalizedPanel : list[dict]` — `year`, `revenue`, `ebit`, `taxRate`, `nopat`, `investedCapital`, `cfo`, `capex`, `fcff`, `sourceTrace`를 담는다.

## 연계 절차

1. recipes.fundamental.valuation.damodaran.reinvestmentRoc - 정규화 패널에서 재투자율과 ROC 계산.
2. recipes.fundamental.valuation.damodaran.fcffDcf - FCFF 현금흐름으로 가치 밴드 계산.
3. recipes.fundamental.valuation.damodaran.scenarioFalsifier - 정규화 값으로 reverse DCF 반증.

## 기본 검증

- 각 핵심 계정은 trace 또는 명시적 fallback reason을 가져야 한다.
- flow 항목은 연간 flow, BS 항목은 연말 stock으로 취급한다.

