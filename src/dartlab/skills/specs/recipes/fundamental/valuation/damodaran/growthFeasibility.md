---
id: recipes.fundamental.valuation.damodaran.growthFeasibility
title: Damodaran 성장 실현가능성 검증
category: recipes
kind: recipe
scope: builtin
status: tested
purpose: 성장률이 reinvestment rate와 ROC로 설명되는지, 현재 가격이 요구하는 성장률이 정규화 재무와 맞는지 검증하는 Damodaran식 value driver 반증 절차. 트리거 — 'growth feasibility', '성장률 실현가능성', 'reinvestment ROC consistency'.
whenToUse:
  - growth feasibility
  - 성장률 실현가능성
  - reinvestment ROC consistency
  - 내재 성장률 검증
  - Damodaran growth driver
linkedSkills:
  - recipes.fundamental.valuation.damodaran.normalizedFinancials
  - recipes.fundamental.valuation.damodaran.reinvestmentRoc
  - recipes.fundamental.valuation.damodaran.costOfCapital
  - recipes.fundamental.valuation.damodaran.scenarioFalsifier
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - sourceRef
  - tableRef
  - valueRef
  - dateRef
  - executionRef
expectedOutputs:
  - ?? ?? ? normalized growth ? reverse DCF ?? ?? ??
  - growth feasibility status? break condition
  - ?? ??? ???/ROC? ???? ??

expectedNovelty:
  - growthFromReinvestmentRoc
  - requiredReinvestmentRate
  - reverseGrowthComparison
forbidden:
  - 성장률을 임의 입력값으로만 두지 않는다.
  - reverse DCF 없이 현재 가격이 요구하는 성장 스토리를 단정하지 않는다.
  - L2 엔진 호출 금지.
failureModes:
  - 재투자율이 음수인데 고성장을 통과
  - ROC가 WACC보다 낮은데 terminal growth를 높게 둠
  - marketCap 결손인데 reverse growth를 usable로 표시
examples:
  - 삼성전자 성장률이 ROC와 재투자로 설명되는지
  - AAPL 현재가 내재 성장률 검증
  - INTC turnaround 성장 가정 반증
gap:
  primary:
    - synth
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
  description: "성장률이 reinvestment x ROC로 설명되지 않는데 DCF 가정을 통과시키면 실패로 본다."
lastUpdated: "2026-05-14"
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
    table=memo["tables"]["growthFeasibility"],
    values=memo["headline"],
    date=memo.get("asOf"),
    units=memo["units"],
    sources=memo["sources"],
)
```

## 호출 동작

### 1. 결론 도출

최근 성장률이 normalized ROC와 required reinvestment rate로 설명되는지 판정한다. 가격과 시총이 있으면 reverse DCF의 요구 성장률도 함께 비교한다.

### 2. 핵심 근거 수집

정규화 매출 성장률, 최신 reinvestment rate, latest/normalized ROC, sales-to-capital, marketCap 기반 reverse growth를 사용한다.

### 3. 메커니즘 분석

Damodaran식 성장 가정은 `growth = reinvestment rate x ROC`로 닫혀야 한다. 성장률이 높아도 reinvestment와 ROC가 뒷받침하지 못하면 DCF 가정은 stretched로 낮춘다.

### 4. 반례·한계

적자 또는 턴어라운드 기업은 과거 reinvestment rate가 왜곡될 수 있다. 이 경우 status를 `partialNoMarketCap` 또는 `stretched`로 낮추고 별도 turnaround gate를 요구한다.

### 5. 후속 모니터링

다음 분기 매출 성장률, 영업마진, capex, 운전자본 증감, ROC-WACC spread를 추적한다.

## 대표 반환 형태

`growthFeasibility : list[dict]` — `metric`, `value`, `status`를 담는다.

## 연계 절차

1. recipes.fundamental.valuation.damodaran.reinvestmentRoc - value driver 입력.
2. recipes.fundamental.valuation.damodaran.costOfCapital - ROC-WACC 비교.
3. recipes.fundamental.valuation.damodaran.scenarioFalsifier - reverse DCF 요구 성장률 비교.
4. recipes.fundamental.valuation.damodaran.fcffDcf - 통과한 성장 가정만 DCF로 전달.

## 기본 검증

- growth, reinvestment, ROC 중 하나라도 없으면 usable로 확정하지 않는다.
- marketCap이 없으면 reverse growth는 blocked/partial이어야 한다.
- 5개 고정 타깃에서 evidence completeness 1.00을 통과해야 한다.
