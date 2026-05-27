---
id: recipes.macro.inflationBreadthWatch
title: 인플레이션 확산성 원자료 점검
category: recipes
kind: recipe
scope: builtin
status: tested
purpose: CPI, PPI, 유가, 기대인플레이션, 정책금리 원자료를 gather로 모아 인플레이션이 단일 품목 충격인지 광범위한 압력인지 확인하는 절차. 트리거 — '인플레 확산', '물가 압력', 'CPI PPI 유가', '기대인플레이션'.
whenToUse:
  - 인플레이션 확산
  - 물가 압력
  - CPI PPI
  - 기대인플레이션
  - inflation breadth
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
  description: "CPI 계열과 원자재/유가 계열 중 한쪽만 있으면 확산성 판단을 보류한다."
expectedNovelty:
  - inflationBreadthTable
  - commodityPassThrough
  - policyPressure
forbidden:
  - CPI 하나만으로 인플레이션 확산성을 단정하지 않는다.
  - 유가 상승을 항상 core inflation 상승으로 연결하지 않는다.
  - 명목/실질 금리 구분 없이 정책 압력을 말하지 않는다.
failureModes:
  - CPI/PPI/유가의 빈도와 발표 지연 차이.
  - headline과 core inflation의 방향 차이.
  - 기대인플레이션 지표의 시장 유동성 왜곡.
examples:
  - 물가 압력이 넓게 퍼지고 있나
  - CPI와 PPI와 유가를 같이 봐줘
  - 인플레 재가속 위험 확인
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
indicators = ["CPIAUCSL", "CPILFESL", "PPIACO", "DCOILWTICO", "T5YIE", "FEDFUNDS"]
rows = []
for indicator in indicators:
    try:
        data = dartlab.gather("macro", indicator)
        rows.append({"indicator": indicator, "data": data, "ok": True})
    except Exception as exc:
        rows.append({"indicator": indicator, "error": str(exc), "ok": False})

try:
    rates = dartlab.macro("rates", market=market)
except Exception as exc:
    rates = {"error": str(exc)}
try:
    inflationScenario = dartlab.macro("scenario", "인플레이션 충격", market=market, severity="moderate")
except Exception as exc:
    inflationScenario = {"error": str(exc)}
try:
    summary = dartlab.macro("summary", market=market)
except Exception as exc:
    summary = {"error": str(exc)}

emit_result(
    table=rows,
    values={
        "market": market,
        "rateDirection": ((rates.get("outlook") or {}).get("direction") if isinstance(rates, dict) else None),
        "scenarioType": ((inflationScenario.get("meta") or {}).get("type") if isinstance(inflationScenario, dict) else None),
        "summaryOverall": summary.get("overall") if isinstance(summary, dict) else None,
    },
    date=summary.get("latestAsOf") if isinstance(summary, dict) else None,
    sources=["dartlab://macro/rates", "dartlab://macro/scenario", "dartlab://macro/summary", "dartlab://gather/macro"],
)
```

## 호출 동작

### 1. 결론 도출

6 시리즈 + breadth 단정. 예: "headline CPI +3.2% YoY / core +3.1% / PPI +2.8% / WTI +18% YoY / 5Y BEI 2.6% (anchored) / FFR 5.25 → 확산성=넓음 (headline+core+PPI 동조 + 기대 anchored — 공급충격 한정 아님)."

### 2. 핵심 근거 수집

- CPIAUCSL (headline CPI), CPILFESL (core CPI), PPIACO (PPI), DCOILWTICO (WTI), T5YIE (5Y BEI), FEDFUNDS — gather macro 6
- macro('rates') outlook direction (cutting / peak / hiking)
- macro('scenario', "인플레이션 충격") type — 조건부 시나리오 type
- macro('summary') overall — 거시 종합

### 3. 메커니즘 분석

```
headline vs core vs PPI vs commodity 분리
   headline > core (gap > 0.5%p) → 공급충격 (에너지/식품)
   core > headline           → 수요 압력 + sticky
   PPI 상승 > CPI 상승 + lag → pipeline pressure (6-12M 후 CPI 전이)
   5Y BEI > 2.5% + 추세      → 기대 unanchor (정책 압박)
   ↓
breadth 판정:
   headline + core + PPI 동조 상승 → 넓음
   headline 만 (commodity 단독)    → 좁음 (공급충격)
   headline + core 추세 분리      → 혼재
```

기대인플레이션 anchored (BEI < 2.5%) + core 하락 = peak inflation 후보. unanchored + PPI lag pressure = 재가속 위험.

### 4. 반례·한계

- 유가 단기 spike (지정학) 는 headline 만 일시 상승 — 확산성 아님.
- core CPI 는 주거비 lag 12-18M 으로 후행 — 실시간 신호 약함.
- T5YIE 는 시장 유동성 thin → 추세 신호 noisy.
- US-only (CPIAUCSL). KR/EU 인플레 분리 필요.

### 5. 후속 모니터링

- 확산성=넓음 + rateDirection=hiking → `recipes.macro.yieldCurveStress` 로 금리곡선 inversion.
- PPI 선행 + CPI lag → `recipes.macro.tailRiskScenarioScan` 으로 재가속 시나리오.
- 유가 충격 단독 → `recipes.macro.dollarFundingStress` 로 commodity-dollar 동조 확인.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `indicator` | CPIAUCSL / CPILFESL / PPIACO / DCOILWTICO / T5YIE / FEDFUNDS |
| `data` | 시계열 원자료 |
| `ok` | gather 성공 여부 |

## 연계 절차

1. 인플레 확산성이 높으면 `recipes.macro.yieldCurveStress` 로 금리곡선과 정책 압력을 확인한다.
2. 상품/에너지 충격 중심이면 `engines.macro` 의 인플레이션 충격 경로와 비교한다.
3. 한국 수출/환율 영향은 `recipes.macro.koreaExportCycleNowcast` 로 넘긴다.

## 기본 검증

- CPI 계열과 상품/생산자 계열을 최소 하나씩 확인한다.
- 확산성은 "넓음/좁음/혼재/판정불가" 중 하나로 표현한다.
