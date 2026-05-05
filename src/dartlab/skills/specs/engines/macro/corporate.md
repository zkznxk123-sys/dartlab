---
id: "engines.macro.corporate"
title: "Macro - 기업집계"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "macro engine application skill for 기업집계: 전종목 이익사이클 + Ponzi비율 + 레버리지."
whenToUse:
  - "macro"
  - "corporate"
  - "기업집계"
  - "전종목 이익사이클 + Ponzi비율 + 레버리지"
inputs:
  - "target"
  - "period"
  - "axis or method"
outputs:
  - "result"
  - "evidence refs"
  - "limits and assumptions"
capabilityRefs:
  - "macro"
knowledgeRefs:
  - "engines.macro"
  - "engines.gather"
  - "engines.story"
sourceRefs:
  - "dartlab://skills/engines.macro.corporate"
requiredEvidence:
  - "market"
  - "indicator"
  - "dateRef"
  - "valueRef"
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
  - "Do not cite macro numbers without date/source."
  - "Do not use macro as a substitute for company financial analysis."
  - "Do not mix macro output as if it were an analysis internal calculation."
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-04'
---

## 엔진 역할

macro engine application skill for 기업집계: 전종목 이익사이클 + Ponzi비율 + 레버리지.

## 공개 호출 방식

```python
import dartlab
result = dartlab.macro("corporate", market="KR")
```

## 호출 동작

Reads market-level data for 제2막: 왜 여기에 있나 and computes signals, regimes, and limitations. Company-level financial interpretation belongs to analysis.

## 대표 반환 형태

Returns a dict or DataFrame-like result. Core fields are market, latestAsOf/date, indicator, value, unit, signal/regime, score, source/basis, assumptions, and flags.

## 기본 실행 순서

1. target, period, and source data are fixed first.
2. Run the public call exactly as documented.
3. Check latestAsOf/date, missing values, flags, and assumptions.
4. Bind numeric claims to tableRef/valueRef/dateRef/executionRef.
5. Hand off multi-axis narrative composition to story or the parent report skill.

## 기본 검증

This skill is a public execution document. If this axis call, representative return keys, error behavior, or runtime limits change, update this file in the same change.
