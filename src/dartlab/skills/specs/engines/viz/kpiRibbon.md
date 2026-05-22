---
id: engines.viz.kpiRibbon
title: Viz - KPI Ribbon
kind: curated
scope: builtin
status: observed
category: engines
purpose: 보고서 첫 화면에 필요한 핵심 KPI 4~8개를 `kpi-ribbon` ChartSpec 으로 묶어 결론 요약과 근거 drill-back 을 동시에 제공한다.
whenToUse:
  - 보고서 KPI
  - 핵심지표 요약
  - dashboard ribbon
  - 종합 분석 첫 화면
inputs:
  - KPI items
  - value / unit / period
  - evidenceRef
outputs:
  - chartType kpi-ribbon ChartSpec
  - KPI cards
  - evidenceBinding
toolRefs:
  - EngineCall
  - RunPython
  - CompileVisual
knowledgeRefs:
  - engines.viz
  - engines.dashboard
sourceRefs:
  - dartlab://skills/engines.viz.kpiRibbon
requiredEvidence:
  - metric
  - value
  - period
  - evidenceRef
  - executionRef
  - sourceRef
expectedOutputs:
  - kpi-ribbon spec
  - KPI 요약 문단
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
    status: supported
failureModes:
  - 서로 다른 기준일의 KPI 를 한 줄에 최신값처럼 배치함
  - 단일 KPI 를 ribbon 으로 과장함
forbidden:
  - evidenceRef 없는 KPI 카드 금지
  - KPI 3개 미만 ribbon 금지
examples:
  - 매출 성장률, 영업이익률, ROE, FCF, 순차입금 KPI
linkedSkills:
  - engines.viz
  - engines.dashboard
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-13'
testUniverse:
  market: KR
  stockCodes:
    - "005930"
---

## 절차

1. 결론 문단에서 실제로 쓰일 KPI 만 고른다.
2. 각 KPI 의 기간, 단위, source, evidenceRef 를 붙인다.
3. `specKpiRibbon(items)` 로 만든다.
4. 한계나 결손 KPI 는 ribbon 에 넣지 않고 coverage note 에 남긴다.

## 공개 호출 방식

```python
from dartlab.viz.generators import specKpiRibbon

spec = specKpiRibbon(kpi_items)
```

## 호출 동작

- 입력 view 또는 rows 를 검산 가능한 ChartSpec 으로 변환한다.
- `evidenceBinding` 또는 `evidenceIds` 가 없으면 emit 하지 않는다.
- 데이터가 부족하면 값을 추정하지 않고 표, coverage note, 또는 bullet path 로 낮춘다.

## 대표 반환 형태

- `dict` ChartSpec: `chartType`, `title`, `series` 또는 `data`, `categories`, `evidenceBinding`, `meta`.
- Mermaid 계열은 diagram source 와 node/edge evidence refs 를 함께 남긴다.

## 기본 검증

- KPI 는 결론 문단 하나 이상을 직접 뒷받침해야 한다.
- KPI 사이 기간이 다르면 카드에 기간을 노출한다.
