---
id: recipes.meta.thesisKillChain.tripwireMonitor
title: Thesis Kill-Chain Tripwire Monitor
category: recipes
kind: recipe
scope: builtin
status: tested
graphTier: L1.5
cluster: incubator.thesisKillChain
purpose: fragility metric별 current, threshold, action을 정리해 thesis가 깨지는 조기 경보선을 만드는 L1/L1.5 절차다. 트리거 — 'Thesis Kill-Chain Tripwire Monitor', 'tripwire monitor', 'tripwireMonitor'.
whenToUse:
  - tripwire monitor
  - thesis 조기 경보
  - kill-chain 임계값
inputs:
  - fragilityMap
  - triggerCatalog
outputs:
  - tripwireMonitor table
capabilityRefs:
  - Company.show
  - Company.gather
toolRefs:
  - EngineCall
  - RunPython
knowledgeRefs:
  - runtime.workbenchEvidenceFlow
sourceRefs:
  - dartlab://skills/recipes.meta.thesisKillChain.tripwireMonitor
requiredEvidence:
  - skillRef
  - tableRef
  - valueRef
  - dateRef
  - sourceRef
  - executionRef
expectedOutputs:
  - tripwire current threshold status action
visualRefs:
  - engines.viz.kpiRibbon
  - engines.viz.evidenceCoverage
visualGuidance:
  - "openTripwireCount는 kpiRibbon chart로 보조하고 tripwireMonitor는 table/표로 제시한다."
linkedSkills:
  - recipes.meta.thesisKillChain.fragilityMap
  - recipes.meta.thesisKillChain.falsifierLedger
  - engines.company
gap:
  primary:
    - synth
    - gather
falsifier:
  description: "threshold 없이 tripwire를 만들면 실패로 본다."
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
  - threshold 없는 watch/risk를 만들지 않는다.
failureModes:
  - current 값만 표시하고 action 누락
examples:
  - 이 thesis의 tripwire 만들어줘
audiences:
  llm: tripwire는 사용자가 나중에 재검사할 수 있게 current/threshold/action을 함께 둔다.
  agent: watch/risk tripwire는 falsifierLedger로 연결한다.
  human: thesis를 계속 들고 가도 되는지 판단할 조기 경보선이다.
humanIntro: "tripwireMonitor는 시나리오를 운영 가능한 체크리스트로 바꾼다. 경보선이 없으면 좋은 pre-mortem도 실행되지 않는다."
lastUpdated: "2026-05-17"
testUniverse:
  market: KR
  stockCodes:
    - "005930"
---

## 공개 호출 방식

AI 도구 실행 순서는 `EngineCall` 우선이다. 아래 Python 블록은 확보한 L1/L1.5 근거를 `buildThesisKillChainMemo`로 묶는 **RunPython fallback** 절차다.

```python
from dartlab.synth.thesisKillChain import buildThesisKillChainMemo

target = "005930"
thesis = "매출 성장과 현금 전환이 유지되어 valuation discount가 해소된다"
priceRows = [{"date": "2026-05-11", "close": 90000}, {"date": "2026-05-10", "close": 100000}]

memo = buildThesisKillChainMemo(target=target, thesis=thesis, priceRows=priceRows)

emit_result(
    table=memo["tables"]["tripwireMonitor"],
    values=memo["headline"],
    date=memo["asOf"],
    sources=memo["sources"],
)
```

## 호출 동작

### 1. 결론 도출

tripwire current + threshold + action 단정. 예: "tripwireMonitor 6 row — T1=opmYoY current=-1.5% threshold=-2% status=watch action='3Q 컨퍼런스콜 모니터링' / T2=cfoNi current=0.85 threshold=0.7 status=ok / T3=price60d current=-12% threshold=-15% status=watch action='reverse signal 확인' / T4=consensus current=-3% threshold=-5% status=ok / T5=foreignFlow current=-5건 missing → 4 ok/watch + 1 missing — 운영 가능 monitor 5 종."

### 2. 핵심 근거 수집

- fragilityMap (current value)
- triggerCatalog (threshold 정의)
- Company.show/gather (실시간 current 재측정)
- buildThesisKillChainMemo() → tripwireMonitor table

### 3. 메커니즘 분석

```
fragility metric → tripwire row 변환
   current (실시간 값) + threshold (임계) + status (현재 거리)
   ↓
status 판정:
   |current - threshold| > 1 std → ok (안전 거리)
   |current - threshold| < 1 std → watch (근접)
   current 가 threshold 를 trigger 방향으로 넘어섬 → risk
   data 결손              → missing
   ↓
action 강제:
   각 watch/risk row 에 action 정의:
     "3Q 컨퍼런스콜 모니터링"
     "reverse signal 확인"
     "consensus 재측정 (월간)"
   threshold + action 없는 row → 실패 (forbidden)
   ↓
운영 가능성:
   thesis 를 *계속 들고 갈지* 판단하는 조기 경보선
   사용자가 나중에 재검사 가능한 체크리스트
```

tripwireMonitor = scenario 를 *운영 체크리스트* 로 변환. threshold + action 없는 watch/risk → forbidden 위반.

### 4. 반례·한계

- threshold 없는 watch/risk → forbidden + failureMode.
- current 값만 표시 + action 누락 → 운영 불가능.
- threshold 가 vague ("적절한 수준") → quantitative 임계 강제.
- missing tripwire 를 결론에 사용 → 실패.

### 5. 후속 모니터링

- watch/risk 다수 → `recipes.meta.thesisKillChain.falsifierLedger` 로 반증 조건.
- 모든 tripwire 가 ok → `recipes.meta.thesisKillChain.premortemQualityGate` 로 thesis 견조 확인.
- tripwire trigger 발동 → `recipes.meta.thesisKillChain.scenarioStoryboard` 로 시나리오 전개.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `tripwire` | 모니터링 지표 |
| `current` | 현재값 |
| `threshold` | watch/risk 임계 |
| `status` | ok/watch/risk/missing |
| `action` | 다음 조치 |

## 연계 절차

1. recipes.meta.thesisKillChain.falsifierLedger - watch/risk 반증 조건.
2. recipes.meta.thesisKillChain.scenarioStoryboard - tripwire를 시나리오로 변환.

## 기본 검증

- threshold와 action이 없는 row는 실패다.
- missing tripwire는 결론에 쓰지 않는다.
