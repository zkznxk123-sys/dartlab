---
id: recipes.fundamental.disclosure.eventRadar.priceFlowReaction
title: Event Radar Price Flow Reaction
category: recipes
kind: recipe
scope: builtin
status: tested
graphTier: L1.5
cluster: incubator.eventRadar
purpose: gather price/flow 원자료로 이벤트 전후 가격·거래량·수급 반응을 확인하는 L1/L1.5 절차다.
whenToUse:
  - price flow reaction
  - 이벤트 주가 반응
  - 거래량 수급 확인
inputs:
  - price rows
  - flow rows
outputs:
  - priceFlowReaction table
capabilityRefs:
  - Company.gather
  - scan.market
toolRefs:
  - EngineCall
  - RunPython
knowledgeRefs:
  - engines.gather
  - engines.scan
sourceRefs:
  - dartlab://skills/recipes.fundamental.disclosure.eventRadar.priceFlowReaction
requiredEvidence:
  - skillRef
  - tableRef
  - valueRef
  - dateRef
  - sourceRef
  - executionRef
expectedOutputs:
  - priceChangePct
  - volumeRatio
  - foreign/institution net flow
visualRefs:
  - engines.viz.priceChart
  - engines.viz.kpiRibbon
visualGuidance:
  - "priceRows의 date/close/volume이 있을 때만 engines.viz.priceChart를 사용한다."
linkedSkills:
  - recipes.fundamental.disclosure.eventRadar.eventInbox
  - recipes.fundamental.disclosure.eventRadar.falsifierLedger
  - engines.company
gap:
  primary:
    - gather
    - synth
falsifier:
  description: "시장 전체 움직임이나 stale flow를 반증하지 않으면 실패로 본다."
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: supported
  pyodide:
    status: limited
forbidden:
  - 가격 급등락만으로 이벤트 원인을 단정하지 않는다.
failureModes:
  - 거래정지·액면분할을 가격 반응으로 오해
examples:
  - 공시 후 주가와 수급 반응 확인
audiences:
  llm: price/flow는 EngineCall로 먼저 가져오고 helper fallback은 계산 ledger만 만든다.
  agent: priceChart는 raw price row가 있을 때만 선택한다.
  human: 이벤트가 시장에서 실제로 반응했는지 확인한다.
humanIntro: "priceFlowReaction은 이벤트 후보와 시장 반응을 연결하지만, 원인 단정은 하지 않는다. 가격·거래량·수급은 falsifier와 함께 읽는다."
lastUpdated: "2026-05-17"
testUniverse:
  market: KR
  stockCodes:
    - "005930"
---

## 공개 호출 방식

AI 도구 실행 순서는 `EngineCall` 우선이다. 아래 Python 블록은 확보한 L1/L1.5 근거를 `buildEventRadarMemo`로 묶는 **RunPython fallback** 절차다.

```python
import dartlab
from dartlab.synth.eventRadar import buildEventRadarMemo

target = "005930"
c = dartlab.Company(target)

def rows(value, limit=40):
    if hasattr(value, "head") and hasattr(value, "to_dicts"):
        return value.head(limit).to_dicts()
    if isinstance(value, list):
        return value[:limit]
    return []

try:
    price_rows = rows(c.gather("price"), limit=40)
except Exception:
    price_rows = []

try:
    flow_rows = rows(c.gather("flow"), limit=40)
except Exception:
    flow_rows = []

memo = buildEventRadarMemo(
    target=target,
    market=str(getattr(c, "market", "KR")),
    companyName=str(getattr(c, "corpName", target)),
    priceRows=price_rows,
    flowRows=flow_rows,
)

emit_result(
    table=memo["tables"]["priceFlowReaction"],
    values=memo["headline"],
    date=memo["asOf"],
    sources=memo["sources"],
)
```

## 호출 동작

### 1. 결론 도출

price + volume + net flow reaction 단정. 예: "기준일 close=78,500 / priceChangePct=+2.1% (직전 종가 대비) / volumeRatio=1.8× (평균 거래량 대비) / netFlow=+45억 (외인+기관) → 가격 + 거래량 + 수급 3 신호 양수 동조 = reaction watch (이벤트 trigger candidate)."

### 2. 핵심 근거 수집

- Company.gather('price') latest 40 row — close + volume
- Company.gather('flow') latest 40 row — 외인 + 기관 순매수
- 최근 2 price row → priceChangePct + volumeRatio 계산
- 최신 flow row → 외인 + 기관 합산 netFlow

### 3. 메커니즘 분석

```
price[-1] vs price[-2] → priceChangePct = (close[-1]/close[-2] - 1) × 100
volume[-1] vs avg(volume[-21:-1]) → volumeRatio = volume[-1] / avg
flow[-1] → netFlow = foreignNet + institutionNet
   ↓
3 signal 동조 판정:
   priceChangePct > 1% + volumeRatio > 1.5 + netFlow > 0 → 강한 reaction (양수)
   priceChangePct < -1% + volumeRatio > 1.5 + netFlow < 0 → 강한 reaction (음수)
   1 신호만 → weak (noise 가능)
   부호 mixed → 해석 어려움 (예: 가격 ↑ + flow ↓ → 개인 매수 추격)
   ↓
status:
   watch  → 3 신호 동조 (이벤트 신호 강함)
   risk   → 가격 -3%+ 또는 거래정지
   ok     → 정상 범위
   missing → row 부재
```

reaction 자체는 *시장 반응* — 원인 단정 X (이벤트 inbox 와 결합 필요). 시장 전체 같은 시점 같은 방향 변동 시 → 회사 고유 신호 아님.

### 4. 반례·한계

- 시장 전체 ±2%+ 움직임 시 → 회사 고유 신호와 분리 불가.
- 거래정지·액면분할 직후 priceChangePct 무의미 (-30% 가짜).
- 거래량 평균 20 일 윈도우 — 분기 이벤트 (실적/배당) 시점 base 왜곡.
- flow 데이터 lag 1 영업일 — 같은 날 price 와 동기화 X.

### 5. 후속 모니터링

- watch + 같은 시점 inbox 이벤트 → `recipes.fundamental.disclosure.eventRadar.eventInbox` 와 cross-check.
- mixed 부호 → `recipes.fundamental.disclosure.eventRadar.falsifierLedger` 로 market-wide 반증.
- volumeRatio 큼 + netFlow 부호 일관 → `recipes.technical.priceVolumeZScore` 로 z-score event 점검.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `date` | 기준일 |
| `close` | 최신 종가 |
| `priceChangePct` | 직전 대비 변화율 |
| `volumeRatio` | 직전 대비 거래량 배수 |
| `netFlow` | 외국인+기관 순매수 |
| `status` | ok/watch/risk/missing |

## 연계 절차

1. recipes.fundamental.disclosure.eventRadar.eventInbox - 어떤 이벤트가 있었는지 확인.
2. recipes.fundamental.disclosure.eventRadar.falsifierLedger - market-wide move 반증.

## 기본 검증

- priceRows가 없으면 priceChart를 만들지 않는다.
- priceChangePct와 volumeRatio는 직전 row가 없으면 None으로 둔다.
