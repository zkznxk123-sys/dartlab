---
id: engines.viz.financialStructureCharts
title: Viz - 재무제표 구조 차트 묶음
kind: curated
scope: builtin
status: observed
category: engines
purpose: 손익·재무상태·현금흐름 표를 `income-trend-matrix`, `balance-structure-trend`, `cashflow-signed-matrix` ChartSpec 으로 바꿔 재무제표 구조와 기간 변화를 설명하는 시각화 실행 스킬이다.
whenToUse:
  - 재무제표 구조 시각화
  - 손익 추이 matrix
  - 자산 부채 자본 구조
  - 현금흐름 부호 matrix
  - 이익품질 시각화
inputs:
  - IncomeTrendView 또는 BalanceStructureView 또는 CashflowSignedView
  - stockCode
  - corpName
  - periods
  - tableRef / evidenceBinding
outputs:
  - chartType income-trend-matrix ChartSpec
  - chartType balance-structure-trend ChartSpec
  - chartType cashflow-signed-matrix ChartSpec
toolRefs:
  - EngineCall
  - RunPython
  - CompileVisual
knowledgeRefs:
  - engines.viz
  - engines.analysis.earningsQuality
  - engines.analysis.assetStructure
  - engines.analysis.cashflow
sourceRefs:
  - dartlab://skills/engines.viz.financialStructureCharts
requiredEvidence:
  - finance:IS
  - finance:BS
  - finance:CF
  - periods
  - evidenceBinding
expectedOutputs:
  - 손익 추이 matrix
  - 자산·조달 구조 stack
  - 현금흐름 부호 matrix
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
    limitations:
      - 브라우저에서는 사전 구성된 view dict 또는 landing dashboard model 이 노출한 범위만 사용한다.
failureModes:
  - 서로 다른 결산기 또는 연결/별도 기준을 섞어 한 차트에 배치함
  - 결손 계정을 0 으로 채워 구조 변화처럼 보이게 함
  - 총자산과 부채+자본 정합성 검산 없이 balance-structure-trend 를 그림
forbidden:
  - finance 원표 또는 view dict 없이 임의 stack 생성 금지
  - evidenceBinding 없는 ChartSpec emit 금지
  - 단일 기간 숫자를 구조 추세 chart 로 승격 금지
examples:
  - 최근 5년 매출·영업이익·순이익 추이 matrix
  - 자산 구조와 부채+자본 구조 stack 비교
  - 영업·투자·재무현금흐름 부호 matrix
linkedSkills:
  - engines.viz
  - engines.viz.balanceStructureTrend
  - engines.analysis.earningsQuality
  - engines.analysis.cashflow
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-13'
---

## 절차

1. 원표 기준을 먼저 고정한다. 연결/별도, 연간/분기, 결산기, 통화를 섞지 않는다.
2. 손익 구조는 `specIncomeTrendMatrix(view)` 로 만들고, 기간별 매출·영업이익·순이익·마진의 같은 방향성을 검산한다.
3. 재무상태 구조는 `specBalanceStructureTrend(view)` 로 만들고, 각 기간 `자산총계 = 부채총계 + 자본총계` 정합성을 확인한다.
4. 현금흐름은 `specCashflowSignedMatrix(view)` 로 만들고, 영업CF·투자CF·재무CF의 부호와 규모를 같이 보여준다.
5. 데이터가 2개 기간 미만이면 chart 대신 원표 요약과 coverage note 로 낮춘다.

## 공개 호출 방식

```python
from dartlab.viz.generators import (
    specIncomeTrendMatrix,
    specBalanceStructureTrend,
    specCashflowSignedMatrix,
)

income_spec = specIncomeTrendMatrix(income_view)
balance_spec = specBalanceStructureTrend(balance_view)
cashflow_spec = specCashflowSignedMatrix(cashflow_view)
```

## 호출 동작

- 입력 view 또는 rows 를 검산 가능한 ChartSpec 으로 변환한다.
- `evidenceBinding` 또는 `evidenceIds` 가 없으면 emit 하지 않는다.
- 데이터가 부족하면 값을 추정하지 않고 표, coverage note, 또는 bullet path 로 낮춘다.

## 대표 반환 형태

- `dict` ChartSpec: `chartType`, `title`, `series` 또는 `data`, `categories`, `evidenceBinding`, `meta`.
- Mermaid 계열은 diagram source 와 node/edge evidence refs 를 함께 남긴다.

## 기본 검증

- 각 spec 에 `evidenceBinding.topic` 이 `IS` / `BS` / `CF` 중 실제 원표와 맞는지 확인한다.
- missing 계정은 0 으로 대체하지 않고 `warnings` 또는 answer coverage note 에 남긴다.
- 차트 해석 문단은 기간·계정·값을 하나 이상 직접 인용해야 한다.
