---
id: engines.recipe.industryDeepDive
title: 산업 deep-dive (산업 지도 + 섹터 매크로 + 핵심 종목)
category: engines
kind: recipe
scope: builtin
status: unverified
purpose: 단일 산업의 가치 사슬 + 매크로 영향 + 핵심 종목 3 축으로 산업 자체를 분석하는 절차. 종목 없이도 가능.
whenToUse:
  - 산업 분석
  - 업종 분석
  - 가치 사슬
  - 산업 구조
  - 산업 deep dive
  - 섹터 분석
  - 산업 지도
linkedSkills:
  - engines.industry
  - engines.macro.marketReview
  - engines.scan.profitability
  - engines.analysis.peerComparison
toolRefs:
  - engine_call
  - run_python
requiredEvidence:
  - skillRef
  - tableRef
  - dateRef
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
    limitations:
      - browser 안에서는 industry stage 단일 호출만
lastUpdated: '2026-05-06'
---

## 공개 호출 방식

```python
import dartlab

industry_map = dartlab.industry("반도체")
upstream = dartlab.industry("반도체", "upstream")
macro = dartlab.macro()
peer_scan = dartlab.scan("profitability")
```

## 호출 동작

산업 가치 사슬 (upstream → midstream → downstream) → 매크로 영향 → peer 횡단 수익성 종합. 종목 없이 산업 자체 분석.

1. industry(industry_name) — 산업 가치 사슬 지도
2. industry(industry_name, stage) — 단계별 종목 (upstream/midstream/downstream)
3. macro() — 매크로 환경 (산업 영향 변수)
4. scan("profitability") — peer 횡단 수익성

## 대표 반환 형태

- `tableRef` 4 개 (industry 지도 + stage 종목 + macro + peer scan)
- `dateRef` 1 개

## 연계 절차

1. engines.industry — 산업 가치 사슬 + stage 별 종목
2. engines.macro.marketReview — 매크로 환경
3. engines.scan.profitability — peer 횡단 수익성
4. engines.analysis.peerComparison — 핵심 종목 비교

## 기본 검증

- 가치 사슬 (upstream/midstream/downstream) 명시.
- 핵심 종목 5~10 (각 stage 별).
- 매크로 영향은 산업 elasticity (예: 반도체 → 환율 / 수요 사이클).
