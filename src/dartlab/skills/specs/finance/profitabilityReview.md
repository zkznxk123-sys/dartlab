---
id: profitabilityReview
title: 수익성 분석
kind: curated
scope: builtin
status: unverified
category: finance
purpose: 매출, 마진, 이익의 변화를 기간·섹터 맥락과 함께 분석한다.
whenToUse:
  - 삼성전자 수익성 분석
  - 이익률과 마진 추세
  - 영업이익 개선 또는 악화 원인
inputs:
  - 기업명 또는 종목코드
outputs:
  - profitability thesis
  - 수익성 표
  - 원인과 한계
capabilityRefs:
  - Company.analysis
  - Company.show
  - scan.profitability
  - scan.quality
  - macro
datasetRefs:
  - dart.scan
  - dart.scan.finance-lite
  - edgar.finance
toolRefs:
  - search_reference
  - run_python
  - finalize_answer
knowledgeRefs:
  - financialStatementConcepts
  - dartlabCausalSixActs
requiredEvidence:
  - target
  - period
  - metric
  - table
expectedOutputs:
  - profitability thesis
  - 기간별 수익성 표
  - 업황/섹터 연결
  - 한계
visualGuidance:
  - 매출, 영업이익률, 순이익률 같은 시계열 표가 있을 때만 chart를 만든다.
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
      - HuggingFace dartlab-data dart/finance/{stockCode}.parquet
      - HuggingFace dartlab-data edgar/finance/{ticker}.parquet
      - HuggingFace dartlab-data dart/scan/finance-lite.parquet
    requiredSetup:
      - Company 재무 snapshot 또는 finance-lite prebuild를 먼저 확인한다.
    limitations:
      - live macro 보강은 서버 환경에서 수행한다.
failureModes:
  - 매출 증가만 보고 수익성 개선 단정
  - 같은 기간이 아닌 마진 비교
  - 업황 맥락 없는 이익률 판단
  - finance-lite 계정명을 확인하지 않고 고정 계정 id만 가정
  - Polars LazyFrame pivot 방식과 eager pivot 방식을 혼동해 실행 실패
  - 단일 기업 질문에서 scan prebuild만 보고 Company 원자료 또는 Company.analysis 확인을 생략
  - table ref는 만들었지만 material claim을 해당 table/value ref에 직접 묶지 않아 최종 검산 실패
forbidden:
  - 숫자 없는 수익성 판단
  - 결손값을 0으로 대체
  - 단일 종목 수익성 질문을 저평가·후보 발굴 screen으로 바꿔 답하기
examples:
  - 삼성전자 수익성 분석해줘
  - 영업이익률이 좋아졌는지 봐줘
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-02"
---

## 절차

- 단일 기업 수익성 질문은 Company 경로가 기본이다. 먼저 Company.analysis와 Company.show capability에서 수익성 관련 축과 원자료 topic을 찾는다.
- Company snapshot 또는 Company.analysis가 가능하면 그것을 1차 근거로 둔다. `dart.scan/finance-lite.parquet`는 횡단 비교·후보 발굴·Company 원자료 부재 시의 보조 근거로만 사용한다.
- 질문이 “수익성 분석”이면 저평가/후보 screen skill로 목적을 바꾸지 않는다. screen은 peer 위치나 후보 발굴이 명시될 때만 보조로 연결한다.
- finance-lite를 쓰는 경우 `stockCode`, 연결/별도, 손익계산서 구분, 기간 구분을 먼저 확인하고 매출·영업이익·순이익 계정 후보를 실제 계정명으로 좁힌다.
- Polars에서 wide table을 만들 때 lazy pivot을 가정하지 말고 collect 후 eager pivot을 사용한다. 현재 Polars는 pivot 축에 `on`을 쓰는 경로가 안전하다.
- 매출, 영업이익률, 순이익률, 현금성 보조 지표를 같은 기간 기준으로 만들고, 실행 결과는 숫자 metric이 검산 가능한 table/value ref가 되도록 남긴다.
- 최종 material claim은 기간·metric·값을 포함하되, 각 claim이 해당 table/value ref를 직접 참조하게 한다. evidence refs만 나열하고 claim refs를 비워 두면 숫자 검산을 통과하지 못한다.
- scan 또는 macro 맥락이 있으면 업황과 기업 수익성 변화를 연결한다.
- claim은 기간, metric, table 또는 value ref에 묶는다.
