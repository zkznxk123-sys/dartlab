---
id: crossSectionStockScreen
title: 전종목 횡단면 주가 스크리닝
kind: curated
scope: builtin
status: unverified
category: screens
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
  - metric
  - table
expectedOutputs:
  - 후보 종목 표
  - 기준일/기간/metric
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
forbidden:
  - 데이터 기준일 없이 최근이라고 말하기
  - 단일 종목만 보고 전종목 결론 내기
  - table 없이 상위 종목명만 prose로 나열하기
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
- 상위 N개 숫자 claim은 ranking table/value ref에 직접 묶고, 기준일·기간·universe·metric을 답변에 함께 밝힌다.
- 후보 표가 2개 이상이고 동일 metric이 있으면 compile_visual로 요약 차트를 만들 수 있지만, chart는 table ref 이후에만 만든다.
