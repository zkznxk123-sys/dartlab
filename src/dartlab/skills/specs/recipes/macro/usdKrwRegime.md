---
id: recipes.macro.usdKrwRegime
title: USD/KRW Regime — KR 수출주 alpha driver
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: USD/KRW 4 regime × KR 수출주 alpha 정합 — KRW 절하 시 수출주 outperform (반도체/자동차/조선). DXY + REER 동행. **status=drafted (engines.macro.fxRegime 신설 동행)**. 트리거 — 'USD/KRW regime', '환율 regime', 'KRW 절하', '수출주 alpha', 'FX regime'.
whenToUse:
  - USD/KRW regime
  - 원/달러 regime
  - 수출주 alpha
  - KRW 절하
  - DXY 동행
linkedSkills:
  - engines.macro.fxRegime
  - engines.scan
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
    - macro
    - scan
testUniverse:
  market: KR
  stockCodes:
    - "005930"
    - "005380"
  asOfPolicy: latest
falsifier:
  description: 4 regime 별 수출주 alpha 차이 0 = FX 영향 없음 = signal 가치 없음.
  pythonCheck: |
    assert abs(export_alpha_strong - export_alpha_weak) > 0.01
expectedNovelty:
  - regime
  - exportImpact
  - exportAlpha
forbidden:
  - KRW 절하 = 수출주 절대 매수 신호 X (산업 별 차이, 원자재 수입 비중 차이).
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
---

## 공개 호출 방식

```python
import dartlab
fx = dartlab.macro("exchange", market="KR")
regime = fx["regime"]
export_codes = ["005930", "005380", "012450"]   # 반도체/자동차/조선 대표
```

## 호출 동작

USD/KRW regime + DXY + REER + 수출주 universe (KR 매출 비중 < 50% 또는 명시 list) alpha 정합.

## 대표 반환 형태

dict — `regime + usdkrw + reer + exportAlpha + winnerSectors`.

## 연계 절차

1. 본 recipe → FX regime + 수출주 alpha.
2. weakening regime → 반도체/자동차 outperform 후보.
3. `recipes.industry.sectorMomentumLeadership` 결합.
