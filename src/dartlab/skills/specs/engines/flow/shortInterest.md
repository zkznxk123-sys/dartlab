---
id: engines.flow.shortInterest
title: Flow — 공매도 잔고 (shortInterest)
category: engines
kind: curated
scope: builtin
status: drafted
purpose: 공매도 잔고 z-score + 매도잔고 비율 + 단주 매도 비중. KRX 공매도 잔고 일별 데이터 SSOT. **status=drafted — KRX `srt` 카테고리 인프라 선결**.
whenToUse:
  - 공매도 잔고
  - short interest
  - 대차잔고 매도
  - short balance
  - 매도잔고 z
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
---

## 엔진 역할

공매도 잔고 = 매도 후 미환매 주식 수. 잔고 ↑ = 하락 베팅 누적 (또는 헷지). 252 일 z-score 로 단방향 해석 회피.

## 공개 호출 방식

```python
import dartlab
sl = dartlab.flow("shortInterest", code="005930", days=30)
# → dict: balance · balanceRatio · z252 · trend
```

## 호출 동작

KRX 공매도 종합 endpoint → 종목 일별 잔고 + 시가총액 대비 비율. 252 일 rolling z.

## 대표 반환 형태

```text
dict
  stockCode : str
  balance : int               # 공매도 잔고 (주)
  balanceRatio : float        # 시총 대비 (%)
  z252 : float                # 252 일 z-score
  trend : str                 # rising / stable / falling
  dateRef : str
```

## 기본 검증

- balance ≥ 0.
- balanceRatio = balance × close / marketCap (시총 대비) 계산 정합.
- trend enum 3 종 (rising/stable/falling).

## 관련

- [engines.flow](/skills/engines.flow) — base SKILL
