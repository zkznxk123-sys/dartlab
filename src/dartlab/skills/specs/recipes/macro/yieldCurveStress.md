---
id: recipes.macro.yieldCurveStress
title: 수익률곡선 스트레스 원자료 점검
category: recipes
kind: recipe
scope: builtin
status: curated
purpose: 장단기 금리차, 정책금리, 장기금리 원자료를 gather로 직접 확인하고 macro.rates 해석과 대조해 경기침체 선행 신호와 정책 압력을 점검하는 절차. 트리거 — '수익률곡선', '장단기 금리차', 'yield curve', '금리 역전'.
whenToUse:
  - 수익률곡선
  - 장단기 금리차
  - yield curve
  - 금리 역전
  - recession signal
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
  description: "T10Y2Y 또는 T10Y3M 둘 중 하나도 조회하지 못하면 yield curve recipe 판단을 중단한다."
expectedNovelty:
  - curveRawTable
  - inversionCheck
  - ratesCrossCheck
forbidden:
  - 금리 역전만으로 즉시 침체를 단정하지 않는다.
  - 정책금리와 시장금리의 시차를 무시하지 않는다.
  - KR/US 금리 코드를 섞어 같은 곡선으로 계산하지 않는다.
failureModes:
  - 일별 금리와 월별 macro forecast의 기준일 불일치.
  - 장단기 스프레드가 정상화되어도 recession lag가 남을 수 있음.
  - FRED 코드 외 시장에서는 별도 provider 필요.
examples:
  - 미국 장단기 금리차 지금 역전인가
  - T10Y2Y와 T10Y3M으로 침체 신호 확인
  - 금리곡선과 macro rates 결과 비교
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
validatedAt: '2026-05-27'
---

## 공개 호출 방식

```python
import dartlab

market = "US"
indicators = ["T10Y2Y", "T10Y3M", "DGS10", "DGS2", "DGS3MO", "FEDFUNDS"]
rows = []
for indicator in indicators:
    try:
        data = dartlab.gather("macro", indicator)
        rows.append({"indicator": indicator, "data": data, "ok": True})
    except Exception as exc:
        rows.append({"indicator": indicator, "error": str(exc), "ok": False})

rates = dartlab.macro("rates", market=market)
forecast = dartlab.macro("forecast", market=market)
try:
    summary = dartlab.macro("summary", market=market)
except Exception as exc:
    summary = {"error": str(exc)}

emit_result(
    table=rows,
    values={
        "market": market,
        "rateDirection": ((rates.get("outlook") or {}).get("direction") if isinstance(rates, dict) else None),
        "recessionProb": (((forecast.get("recessionProb") or {}).get("probability")) if isinstance(forecast, dict) else None),
        "summaryOverall": summary.get("overall") if isinstance(summary, dict) else None,
    },
    date=summary.get("latestAsOf") if isinstance(summary, dict) else None,
    sources=["dartlab://macro/rates", "dartlab://macro/forecast", "dartlab://macro/summary"],
)
```

## 호출 동작

### 1. 결론 도출

T10Y2Y + T10Y3M + recessionProb 단정. 예: "T10Y2Y = -0.45% (역전 18M 지속) / T10Y3M = +0.05% (정상화 진행) / DGS10 = 4.2% / FEDFUNDS = 5.25% / recessionProb = 38% → curve 일부 역전 + 정상화 mix phase — 침체 nowcast 강하지 않으나 1y lag 후행 risk 잔존."

### 2. 핵심 근거 수집

- FRED 금리 6 시리즈 (T10Y2Y, T10Y3M, DGS10, DGS2, DGS3MO, FEDFUNDS) — gather macro
- macro('rates') outlook direction (cutting / peak / hiking)
- macro('forecast').recessionProb.probability — 침체 확률 (모델 산출)
- macro('summary') overall — 거시 종합

### 3. 메커니즘 분석

```
2 spread 시리즈 → curve 상태
   T10Y2Y < 0 (역전)        → 2024-2025 강한 침체 선행 신호 (US historical)
   T10Y3M < 0 (단기 역전)   → 단기 통화정책 vs 10년 mismatch
   둘 다 정상화 (양수)      → 침체 위험 후퇴
   ↓
정책 vs 시장 분리:
   FEDFUNDS - DGS2 큰 갭   → 시장이 인하 baseline (Fed peak 의식)
   rate direction=peak     → 정책 정점 — curve normalization 임박
   rate direction=cutting  → 정책 + 시장 동조 (curve 역전 해제 가속)
   ↓
recessionProb 결합:
   curve 역전 + recessionProb > 40% → 침체 nowcast 강
   curve 정상화 + recessionProb < 20% → 침체 위험 완화
   curve 역전 + recessionProb 낮음   → lag risk 잔존 (역전 후 12-24M 침체 도래)
```

US historical (1955-2024) — yield curve 역전 후 평균 12-18M 침체 도래 (10/10 신뢰). 단, 2022-2024 역전 후 침체 미발현 (예외 가능성) — *지속 기간* + 다른 신호 동행 필수.

### 4. 반례·한계

- 일별 금리 vs 월별 macro forecast 기준일 불일치.
- 장단기 스프레드 정상화 후에도 recession lag 12-18M 잔존.
- KR/US 금리 코드 섞으면 의미 무효 — 시장 명시 필수.
- 2022-2024 역전 후 침체 미발현 — 모델 예외 검증 필요.

### 5. 후속 모니터링

- 역전 + 정상화 mix → `recipes.macro.laborMarketTurningPoint` 로 고용 후행 신호.
- 정책금리 hiking 지속 → `recipes.macro.inflationBreadthWatch` 로 인플레 확산성.
- HY spread 동시 확대 → `recipes.fundamental.credit.usHighYieldSpread` 로 credit market 신호 cross-check.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `indicator` | T10Y2Y / T10Y3M / DGS10 / DGS2 / DGS3MO / FEDFUNDS |
| `data` | 시계열 원자료 |
| `ok` | gather 성공 여부 |

## 연계 절차

1. 금리곡선 역전이 확인되면 `recipes.macro.laborMarketTurningPoint` 로 고용 후행 신호를 확인한다.
2. 금리 상승이 물가 압력 때문이면 `recipes.macro.inflationBreadthWatch` 로 물가 확산성을 확인한다.
3. 정책/유동성 압력은 `recipes.macro.globalLiquidityPulse` 와 함께 본다.

## 기본 검증

- `T10Y2Y`와 `T10Y3M` 중 적어도 하나가 있어야 곡선 판단을 한다.
- forecast와 rates가 충돌하면 "시장금리 선행 vs macro forecast 지연"으로 분리한다.
