---
id: recipes.macro.koreaMacroStressMap
title: 한국 매크로 스트레스 지도
category: recipes
kind: recipe
scope: builtin
status: tested
purpose: 한국 시장을 기준으로 환율, 교역, 금리, 유동성, 위기, 자산/심리 축을 묶어 외국인 수급과 수출 민감도가 큰 시장의 거시 스트레스를 판단하는 절차. 트리거 — '한국 매크로', 'KR 스트레스', '원달러', 'KOSPI 위험', '수출 경기'.
whenToUse:
  - 한국 매크로
  - KR macro stress
  - 원달러 스트레스
  - KOSPI 위험
  - 수출 경기
  - 외국인 수급과 환율
linkedSkills:
  - engines.macro
  - engines.scan
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
    - scan
testUniverse:
  market: KR
  asOfPolicy: latest
falsifier:
  description: "market='KR' 호출 없이 한국 스트레스 결론을 내리면 recipe 실패다."
expectedNovelty:
  - koreaStressMap
  - fxTradeLink
  - marketFragility
forbidden:
  - US macro 결과를 한국 시장 결론으로 전용하지 않는다.
  - 환율 하나만으로 한국 시장 스트레스를 단정하지 않는다.
  - KOSPI 방향 예측을 직접 투자 권고로 쓰지 않는다.
failureModes:
  - KR macro 축의 일부 데이터 결손.
  - 환율, 교역조건, 주식시장 반응의 기준일 차이.
  - 수출주와 내수주의 macro 민감도 차이를 무시함.
examples:
  - 한국 매크로 스트레스 지금 어느 정도야
  - 원달러와 교역조건으로 수출 경기 봐줘
  - 한국 시장이 신용/환율/심리 중 어디가 취약한가
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
    summary = dartlab.macro("summary", market=market)
except Exception as exc:
    summary = {"error": str(exc)}
trade = dartlab.macro("trade", market=market)
rates = dartlab.macro("rates", market=market)
liquidity = dartlab.macro("liquidity", market=market)
crisis = dartlab.macro("crisis", market=market)
assets = dartlab.macro("assets", market=market)
sentiment = dartlab.macro("sentiment", market=market)

rows = [
    {"axis": "summary", "result": summary},
    {"axis": "trade", "result": trade},
    {"axis": "rates", "result": rates},
    {"axis": "liquidity", "result": liquidity},
    {"axis": "crisis", "result": crisis},
    {"axis": "assets", "result": assets},
    {"axis": "sentiment", "result": sentiment},
]

emit_result(
    table=rows,
    values={
        "market": market,
        "overall": summary.get("overall") if isinstance(summary, dict) else None,
        "score": summary.get("score") if isinstance(summary, dict) else None,
        "tradeDirection": ((trade.get("termsOfTrade") or {}).get("direction") if isinstance(trade, dict) else None),
        "crisisZone": ((crisis.get("recessionDashboard") or {}).get("zone") if isinstance(crisis, dict) else None),
    },
    date=summary.get("latestAsOf") if isinstance(summary, dict) else None,
    sources=["dartlab://macro/assets", "dartlab://macro/crisis", "dartlab://macro/liquidity", "dartlab://macro/rates", "dartlab://macro/sentiment", "dartlab://macro/trade", "dartlab://macro/summary"],
)
```

## 호출 동작

### 1. 결론 도출

7 축 결합 stress 지도 단정. 예: "summary overall=cautious / trade.termsOfTrade=deteriorating / rates=peak / liquidity=neutral / crisis.zone=watch / assets=mixed / sentiment=neutral → KR 매크로 스트레스 phase=mid-stress (7 축 중 3 negative + 3 neutral + 1 mixed). 가장 취약 축: 교역조건 + 신용 zone."

### 2. 핵심 근거 수집

- macro('summary', KR) overall + score — 거시 종합
- macro('trade', KR).termsOfTrade.direction — 교역조건
- macro('rates', KR), macro('liquidity', KR) — 금융 환경
- macro('crisis', KR).recessionDashboard.zone — 위기 zone (normal / watch / alarm)
- macro('assets', KR), macro('sentiment', KR) — 시장 반응

### 3. 메커니즘 분석

```
7 축 (summary / trade / rates / liquidity / crisis / assets / sentiment)
   각 축별 status code → negative / neutral / positive
   ↓
스트레스 score 집계:
   negative 5+ → high-stress
   negative 3-4 + crisis.zone=watch → mid-stress
   neutral majority + negative ≤ 2 → low-stress
   ↓
가장 취약 축 (negative status) 1-2 종 명시
   weak axis = 다음 모니터링 대상 (이 recipe 가 leadership 정함)
```

KR 시장 특성: 외인 수급 + 수출 의존도 ↑ → trade + assets 축이 sentiment leading. rates/liquidity 는 US 의존 — Fed 정책 spillover.

### 4. 반례·한계

- 7 축 데이터 결손 — fragmentation 신호 vs 데이터 부재 분리 X (혼동 위험).
- US macro 의 KR 적용 — Fed 정책 → BOK 정책 lag 변동.
- 환율 단일 축으로 모든 KR stress 단정 금지 — 내수주 vs 수출주 분리 필요.
- 정치 risk (선거 / 외교) 는 7 축 외 — 본 recipe 미커버.

### 5. 후속 모니터링

- crisis.zone=alarm → `recipes.macro.tailRiskScenarioScan` 으로 tail risk 시나리오.
- trade 취약 축 → `recipes.macro.koreaExportCycleNowcast` 로 수출 nowcast.
- assets/sentiment 동시 negative → `recipes.sentiment.flowImbalance` 로 외인 수급 cluster 확인.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `axis` | summary / trade / rates / liquidity / crisis / assets / sentiment |
| `result` | macro 축별 raw result |

## 연계 절차

1. 특정 업종 영향은 `engines.scan` 또는 `engines.industry`.
2. 신용 스트레스가 크면 `recipes.fundamental.credit.cycleStressMap`.
3. 과거 위기 비교는 `recipes.macro.historicalPositioning`.

## 기본 검증

- KR 시장 판단에는 모든 호출에 `market="KR"` 를 명시한다.
- 데이터 결손이 있는 축은 결론에서 제외하거나 낮은 신뢰도로 표시한다.
- 환율/교역/자산 반응의 기준일이 다를 수 있음을 병기한다.
