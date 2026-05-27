---
id: recipes.macro.historicalPositioning
title: 현재 매크로 위치의 역사적 비교
category: recipes
kind: recipe
scope: builtin
status: tested
purpose: 현재 거시 상태를 1997 아시아 위기, 2008 금융위기, 2020 COVID, 2022 인플레 긴축 같은 역사적 충격과 나란히 비교해 지금의 위치를 설명하는 절차. 트리거 — '2008과 비교', '과거 위기 대비', '현재 위치', '역사적 percentile'.
whenToUse:
  - 과거 위기 비교
  - 2008 대비 현재
  - 2020 COVID 대비
  - 현재 매크로 위치
  - historical positioning
linkedSkills:
  - engines.macro
  - engines.company
  - engines.scan
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - dateRef
  - valueRef
  - executionRef
  - sourceRef
visualRefs:
  - "engines.viz.scenarioVisuals"
  - "engines.viz.tableBackedChart"
  - "engines.viz.mermaidDiagram"
visualGuidance:
  - "stress·민감도·충격 전파는 engines.viz.scenarioVisuals를 사용하고 assumption grid 또는 수치 임계가 없으면 scenario table로 낮춘다."
  - "표 기반 순위·추세는 engines.viz.tableBackedChart만 사용하고 tableRef/evidenceBinding이 없으면 차트 대신 검산 표로 낮춘다."
  - "메커니즘 diagram은 engines.viz.mermaidDiagram으로 8노드 이하만 만들고 모든 edge에 문장·수치·sourceRef 근거를 둔다."

gap:
  primary:
    - macro
    - scenario
testUniverse:
  market: KR
  asOfPolicy: latest
falsifier:
  description: "비교 대상 시나리오의 meta/period/outcome 없이 현재와 비교하면 역사적 비교 recipe로 부적합하다."
expectedNovelty:
  - historicalAnalogue
  - scenarioDelta
  - crisisComparison
forbidden:
  - 역사적 사건을 현재와 동일하다고 단정하지 않는다.
  - 시나리오 override 결과를 실제 현재 데이터로 말하지 않는다.
  - 단일 사건 하나만 골라 결론을 고정하지 않는다.
failureModes:
  - 사건별 기간이 다르고 지표 빈도가 달라 직접 수치 비교가 왜곡됨.
  - 1997 KR 위기와 2008 US 위기를 같은 시장 기준으로 섞음.
  - scenario 결과의 delta와 현재 summary를 구분하지 못함.
examples:
  - 지금은 2008 금융위기와 얼마나 비슷한가
  - 현재 한국 거시 상황을 1997/2008/2020과 비교
  - 2022 인플레 긴축과 지금 금리 환경 비교
lastUpdated: '2026-05-13'
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: limited
  pyodide:
    status: limited
---

## 공개 호출 방식

```python
import dartlab

market = "KR"
try:
    current = dartlab.macro("summary", market=market)
except Exception as exc:
    current = {"error": str(exc)}
cycle = dartlab.macro("cycle", market=market)
crisis = dartlab.macro("crisis", market=market)

scenarioNames = ["1997 아시아 위기", "2008 금융위기", "2020 COVID", "2022 인플레 긴축"]
comparisons = []
for name in scenarioNames:
    try:
        scenario = dartlab.macro("scenario", name, market=market)
    except Exception as exc:
        scenario = {"error": str(exc)}
    comparisons.append({"scenarioName": name, "scenario": scenario})

emit_result(
    table=comparisons,
    values={
        "market": market,
        "currentOverall": current.get("overall") if isinstance(current, dict) else None,
        "currentScore": current.get("score") if isinstance(current, dict) else None,
        "cyclePhase": cycle.get("phase") if isinstance(cycle, dict) else None,
        "crisisZone": ((crisis.get("recessionDashboard") or {}).get("zone") if isinstance(crisis, dict) else None),
    },
    date=current.get("latestAsOf") if isinstance(current, dict) else None,
    sources=["dartlab://macro/summary", "dartlab://macro/cycle", "dartlab://macro/crisis", "dartlab://macro/scenario"],
)
```

## 호출 동작

### 1. 결론 도출

현재 + 4 시나리오 비교 단정. 예: "현재 KR cyclePhase=late-cycle / crisisZone=watch / overall=cautious → 1997 (외환위기, KR-specific) 다름 (FX 보유 ↑) / 2008 (글로벌 신용) 일부 닮음 (HY spread ↑) / 2020 (COVID 충격) 다름 (liquidity easing 아님) / 2022 (인플레 긴축) 가장 유사 (금리 peak + 자산 valuation 압축)."

### 2. 핵심 근거 수집

- macro('summary', market) — 현재 overall + score + latestAsOf
- macro('cycle', market).phase — 현재 사이클 위치
- macro('crisis', market).recessionDashboard.zone — 위기 zone
- macro('scenario', name, market) × 4 — 1997 / 2008 / 2020 / 2022 시나리오 meta + outcome

### 3. 메커니즘 분석

```
현재 vector (cyclePhase + crisisZone + summaryScore)
   vs 4 시나리오 outcome vector
   ↓
닮은 축 (rate level / FX / credit spread / volatility) 매칭
다른 축 (정책공간 / 부채구성 / 외부충격 / FX 보유) 분리
   ↓
유사도 ranking — 가장 닮은 시나리오 1순위 + 차이점 명시
   "전체 동일" 단정 금지 — 항상 닮은/다른 축 동시 제시
```

각 위기는 다른 transmission mechanism. 1997 = KR FX + 외채 / 2008 = US 신용 + 글로벌 전이 / 2020 = pandemic + 정책 완화 / 2022 = 인플레 + 긴축. 현재와 1:1 매칭 시 어떤 mechanism 닮았는지 명시 필수.

### 4. 반례·한계

- scenario API 의 outcome 은 hypothesis — 실제 outcome 아님.
- 시나리오 period 길이 ≠ 현재 측정 period — 직접 수치 비교 왜곡.
- 1997 KR 위기를 US 시장 frame 으로 가져오면 무의미.
- 2022 와 현재 (2026) 는 같은 사이클 후반 — 비교 vs 연속 구분 필요.

### 5. 후속 모니터링

- 1997/2008 유사도 ↑ → `recipes.fundamental.credit.cycleStressMap` 으로 신용 사이클 확인.
- 2020 유사도 ↑ → `recipes.macro.tailRiskScenarioScan` 으로 tail 시나리오 분포.
- 2022 유사도 ↑ → `recipes.macro.koreaMacroStressMap` 으로 KR 시장 stress 확장.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `scenarioName` | 1997 / 2008 / 2020 / 2022 |
| `scenario` | scenario meta + outcome |

## 연계 절차

1. 위기 유사성이 높으면 `recipes.fundamental.credit.cycleStressMap`.
2. scenario 손실 분포가 필요하면 `recipes.macro.tailRiskScenarioScan`.
3. 한국 시장 적용이 핵심이면 `recipes.macro.koreaMacroStressMap`.

## 기본 검증

- 현재 데이터와 scenario override를 같은 행에 두되 `current` / `scenario` 라벨을 분리한다.
- 비교 결과에는 최소 2개 이상의 역사적 사건을 포함한다.
- 가장 유사한 사건을 말할 때도 "완전 동일" 표현은 금지한다.
