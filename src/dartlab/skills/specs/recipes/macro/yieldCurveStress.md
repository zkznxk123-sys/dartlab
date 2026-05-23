---
id: recipes.macro.yieldCurveStress
title: 수익률곡선 스트레스 원자료 점검
category: recipes
kind: recipe
scope: builtin
status: drafted
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

1. 장단기 스프레드와 금리 레벨 원자료를 gather로 확인한다.
2. `macro("rates")` 로 정책/곡선 해석을 대조한다.
3. `macro("forecast")` 로 침체확률/LEI와 같은 후속 신호를 점검한다.
4. 역전, 정상화, steepening을 경기 신호와 정책 신호로 분리해 설명한다.

## 대표 반환 형태

- `tableRef`: 금리 지표별 원자료.
- `valueRef`: rateDirection, recessionProb, summaryOverall.
- 답변 본문: 역전 여부, 곡선 정상화 여부, 침체 신호의 lag 위험.

## 연계 절차

1. 금리곡선 역전이 확인되면 `recipes.macro.laborMarketTurningPoint` 로 고용 후행 신호를 확인한다.
2. 금리 상승이 물가 압력 때문이면 `recipes.macro.inflationBreadthWatch` 로 물가 확산성을 확인한다.
3. 정책/유동성 압력은 `recipes.macro.globalLiquidityPulse` 와 함께 본다.

## 기본 검증

- `T10Y2Y`와 `T10Y3M` 중 적어도 하나가 있어야 곡선 판단을 한다.
- forecast와 rates가 충돌하면 “시장금리 선행 vs macro forecast 지연”으로 분리한다.
