---
id: recipes.macro.globalLiquidityPulse
title: 글로벌 유동성 펄스 원자료 점검
category: recipes
kind: recipe
scope: builtin
status: tested
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
    sources=["dartlab://macro/liquidity", "dartlab://macro/rates", "dartlab://macro/summary", "dartlab://gather/macro"],
)
```

## 호출 동작

### 1. 결론 도출

liquidityRegime + rateDirection 결합 단정. 예: "WALCL 6M MoM -2.1% (QT 진행) / RRP 4M -45% (시장 흡수) / M2SL +0.2% / FFR 5.25 (peak) / SOFR 5.31 → liquidityRegime=tightening (수축 phase), rateDirection=peak — 유동성 펄스 수축 + 정점 금리 결합."

### 2. 핵심 근거 수집

- WALCL (Fed balance sheet), RRPONTSYD (overnight reverse repo), M2SL (광의통화), FEDFUNDS (정책금리), SOFR (시장금리), NFCI (financial conditions) — gather macro 6 시리즈
- macro('liquidity') regime (easing / neutral / tightening)
- macro('rates') outlook direction (cutting / peak / hiking)
- macro('summary') overall — 거시 종합 점수

### 3. 메커니즘 분석

```
6 source → 유동성 방향
  WALCL 6M MoM > +0.5% + RRP 감소(시장 자금 흡수)
     → easing 후보
  WALCL MoM < -1% (QT) + M2 둔화 + NFCI 상승
     → tightening 후보
  방향 mixed → neutral
     ↓
  rate direction 결합
     hiking + tightening → 강한 긴축 (자산가격 하방)
     cutting + easing → 강한 완화 (자산가격 상방)
     hiking + easing → 금리/유동성 분리 (혼재)
```

WALCL 추세 > RRP 추세 > M2 추세 우선순위. RRP 감소는 시장 유동성 증가 (Fed→시장) 의미 — balance sheet 감소와 다른 신호.

### 4. 반례·한계

- 정책금리 hiking 중에도 WALCL 증가 (긴급 지원) 시 유동성 신호 혼재.
- M2 는 월간, WALCL 은 주간 — 동기화 어려움.
- RRP 잔액 0 도달 후 추가 흡수 불가 — 신호 포화.
- 글로벌 유동성 (ECB/BOJ/PBOC) 미반영 — US-only.

### 5. 후속 모니터링

- liquidityRegime=tightening + rateDirection=hiking → `recipes.macro.yieldCurveStress` 로 금리곡선 inversion 점검.
- liquidityRegime=easing 지속 → `recipes.macro.dollarFundingStress` 로 위험자산 sentiment 확인.
- WALCL 급변 (긴급 지원) → `recipes.macro.tailRiskScenarioScan` 으로 tail event 점검.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `indicator` | WALCL / RRPONTSYD / M2SL / FEDFUNDS / SOFR / NFCI |
| `data` | 시계열 원자료 |
| `ok` | gather 성공 여부 |

## 연계 절차

1. 유동성 축소가 확인되면 `recipes.macro.yieldCurveStress` 로 금리곡선 압력을 확인한다.
2. 달러 유동성 압력이 크면 `recipes.macro.dollarFundingStress` 로 환율/위험회피 신호를 확인한다.
3. 거시 해석으로 묶을 때는 `engines.macro` 를 기준 판정으로 사용한다.

## 기본 검증

- 원자료 2개 이상이 성공해야 방향성을 말한다.
- 서로 다른 빈도의 지표는 최근값만 단순 비교하지 않고 기준일을 병기한다.
- macro 유동성 판정과 raw 지표 방향이 충돌하면 충돌을 그대로 표시한다.
