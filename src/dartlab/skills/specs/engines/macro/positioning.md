---
id: engines.macro.positioning
title: Macro — CFTC COT Positioning
category: engines
kind: curated
scope: builtin
status: drafted
purpose: CFTC Commitments of Traders (COT) 보고서 — 상품/통화/금리 선물 포지셔닝 (commercial vs non-commercial vs small spec) z-score. 시장 sentiment 측정.
whenToUse:
  - CFTC COT
  - 포지셔닝
  - positioning
  - 선물 포지션
  - commercial
  - non-commercial
  - small spec
capabilityRefs: []
knowledgeRefs:
  - engines.macro
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
  - engines.macro
---

## 엔진 역할

CFTC COT 주간 보고서 — 선물 시장 포지션 3 그룹 (commercial = hedger / non-commercial = speculator / small spec). non-commercial net long z 가 sentiment 측정 표준.

## 공개 호출 방식

```python
import dartlab
pos = dartlab.macro("positioning", contract="DXY", weeks=52)
# → dict: longShort · z52 · regime
```

## 호출 동작

CFTC 주간 endpoint → contract 별 long/short + net + z-score (52 주 baseline).

## 대표 반환 형태

```text
dict
  contract : str
  commercialNet : int
  nonCommercialNet : int
  smallSpecNet : int
  z52_nonCommercial : float
  regime : str               # extreme_short / short / neutral / long / extreme_long
  dateRef : str              # 주 단위 (화요일 기준)
```

## 기본 검증

- commercialNet + nonCommercialNet + smallSpecNet 합 = 0 (시장 균형).
- dateRef 화요일 (CFTC 표준).
- regime enum 5 종 (extreme_short/short/neutral/long/extreme_long).

## 관련

- [engines.macro](/skills/engines.macro) — base SKILL
