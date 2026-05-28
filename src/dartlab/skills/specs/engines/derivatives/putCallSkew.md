---
id: engines.derivatives.putCallSkew
title: Derivatives — Put-Call Skew (25Δ)
category: engines
kind: curated
scope: builtin
status: drafted
purpose: 25Δ put-call skew (25Δ put IV - 25Δ call IV) — 하방 헷지 수요 z-score. 시장 fear gauge forward-looking. **status=drafted — D-track 선결**.
whenToUse:
  - put-call skew
  - 25Δ skew
  - 하방 헷지
  - fear gauge
  - volatility smile
capabilityRefs: []
knowledgeRefs:
  - engines.derivatives
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
  - engines.derivatives.ivSurface
  - engines.derivatives.vkospi
---

## 엔진 역할

25Δ skew = 25Δ put IV − 25Δ call IV. 하방 헷지 수요 시장 측정. skew ↑ = 풋 비싸 = 하방 우려 ↑. VIX/VKOSPI 와 직교 신호 (VKOSPI 는 ATM IV 합산, skew 는 OTM IV 비대칭).

## 공개 호출 방식

```python
import dartlab
skew = dartlab.derivatives("putCallSkew", date="2026-05-28", expiry="30d")
# → dict: skew25d · skewZ · regime · smileMetrics
```

## 호출 동작

ivSurface 에서 25Δ 행사가 추출 (forward 대비 25Δ moneyness) → put IV - call IV. 252 일 z-score 동행.

- 만기 표준: 30d / 60d / 90d (3 종 동시)
- z-score baseline = 252 일 rolling
- regime: low (z < -1) / normal / elevated (z > 1) / extreme (z > 2)

## 대표 반환 형태

```text
dict
  skew25d_30d : float       # 25Δ skew 30 일 (IV pt)
  skewZ_30d : float         # 252 일 z-score
  regime : str              # low/normal/elevated/extreme
  smileMetrics : dict       # convexity / butterfly / risk reversal
  dateRef : str
```

## 기본 검증

- skew 단위 IV pt (% 차이).
- z-score 252 일 baseline 명시.
- regime enum 4 종 안 (low/normal/elevated/extreme).

## 관련

- [engines.derivatives](/skills/engines.derivatives) — base SKILL
- [engines.derivatives.vkospi](/skills/engines.derivatives.vkospi) — ATM IV regime (직교 신호)
