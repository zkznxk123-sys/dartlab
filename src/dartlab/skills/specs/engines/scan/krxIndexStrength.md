---
id: engines.scan.krxIndexStrength
title: KRX Index Strength
category: engines
kind: curated
status: observed
purpose: KRX 지수 시계열 강도 측정 — relative strength · momentum · breadth.
sourceRefs:
  - dartlab://skills/engines.scan.krxIndexStrength
knowledgeRefs:
  - engines.scan
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: limited
  pyodide:
    status: limited
whenToUse:
  - KRX 지수 시계열 강도
  - relative strength · momentum · breadth
---

## 절차

- RuntimeDatasetCatalog에서 KRX 지수 데이터셋 후보를 찾는다.
- `InspectDataset`으로 날짜 컬럼, 지수명 컬럼, 가격/등락률 컬럼, 최신 관측일을 확인한다.
- `RunPython`으로 최신일 기준 비교 가능한 지수별 수익률 또는 등락률 표를 계산한다.
- 강세 판단은 기준일, 기간, universe, metric이 모두 있는 표를 근거로 제한한다.
- visual은 지수별 비교 표가 있을 때만 만든다.

## 공개 호출 방식

```python
import dartlab

# KRX 지수 시계열 강도 측정
strength = dartlab.scan("krxIndexStrength", lookback=252)
print(strength)
```


- `dartlab.scan()`
- `dartlab.scan("fields")`
- `dartlab.scan("ratio", universe="KR")`
- `dartlab.scan("account", account="revenue")`

## 호출 동작

- 시장/유니버스 횡단면에서 필터, 순위, peer 위치를 계산한다. 단일 종목 원자료 확인은 Company가 우선이다.
- 실행 전에 target, period/date, metric, source 또는 universe를 확인한다.
- 데이터가 없거나 runtime 제한이 있으면 값을 추정하지 않고 한계와 필요한 다음 수집 경로를 말한다.

## 대표 반환 형태

- ranking/filter DataFrame을 반환한다. 핵심 컬럼은 universe, asOf/latestAsOf, stockCode/ticker, name, metric, value, rank, basis다.
- 전체 세부 필드는 공개 docstring/capability와 동기화한다. 코드/API 변경으로 이 설명이 오래되면 skill 갱신 누락으로 본다.

## 기본 검증

- 실행 결과는 tableRef, valueRef, dateRef, executionRef 중 필요한 근거로 남긴다.
- 최종 판단의 숫자 claim은 해당 table/value ref에 직접 묶는다.
- 스킬과 실제 공개 API의 호출 방식, 대표 반환 형태, 오류/제한 동작이 다르면 같은 변경에서 스킬을 갱신한다.
