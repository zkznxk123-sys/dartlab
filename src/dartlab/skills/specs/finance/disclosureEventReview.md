---
id: disclosureEventReview
title: 공시 이벤트 중요도 검토
kind: curated
scope: builtin
status: unverified
category: finance
purpose: 기업 공시 목록과 가능한 경량 본문 근거를 확인해 중요한 이벤트 후보와 한계를 구분한다.
whenToUse:
  - 최근 공시 중요한 내용
  - DART 공시 영향 또는 리스크 질문
inputs:
  - 기업명 또는 종목코드
capabilityRefs:
  - Company.disclosure
  - Company.liveFilings
  - Company.readFiling
toolRefs:
  - search_reference
  - run_python
  - finalize_answer
knowledgeRefs:
  - dartDisclosureStructure
requiredEvidence:
  - target
  - period
  - table
  - basis
expectedOutputs:
  - 중요 공시 후보
  - 판단 근거
  - 제목 기준 또는 본문 기준 한계
visualGuidance:
  - 공시 이벤트는 필요할 때 timeline/table 중심으로 설명한다.
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
      - HuggingFace dartlab-data dart/docs/{stockCode}.parquet
      - HuggingFace dartlab-data dart/report/{stockCode}.parquet
    requiredSetup:
      - await dartlab.prefetch(stockCode) 후 prefetched 공시/보고서 데이터만 사용한다.
    limitations:
      - liveFilings와 DART OpenAPI 직접 호출은 CORS 때문에 사용하지 않는다.
      - 본문 미조회 상태에서는 제목/프리빌드 기준 한계로 표시한다.
failureModes:
  - 제목 목록만 보고 영향 단정
  - sections 대량 로딩
forbidden:
  - 본문 근거 없는 영향 단정
examples:
  - 삼성전자 최근 공시 중요한 내용 찾아줘
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-02"
---

## 절차

- 공시 목록의 접수일, 제목, 유형을 확인한다.
- 가능한 경우 경량 본문 조회로 제목 기준 판단을 보강한다.
- 본문 미조회 상태에서는 제목 기준 우선순위라고 명시한다.
