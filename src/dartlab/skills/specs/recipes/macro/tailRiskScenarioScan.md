---
id: recipes.macro.tailRiskScenarioScan
title: 꼬리위험 시나리오 스캔
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: 2008 금융위기, 2020 COVID, 인플레이션 충격, 신용 충격 같은 macro.scenario 결과를 나란히 실행해 현재 macro summary 대비 하방 시나리오의 손실 경로와 취약 축을 찾는 절차. 트리거 — 'tail risk', '꼬리위험', '최악 시나리오', '5시그마 이벤트'.
whenToUse:
  - tail risk
  - 꼬리위험
  - 최악 시나리오
  - 하방 시나리오
  - scenario scan
linkedSkills:
  - engines.macro.scenario
  - engines.macro.crisis
  - engines.macro.assets
  - engines.macro.summary
  - engines.quant.tailrisk
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
    - quant
testUniverse:
  market: US
  asOfPolicy: latest
falsifier:
  description: "scenario를 3개 미만만 실행하면 tail scan으로 보지 않는다."
expectedNovelty:
  - tailScenarioMatrix
  - downsideRank
  - vulnerableAxis
forbidden:
  - 시나리오 결과를 확률 예측으로 말하지 않는다.
  - 극단 시나리오 하나만 보고 기본 전망을 뒤집지 않는다.
  - quant tailrisk와 혼동해 실제 포트폴리오 CVaR처럼 표현하지 않는다.
failureModes:
  - scenario override가 현재 시장 데이터와 섞여 기준일이 모호해짐.
  - severe/extreme 심각도 비교가 유형별로 동일한 확률을 의미하지 않음.
  - 꼬리위험 스캔을 투자 권고로 오해함.
examples:
  - 지금 가장 위험한 꼬리 시나리오는 뭐야
  - 2008/COVID/인플레 충격을 현재와 비교
  - 신용 충격과 금리 충격 중 어느 쪽이 더 취약한가
lastUpdated: '2026-05-12'
---

## 공개 호출 방식

```python
import dartlab

market = "US"
try:
    current = dartlab.macro("summary", market=market)
except Exception as exc:
    current = {"error": str(exc)}
scenarioNames = [
    "2008 금융위기",
    "2020 COVID",
    "신용 충격",
    "금리 충격",
    "인플레이션 충격",
    "자산 버블 붕괴",
]

rows = []
for name in scenarioNames:
    try:
        result = dartlab.macro("scenario", name, market=market, severity="severe")
        scenario = result.get("scenario") if isinstance(result, dict) else None
        delta = result.get("delta") if isinstance(result, dict) else None
        meta = result.get("meta") if isinstance(result, dict) else None
        rows.append({"scenarioName": name, "meta": meta, "delta": delta, "scenario": scenario})
    except Exception as exc:
        rows.append({"scenarioName": name, "error": str(exc)})

emit_result(
    table=rows,
    values={
        "market": market,
        "currentOverall": current.get("overall") if isinstance(current, dict) else None,
        "currentScore": current.get("score") if isinstance(current, dict) else None,
        "scenarioCount": len(rows),
    },
    date=current.get("latestAsOf") if isinstance(current, dict) else None,
)
```

## 호출 동작

1. 현재 `macro("summary")` 를 기준선으로 고정한다.
2. 역사적·유형별 하방 scenario를 6개 이상 실행한다.
3. 각 scenario의 `delta`, `meta`, `scenario.overall/score`를 표로 모은다.
4. 가장 나쁜 score 하나보다, 어느 축이 반복적으로 취약한지 확인한다.

## 대표 반환 형태

- `tableRef`: scenarioName, meta, delta, scenario.
- `valueRef`: currentScore, scenario별 score/delta.
- 답변 본문: 하방 시나리오 순위, 반복 취약 축, 현재 기준선과의 차이.

## 연계 절차

1. 신용 시나리오가 핵심이면 `recipes.credit.creditCycleStressMap`.
2. 한국 특화 위기가 필요하면 `recipes.macro.koreaMacroStressMap`.
3. 실제 포트폴리오 손실률이 필요하면 `engines.quant.tailrisk`.

## 기본 검증

- 최소 3개 이상의 scenario를 실행한다.
- `severity`를 명시하고, 역사적 사건과 유형별 stress를 구분한다.
- scenario 결과는 확률이 아니라 “조건부 충격 경로”라고 설명한다.
