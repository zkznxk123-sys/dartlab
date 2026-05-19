---
id: recipes.incubator.eventRadar.capitalActionMonitor
title: Event Radar Capital Action Monitor
category: recipes
kind: recipe
scope: builtin
status: observed
graphTier: L1.5
cluster: incubator.eventRadar
purpose: dividends, splits, 자사주, 증자, 전환사채 등 자본 이벤트 원자료를 묶어 단기 촉매를 확인하는 L1/L1.5 절차다.
whenToUse:
  - capital action monitor
  - 배당 자사주 분할 증자
  - 전환사채 이벤트
inputs:
  - dividend rows
  - split rows
  - filing event rows
outputs:
  - capitalActionMonitor table
capabilityRefs:
  - Company.disclosure
  - Company.gather
toolRefs:
  - EngineCall
  - RunPython
knowledgeRefs:
  - engines.company
  - engines.gather
  - engines.scan
sourceRefs:
  - dartlab://skills/recipes.incubator.eventRadar.capitalActionMonitor
requiredEvidence:
  - skillRef
  - target
  - tableRef
  - valueRef
  - dateRef
  - sourceRef
  - executionRef
expectedOutputs:
  - dividend/split/filing capital action rows
visualRefs:
  - engines.viz.kpiRibbon
  - engines.viz.evidenceCoverage
visualGuidance:
  - "capital action count는 engines.viz.kpiRibbon chart의 보조 숫자로만 표시하고 원표는 table/표로 보존한다."
linkedSkills:
  - recipes.incubator.eventRadar.eventInbox
  - recipes.incubator.eventRadar.falsifierLedger
gap:
  primary:
    - gather
    - synth
falsifier:
  description: "정기 배당, 기계적 분할, 희석 이벤트 여부를 분리하지 않으면 실패로 본다."
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
  - 배당·분할을 항상 호재로 단정하지 않는다.
failureModes:
  - 유상증자와 무상증자 영향을 섞음
examples:
  - 배당 자사주 분할 증자 이벤트 확인
audiences:
  llm: capital 관련 원자료는 EngineCall로 받고 helper fallback으로 action table을 만든다.
  agent: action과 value를 source/date에 묶어 표시한다.
  human: 자본 이벤트가 실제 촉매인지 따로 확인한다.
humanIntro: "capitalActionMonitor는 배당·분할·증자 같은 표면상 큰 이벤트를 모으되, 반복 배당과 희석 이벤트를 분리해 과잉 해석을 막는다."
lastUpdated: "2026-05-17"
---

## 공개 호출 방식

AI 도구 실행 순서는 `EngineCall` 우선이다. 아래 Python 블록은 확보한 L1/L1.5 근거를 `buildEventRadarMemo`로 묶는 **RunPython fallback** 절차다.

```python
import dartlab
from dartlab.synth.eventRadar import buildEventRadarMemo

target = "005930"
c = dartlab.Company(target)

def rows(value, limit=20):
    if hasattr(value, "head") and hasattr(value, "to_dicts"):
        return value.head(limit).to_dicts()
    if isinstance(value, list):
        return value[:limit]
    return []

try:
    filings = rows(c.disclosure(), limit=50)
except Exception:
    filings = []

try:
    dividend_rows = rows(c.gather("dividends"), limit=20)
except Exception:
    dividend_rows = []

try:
    split_rows = rows(c.gather("splits"), limit=20)
except Exception:
    split_rows = []

memo = buildEventRadarMemo(
    target=target,
    market=str(getattr(c, "market", "KR")),
    companyName=str(getattr(c, "corpName", target)),
    filings=filings,
    dividendRows=dividend_rows,
    splitRows=split_rows,
)

emit_result(
    table=memo["tables"]["capitalActionMonitor"],
    values=memo["headline"],
    date=memo["asOf"],
    sources=memo["sources"],
)
```

## 호출 동작

dividend/split row와 filing event의 capitalAction category를 하나의 action table로 합친다.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `date` | 기준일 |
| `action` | dividend/split/filingCapitalAction |
| `value` | 배당금, 분할비율, filing title |
| `status` | watch/missing |
| `evidence` | 원자료 출처 |

## 연계 절차

1. recipes.incubator.eventRadar.eventInbox - 자본 이벤트 공시 분류.
2. recipes.incubator.eventRadar.falsifierLedger - 정기성·희석 반증.

## 기본 검증

- 자본 이벤트는 호재·악재 결론이 아니라 action row로 둔다.
- value가 없으면 제목과 sourceRef를 근거로 둔다.
