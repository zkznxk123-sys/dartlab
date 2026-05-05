---
id: engines.scan.crossSectionStockScreen
title: 전종목 횡단면 주가 스크리닝
kind: curated
scope: builtin
status: unverified
category: engines
purpose: 런타임 시장 데이터에서 종목 universe와 최신 관측일을 확인한 뒤 조건에 맞는 종목 후보군을 만든다.
whenToUse:
  - 최근 많이 오른 종목을 찾는 질문
  - 전종목에서 특정 조건을 만족하는 종목 검색
inputs:
  - universe
  - 기간 또는 최신 가용일
  - ranking metric
outputs:
  - 후보 종목 표
  - 기준일/기간/metric
capabilityRefs:
  - gather
  - scan
datasetRefs:
  - krx.prices
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
  - input
  - filters
  - formula
  - metric
  - table
  - executionRef
expectedOutputs:
  - 후보 종목 표
  - 기준일/기간/metric
  - 입력/유니버스
  - 필터
  - 계산식/지표
  - 한계
visualGuidance:
  - ranking table의 상위 N개만 chart로 요약한다.
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
      - HuggingFace dartlab-data krx/prices parquet
      - HuggingFace dartlab-data dart/scan/finance-lite.parquet
    requiredSetup:
      - 가격 랭킹은 HF KRX 가격 parquet를 /data/krx/prices에 내려받아 계산한다.
      - 재무 조건형 스크리닝은 finance-lite prebuild로 제한한다.
    limitations:
      - KRX API 실시간 호출은 CORS 때문에 사용하지 않는다.
      - finance-lite에는 주요 계정만 있어 전체 scan과 동일하지 않다.
failureModes:
  - 종목명/코드 오매칭
  - 기간 없는 급등 단정
  - ranking 표를 만들었지만 artifact/table ref를 남기지 않아 서버 audit에서 산출물 누락
  - 숫자 ranking claim을 table/value ref에 직접 묶지 않아 최종 검산 실패
  - 최종 답변이 bullet 나열이고 evidence table, 입력, 필터, 계산식이 없음
forbidden:
  - 데이터 기준일 없이 최근이라고 말하기
  - 단일 종목만 보고 전종목 결론 내기
  - table 없이 상위 종목명만 prose로 나열하기
  - 입력/유니버스, 필터, 계산식/지표 없이 후보 표를 결론으로 제시하기
examples:
  - 최근 주가가 많이 오른 종목 찾아줘
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-02"
---

## 절차

- RuntimeDatasetCatalog에서 KRX 가격 또는 종목 데이터셋 후보를 찾는다.
- `inspect_dataset`으로 종목코드, 종목명, 날짜, 가격/거래대금/등락률 컬럼을 확인한다.
- `run_python`으로 동일 기준의 횡단면 ranking 표를 만든다. 표에는 종목 식별자, 종목명, 기준일, 비교 시작일 또는 기간, ranking metric, rank가 있어야 한다.
- ranking 또는 “찾아줘” 유형의 결과는 답변 prose보다 table ref와 필요 시 CSV artifact가 우선이다. 산출물 ref가 없으면 후보 발굴을 완료한 것으로 보지 않는다.
- 최종 답변 본문에는 입력/유니버스, 필터, 계산식/지표, 결과 섹션을 두고 markdown evidence table을 렌더링한다.
- 상위 N개 숫자 claim은 ranking table/value ref에 직접 묶고, 기준일·기간·universe·metric을 답변에 함께 밝힌다.
- 후보 표가 2개 이상이고 동일 metric이 있으면 compile_visual로 요약 차트를 만들 수 있지만, chart는 table ref 이후에만 만든다.

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


