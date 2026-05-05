---
id: engines.scan.krxIndexStrength
title: KRX 지수 강세 분석
kind: curated
scope: builtin
status: unverified
category: engines
purpose: 런타임 KRX 지수 데이터에서 최신 관측일과 비교 기간을 확인하고 여러 지수의 상대 강세를 검토한다.
whenToUse:
  - 최근 주가지수 강세를 묻는 질문
  - 뜨는 지수, 강한 지수, 지수 랭킹 질문
inputs:
  - 분석 기준일 또는 최신 가용일
  - 비교 기간
outputs:
  - 강세 지수 후보
  - 기준일과 기간
  - 수치 표
capabilityRefs:
  - gather
datasetRefs:
  - krx.indices
toolRefs:
  - search_reference
  - inspect_dataset
  - run_python
  - compile_visual
  - finalize_answer
knowledgeRefs:
  - krxDatasetStructure
visualRefs:
  - rankingChart
requiredEvidence:
  - latestAsOf
  - universe
  - metric
  - table
expectedOutputs:
  - 강세 지수 후보
  - 기준일과 기간
  - 수치 표
  - 한계
visualGuidance:
  - 최소 2개 이상 지수의 동일 metric 비교만 chart로 만든다.
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
    dataSources:
      - HuggingFace dartlab-data krx/indices parquet
    requiredSetup:
      - HF parquet를 Pyodide FS의 /data/krx/indices에 내려받은 뒤 inspect_dataset과 run_python으로 계산한다.
    limitations:
      - KRX API 실시간 호출은 CORS 때문에 사용하지 않는다.
      - 최신성은 HF에 업로드된 parquet의 BAS_DD 기준으로만 말한다.
failureModes:
  - 최신일을 오늘로 오인
  - 단일 지수 또는 단일값 chart 생성
forbidden:
  - 기준 기간 없는 강세 단정
  - 계산 없이 원하면 계산하겠다는 답변
examples:
  - 최근 주가지수를 보고 강세 지수를 찾아봐라
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-02"
---

## 절차

- RuntimeDatasetCatalog에서 KRX 지수 데이터셋 후보를 찾는다.
- `inspect_dataset`으로 날짜 컬럼, 지수명 컬럼, 가격/등락률 컬럼, 최신 관측일을 확인한다.
- `run_python`으로 최신일 기준 비교 가능한 지수별 수익률 또는 등락률 표를 계산한다.
- 강세 판단은 기준일, 기간, universe, metric이 모두 있는 표를 근거로 제한한다.
- visual은 지수별 비교 표가 있을 때만 만든다.

## 공개 호출 방식

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


