---
id: recipes.macro.koreaMacroStressMap
title: 한국 매크로 스트레스 지도
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: 한국 시장을 기준으로 환율, 교역, 금리, 유동성, 위기, 자산/심리 축을 묶어 외국인 수급과 수출 민감도가 큰 시장의 거시 스트레스를 판단하는 절차. 트리거 — '한국 매크로', 'KR 스트레스', '원달러', 'KOSPI 위험', '수출 경기'.
whenToUse:
  - 한국 매크로
  - KR macro stress
  - 원달러 스트레스
  - KOSPI 위험
  - 수출 경기
  - 외국인 수급과 환율
linkedSkills:
  - engines.macro.trade
  - engines.macro.rates
  - engines.macro.liquidity
  - engines.macro.crisis
  - engines.macro.assets
  - engines.macro.sentiment
  - engines.macro.summary
  - engines.scan
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - dateRef
  - valueRef
visualRefs:
  - "engines.viz.scenarioVisuals"
  - "engines.viz.tableBackedChart"
  - "engines.viz.mermaidDiagram"
visualGuidance:
  - "stress·민감도·충격 전파는 engines.viz.scenarioVisuals를 사용하고 assumption grid 또는 수치 임계가 없으면 scenario table로 낮춘다."
  - "표 기반 순위·추세는 engines.viz.tableBackedChart만 사용하고 tableRef/evidenceBinding이 없으면 차트 대신 검산 표로 낮춘다."
  - "메커니즘 diagram은 engines.viz.mermaidDiagram으로 8노드 이하만 만들고 모든 edge에 문장·수치·sourceRef 근거를 둔다."

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
)
```

## 호출 동작

1. `market="KR"` 를 모든 macro 호출에 명시한다.
2. `trade` 로 수출/교역조건 축을 먼저 확인한다.
3. `rates/liquidity/crisis` 로 금융 스트레스와 정책 환경을 확인한다.
4. `assets/sentiment` 로 시장 반응을 확인한다.
5. `summary` 와 개별 축이 충돌하면 개별 축의 기준일과 결손을 확인한다.

## 대표 반환 형태

- `tableRef`: KR macro 축별 결과.
- `valueRef`: overall, score, tradeDirection, crisisZone.
- `dateRef`: 각 축의 최신 관측일.
- 답변 본문: 환율/교역, 금리/유동성, 신용/위기, 자산/심리의 스트레스 지도.

## 연계 절차

1. 특정 업종 영향은 `engines.scan` 또는 `engines.industry`.
2. 신용 스트레스가 크면 `recipes.credit.cycleStressMap`.
3. 과거 위기 비교는 `recipes.macro.historicalPositioning`.

## 기본 검증

- KR 시장 판단에는 모든 호출에 `market="KR"` 를 명시한다.
- 데이터 결손이 있는 축은 결론에서 제외하거나 낮은 신뢰도로 표시한다.
- 환율/교역/자산 반응의 기준일이 다를 수 있음을 병기한다.
