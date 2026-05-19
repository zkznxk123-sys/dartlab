---
id: recipes.fundamental.quality.forensics.accountTraceLedger
title: Forensics Account Trace Ledger
category: recipes
kind: recipe
scope: builtin
status: observed
graphTier: L1.5
cluster: incubator.forensics
purpose: 매출, CFO, 매출채권, 재고, 매입채무 같은 포렌식 핵심 metric이 어떤 raw statement row에서 왔는지 추적해 엔진 승격 전 계정 매핑 품질을 검증한다. 트리거 — '계정 trace ledger', 'raw 계정 매핑 검산'.
whenToUse:
  - 계정 trace ledger
  - raw 계정 매핑 검산
  - 매출 CFO 매출채권 trace
  - snakeId coverage
inputs:
  - Company.show BS IS CF
outputs:
  - metric to source row mapping
  - missing metric list
capabilityRefs:
  - Company.show
  - Company.trace
toolRefs:
  - EngineCall
  - RunPython
sourceRefs:
  - dartlab://skills/recipes.fundamental.quality.forensics.accountTraceLedger
requiredEvidence:
  - skillRef
  - target
  - tableRef
  - valueRef
  - dateRef
  - sourceRef
  - executionRef
expectedOutputs:
  - metric별 mapped/missing 상태
  - sourceTopic/sourceColumn/sourceLabel
  - aliasesTried
linkedSkills:
  - recipes.fundamental.quality.forensics.revenueToCashBridge
  - recipes.fundamental.quality.forensics.workingCapitalPressureMap
gap:
  primary:
    - reference
    - synth
falsifier:
  description: "핵심 metric trace가 missing인데도 해당 metric으로 위험 신호를 계산하면 실패로 본다."
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
forbidden:
  - 계정명 substring만 보고 단위를 확인하지 않은 채 결론화하지 않는다.
  - missing metric을 0으로 처리하지 않는다.
failureModes:
  - 회사별 snakeId alias가 달라 매출채권/매입채무 매핑 실패
  - 연결과 별도 재무제표 row가 섞임
examples:
  - 삼성전자 raw 계정 trace
  - CFO와 매출채권 source row 확인
lastUpdated: "2026-05-15"
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
    table=memo["tables"]["accountTraceLedger"],
    values={"target": target, "mappedCount": sum(1 for row in memo["tables"]["accountTraceLedger"] if row["status"] == "mapped")},
    date=memo["asOf"],
    sources=memo["sources"],
)
```

## 호출 동작

### 1. 결론 도출

핵심 metric의 mapped/missing 현황을 먼저 보여준다. 이 결과는 후속 bridge의 신뢰도를 결정하는 계정 lineage다.

### 2. 핵심 근거 수집

IS/BS/CF 원표의 `snakeId`, `항목`, `account`, `label` 컬럼을 순서대로 확인하고 표준 alias와 매칭한다.

### 3. 메커니즘 분석

계정 trace는 분석값보다 중요하다. 같은 `receivables`라도 매출채권, 기타채권, 장기채권이 섞이면 DSO가 왜곡된다.

### 4. 반례·한계

은행·보험은 대출채권과 예수부채가 일반 제조업 receivables/payables와 다르다. 이 경우 missing이 정상이며 별도 금융업 모델 후보로 보낸다.

### 5. 후속 모니터링

missing metric은 `reference` alias 후보로 남기고, 반복적으로 등장하면 L1.5 reference mapping 보강 후보가 된다.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `metric` | 표준 metric id |
| `status` | mapped 또는 missing |
| `sourceTopic` | IS/BS/CF |
| `sourceColumn` | 매칭된 label 컬럼 |
| `sourceLabel` | raw row label |
| `aliasesTried` | 시도한 alias |

## 연계 절차

1. recipes.fundamental.quality.forensics.dataCoverageAudit - 원표 coverage를 먼저 확인한다.
2. recipes.fundamental.quality.forensics.revenueToCashBridge - revenue, receivables, CFO, netIncome이 mapped이면 실행한다.
3. recipes.fundamental.quality.forensics.workingCapitalPressureMap - receivables, inventories, payables가 mapped이면 실행한다.

## 기본 검증

- trace missing metric을 사용하는 후속 표는 `status=limited`로 낮춘다.
- 계정 trace 결과 자체를 engineCandidateMemo의 reference 보강 후보로 남긴다.
