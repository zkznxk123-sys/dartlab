---
id: engines.scan.crossSectionStockScreen
title: Cross-section Stock Screen
category: engines
kind: curated
status: observed
purpose: 전 종목 횡단면 스크리닝 — universe filter + sort + rank.
sourceRefs:
  - dartlab://skills/engines.scan.crossSectionStockScreen
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
  - 전 종목 횡단면 스크리닝
  - universe filter + sort + rank
---

## 절차

- RuntimeDatasetCatalog에서 KRX 가격 또는 종목 데이터셋 후보를 찾는다.
- `InspectDataset`으로 종목코드, 종목명, 날짜, 가격/거래대금/등락률 컬럼을 확인한다.
- `RunPython`으로 동일 기준의 횡단면 ranking 표를 만든다. 표에는 종목 식별자, 종목명, 기준일, 비교 시작일 또는 기간, ranking metric, rank가 있어야 한다.
- ranking 또는 “찾아줘” 유형의 결과는 답변 prose보다 table ref와 필요 시 CSV artifact가 우선이다. 산출물 ref가 없으면 후보 발굴을 완료한 것으로 보지 않는다.
- 최종 답변 본문에는 입력/유니버스, 필터, 계산식/지표, 결과 섹션을 두고 markdown evidence table을 렌더링한다.
- 상위 N개 숫자 claim은 ranking table/value ref에 직접 묶고, 기준일·기간·universe·metric을 답변에 함께 밝힌다.
- 후보 표가 2개 이상이고 동일 metric이 있으면 compile_visual로 요약 차트를 만들 수 있지만, chart는 table ref 이후에만 만든다.

## 공개 호출 방식

```python
import dartlab

# 전 종목 횡단면 스크리닝
df = dartlab.scan("growth", universe="KOSPI200")
top = df.sort("rank").head(30)
print(top)
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
