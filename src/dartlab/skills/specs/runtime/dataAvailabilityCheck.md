---
id: runtime.dataAvailabilityCheck
title: 데이터 가용성 확인
kind: curated
scope: builtin
status: unverified
category: runtime
purpose: 분석 전에 dataset, Company topic, snapshot 최신성, 실행 가능 runtime을 확인한다.
whenToUse:
  - 데이터가 있는지 확인
  - dataset 확인
  - 최신 기준일 확인
  - 분석 가능한 데이터 범위 점검
inputs:
  - 분석 대상
  - 선택한 skill
outputs:
  - datasetRef
  - latestAsOf
  - availableMetrics
  - runtime limits
capabilityRefs:
  - Company.index
  - Company.topics
  - gather
  - scan
toolRefs:
  - search_reference
  - InspectDataset
  - EngineCall
  - RunPython
requiredEvidence:
  - latestAsOf
  - dataset
  - metric
  - executionRef
  - sourceRef
expectedOutputs:
  - 데이터 있음/없음 판단
  - 기준일
  - 가능한 metric 목록
  - 한계
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
    dataSources:
      - HuggingFace dartlab-data snapshot
      - browser uploaded parquet/csv
    limitations:
      - live API 최신성은 서버 또는 로컬 Python 경로에서 확인한다.
failureModes:
  - 데이터 없음과 API 미설정을 혼동
  - snapshot 기준일을 오늘로 오인
  - schema 확인 없이 컬럼명을 추측
forbidden:
  - 데이터 확인 없이 최신이라고 말하기
  - missing 값을 0으로 대체
examples:
  - 삼성전자 데이터가 있는지 확인해줘
  - 이 skill을 브라우저에서 실행할 수 있나?
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-02"
testUniverse:
  market: KR
  stockCodes:
    - "005930"
---

## 절차

- 선택한 skill의 runtimeCompatibility와 datasetRefs를 먼저 확인한다.
- runtime dataset 또는 Company topic 목록에서 대상 데이터가 있는지 확인한다.
- date column, latestAsOf, entity column, metric 후보를 기록한다.
- 데이터가 없으면 필요한 수집 또는 prefetch 경로를 한계로 남긴다.
- 최신성 claim은 snapshot 기준일 또는 live 조회 기준일이 있을 때만 작성한다.

