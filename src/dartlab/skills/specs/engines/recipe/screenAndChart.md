---
id: engines.recipe.screenAndChart
title: 스캔 + 차트 결합 (scan 결과 → table-backed chart)
category: engines
kind: recipe
scope: builtin
status: unverified
purpose: scan 으로 후보를 스크리닝한 뒤 그 결과를 table-backed chart 로 시각화하는 절차. UI / 보고서 출력 직전 단계. 트리거 — '스캔 후 차트', 'table-backed chart', '보고서 직전 시각화'.
whenToUse:
  - 스캔 차트
  - 후보 시각화
  - 랭킹 차트
  - 스크리닝 차트
  - scan visualization
  - 후보 chart
linkedSkills:
  - engines.scan
  - engines.viz.tableBackedChart
  - engines.scan.crossSectionStockScreen
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - artifactRef
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
    limitations:
      - browser 안에서는 chart artifact 저장 제약
lastUpdated: '2026-05-07'
---

## 공개 호출 방식

```python
import dartlab

candidates = dartlab.scan("growth")
top10 = candidates.head(10)
# table-backed chart 로 시각화 (viz 엔진)
chart = dartlab.viz.bar(top10, x="종목명", y="매출CAGR")
```

## 호출 동작

scan 결과 (~2000 종목) 에서 상위 N 추출 → table-backed chart 로 시각화 (artifact 저장).

1. scan(axis) — 전종목 스코어
2. crossSectionStockScreen — 매출 규모·기간 필터
3. 상위 10~20 추출
4. viz.tableBackedChart — chart 생성 + artifactRef 저장

## 대표 반환 형태

- `tableRef` 1 (scan + 필터 결과)
- `artifactRef` 1 (chart 파일)
- 답변 본문: chart 미리보기 + 상위 N 행 markdown table

## 연계 절차

1. engines.scan — 전종목 스코어
2. engines.scan.crossSectionStockScreen — 매출 규모·기간 필터
3. engines.viz.tableBackedChart — chart 생성

## 기본 검증

- chart 는 항상 table 뒷받침 — 단일값 chart X.
- 차트 axis label + 단위 명시.
- 상위 N 추출 기준 (CAGR / score) 명시.
