---
id: engines.flow.securitiesLending
title: Flow — 대차잔고 (securitiesLending)
category: engines
kind: curated
scope: builtin
status: drafted
purpose: 대차잔고 (주식 대여 잔량) — 공매도 선행 지표 + 차익거래 활용. 예탁원 대차거래 통계 SSOT. **status=drafted — 예탁원 endpoint 인프라 선결**.
whenToUse:
  - 대차잔고
  - securities lending
  - 주식 대여
  - 공매도 선행
  - 대차 z
capabilityRefs: []
knowledgeRefs:
  - engines.flow
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
  - engines.flow
  - engines.flow.shortInterest
---

## 엔진 역할

대차잔고 = 대여된 주식 누적량. 공매도 = 대차거래 후 매도 → 대차잔고는 공매도 선행 지표 (1~2 주). 단, 대차의 절반은 헷지 + 차익 + 옵션 인수 등 비-공매도 활용.

## 공개 호출 방식

```python
import dartlab
sl = dartlab.flow("securitiesLending", code="005930", days=30)
# → dict: balance · z252 · shortPredict
```

## 호출 동작

한국예탁결제원 대차거래 endpoint → 종목 일별 잔고. 252 일 z. shortInterest 와의 lead-lag 정량화.

## 대표 반환 형태

```text
dict
  stockCode : str
  balance : int               # 대차잔고 (주)
  balanceRatio : float        # 시총 대비 (%)
  z252 : float
  shortLeadDays : int         # 공매도 leading days (lag-lead 분석)
  dateRef : str
```

## 기본 검증

- balance ≥ 0.
- shortLeadDays 정수 (lag-lead 분석 결과).
- 단위 주식 수 명시.

## 관련

- [engines.flow](/skills/engines.flow) — base SKILL
- [engines.flow.shortInterest](/skills/engines.flow.shortInterest) — 대차 후속 신호
