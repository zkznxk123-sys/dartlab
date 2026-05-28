---
id: engines.macro.fxRegime
title: Macro — FX Regime (USD/KRW)
category: engines
kind: curated
scope: builtin
status: drafted
purpose: USD/KRW 환율 regime 4 분류 (strong KRW / stable / weakening / crisis) + DXY 동행 + 실효환율 (REER) 비교. macro `exchange` axis sub-spec. KR 수출주 alpha 핵심 driver.
whenToUse:
  - USD/KRW
  - 원/달러
  - FX regime
  - 환율 regime
  - DXY
  - REER
  - 실효환율
capabilityRefs: []
knowledgeRefs:
  - engines.macro
  - engines.macro.observables
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: supported
  pyodide:
    status: limited
linkedSkills:
  - engines.macro
  - engines.macro.observables
---

## 엔진 역할

USD/KRW + DXY + REER 결합 regime 4 분류. KRW 절하 = 수출주 alpha + 수입물가 ↑. macro `exchange` axis 의 분류 어휘 SSOT.

## 공개 호출 방식

```python
import dartlab
fx = dartlab.macro("exchange", market="KR")
# → dict: usdkrw · dxy · reer · regime
```

## 4 regime

| regime | USD/KRW | DXY | REER | 수출주 |
|---|---|---|---|---|
| **strong KRW** | < 1100 | < 95 | overvalued | underperform |
| **stable** | 1100-1300 | 95-105 | fair | neutral |
| **weakening** | 1300-1450 | 105-110 | undervalued | outperform |
| **crisis** | > 1450 또는 급변 | > 110 | extreme | volatility 큼 |

## 호출 동작

한국은행 USD/KRW 일별 + ICE DXY + BIS REER 월별. 252 일 z + regime 분류.

## 대표 반환 형태

```text
dict
  usdkrw : float
  dxy : float
  reer : float            # 100 = 균형
  regime : str            # strong_krw/stable/weakening/crisis
  z252_usdkrw : float
  exportImpact : str      # outperform/neutral/underperform
  dateRef : str
```

## 기본 검증

- regime enum 4 종 (strong_krw/stable/weakening/crisis).
- usdkrw 단위 원, dxy / reer 단위 index.
- exportImpact enum (outperform/neutral/underperform).

## 관련

- [engines.macro](/skills/engines.macro) — base SKILL exchange axis
- [engines.macro.observables](/skills/engines.macro.observables) — FX indicator 카탈로그
