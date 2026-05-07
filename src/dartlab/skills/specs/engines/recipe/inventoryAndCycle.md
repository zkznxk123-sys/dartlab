---
id: engines.recipe.inventoryAndCycle
title: 재고·사이클 점검 (inventory + macro cycle + 회사 영향)
category: engines
kind: recipe
scope: builtin
status: unverified
purpose: 산업 재고 사이클 + 회사 재고 회전 + 매크로 수요 신호 결합으로 사이클 위치를 진단하는 절차. 반도체·석유화학·철강 등에 유용. 트리거 — '재고 사이클', '회전 진단', '반도체/석유화학 사이클'.
whenToUse:
  - 재고 사이클
  - 재고 회전
  - inventory cycle
  - 산업 사이클
  - 수요 사이클
  - 재고 분석
linkedSkills:
  - engines.macro.inventory
  - engines.company.researchStarter
  - engines.analysis.efficiency
  - engines.macro.cycle
toolRefs:
  - engine_call
  - run_python
requiredEvidence:
  - skillRef
  - tableRef
  - valueRef
  - dateRef
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
    limitations:
      - browser 안에서는 macro inventory 시계열 일부 한정
lastUpdated: '2026-05-07'
---

## 공개 호출 방식

```python
import dartlab

inventory_macro = dartlab.macro("inventory")
c = dartlab.Company("005930")
efficiency = c.analysis("financial", "효율성")
cycle = dartlab.macro("cycle")
```

## 호출 동작

산업 재고 지수 + 회사 재고 회전율 + 매크로 사이클 결합. 사이클 위치 (저점/회복/확장/정점/하락) 판정.

1. macro("inventory") — 산업 재고 지수 시계열
2. 회사 진입
3. analysis("financial", "효율성") — 재고 회전율 + 매출채권 회전율
4. macro("cycle") — 경기 사이클 위치

## 대표 반환 형태

- `tableRef` 3 개 (inventory + efficiency + cycle)
- `valueRef` 4+ (재고 지수 / 재고 회전 / 매출채권 회전 / 사이클 위치)
- `dateRef` 1 개

## 연계 절차

1. engines.macro.inventory — 산업 재고 지수
2. engines.company.researchStarter — 회사 진입
3. engines.analysis.efficiency — 회사 회전율
4. engines.macro.cycle — 경기 사이클

## 기본 검증

- 사이클 위치 (저점/회복/확장/정점/하락) + 근거 지표.
- 재고 회전율 단위 (회) + 매출채권 회전율 (일) 명시.
- "사이클 저점" 단정 X — 시나리오 + 모니터링 트리거.
