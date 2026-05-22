---
id: recipes.macro.globalLiquidityPulse
title: 글로벌 유동성 펄스 원자료 점검
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: macro 축의 유동성 판정에 아직 직접 드러나지 않는 Fed balance sheet, reverse repo, M2, 정책금리 원자료를 gather로 모아 글로벌 달러 유동성의 방향을 점검하는 절차. 트리거 — '글로벌 유동성', '달러 유동성', 'Fed balance sheet', 'RRP', 'M2'.
whenToUse:
  - 글로벌 유동성
  - 달러 유동성
  - Fed balance sheet
  - reverse repo
  - M2
  - liquidity pulse
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
  description: "원자료 fetch 결과가 하나도 없으면 유동성 펄스 판단을 하지 않는다."
expectedNovelty:
  - liquidityPulseTable
  - rawMacroEvidence
  - macroCrossCheck
forbidden:
  - Fed balance sheet 증가를 곧바로 주식시장 상승으로 단정하지 않는다.
  - RRP 감소를 단독 유동성 완화로 해석하지 않는다.
  - 기준일과 source 없는 유동성 판단 금지.
failureModes:
  - FRED/HF 카탈로그에 없는 지표는 apiKey 또는 직접 provider가 필요할 수 있음.
  - 주간/월간/일간 지표의 빈도 차이.
  - 정책금리 방향과 유동성 잔액 방향이 충돌할 수 있음.
examples:
  - 글로벌 유동성 펄스 확인
  - Fed balance sheet와 RRP를 같이 봐줘
  - M2와 금리로 달러 유동성 방향 점검
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
indicators = ["WALCL", "RRPONTSYD", "M2SL", "FEDFUNDS", "SOFR", "NFCI"]
rows = []
for indicator in indicators:
    try:
        data = dartlab.gather("macro", indicator)
        rows.append({"indicator": indicator, "data": data, "ok": True})
    except Exception as exc:
        rows.append({"indicator": indicator, "error": str(exc), "ok": False})

liquidity = dartlab.macro("liquidity", market=market)
rates = dartlab.macro("rates", market=market)
try:
    summary = dartlab.macro("summary", market=market)
except Exception as exc:
    summary = {"error": str(exc)}

emit_result(
    table=rows,
    values={
        "market": market,
        "liquidityRegime": liquidity.get("regime") if isinstance(liquidity, dict) else None,
        "rateDirection": ((rates.get("outlook") or {}).get("direction") if isinstance(rates, dict) else None),
        "summaryOverall": summary.get("overall") if isinstance(summary, dict) else None,
    },
    date=summary.get("latestAsOf") if isinstance(summary, dict) else None,
)
```

## 호출 동작

1. `gather("macro", indicator)` 로 달러 유동성 원자료 후보를 행 단위로 조회한다.
2. 실패한 지표는 버리지 않고 `error` 로 기록한다.
3. `macro("liquidity")`, `macro("rates")`, `macro("summary")` 로 해석 결과와 충돌 여부를 확인한다.
4. 결론은 “유동성 펄스 확장/수축/혼재”처럼 방향과 불확실성을 함께 쓴다.

## 대표 반환 형태

- `tableRef`: indicator별 원자료 조회 결과와 실패 사유.
- `valueRef`: liquidityRegime, rateDirection, summaryOverall.
- `dateRef`: 원자료의 latestAsOf/date 또는 summary 기준일.

## 연계 절차

1. 유동성 축소가 확인되면 `recipes.macro.yieldCurveStress` 로 금리곡선 압력을 확인한다.
2. 달러 유동성 압력이 크면 `recipes.macro.dollarFundingStress` 로 환율/위험회피 신호를 확인한다.
3. 거시 해석으로 묶을 때는 `engines.macro` 를 기준 판정으로 사용한다.

## 기본 검증

- 원자료 2개 이상이 성공해야 방향성을 말한다.
- 서로 다른 빈도의 지표는 최근값만 단순 비교하지 않고 기준일을 병기한다.
- macro 유동성 판정과 raw 지표 방향이 충돌하면 충돌을 그대로 표시한다.
