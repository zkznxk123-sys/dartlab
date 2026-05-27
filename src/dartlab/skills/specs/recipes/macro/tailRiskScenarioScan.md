---
id: recipes.macro.tailRiskScenarioScan
title: 꼬리위험 시나리오 스캔
category: recipes
kind: recipe
scope: builtin
status: tested
purpose: 2008 금융위기, 2020 COVID, 인플레이션 충격, 신용 충격 같은 macro.scenario 결과를 나란히 실행해 현재 macro summary 대비 하방 시나리오의 손실 경로와 취약 축을 찾는 절차. 트리거 — 'tail risk', '꼬리위험', '최악 시나리오', '5시그마 이벤트'.
whenToUse:
  - tail risk
  - 꼬리위험
  - 최악 시나리오
  - 하방 시나리오
  - scenario scan
linkedSkills:
  - engines.macro
  - engines.quant
  - engines.company
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
    sources=["dartlab://macro/scenario", "dartlab://macro/summary"],
)
```

## 호출 동작

### 1. 결론 도출

6 scenario delta + 취약 축 단정. 예: "현재 overall=cautious / score=-0.3 기준선 → 6 scenario severe 충격 시 score 분포: 신용충격 -1.8 (worst) / 2008 -1.6 / 자산버블 -1.4 / 금리충격 -1.0 / 2020 -0.8 / 인플레 -0.6. 반복 취약 축 = 신용 (4/6 시나리오에서 credit zone alarm)."

### 2. 핵심 근거 수집

- macro('summary', market) — 기준선 overall + score + latestAsOf
- macro('scenario', name, severity='severe') × 6 — 역사 (2008/2020) + 유형 (신용/금리/인플레/버블)
- 각 scenario meta + delta + scenario.score 추출

### 3. 메커니즘 분석

```
6 scenario × 1 기준선 → delta matrix
   delta = scenario.score - current.score
   ↓
하방 ranking — delta 큰 순서 정렬
   worst 1개 = 가장 위험 시나리오
   ↓
반복 취약 축 추출:
   6 scenario 중 credit zone alarm 4건 → 신용 = 반복 취약
   FX zone alarm 2건                   → 환율 = 부분 취약
   ↓
worst scenario 단일 vs 반복 취약 축 분리:
   worst 단일 — 특정 시나리오 가정 의존
   반복 취약 — 시나리오 무관 구조적 약점
```

worst scenario 보다 반복 취약 축이 더 신호 강함 — 1 시나리오는 가정 의존이지만 4+ 시나리오 공통 취약 축은 구조적 weakness.

### 4. 반례·한계

- scenario API delta 는 hypothetical — 확률 분포 X.
- severity='severe' 비교는 시나리오 유형별 동일 확률 의미 X.
- 6 시나리오는 알려진 패턴 — black swan (예: cyber / 지정학) 미포함.
- US-only — KR/EU 동시 비교 필요 시 market 별 재호출.

### 5. 후속 모니터링

- 반복 취약 축 = 신용 → `recipes.fundamental.credit.cycleStressMap` 으로 신용 사이클 추적.
- 반복 취약 축 = 환율 → `recipes.macro.dollarFundingStress` 로 달러 펀딩 압력 점검.
- worst scenario 일관 historical → `recipes.macro.historicalPositioning` 으로 현재 위치 비교.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `scenarioName` | 2008 / 2020 / 신용 / 금리 / 인플레 / 자산버블 |
| `meta` | scenario meta |
| `delta` | 기준선 대비 변화 |
| `scenario` | scenario 결과 본문 |

## 연계 절차

1. 신용 시나리오가 핵심이면 `recipes.fundamental.credit.cycleStressMap`.
2. 한국 특화 위기가 필요하면 `recipes.macro.koreaMacroStressMap`.
3. 실제 포트폴리오 손실률이 필요하면 `engines.quant`.

## 기본 검증

- 최소 3개 이상의 scenario를 실행한다.
- `severity`를 명시하고, 역사적 사건과 유형별 stress를 구분한다.
- scenario 결과는 확률이 아니라 "조건부 충격 경로"라고 설명한다.
