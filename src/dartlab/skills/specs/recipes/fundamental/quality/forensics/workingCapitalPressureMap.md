---
id: recipes.fundamental.quality.forensics.workingCapitalPressureMap
title: Working Capital Pressure Map
category: recipes
kind: recipe
scope: builtin
status: observed
graphTier: L1.5
cluster: incubator.forensics
purpose: raw BS/IS만으로 DSO, DIO, DPO, CCC와 재고 성장 gap을 계산해 운전자본 압력이 이익품질·유동성 신호로 승격 가능한지 실험한다. 트리거 — '운전자본 pressure', 'CCC 원표 계산', '재고 매출 gap'.
whenToUse:
  - 운전자본 pressure
  - CCC 원표 계산
  - DSO DIO DPO
  - 재고 매출 gap
  - 매입채무 회전
inputs:
  - Company.show BS IS
outputs:
  - DSO DIO DPO CCC
  - inventory growth minus revenue growth
  - pressure status
capabilityRefs:
  - Company.show
toolRefs:
  - EngineCall
  - RunPython
sourceRefs:
  - dartlab://skills/recipes.fundamental.quality.forensics.workingCapitalPressureMap
requiredEvidence:
  - skillRef
  - target
  - tableRef
  - valueRef
  - dateRef
  - sourceRef
  - executionRef
expectedOutputs:
  - 기간별 CCC와 구성요소
  - 재고 성장 초과분
  - pressure status와 반증 조건
linkedSkills:
  - recipes.fundamental.quality.forensics.falsifierLedger
  - recipes.fundamental.quality.forensics.engineCandidateMemo
gap:
  primary:
    - synth
    - scan
falsifier:
  description: "재고 증가는 수주잔고 또는 신제품 선출하 준비로 설명될 수 있으므로 매출 부진 신호와 함께 볼 때만 위험으로 본다."
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
forbidden:
  - 산업별 정상 CCC 차이를 무시하고 절대 일수만 비교하지 않는다.
  - 재고 증가 하나만으로 평가손 위험을 단정하지 않는다.
failureModes:
  - costOfSales 결손 시 revenue를 대체 분모로 쓰면서 한계를 숨김
  - 금융업과 제조업 CCC를 같은 기준으로 비교
examples:
  - 재고가 매출보다 빠르게 느는지 봐줘
  - 삼성전자 CCC 원표 계산
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
    table=memo["tables"]["workingCapitalPressureMap"],
    values={"target": target, "latestStatus": memo["tables"]["workingCapitalPressureMap"][0]["status"] if memo["tables"]["workingCapitalPressureMap"] else "missing"},
    date=memo["asOf"],
    sources=memo["sources"],
)
```

## 호출 동작

### 1. 결론 도출

최근 기간의 CCC와 inventory growth gap을 보고 `ok`, `watch`, `risk`로 분류한다.

### 2. 핵심 근거 수집

BS의 receivables, inventories, payables와 IS의 revenue, costOfSales를 기간별로 맞춘다.

### 3. 메커니즘 분석

DSO는 회수 지연, DIO는 재고 적체, DPO는 거래처 신용 사용을 보여준다. 셋을 합친 CCC가 길어질수록 현금이 영업 운전자본에 묶인다.

### 4. 반례·한계

수주산업, 유통업, 플랫폼, 금융업은 정상 운전자본 구조가 다르다. costOfSales가 없으면 revenue 분모 fallback이 들어가므로 한계를 표시한다.

### 5. 후속 모니터링

CCC가 길어지고 revenue-to-cash bridge도 약하면 대손·재고평가 주석과 이벤트 공시를 확인한다.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `period` | 기간 |
| `dsoDays` | 매출채권 회수일수 |
| `dioDays` | 재고 보유일수 |
| `dpoDays` | 매입채무 지급일수 |
| `cccDays` | 현금전환주기 |
| `inventoryGrowthMinusRevenueGrowth` | 재고 성장 초과분 |
| `status` | ok/watch/risk |

## 연계 절차

1. recipes.fundamental.quality.forensics.accountTraceLedger - receivables, inventories, payables trace를 확인한다.
2. recipes.fundamental.quality.forensics.noteSignalExtractor - 재고평가·대손 주석 확인.
3. recipes.fundamental.quality.forensics.falsifierLedger - backlog, 신제품, 계절성 반증.

## 기본 검증

- DSO + DIO - DPO가 CCC와 일치해야 한다.
- 단년도 spike는 trend가 아니라 watch로만 둔다.
