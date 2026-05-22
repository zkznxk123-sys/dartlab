---
id: recipes.fundamental.quality.forensics.revenueToCashBridge
title: Revenue To Cash Bridge
category: recipes
kind: recipe
scope: builtin
status: observed
graphTier: L1.5
cluster: incubator.forensics
purpose: L2 이익품질 엔진 없이 raw IS/BS/CF만으로 매출 성장, 매출채권 성장, CFO/순이익 괴리를 연결해 매출이 현금으로 회수되는지 검증한다. 트리거 — '매출 현금 bridge', 'revenue to cash', '매출채권 괴리'.
whenToUse:
  - 매출 현금 bridge
  - revenue to cash
  - 매출채권 괴리
  - CFO 순이익 괴리
  - 매출 신뢰도 원표 검증
inputs:
  - Company.show IS BS CF
outputs:
  - revenue growth
  - receivable growth
  - CFO to net income
  - divergence status
capabilityRefs:
  - Company.show
toolRefs:
  - EngineCall
  - RunPython
sourceRefs:
  - dartlab://skills/recipes.fundamental.quality.forensics.revenueToCashBridge
requiredEvidence:
  - skillRef
  - target
  - tableRef
  - valueRef
  - dateRef
  - sourceRef
  - executionRef
expectedOutputs:
  - 기간별 매출 성장과 매출채권 성장 gap
  - CFO/NI와 CFO/Revenue 비율
  - watch/risk 판정과 반증 조건
linkedSkills:
  - recipes.fundamental.quality.forensics.falsifierLedger
  - recipes.fundamental.quality.forensics.engineCandidateMemo
  - engines.company
gap:
  primary:
    - synth
    - frame
falsifier:
  description: "매출채권 증가가 신규 대형 고객의 결제조건 또는 계절성으로 설명되면 위험 신호를 낮춘다."
forbidden:
  - 매출채권 증가 하나만으로 분식 또는 매출 과대계상을 단정하지 않는다.
  - CFO가 음수인 성장기업을 즉시 위험으로 단정하지 않는다.
failureModes:
  - 매출채권 계정에 기타채권이 섞여 false positive 발생
  - 대형 프로젝트 검수·정산 시점으로 특정 연도만 왜곡
examples:
  - 매출은 늘었는데 현금이 안 따라오는지 봐줘
  - 삼성전자 revenue to cash bridge
lastUpdated: "2026-05-15"
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
testUniverse:
  market: KR
  stockCodes:
    - "005930"
visualRefs:
  - "engines.viz.evidenceCoverage"
  - "engines.viz.mermaidDiagram"
  - "engines.viz.tableBackedChart"
---

## 공개 호출 방식

```python
import dartlab
from dartlab.synth.evidenceForensics import buildEvidenceForensicsMemo

target = "005930"
c = dartlab.Company(target)
statements = {}
for topic in ("IS", "BS", "CF"):
    try:
        statements[topic] = c.show(topic, freq="Y")
    except TypeError:
        statements[topic] = c.show(topic)
    except Exception:
        pass

memo = buildEvidenceForensicsMemo(
    target=target,
    market=str(getattr(c, "market", "KR")),
    companyName=str(getattr(c, "corpName", target)),
    statements=statements,
)

emit_result(
    table=memo["tables"]["revenueToCashBridge"],
    values={"target": target, "latestStatus": memo["tables"]["revenueToCashBridge"][0]["status"] if memo["tables"]["revenueToCashBridge"] else "missing"},
    date=memo["asOf"],
    sources=memo["sources"],
)
```

## 호출 동작

### 1. 결론 도출

최근 기간의 `receivableGrowthMinusRevenueGrowth`와 `cfoToNetIncome`을 함께 보고 `ok`, `watch`, `risk`로만 표시한다. 투자 결론은 만들지 않는다.

### 2. 핵심 근거 수집

IS의 revenue, BS의 receivables, CF의 CFO, IS의 netIncome을 기간별로 맞춘다.

### 3. 메커니즘 분석

매출이 늘었는데 매출채권이 더 빠르게 늘고 CFO/NI가 약하면 이익이 현금으로 회수되지 않았을 가능성이 커진다.

### 4. 반례·한계

매출채권 증가는 신규 고객, 수출 결제조건, 계절성, 프로젝트 검수 지연으로 설명될 수 있다. 반드시 `falsifierLedger`로 넘긴다.

### 5. 후속 모니터링

`risk`이면 다음 분기 receivables gap, CFO/NI, 대손충당금 주석, 정정공시를 같이 본다.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `period` | 기간 |
| `revenueGrowth` | 매출 성장률 |
| `receivableGrowth` | 매출채권 성장률 |
| `receivableGrowthMinusRevenueGrowth` | 채권 성장 초과분 |
| `cfoToNetIncome` | 영업현금흐름 / 순이익 |
| `cfoToRevenue` | 영업현금흐름 / 매출 |
| `status` | ok/watch/risk |

## 연계 절차

1. recipes.fundamental.quality.forensics.accountTraceLedger - revenue, receivables, CFO trace 확인.
2. recipes.fundamental.quality.forensics.workingCapitalPressureMap - 운전자본 압력과 함께 해석한다.
3. recipes.fundamental.quality.forensics.falsifierLedger - 반증 조건 확인.
4. recipes.fundamental.quality.forensics.engineCandidateMemo - 반복 가능 신호면 엔진 후보 등록.

## 기본 검증

- gap 값은 percent point가 아니라 ratio difference로 저장한다.
- 결손 metric이 있으면 해당 행의 status를 과하게 올리지 않는다.
