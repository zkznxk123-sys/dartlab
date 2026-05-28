---
id: recipes.derivatives.kospi200ImpliedVol
title: KOSPI200 Implied Volatility — ATM IV term structure
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: KOSPI200 옵션 ATM IV term structure (30d/60d/90d) + VKOSPI 비교. forward-looking volatility 측정. **status=drafted — D-track 선결**. 트리거 — 'KOSPI200 IV', 'implied volatility', 'IV term structure'.
whenToUse:
  - KOSPI200 IV
  - implied volatility
  - IV term structure
  - ATM IV
linkedSkills:
  - engines.derivatives
  - engines.derivatives.ivSurface
  - engines.derivatives.vkospi
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
visualRefs:
  - engines.viz.tableBackedChart
gap:
  primary:
    - derivatives
    - quant
testUniverse:
  market: KR
  stockCodes:
    - "005930"
  asOfPolicy: latest
falsifier:
  description: IV term structure 가 모든 만기 동일 = 데이터 수집 실패 (정상 시장에서 term 별 차이 expectable).
  pythonCheck: |
    assert iv_30d != iv_60d or iv_60d != iv_90d
expectedNovelty:
  - ivAtm30d
  - ivAtm60d
  - termSlope
forbidden:
  - IV ≠ realized volatility — 시장 기대 변동성이지 실제 X.
  - D-track 미가용 시 본 recipe 실행 금지 (status=drafted).
runtimeCompatibility:
  server:
    status: limited
  localPython:
    status: limited
  mcp:
    status: limited
  webAi:
    status: limited
  pyodide:
    status: limited
---

## 공개 호출 방식

```python
import dartlab
iv = dartlab.derivatives("ivSurface", date="2026-05-28")
atm_30d = iv.filter((pl.col("expiry_days") == 30) & (pl.col("moneyness") == "ATM"))
atm_60d = iv.filter((pl.col("expiry_days") == 60) & (pl.col("moneyness") == "ATM"))
atm_90d = iv.filter((pl.col("expiry_days") == 90) & (pl.col("moneyness") == "ATM"))

vkospi = dartlab.derivatives("vkospi", date="2026-05-28")
```

## 호출 동작

ATM IV (콜·풋 mid) 만기별 추출 + VKOSPI 비교 + term slope 산출. slope > 0 = contango (forward higher), < 0 = backwardation (panic).

## 대표 반환 형태

dict — `ivAtm30d/60d/90d` + `vkospi` + `termSlope` + `regime`.

## 연계 절차

1. 본 recipe → IV term structure snapshot.
2. backwardation → `engines.derivatives.vkospi` panic regime check.
3. `recipes.derivatives.vkospiRegime` 결합.
