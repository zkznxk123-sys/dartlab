---
id: screens.findUndervaluedQualityStocks
title: 저평가·수익성 종목 후보 찾기
kind: curated
scope: builtin
status: unverified
category: screens
purpose: scan과 재무 prebuild를 이용해 밸류에이션이 낮고 수익성 근거가 있는 후보 종목을 횡단면으로 찾는다.
whenToUse:
  - 스캔엔진으로 저평가 종목 찾기
  - 저평가이면서 수익성 좋은 종목
  - value quality screen
inputs:
  - universe
  - valuation metric
  - profitability metric
outputs:
  - candidate table
  - screening basis
capabilityRefs:
  - scan
  - Company.analysis
datasetRefs:
  - dart.scan.financeLite
toolRefs:
  - search_reference
  - inspect_dataset
  - run_python
  - finalize_answer
knowledgeRefs:
  - valuationPrinciples
  - financialStatementConcepts
requiredEvidence:
  - universe
  - input
  - filters
  - metric
  - formula
  - table
  - basis
  - executionRef
expectedOutputs:
  - 저평가 후보 표
  - 입력/유니버스
  - 필터
  - 계산식/지표
  - 수익성 보조 지표
  - 한계
visualGuidance:
  - 후보가 2개 이상이고 동일 metric이 있을 때만 ranking chart를 만든다.
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
      - HuggingFace dartlab-data dart/scan/finance-lite.parquet
    requiredSetup:
      - finance-lite prebuild를 브라우저 런타임에 로드한다.
    limitations:
      - full scan 축 전체가 아니라 prebuild에 포함된 지표 기준 후보만 만든다.
failureModes:
  - 낮은 PER/PBR만 보고 저평가 단정
  - 수익성 또는 재무 안정성 확인 없이 후보를 결론으로 포장
  - 후보를 bullet 나열로만 내고 valuation/profitability evidence table을 빠뜨림
forbidden:
  - 후보 종목을 매수 추천으로 단정
  - universe와 기준일 없는 ranking
  - 입력/필터/계산식/표 근거 없는 후보 발굴 답변
examples:
  - 스캔엔진으로 저평가 종목 찾아줘
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-02"
---

## 절차

- `engines.scanUsage`와 `basic.scan`으로 가능한 횡단면 축을 확인한다.
- valuation metric과 profitability metric이 같은 universe와 기준일에서 있는지 확인한다.
- `run_python`으로 후보 표를 만들고 value metric만 아니라 profitability 보조 지표를 같이 둔다.
- 최종 답변은 입력/유니버스, 필터, 계산식/지표, 결과를 명시하고 후보별 valuation/profitability evidence table을 본문에 렌더링한다.
- 낮은 valuation은 후보 조건이지 최종 투자 판단이 아니라고 한계를 남긴다.
