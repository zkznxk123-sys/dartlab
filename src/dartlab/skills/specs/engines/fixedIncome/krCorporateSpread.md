---
id: engines.fixedIncome.krCorporateSpread
title: Fixed Income — KR 회사채 Spread
category: engines
kind: curated
scope: builtin
status: drafted
purpose: KR 회사채 spread (회사채 yield - 국고채 yield) 일별 by rating (AAA/AA+/AA/AA-/A+/A/A-/BBB+/BBB/BBB-) × tenor (1Y/3Y/5Y). KIS평가 SSOT. **status=drafted — KIS API 인프라 선결**.
whenToUse:
  - 회사채 spread
  - corporate spread
  - KR 회사채
  - 신용 spread
  - rating × tenor
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
  - engines.credit
---

## 엔진 역할

KR 회사채 spread = 회사채 yield − 동일 tenor 국고채 yield. rating × tenor 격자 + 252 일 z + regime (compressed / normal / widening / extreme).

## 공개 호출 방식

```python
import dartlab
cs = dartlab.fixedIncome("krCorporateSpread", rating="AA", tenor="3Y", days=30)
# → DataFrame: date · spread · z252 · regime
```

## 호출 동작

KIS평가 일별 회사채 평균 yield + KOFIA 국고채 → spread 산출 + z + regime.

## 대표 반환 형태

```text
pl.DataFrame
  date : str
  rating : str               # AAA/AA+/.../BBB-
  tenor : str                # 1Y/3Y/5Y
  spread : float             # bp
  z252 : float
  regime : str               # compressed/normal/widening/extreme
```

## 기본 검증

- spread 단위 bp + 양수 (회사채 yield > 국고채 yield).
- rating × tenor 조합 enum 안.
- regime enum 4 종 (compressed/normal/widening/extreme).

## 관련

- [engines.fixedIncome](/skills/engines.fixedIncome) — base SKILL
- [engines.credit](/skills/engines.credit) — 회사 단위 dCR rating 과 결합
