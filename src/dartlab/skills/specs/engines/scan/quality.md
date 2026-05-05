---
id: "engines.scan.quality"
title: "Scan - 이익의 질"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "scan engine application skill for 이익의 질: Accrual Ratio + CF/NI 비율 — 이익이 현금 뒷받침되는지."
whenToUse:
  - "scan"
  - "quality"
  - "이익의 질"
  - "Accrual Ratio + CF/NI 비율 — 이익이 현금 뒷받침되는지"
inputs:
  - "target"
  - "period"
  - "axis or method"
outputs:
  - "result"
  - "evidence refs"
  - "limits and assumptions"
capabilityRefs:
  - "scan"
knowledgeRefs:
  - "engines.scan"
  - "engines.data.foundation"
  - "engines.analysis"
sourceRefs:
  - "dartlab://skills/engines.scan.quality"
requiredEvidence:
  - "universe"
  - "datasetAsOf"
  - "filter"
  - "formula"
  - "table"
  - "executionRef"
expectedOutputs:
  - "public call"
  - "representative return shape"
  - "verification result"
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
  - "Do not list candidates without universe and datasetAsOf."
  - "Do not answer with company names only; include a ranking/evidence table."
  - "Do not present screening output as deep analysis."
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-04'
---

## 엔진 역할

scan engine application skill for 이익의 질: Accrual Ratio + CF/NI 비율 — 이익이 현금 뒷받침되는지.

## 공개 호출 방식

```python
import dartlab
result = dartlab.scan("quality")
```

## 호출 동작

Reads financial universe prebuilt/provider data and computes candidates or rankings. Primitive axes may require a target argument, so check the guide example first.

## 대표 반환 형태

Returns a DataFrame. Core fields are stockCode/ticker, corpName/name, market/universe, latestAsOf/asOf, metric/value/score, rank, source/basis, and flags.

## 기본 실행 순서

1. target, period, and source data are fixed first.
2. Run the public call exactly as documented.
3. Check latestAsOf/date, missing values, flags, and assumptions.
4. Bind numeric claims to tableRef/valueRef/dateRef/executionRef.
5. Hand off multi-axis narrative composition to story or the parent report skill.

## 기본 검증

This skill is a public execution document. If this axis call, representative return keys, error behavior, or runtime limits change, update this file in the same change.
