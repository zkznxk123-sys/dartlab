---
id: engines.recipe.creditCycleStressMap
title: 신용사이클 스트레스 지도
category: engines
kind: recipe
scope: builtin
status: drafted
purpose: BIS Credit-to-GDP gap, Minsky phase, Koo balance sheet recession, Fisher debt deflation, HY spread 등 macro.crisis의 신용 관련 출력을 묶어 신용사이클 위치와 tipping point를 읽는 절차. 트리거 — '신용사이클', 'credit stress', 'Minsky', '부채 디플레이션', '금융위기 신호'.
whenToUse:
  - 신용사이클
  - credit cycle
  - credit stress
  - Minsky phase
  - 부채 디플레이션
  - 금융위기 신호
linkedSkills:
  - engines.macro.crisis
  - engines.macro.liquidity
  - engines.macro.rates
  - engines.macro.summary
  - engines.credit
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - dateRef
  - valueRef
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
gap:
  primary:
    - macro
    - credit
testUniverse:
  market: US
  asOfPolicy: latest
falsifier:
  description: "creditGap, minskyPhase, recessionDashboard 중 2개 이상이 없으면 신용사이클 위치 판정으로 쓰지 않는다."
expectedNovelty:
  - creditCycleZone
  - minskyMap
  - tippingSignals
forbidden:
  - 신용위험을 주가 하락 가능성과 동일시하지 않는다.
  - HY spread 하나만으로 위기 임박을 단정하지 않는다.
  - US 전용 지표를 KR 판단에 그대로 전용하지 않는다.
failureModes:
  - creditGap은 느린 분기 지표라 단기 market stress와 시차가 큼.
  - Koo/Fisher 일부 신호는 US 데이터 중심이라 KR에서는 결손 가능.
  - 유동성 풍부와 신용위험 확대가 동시에 나올 수 있음.
examples:
  - 지금 신용사이클은 Minsky 몇 단계인가
  - Credit-to-GDP gap과 HY spread로 위기 신호 봐줘
  - 부채 디플레이션 위험이 있는지 확인
lastUpdated: '2026-05-12'
---

## 공개 호출 방식

```python
import dartlab

market = "US"
crisis = dartlab.macro("crisis", market=market)
liquidity = dartlab.macro("liquidity", market=market)
rates = dartlab.macro("rates", market=market)
try:
    summary = dartlab.macro("summary", market=market)
except Exception as exc:
    summary = {"error": str(exc)}

creditRows = []
if isinstance(crisis, dict):
    for key in [
        "creditGap",
        "ghsScore",
        "minskyPhase",
        "recessionDashboard",
        "kooRecession",
        "fisherDeflation",
        "excessBondPremium",
        "creditCycle",
    ]:
        creditRows.append({"signal": key, "value": crisis.get(key)})

emit_result(
    table=creditRows,
    values={
        "market": market,
        "summaryOverall": summary.get("overall") if isinstance(summary, dict) else None,
        "liquidityRegime": liquidity.get("regime") if isinstance(liquidity, dict) else None,
        "rateDirection": ((rates.get("outlook") or {}).get("direction") if isinstance(rates, dict) else None),
    },
    date=summary.get("latestAsOf") if isinstance(summary, dict) else None,
)
```

## 호출 동작

1. `macro("crisis")` 를 중심으로 신용 지표 묶음을 가져온다.
2. `macro("liquidity")` 로 신용 스트레스가 유동성 긴축과 같이 움직이는지 확인한다.
3. `macro("rates")` 로 금리 방향이 신용위험을 완화/증폭하는지 확인한다.
4. `macro("summary")` 로 전체 거시 판단과 신용 신호의 충돌 여부를 검산한다.

## 대표 반환 형태

- `tableRef`: creditGap, ghsScore, minskyPhase, recessionDashboard, Koo/Fisher, EBP, creditCycle.
- `valueRef`: liquidityRegime, rateDirection, summaryOverall.
- 답변 본문: 신용사이클 위치, tipping 신호, 결손 지표, 확인해야 할 다음 데이터.

## 연계 절차

1. 기업 신용 질문이면 `engines.credit` 또는 `engines.recipe.creditMacroStress`.
2. 역사적 유사 사례가 필요하면 `engines.recipe.historicalPositioning`.
3. 꼬리손실 분포가 필요하면 `engines.recipe.tailRiskScenarioScan`.

## 기본 검증

- 신용 신호는 최소 2개 이상 교차 확인한다.
- 결손 지표는 “없음”이 아니라 “현재 데이터로 판정 불가”로 표시한다.
- 빠른 시장 스트레스와 느린 신용갭 지표를 구분한다.
