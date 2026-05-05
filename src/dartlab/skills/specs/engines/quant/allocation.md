---
id: "engines.quant.allocation"
title: "Quant - 자산배분"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "quant engine application skill for 자산배분: Equal Risk Contribution (Maillard 2010) — 종목별 위험 기여도 균등 배분 (종목 리스트)."
whenToUse:
  - "quant"
  - "allocation"
  - "자산배분"
  - "포트폴리오"
  - "Equal Risk Contribution (Maillard 2010) — 종목별 위험 기여도 균등 배분 (종목 리스트)"
inputs:
  - "target"
  - "period"
  - "axis or method"
outputs:
  - "result"
  - "evidence refs"
  - "limits and assumptions"
capabilityRefs:
  - "quant"
  - "Company.quant"
knowledgeRefs:
  - "engines.quant"
  - "engines.gather"
  - "engines.analysis"
sourceRefs:
  - "dartlab://skills/engines.quant.allocation"
requiredEvidence:
  - "target"
  - "period"
  - "metric"
  - "benchmark"
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
  - "Do not guarantee performance."
  - "Do not cite returns without period, benchmark, and assumptions."
  - "Do not present a quantitative signal as causal financial analysis."
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-04'
---

## 엔진 역할

quant engine application skill for 자산배분: Equal Risk Contribution (Maillard 2010) — 종목별 위험 기여도 균등 배분 (종목 리스트).

## 공개 호출 방식

```python
import dartlab
result = dartlab.quant("allocation", "005930")
```

## 호출 동작

Runs a 포트폴리오 quantitative calculation. Confirm period, benchmark, target requirements, and for strategy/backtest axes separate rule and cost assumptions.

## 대표 반환 형태

Returns a DataFrame or dict. Core fields are target, period, priceDate/latestAsOf, benchmark, metric, value, score/signal/rank, assumptions, and flags.

## 기본 실행 순서

1. target, period, and source data are fixed first.
2. Run the public call exactly as documented.
3. Check latestAsOf/date, missing values, flags, and assumptions.
4. Bind numeric claims to tableRef/valueRef/dateRef/executionRef.
5. Hand off multi-axis narrative composition to story or the parent report skill.

## 기본 검증

This skill is a public execution document. If this axis call, representative return keys, error behavior, or runtime limits change, update this file in the same change.
