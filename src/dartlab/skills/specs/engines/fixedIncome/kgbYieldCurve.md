---
id: engines.fixedIncome.kgbYieldCurve
title: Fixed Income — KGB Yield Curve Regime
category: engines
kind: curated
scope: builtin
status: drafted
purpose: 국고채 (KGB) yield curve regime + butterfly + 역전 신호. 4 phase (steepening/flattening/inversion/normal). recession indicator (10Y-3M / 10Y-2Y). **status=drafted — KOFIA 인프라 선결**.
whenToUse:
  - 국고채 yield curve
  - KGB curve
  - yield curve regime
  - 역전 신호
  - butterfly
  - 2s10s
  - 3m10y
capabilityRefs: []
knowledgeRefs:
  - engines.fixedIncome
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
linkedSkills:
  - engines.fixedIncome
  - engines.macro.cycles
---

## 엔진 역할

KGB yield curve = 만기 (3M/1Y/3Y/5Y/10Y/20Y/30Y) × yield. 4 regime + butterfly. 10Y-3M / 10Y-2Y spread 가 recession 1~2 년 선행 (US 학술 정통, KR 도 부분 적용).

## 공개 호출 방식

```python
import dartlab
yc = dartlab.fixedIncome("kgbYieldCurve", date="2026-05-28")
# → dict: curve · slope · butterfly · regime
```

## 호출 동작

KOFIA 일별 국고채 yield + slope (10Y-2Y, 10Y-3M) + butterfly (2*5Y - 2Y - 10Y) + regime 분류.

## 4 regime

- **steepening** : 장단기 차 ↑ (recovery / expansion early)
- **flattening** : 장단기 차 ↓ (late cycle)
- **inversion** : 단기 > 장기 (recession 1-2y 선행)
- **normal** : 평탄

## 대표 반환 형태

```text
dict
  curve : dict                # {3M: 3.5, 1Y: 3.3, ..., 30Y: 3.8}
  slope_10y_2y : float        # bp
  slope_10y_3m : float        # bp
  butterfly_2_5_10 : float
  regime : str
  inversionDays : int         # 역전 지속일 (역전 시)
  dateRef : str
```

## 기본 검증

- curve dict 만기 enum 안.
- slope / butterfly 단위 bp.
- regime enum 4 종.
- inversionDays ≥ 0.

## 관련

- [engines.fixedIncome](/skills/engines.fixedIncome) — base SKILL
- [engines.macro.cycles](/skills/engines.macro.cycles) — curve 신호 → cycle phase 입력
