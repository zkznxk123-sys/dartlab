---
id: engines.viz.cashflowWaterfall
title: Viz - Cashflow Waterfall
kind: curated
scope: builtin
status: observed
category: engines
purpose: 영업·투자·재무활동 현금흐름과 배당/차입 변화가 현금 잔고를 어떻게 설명하는지 `waterfall` ChartSpec 으로 만든다.
whenToUse:
  - 현금흐름 waterfall
  - 배당 지속성
  - FCF bridge
  - 자본배분 bridge
inputs:
  - cashflow rows
  - beginning cash / ending cash
  - OCF / Capex / Financing / Dividend
  - evidenceBinding
outputs:
  - chartType waterfall ChartSpec
  - cash bridge
  - coverage warnings
toolRefs:
  - EngineCall
  - RunPython
  - CompileVisual
knowledgeRefs:
  - engines.viz
  - engines.analysis.cashflow
  - engines.gather.dividends
sourceRefs:
  - dartlab://skills/engines.viz.cashflowWaterfall
requiredEvidence:
  - finance:CF
  - period
  - cashflow metric
  - evidenceBinding
expectedOutputs:
  - cashflow waterfall spec
  - 현금 bridge 설명
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
  - 발생주의 이익 항목과 현금흐름 항목을 같은 bridge 에 섞음
  - Capex 부호를 뒤집어 FCF 를 과대 표시함
  - 현금성자산 기초/기말 검산 없이 waterfall 을 그림
forbidden:
  - finance:CF 근거 없는 waterfall 금지
  - 단일 기간 OCF 하나로 지속성 단정 금지
examples:
  - 영업CF에서 FCF와 배당까지 bridge
  - 자사주/차입/배당 자본환원 bridge
linkedSkills:
  - engines.viz
  - engines.analysis.cashflow
  - engines.gather.dividends
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-13'
---

## 절차

1. CF 표에서 영업·투자·재무활동 현금흐름과 현금성자산 증감을 같은 기간으로 맞춘다.
2. `specCashflowWaterfall(company)` 또는 직접 waterfall ChartSpec 을 사용한다.
3. dividend 분석이면 배당 지급액과 FCF 를 같은 기간으로 맞춘다.
4. bridge 합계가 기말 현금 변화와 맞지 않으면 chart 대신 reconciliation table 을 낸다.

## 공개 호출 방식

```python
from dartlab.viz.generators import specCashflowWaterfall

spec = specCashflowWaterfall(company)
```

## 호출 동작

- 입력 view 또는 rows 를 검산 가능한 ChartSpec 으로 변환한다.
- `evidenceBinding` 또는 `evidenceIds` 가 없으면 emit 하지 않는다.
- 데이터가 부족하면 값을 추정하지 않고 표, coverage note, 또는 bullet path 로 낮춘다.

## 대표 반환 형태

- `dict` ChartSpec: `chartType`, `title`, `series` 또는 `data`, `categories`, `evidenceBinding`, `meta`.
- Mermaid 계열은 diagram source 와 node/edge evidence refs 를 함께 남긴다.

## 기본 검증

- waterfall 합계가 cash delta 또는 FCF bridge 와 맞는지 검산한다.
- 부호 convention 을 차트 제목 또는 note 에 명시한다.
