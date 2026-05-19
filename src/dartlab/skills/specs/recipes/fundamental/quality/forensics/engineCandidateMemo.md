---
id: recipes.fundamental.quality.forensics.engineCandidateMemo
title: Forensics Engine Candidate Memo
category: recipes
kind: recipe
scope: builtin
status: observed
graphTier: L1.5
cluster: incubator.forensics
purpose: 포렌식 스킬 실행 결과에서 반복 가능하고 반증 조건이 명확한 신호를 L2 엔진 후보로 정리하되, 승격 후에도 recipe 검산 경로로 계속 남기는 계약을 만든다. 트리거 — '엔진 후보 memo', '스킬에서 엔진 환류'.
whenToUse:
  - 엔진 후보 memo
  - 스킬에서 엔진 환류
  - forensics promotion candidate
  - ask 품질 기반 승격 후보
inputs:
  - forensics memo
  - selfRun results
  - ask quality observations
outputs:
  - signalId
  - recommendedEngineOwner
  - promotionGate
  - keepAsSkillAfterPromotion
capabilityRefs:
  - Company.show
toolRefs:
  - EngineCall
  - RunPython
sourceRefs:
  - dartlab://skills/recipes.fundamental.quality.forensics.engineCandidateMemo
requiredEvidence:
  - skillRef
  - target
  - tableRef
  - valueRef
  - dateRef
  - sourceRef
  - executionRef
expectedOutputs:
  - 엔진 후보 신호 목록
  - owner 후보
  - promotion gate
  - 승격 후 recipe 유지 여부
linkedSkills:
  - operation.skillDevelopmentLoop
  - recipes.fundamental.quality.forensics.deepDive
gap:
  primary:
    - synth
    - scan
falsifier:
  description: "ask 답변 품질과 3 케이스 selfRun 없이 engine candidate를 완료 상태로 표시하면 실패로 본다."
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
forbidden:
  - 단일 케이스 성공을 엔진 후보 완료로 표시하지 않는다.
  - 승격 후 recipe를 폐기한다는 가정을 두지 않는다.
failureModes:
  - recommendedEngineOwner가 추상적이라 실제 코드 위치로 이어지지 않음
  - ask 품질이 나쁜데 계산만 보고 승격 후보로 둠
examples:
  - 포렌식 신호를 엔진 후보 memo로 정리
  - ask 품질 기반 L2 환류 후보
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
    table=memo["tables"]["engineCandidateMemo"],
    values={"target": target, "candidateCount": len(memo["tables"]["engineCandidateMemo"])},
    date=memo["asOf"],
    sources=memo["sources"],
)
```

## 호출 동작

### 1. 결론 도출

signal별 `recommendedEngineOwner`, `promotionGate`, `keepAsSkillAfterPromotion`을 남긴다.

### 2. 핵심 근거 수집

forensics memo의 신호 status, falsifier 상태, selfRun 결과, ask 품질 관찰을 연결한다.

### 3. 메커니즘 분석

스킬팩은 엔진을 대체하지 않는다. 반복되는 신호를 발견하면 L2 엔진 후보로 넘기되, recipe는 원표 검산과 반증 ledger로 계속 남는다.

### 4. 반례·한계

계산이 좋아도 ask 답변이 신호를 오해하거나 반증 조건을 빼먹으면 승격하면 안 된다.

### 5. 후속 모니터링

3개 이상 target selfRun, false-positive ledger, ask answer quality P 2회가 최소 승격 gate다.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `signalId` | 후보 신호 |
| `status` | ok/watch/risk/missing |
| `recommendedEngineOwner` | 승격 후보 영역 |
| `promotionGate` | 필요한 검증 |
| `keepAsSkillAfterPromotion` | 승격 후 recipe 유지 여부 |

## 연계 절차

1. recipes.fundamental.quality.forensics.falsifierLedger - 반증 조건을 먼저 확인한다.
2. operation.skillDevelopmentLoop - selfRun/redTeam/graduate 규칙을 적용한다.
3. recipes.fundamental.quality.forensics.deepDive - ask 품질 관찰까지 포함해 재실행한다.

## 기본 검증

- 모든 candidate는 promotionGate를 가져야 한다.
- `keepAsSkillAfterPromotion`은 true여야 한다.
