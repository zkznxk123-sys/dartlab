---
id: recipes.fundamental.disclosure.eventRadar.eventInbox
title: Event Radar Event Inbox
category: recipes
kind: recipe
scope: builtin
status: observed
graphTier: L1.5
cluster: incubator.eventRadar
purpose: Company.disclosure/liveFilings와 gather.news 원자료의 제목·본문 키워드만으로 단기 이벤트 inbox를 만드는 L1/L1.5 절차다.
whenToUse:
  - event inbox
  - 공시 뉴스 촉매
  - 이벤트 분류
inputs:
  - filing rows
  - news rows
outputs:
  - eventInbox table
capabilityRefs:
  - Company.disclosure
  - Company.liveFilings
  - Company.gather
toolRefs:
  - EngineCall
  - RunPython
knowledgeRefs:
  - engines.company
  - engines.gather
sourceRefs:
  - dartlab://skills/recipes.fundamental.disclosure.eventRadar.eventInbox
requiredEvidence:
  - skillRef
  - target
  - tableRef
  - dateRef
  - sourceRef
  - executionRef
expectedOutputs:
  - event category와 status
  - filing/news source
visualRefs:
  - engines.viz.evidenceCoverage
visualGuidance:
  - "eventInbox는 table/표가 우선이며 coverage 상태만 engines.viz.evidenceCoverage로 보조한다."
linkedSkills:
  - recipes.fundamental.disclosure.eventRadar.falsifierLedger
  - recipes.fundamental.disclosure.eventRadar.deepDive
gap:
  primary:
    - synth
    - gather
falsifier:
  description: "정기 공시·중복 뉴스 여부를 반증하지 않으면 실패로 본다."
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
  - 키워드만으로 이벤트 중요도를 확정하지 않는다.
failureModes:
  - 정기보고서 제출을 새로운 촉매로 오해
examples:
  - 오늘 공시 뉴스 이벤트 inbox
audiences:
  llm: filing/news row를 EngineCall로 받은 뒤 helper fallback으로 eventInbox를 만든다.
  agent: category와 status를 항상 source/date와 함께 표시한다.
  human: 공시·뉴스 원자료를 하나의 촉매 inbox로 정리한다.
humanIntro: "eventInbox는 이벤트 후보를 모으는 단계다. 아직 원인·결론이 아니라, 뒤의 reaction과 falsifier를 붙일 후보 목록이다."
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

def rows(value, limit=30):
    if hasattr(value, "head") and hasattr(value, "to_dicts"):
        return value.head(limit).to_dicts()
    if isinstance(value, list):
        return value[:limit]
    return []

try:
    filings = rows(c.liveFilings(days=7), limit=20)
except Exception:
    try:
        filings = rows(c.disclosure(), limit=50)
    except Exception:
        filings = []

try:
    news_rows = rows(c.gather("news"), limit=20)
except Exception:
    news_rows = []

memo = buildEventRadarMemo(
    target=target,
    market=str(getattr(c, "market", "KR")),
    companyName=str(getattr(c, "corpName", target)),
    filings=filings,
    newsRows=news_rows,
)

emit_result(
    table=memo["tables"]["eventInbox"],
    values=memo["headline"],
    date=memo["asOf"],
    sources=memo["sources"],
)
```

## 호출 동작

공시·뉴스 row를 날짜 역순으로 정렬하고 earnings, capitalAction, financing, governance, regulatory, filingRisk, deal category로 분류한다.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `date` | 공시·뉴스 날짜 |
| `source` | filing/news |
| `title` | 원문 제목 |
| `category` | 이벤트 유형 |
| `status` | ok/watch/risk/missing |

## 연계 절차

1. recipes.fundamental.disclosure.eventRadar.priceFlowReaction - 이벤트 뒤 시장 반응 확인.
2. recipes.fundamental.disclosure.eventRadar.falsifierLedger - 정기·중복 이벤트 반증.

## 기본 검증

- eventInbox row에는 date/source/title/status가 있어야 한다.
- missing이면 이벤트 결론을 내지 않는다.
