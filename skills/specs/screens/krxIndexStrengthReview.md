---
id: krxIndexStrengthReview
title: KRX 지수 강세 분석
kind: curated
scope: builtin
status: unverified
category: screens
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
