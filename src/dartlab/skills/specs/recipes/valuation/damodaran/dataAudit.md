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
expectedOutputs:
  - IS/BS/CF/??/??/reference ?? ??? ?
  - usable ? usableWithFallback ? blocked ??
  - missing evidence? fallback reason ??

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
    table=memo["tables"]["dataAudit"],
    values=memo["headline"],
    date=memo.get("asOf"),
    units=memo["units"],
    sources=memo["sources"],
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

