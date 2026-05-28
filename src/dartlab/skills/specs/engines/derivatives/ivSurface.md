---
id: engines.derivatives.ivSurface
title: Derivatives — IV Surface (strike × expiry)
category: engines
kind: curated
scope: builtin
status: drafted
purpose: KOSPI200 옵션 IV (implied volatility) surface — strike × expiry 2 차원 격자. ATM IV term structure + smile/skew 분석 SSOT. **status=drafted — D-track 인프라 선결**.
whenToUse:
  - IV surface
  - implied volatility
  - ATM IV
  - term structure
  - volatility smile
  - 옵션 IV
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
  - engines.derivatives.putCallSkew
---

## 엔진 역할

KOSPI200 옵션 IV surface — strike × expiry 2 차원. ATM IV 항을 forward-looking volatility 측정 정공.

## 공개 호출 방식

```python
import dartlab
iv = dartlab.derivatives("ivSurface", date="2026-05-28", expiry="all")
# → DataFrame: expiry · strike · ivCall · ivPut · midIV
```

## 호출 동작

KRX 옵션 일별 데이터에서 strike × expiry 격자 추출 + Black-Scholes inverse 로 IV 산출 (옵션 가격 → IV).

- ATM strike 자동 식별 (forward 기준)
- 외삽 금지 — 실거래 strike 만
- expiry weekly/monthly/quarterly 분리

## 대표 반환 형태

```text
pl.DataFrame
  expiry : str          # YYYY-MM-DD
  strike : float        # 행사가
  ivCall : float        # 콜 IV (%)
  ivPut : float         # 풋 IV (%)
  midIV : float         # mid (put-call parity 사용)
  volume : int
  openInt : int
```

## 기본 검증

- expiry 단위 표준 YYYY-MM-DD.
- IV 단위 % (소수 아닌 백분율).
- 같은 strike × expiry 의 ivCall ≈ ivPut (put-call parity, 차이 < 0.5%).

## 관련

- [engines.derivatives](/skills/engines.derivatives) — base SKILL
- [engines.derivatives.putCallSkew](/skills/engines.derivatives.putCallSkew) — surface 의 skew 추출
