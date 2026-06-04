---
id: recipes.fundamental.valuation.damodaran.lifeCycleClassifier
title: Damodaran 생애주기 분류
category: recipes
kind: recipe
scope: builtin
status: curated
purpose: L1 재무 패널만으로 Damodaran식 기업 생애주기(highGrowth, matureGrowth, matureStable, decline, turnaround, financialFirmOnly)를 분류하고 DCF 가정의 출발점을 고정하는 절차. 트리거 — 'Damodaran life cycle', '기업 생애주기 분류', '성장 단계 판정'.
whenToUse:
  - Damodaran life cycle
  - 기업 생애주기 분류
  - 성장 단계 판정
  - mature growth stable decline
  - DCF 가정 출발점
linkedSkills:
  - recipes.fundamental.valuation.damodaran.dataAudit
  - recipes.fundamental.valuation.damodaran.businessModelFit
  - recipes.fundamental.valuation.damodaran.normalizedFinancials
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
  - growth ? margin ? ROC-WACC spread ?? life-cycle phase
  - phase? valuation assumption ??
  - ?? confidence? ?? ??

expectedNovelty:
  - lifeCyclePhase
  - growthMarginRocEvidence
  - financialFirmBlocker
forbidden:
  - 금융업을 generic FCFF 생애주기로 통과시키지 않는다.
  - 단일 연도 성장률만으로 highGrowth 또는 decline을 확정하지 않는다.
  - L2 엔진 호출 금지.
failureModes:
  - 경기순환 저점의 적자를 영구 decline으로 오판
  - FCF 전환 여부 없이 turnaround를 놓침
  - ROC-WACC spread를 보지 않고 성장률만으로 단계 분류
examples:
  - 삼성전자 Damodaran 생애주기 분류
  - INTC turnaround gate
  - 138930 금융업 generic FCFF 차단
gap:
  primary:
    - synth
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
  description: "금융업 또는 FCF 결손 기업을 정상 matureStable로 통과시키면 실패로 본다."
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
    table=memo["tables"]["lifeCycleClassifier"],
    values=memo["headline"],
    date=memo.get("asOf"),
    units=memo["units"],
    sources=memo["sources"],
)
```

## 호출 동작

### 1. 결론 도출

최근 성장률, 정상 마진, ROC-WACC spread, FCFF 양수 비율로 생애주기 phase를 낸다. 금융업은 `financialFirmOnly`로 분리하고 generic FCFF phase를 부여하지 않는다.

### 2. 핵심 근거 수집

`normalizedFinancials`의 매출 성장, 영업마진, FCFF, `reinvestmentRoc`의 ROC, `costOfCapital`의 WACC를 사용한다.

### 3. 메커니즘 분석

성장률이 높고 ROC가 WACC를 넘으면 growth 단계, 성장률이 낮고 현금흐름이 안정되면 stable 단계, 성장률이 음수거나 FCFF 전환 근거가 약하면 decline/turnaround로 낮춘다.

### 4. 반례·한계

순환주는 단순 최근 5년 성장률만으로 안정 단계로 확정하지 않는다. cycle-normal margin은 별도 `cyclicalNormalizer`가 채워질 때까지 fallback이다.

### 5. 후속 모니터링

다음 단계는 phase별 성장률 상한, terminal margin, reinvestment rate를 `growthFeasibility`와 `fcffDcf`에 넘긴다.

## 대표 반환 형태

`lifeCycleClassifier : list[dict]` — `metric`, `value`, `status`, `confidence`, `source`를 담는다.

## 연계 절차

1. recipes.fundamental.valuation.damodaran.businessModelFit - 금융업/특수상황 차단.
2. recipes.fundamental.valuation.damodaran.normalizedFinancials - 성장률과 FCFF 패널.
3. recipes.fundamental.valuation.damodaran.growthFeasibility - phase와 성장 가정 정합성 검증.

## 기본 검증

- 5개 고정 타깃에서 실행되어야 한다.
- `138930`은 generic FCFF phase가 아니라 financial-firm blocker로 남아야 한다.
- 최소 3년 미만 패널은 phase 확정 금지.
