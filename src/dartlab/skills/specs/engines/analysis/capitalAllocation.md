---
id: "engines.analysis.capitalAllocation"
title: "Analysis - 자본배분"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "analysis engine application skill for the 자본배분 axis: 번 돈을 어디에 쓰는가."
whenToUse:
  - "analysis"
  - "자본배분"
  - "번 돈을 어디에 쓰는가"
  - "자본배분"
inputs:
  - "target"
  - "period"
  - "axis or method"
outputs:
  - "result"
  - "evidence refs"
  - "limits and assumptions"
capabilityRefs:
  - "analysis"
  - "Company.analysis"
knowledgeRefs:
  - "engines.analysis"
  - "engines.company"
  - "engines.data.foundation"
sourceRefs:
  - "dartlab://skills/engines.analysis.capitalAllocation"
requiredEvidence:
  - "target"
  - "period"
  - "metric"
  - "tableRef"
  - "valueRef"
  - "dateRef"
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
  - "Do not fabricate numbers."
  - "Do not zero-fill missing values."
  - "Do not treat one axis result as a final investment conclusion."
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-04'
---

## 엔진 역할

analysis engine application skill for the 자본배분 axis: 번 돈을 어디에 쓰는가.

## 공개 호출 방식

```python
import dartlab
c = dartlab.Company("005930")
result = c.analysis("자본배분", "자본배분")
```

## 호출 동작

Reads the Company financial/disclosure/market snapshot required for the 자본배분 axis. The guide reports 7 calculation items. Missing values are represented through flags, assumptions, dataAsOf, nulls, or empty history; they are not zero-filled.

## 대표 반환 형태

Returns a dict. Check items, history, displayHints, turningPoints, dataAsOf, assumptions, flags, _summary, tableRef, valueRef, dateRef, and executionRef-style evidence fields.

## 기본 실행 순서

1. target, period, and source data are fixed first.
2. Run the public call exactly as documented.
3. Check latestAsOf/date, missing values, flags, and assumptions.
4. Bind numeric claims to tableRef/valueRef/dateRef/executionRef.
5. Hand off multi-axis narrative composition to story or the parent report skill.

## 기본 검증

This skill is a public execution document. If this axis call, representative return keys, error behavior, or runtime limits change, update this file in the same change.
