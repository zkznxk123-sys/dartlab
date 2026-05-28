---
id: engines.derivatives.riskNeutralDensity
title: Derivatives — Risk-Neutral Density (Breeden-Litzenberger)
category: engines
kind: curated
scope: builtin
status: drafted
purpose: 옵션 가격 → 위험중립확률밀도 (Breeden-Litzenberger 1978). 시장 implied 기초자산 분포 SSOT. 시장 기대 분포 + tail risk 정량화. **status=drafted — D-track 선결**.
whenToUse:
  - risk-neutral density
  - Breeden-Litzenberger
  - implied 분포
  - tail risk
  - 시장 기대 분포
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
---

## 엔진 역할

Breeden-Litzenberger 1978 정통 — 옵션 가격 C(K) 2 차 미분 = 위험중립 확률밀도. 시장이 implied 기초자산 분포 직접 노출.

본 spec 은 산출 절차 + smoothing 방법 (cubic spline IV interpolation) + tail percentile (p1/p5/p95/p99) SSOT.

## 공개 호출 방식

```python
import dartlab
rnd = dartlab.derivatives("riskNeutralDensity", date="2026-05-28", expiry="30d")
# → DataFrame: strike · density · cdf · percentile
```

## 호출 동작

1. ivSurface → strike × IV (해당 expiry)
2. cubic spline IV interpolation (smooth surface)
3. Black-Scholes → C(K) 재계산 (smooth)
4. Breeden-Litzenberger: f(K) = e^(rT) × ∂²C/∂K²
5. tail percentile + skewness / kurtosis 산출

## 대표 반환 형태

```text
pl.DataFrame
  strike : float
  density : float          # 위험중립 확률밀도
  cdf : float              # 누적
  percentile : float       # 0~1

dict (summary)
  expiry : str
  spot : float
  forward : float
  p5 / p25 / p50 / p75 / p95 : float    # implied price percentile
  skewness : float
  kurtosis : float          # tail thickness
  dateRef : str
```

## 기본 검증

- density 적분 = 1 (확률밀도 정의).
- p5/p25/p50/p75/p95 단조 증가.
- skewness / kurtosis 정상 분포 비교 가능.

## 관련

- [engines.derivatives](/skills/engines.derivatives) — base SKILL
- [engines.derivatives.ivSurface](/skills/engines.derivatives.ivSurface) — RND 입력
