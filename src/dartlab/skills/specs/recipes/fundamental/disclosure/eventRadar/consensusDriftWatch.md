---
id: recipes.fundamental.disclosure.eventRadar.consensusDriftWatch
title: Event Radar Consensus Drift Watch
category: recipes
kind: recipe
scope: builtin
status: observed
graphTier: L1.5
cluster: incubator.eventRadar
purpose: gather consensus 원자료의 최근 두 row를 비교해 매출, 영업이익, EPS, 목표가 변화 신호를 확인하는 L1/L1.5 절차다.
whenToUse:
  - consensus drift
  - 컨센서스 변화
  - 목표주가 변동
inputs:
  - consensus rows
outputs:
  - consensusDriftWatch table
capabilityRefs:
  - Company.gather
toolRefs:
  - EngineCall
  - RunPython
knowledgeRefs:
  - engines.gather
sourceRefs:
  - dartlab://skills/recipes.fundamental.disclosure.eventRadar.consensusDriftWatch
requiredEvidence:
  - skillRef
  - target
  - tableRef
  - valueRef
  - dateRef
  - sourceRef
  - executionRef
expectedOutputs:
  - metric별 latest previous revisionPct
visualRefs:
  - engines.viz.kpiRibbon
  - engines.viz.evidenceCoverage
visualGuidance:
  - "컨센서스 drift는 source/date가 안정적일 때만 kpiRibbon chart 보조 숫자로 표시하고 원자료 table을 보존한다."
linkedSkills:
  - recipes.fundamental.disclosure.eventRadar.falsifierLedger
  - recipes.fundamental.disclosure.eventRadar.deepDive
  - engines.company
gap:
  primary:
    - gather
    - synth
falsifier:
  description: "단일 stale broker update, currency/unit change를 반증하지 않으면 실패로 본다."
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
  - 컨센서스 변화 하나로 실적 결론을 단정하지 않는다.
failureModes:
  - 단위 변경을 실적 하향으로 오해
examples:
  - 컨센서스가 최근 하향됐는지 확인
audiences:
  llm: consensus row는 EngineCall로 받고 helper fallback은 최근 두 row drift만 계산한다.
  agent: metric별 latest/previous/revisionPct를 sourceRef와 함께 제시한다.
  human: 시장 기대가 변했는지 원자료로만 확인한다.
humanIntro: "consensusDriftWatch는 시장 기대의 움직임을 보는 보조 신호다. 원자료 날짜와 단위를 모르면 방향성을 말하지 않는다."
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

def rows(value, limit=12):
    if hasattr(value, "head") and hasattr(value, "to_dicts"):
        return value.head(limit).to_dicts()
    if isinstance(value, list):
        return value[:limit]
    return []

try:
    consensus_rows = rows(c.gather("consensus"), limit=12)
except Exception:
    consensus_rows = []

memo = buildEventRadarMemo(
    target=target,
    market=str(getattr(c, "market", "KR")),
    companyName=str(getattr(c, "corpName", target)),
    consensusRows=consensus_rows,
)

emit_result(
    table=memo["tables"]["consensusDriftWatch"],
    values=memo["headline"],
    date=memo["asOf"],
    sources=memo["sources"],
)
```

## 호출 동작

최근 두 consensus row의 revenue, operatingProfit, eps, targetPrice 값을 비교해 revisionPct와 status를 만든다.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `date` | 최신 consensus 날짜 |
| `metric` | revenue/operatingProfit/eps/targetPrice |
| `latest` | 최신값 |
| `previous` | 이전값 |
| `revisionPct` | 변화율 |
| `status` | ok/watch/risk/missing |

## 연계 절차

1. recipes.fundamental.disclosure.eventRadar.eventInbox - 컨센서스 변화 전후 이벤트 확인.
2. recipes.fundamental.disclosure.eventRadar.falsifierLedger - stale update 반증.

## 기본 검증

- consensus row가 2개 미만이면 drift를 계산하지 않는다.
- 단위·통화가 확인되지 않으면 결론을 제한한다.
