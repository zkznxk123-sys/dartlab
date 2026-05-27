---
id: recipes.macro.laborMarketTurningPoint
title: 노동시장 전환점 원자료 점검
category: recipes
kind: recipe
scope: builtin
status: tested
purpose: 실업률, 신규실업수당, 비농업고용, 임금, Sahm rule 관련 원자료를 gather로 확인하고 macro.forecast와 대조해 노동시장 둔화의 전환점을 찾는 절차. 트리거 — '노동시장 둔화', '실업률', '고용 전환점', 'Sahm rule'.
whenToUse:
  - 노동시장 둔화
  - 실업률
  - 신규실업수당
  - 고용 전환점
  - Sahm rule
linkedSkills:
  - engines.gather
  - engines.macro
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
    - gather
    - macro
testUniverse:
  market: US
  asOfPolicy: latest
falsifier:
  description: "실업률 또는 신규실업수당 원자료가 없으면 노동시장 전환점 판정을 하지 않는다."
expectedNovelty:
  - laborRawTable
  - turningPointSignal
  - forecastCrossCheck
forbidden:
  - 고용지표 한 달치 변화로 추세 전환을 단정하지 않는다.
  - 임금 상승을 항상 경기 호조로만 해석하지 않는다.
  - Sahm rule 신호와 recession nowcast를 혼동하지 않는다.
failureModes:
  - 고용지표 revision이 커서 최신 발표치가 바뀔 수 있음.
  - 실업률과 신규실업수당의 선후행 차이.
  - 임금은 인플레이션과 노동수요를 동시에 반영.
examples:
  - 미국 노동시장 전환점 확인
  - 신규실업수당과 실업률로 경기 둔화 봐줘
  - Sahm rule 위험 점검
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
indicators = ["UNRATE", "ICSA", "PAYEMS", "AHEPA", "CIVPART", "JTSJOL"]
rows = []
for indicator in indicators:
    try:
        data = dartlab.gather("macro", indicator)
        rows.append({"indicator": indicator, "data": data, "ok": True})
    except Exception as exc:
        rows.append({"indicator": indicator, "error": str(exc), "ok": False})

try:
    forecast = dartlab.macro("forecast", market=market)
except Exception as exc:
    forecast = {"error": str(exc)}
try:
    cycle = dartlab.macro("cycle", market=market)
except Exception as exc:
    cycle = {"error": str(exc)}
try:
    summary = dartlab.macro("summary", market=market)
except Exception as exc:
    summary = {"error": str(exc)}

emit_result(
    table=rows,
    values={
        "market": market,
        "sahmRule": ((forecast.get("sahmRule") or {}).get("signal") if isinstance(forecast, dict) else None),
        "cyclePhase": cycle.get("phase") if isinstance(cycle, dict) else None,
        "summaryOverall": summary.get("overall") if isinstance(summary, dict) else None,
    },
    date=summary.get("latestAsOf") if isinstance(summary, dict) else None,
    sources=["dartlab://macro/cycle", "dartlab://macro/forecast", "dartlab://macro/summary", "dartlab://gather/macro"],
)
```

## 호출 동작

### 1. 결론 도출

UNRATE + ICSA + sahmRule + cyclePhase 결합 단정. 예: "UNRATE 3.9% (3M low 3.4% → +0.5%p) / ICSA 245k (12M high) / PAYEMS +175k (slowing) / AHEPA +4.1% / sahmRule=triggered (≥0.5%p) / cyclePhase=late-cycle → 노동시장 전환점 임박 (둔화 초기 phase confirmed)."

### 2. 핵심 근거 수집

- UNRATE (실업률), ICSA (initial claims), PAYEMS (비농업고용), AHEPA (시간당임금), CIVPART (참가율), JTSJOL (구인) — gather macro 6 시리즈
- macro('forecast').sahmRule.signal — 0.5%p rule trigger 여부
- macro('cycle').phase — early-recovery / mid-expansion / late-cycle / contraction
- macro('summary') overall

### 3. 메커니즘 분석

```
6 source → 전환점 phase
  UNRATE 3M low 대비 +0.5%p 이상 (Sahm 발동)
     → 침체 nowcast 강함
  ICSA 4주 평균 상승 + PAYEMS 둔화 (<150k)
     → 둔화 초기
  JTSJOL/UNRATE > 1.5 (구인↑) + AHEPA 안정
     → 아직 tight (둔화 늦음)
     ↓
sahmRule=triggered + ICSA 상승 + PAYEMS<150k → 전환 confirm
1-2 신호만 → 둔화 초기 (단정 보류)
0 신호 → 노동시장 강세 유지
```

UNRATE 와 ICSA 는 선후행 — ICSA (주간) 선행, UNRATE (월간) 후행. PAYEMS revision ±50k 큼 — 한달치만으로 단정 X.

### 4. 반례·한계

- PAYEMS 발표 후 revision 으로 1-2 개월 후 바뀜.
- AHEPA 상승 = 노동수요 강함 + 인플레 압력 — sentiment 양면.
- CIVPART 하락 (구조적 은퇴) → UNRATE 하락이 강세 아님.
- Sahm rule 은 1948-2024 US-only 패턴 — KR/EU 직접 적용 X.

### 5. 후속 모니터링

- sahmRule=triggered + cyclePhase=late-cycle → `recipes.macro.tailRiskScenarioScan` 으로 침체 시나리오.
- ICSA 추세 상승만 → `recipes.macro.yieldCurveStress` 로 금리곡선 선행 신호 확인.
- 노동시장 강세 유지 → `recipes.macro.inflationBreadthWatch` 로 임금-인플레 spiral 확인.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `indicator` | UNRATE / ICSA / PAYEMS / AHEPA / CIVPART / JTSJOL |
| `data` | 시계열 원자료 |
| `ok` | gather 성공 여부 |

## 연계 절차

1. 노동시장 둔화가 확인되면 `engines.macro` 로 침체확률과 LEI를 함께 확인한다.
2. 금리곡선 선행 신호와 비교하려면 `recipes.macro.yieldCurveStress` 로 이동한다.
3. 신용 스트레스가 동반되면 `recipes.fundamental.credit.cycleStressMap` 으로 확장한다.

## 기본 검증

- 한 지표만 성공하면 결론 대신 추가 데이터 필요로 표시한다.
- 신규실업수당과 실업률의 시차를 분리한다.
