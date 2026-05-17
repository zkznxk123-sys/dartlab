---
id: recipes.incubator.forensics.dataCoverageAudit
title: Forensics Data Coverage Audit
category: recipes
kind: recipe
scope: builtin
status: observed
graphTier: L1.5
cluster: incubator.forensics
purpose: 포렌식 분석 전에 Company.show 원표와 L1.5 helper가 실제로 어떤 기간·계정 coverage를 갖는지 확인해 결손을 0으로 채우는 회귀를 막는다. 트리거 — '포렌식 데이터 coverage', '원표 결손 점검'.
whenToUse:
  - 포렌식 데이터 coverage
  - 원표 결손 점검
  - BS IS CF 가용성
  - L1.5 helper 입력 검산
inputs:
  - Company.show BS IS CF
outputs:
  - coverage table
  - latest period
  - mapped metric count
capabilityRefs:
  - Company.show
toolRefs:
  - EngineCall
  - RunPython
sourceRefs:
  - dartlab://skills/recipes.incubator.forensics.dataCoverageAudit
requiredEvidence:
  - skillRef
  - target
  - tableRef
  - valueRef
  - dateRef
  - sourceRef
  - executionRef
expectedOutputs:
  - IS BS CF rowCount와 periodCount
  - normalizedPanel metric coverage
  - 결손 시 후속 분석 차단 사유
linkedSkills:
  - recipes.incubator.forensics.accountTraceLedger
  - recipes.incubator.forensics.revenueToCashBridge
gap:
  primary:
    - synth
    - frame
falsifier:
  description: "IS/BS/CF 중 하나가 없는데도 이후 포렌식 계산이 정상 결론처럼 진행되면 실패로 본다."
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
forbidden:
  - 결손 원표를 0으로 채우지 않는다.
  - latestPeriod 없이 최신 데이터라고 말하지 않는다.
  - coverage가 낮은데 riskScore를 단정하지 않는다.
failureModes:
  - topic 이름을 추측하고 c.topics 확인 없이 실패를 숨김
  - 분기/연간 컬럼을 섞어 같은 period처럼 사용
examples:
  - 삼성전자 포렌식 데이터 coverage
  - BS IS CF 원표 결손 점검
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
    table=memo["tables"]["dataCoverageAudit"],
    values={"target": target, "decisionStatus": memo["decisionStatus"], "riskScore": memo["headline"]["riskScore"]},
    date=memo["asOf"],
    sources=memo["sources"],
)
```

## 호출 동작

### 1. 결론 도출

coverage가 충분하면 `usable`, 핵심 원표 일부가 없으면 `usableWithGaps`, panel 자체가 없으면 `insufficientStatements`로 판정한다.

### 2. 핵심 근거 수집

`Company.show("IS"|"BS"|"CF")` 반환 DataFrame의 row 수, 기간 컬럼 수, 최신 period, 표준 metric 매핑 수를 모은다.

### 3. 메커니즘 분석

coverage audit은 모든 세부 포렌식 스킬의 선행 gate다. 이 단계에서 결손을 숨기면 매출·현금·운전자본 계산이 모두 거짓 안전 신호로 바뀐다.

### 4. 반례·한계

금융업, 지주회사, 상장 기간 짧은 회사는 IS/BS/CF가 있어도 metric coverage가 낮을 수 있다. 결손은 위험이 아니라 분석 가능성 제한으로 표시한다.

### 5. 후속 모니터링

coverage가 낮으면 `accountTraceLedger`에서 어떤 metric이 빠졌는지 확인하고, 충분하면 `revenueToCashBridge`로 넘어간다.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `dataset` | IS, BS, CF, normalizedPanel |
| `status` | ok 또는 missing |
| `rowCount` | 원표 행 수 |
| `periodCount` | 기간 컬럼 수 |
| `latestPeriod` | 최신 기간 |
| `requiredFor` | 후속 계산에서 쓰는 이유 |

## 연계 절차

1. engines.company - 대상 기업 facade에서 원표 topic을 확보한다.
2. recipes.incubator.forensics.accountTraceLedger - metric별 raw 계정 trace 확인.
3. recipes.incubator.forensics.revenueToCashBridge - coverage 충분 시 매출-현금 bridge 실행.

## 기본 검증

- IS/BS/CF 중 누락된 표가 있으면 답변에 명시한다.
- normalizedPanel의 mapped metric count가 낮으면 riskScore를 해석하지 않는다.
