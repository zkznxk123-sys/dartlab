---
id: "engines.gather.price"
title: "Gather - Current price snapshot"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "gather engine application skill for Current price snapshot."
whenToUse:
  - "gather"
  - "price"
  - "Current price snapshot"
inputs:
  - "target"
  - "period"
  - "axis or method"
outputs:
  - "result"
  - "evidence refs"
  - "limits and assumptions"
capabilityRefs:
  - "gather"
  - "Company.gather"
knowledgeRefs:
  - "engines.gather"
  - "engines.data.foundation"
sourceRefs:
  - "dartlab://skills/engines.gather.price"
requiredEvidence:
  - "target"
  - "provider"
  - "latestAsOf"
  - "source"
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
  - "Do not expose API keys or credentials."
  - "Do not claim freshness without source/latestAsOf."
  - "Do not present raw gather output as analysis."
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-04'
---

## 엔진 역할

gather engine application skill for Current price snapshot.

## 공개 호출 방식

```python
import dartlab
g = dartlab.gather()
result = g.price("005930", market="KR")
```

## 호출 동작

Reads provider/cache/snapshot data and checks freshness, source, and API-key limits. Interpretation is handed off to analysis, macro, scan, or story.

## 대표 반환 형태

Returns a DataFrame, dict/list, snapshot object, or None. Core fields are provider, source, target, market, latestAsOf/date, metric, value, unit, and flags.

## 기본 실행 순서

1. target, period, and source data are fixed first.
2. Run the public call exactly as documented.
3. Check latestAsOf/date, missing values, flags, and assumptions.
4. Bind numeric claims to tableRef/valueRef/dateRef/executionRef.
5. Hand off multi-axis narrative composition to story or the parent report skill.

## 기본 검증

This skill is a public execution document. If this axis call, representative return keys, error behavior, or runtime limits change, update this file in the same change.
