---
id: recipes.fundamental.flow.shortInterestSpike
title: Short Interest Spike — 공매도 잔고 z>2 detection
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: 공매도 잔고 z-score > 2 종목 detection — 단기 squeeze 위험 vs 진짜 하방 신호 구분 (잔고 비율 + 대차잔고 동행 확인). **status=drafted**. 트리거 — '공매도 spike', 'short interest spike', '공매도 잔고 급증', 'short squeeze'.
whenToUse:
  - 공매도 spike
  - short interest spike
  - 공매도 잔고 급증
  - short squeeze
linkedSkills:
  - engines.flow.shortInterest
  - engines.flow.securitiesLending
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - valueRef
  - dateRef
  - executionRef
  - sourceRef
visualRefs:
  - engines.viz.tableBackedChart
gap:
  primary:
    - flow
    - scan
testUniverse:
  market: KR
  stockCodes:
    - "005930"
  asOfPolicy: latest
falsifier:
  description: z > 2 진입 후 30d 가격 평균 -5% 이상 = 진짜 신호. 평균 0 근처 = squeeze 가능성.
  pythonCheck: |
    assert avg_post_return_30d != 0
expectedNovelty:
  - balanceZ
  - balanceRatio
  - squeezeRisk
forbidden:
  - 공매도 spike = 절대 매도 신호 X — 평균 lag 작고 squeeze 위험.
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
---

## 공개 호출 방식

```python
import dartlab
sl = dartlab.flow("shortInterest", code="005930", days=30)
if sl["z252"] > 2:
    # 대차잔고 동행 확인
    sb = dartlab.flow("securitiesLending", code="005930", days=30)
    squeeze_risk = sb["z252"] < 0   # 대차 부족 = squeeze 위험
```

## 호출 동작

공매도 잔고 z > 2 종목 + 대차잔고 z 동행 확인 + 시총 대비 비율.

## 대표 반환 형태

dict — `balanceZ + balanceRatio + lendingZ + squeezeRisk + signal`.

## 연계 절차

1. 본 recipe → 공매도 spike + squeeze 위험.
2. squeezeRisk True → 단기 short cover rally 후보.
3. squeezeRisk False + 잔고비율 ↑ → 하방 신호 후보 검증.
