---
id: engines.macro.commodityCycle
title: Macro — Commodity Cycle (Copper-Gold + Oil)
category: engines
kind: curated
scope: builtin
status: drafted
purpose: 원자재 사이클 — Copper-Gold ratio (성장 sentiment) + WTI 사이클 + Iron Ore 중국 PMI 선행. KR 시장 수출주·소재주 alpha driver.
whenToUse:
  - 원자재
  - commodity cycle
  - copper-gold
  - WTI
  - 유가
  - iron ore
  - 중국 PMI
capabilityRefs: []
knowledgeRefs:
  - engines.macro
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
  - engines.macro.cycles
---

## 엔진 역할

원자재 cycle 3 신호 결합:
- **Copper-Gold ratio**: 성장 vs 안전 sentiment (ratio ↑ = 위험자산 alpha)
- **WTI cycle**: 글로벌 수요 + OPEC 공급
- **Iron Ore**: 중국 PMI 선행 (3-6 개월)

## 공개 호출 방식

```python
import dartlab
co = dartlab.macro("commodityCycle", market="global")
# → dict: copperGold · wti · ironOre · regime
```

## 호출 동작

LME 구리 / COMEX 금 / WTI / SGX Iron Ore 일별 → ratio + z + regime.

## 대표 반환 형태

```text
dict
  copper : float            # USD/ton
  gold : float              # USD/oz
  copperGoldRatio : float
  wti : float               # USD/bbl
  ironOre : float           # USD/ton
  regime : str              # risk_on / mixed / risk_off
  z252 : dict
  dateRef : str
```

## 기본 검증

- copper/gold/wti 단위 USD 명시 (ton / oz / bbl).
- regime enum 3 종 (risk_on/mixed/risk_off).
- z252 단위 σ.

## 관련

- [engines.macro](/skills/engines.macro) — base SKILL
- [engines.macro.cycles](/skills/engines.macro.cycles) — copper-gold 가 cycle phase 보조 신호
