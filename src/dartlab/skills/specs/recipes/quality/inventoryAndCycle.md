---
id: recipes.quality.inventoryAndCycle
title: 재고·사이클 점검 (inventory + macro cycle + 회사 영향)
category: recipes
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
  - engines.macro
  - engines.company.researchStarter
  - engines.analysis
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - valueRef
  - dateRef
visualRefs:
  - "engines.viz.financialStructureCharts"
  - "engines.viz.cashflowWaterfall"
  - "engines.viz.mermaidDiagram"
visualGuidance:
  - "재무제표 구조는 engines.viz.financialStructureCharts를 사용하고 IS/BS/CF 원표와 결산기·연결 기준이 맞을 때만 emit한다."
  - "현금흐름·배당·자본배분 bridge는 engines.viz.cashflowWaterfall을 사용하고 CF 원표와 부호 convention을 검산한다."
  - "메커니즘 diagram은 engines.viz.mermaidDiagram으로 8노드 이하만 만들고 모든 edge에 문장·수치·sourceRef 근거를 둔다."

runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
    limitations:
      - browser 안에서는 macro inventory 시계열 일부 한정
forbidden:
  - 산업 재고 사이클만 보고 회사 재고 회전 단정 금지 — 회사 분기 데이터 동반.
  - ISM 재고순환 4 국면 (보충 / 축소 / 가속축적 / 강제축소) 명시 없이 사이클 단정 금지.
  - 단일 분기 재고 변동을 영구 사이클 변화로 단정 금지.
  - 매크로 수요 신호 (수출 / 글로벌 PMI) 결여 시 사이클 결론 금지.
failureModes:
  - 회사 재고 (BS) 와 산업 재고 (ISM) 단위 / scope 혼동
  - 산업 (반도체 / 화학 / 철강) 별 사이클 길이 / 진폭 차이"
  - 공급망 충격 (코로나 / 반도체 부족) 시기의 재고 신호 왜곡
  - 매출 vs 재고 회전율 의 시차 (3M / 6M) 무시
  - 재고 정의 (제품 vs 원재료 vs 재공품) 분리 누락
examples:
  - 삼성전자 재고 사이클 (반도체)
  - 화학 산업 재고 + 회사 회전
  - ISM 4 국면 + 회사 영향
  - 사이클 위치 + 매크로 수요
gap:
  primary:
    - macro
    - analysis
lastUpdated: '2026-05-13'
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

1. engines.macro — 산업 재고 지수
2. engines.company.researchStarter — 회사 진입
3. engines.analysis — 회사 회전율
4. engines.macro — 경기 사이클

## 기본 검증

- 사이클 위치 (저점/회복/확장/정점/하락) + 근거 지표.
- 재고 회전율 단위 (회) + 매출채권 회전율 (일) 명시.
- "사이클 저점" 단정 X — 시나리오 + 모니터링 트리거.
