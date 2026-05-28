---
id: engines.derivatives.vkospi
title: Derivatives — VKOSPI Regime
category: engines
kind: curated
scope: builtin
status: drafted
purpose: VKOSPI (KOSPI200 옵션 implied volatility index) regime 분류 — KR 시장 fear gauge. 4 regime (calm/normal/elevated/panic) + macro regime 정합. **status=drafted — D-track 선결**.
whenToUse:
  - VKOSPI
  - V-KOSPI
  - KOSPI200 IV
  - fear gauge
  - 변동성 regime
  - 옵션 변동성
capabilityRefs: []
knowledgeRefs:
  - engines.derivatives
  - engines.macro.regimes
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
  - engines.derivatives
  - engines.macro.regimes
---

## 엔진 역할

VKOSPI = KOSPI200 옵션 30 일 model-free implied volatility (VIX 한국판). 시장 fear gauge forward-looking. 본 spec 은 VKOSPI level 의 regime 분류 SSOT + macro regime (engines.macro.regimes 5 enum) 정합 매핑.

## 공개 호출 방식

```python
import dartlab
vk = dartlab.derivatives("vkospi", date="2026-05-28")
# → dict: level · regime · macroAlignment
```

## 호출 동작

KRX VKOSPI 일별 데이터 (또는 옵션 chain 으로부터 자체 산출). 4 regime 분류:

- **calm** : level < 15 (variance crush)
- **normal** : 15 ≤ level < 25
- **elevated** : 25 ≤ level < 40
- **panic** : level ≥ 40 (위기)

macroAlignment: macro regime (expansion/slowdown/contraction/recovery/crisis) vs VKOSPI regime 일치성. crisis ↔ panic 동시 = 강한 신호.

## 대표 반환 형태

```text
dict
  level : float              # VKOSPI level (%)
  regime : str               # calm/normal/elevated/panic
  z252 : float               # 252 일 z-score
  macroRegime : str          # engines.macro.regimes 5 enum 동행
  macroAlignment : bool
  dateRef : str
```

## 기본 검증

- level 단위 % (VIX 표준).
- regime enum 4 종 안 (calm/normal/elevated/panic).
- macroAlignment 시 `engines.macro.regimes` 5 enum 동시 인용.

## 관련

- [engines.derivatives](/skills/engines.derivatives) — base SKILL
- [engines.macro.regimes](/skills/engines.macro.regimes) — macro 5 regime 정합 매핑
